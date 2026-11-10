import os
import time
import psycopg
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv(
    "DATABASE_URL", "postgresql://finsight:finsight@localhost:5433/finsight"
)
_clients = {}


def _providers():
    out = []
    for prefix in ("LLM", "FALLBACK_LLM"):
        key = os.getenv(f"{prefix}_API_KEY")
        if key:
            out.append({
                "name": prefix.lower(),
                "key": key,
                "base_url": os.getenv(f"{prefix}_BASE_URL"),
                "model": os.getenv(f"{prefix}_MODEL"),
                "price_in": float(os.getenv(f"{prefix}_PRICE_IN", "0")),
                "price_out": float(os.getenv(f"{prefix}_PRICE_OUT", "0")),
            })
    return out


def _client(p):
    if p["name"] not in _clients:
        _clients[p["name"]] = OpenAI(
            api_key=p["key"], base_url=p["base_url"], timeout=60, max_retries=2
        )
    return _clients[p["name"]]


def _log(p, latency, tin=0, tout=0, error=None):
    cost = (tin * p["price_in"] + tout * p["price_out"]) / 1_000_000
    try:
        with psycopg.connect(DB_URL) as conn:
            conn.execute(
                """INSERT INTO llm_calls (provider, model, input_tokens,
                   output_tokens, cost_usd, latency_s, success, error)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (p["name"], p["model"], tin, tout, cost, latency,
                 error is None, error),
            )
    except Exception as e:
        print("LLM call log failed:", e)
    return round(cost, 6)


def chat(messages, tools=None, temperature=0.0):
    errors = []
    for p in _providers():
        start = time.time()
        try:
            kwargs = {"model": p["model"], "messages": messages,
                      "temperature": temperature}
            if tools:
                kwargs["tools"] = tools
            resp = _client(p).chat.completions.create(**kwargs)
            msg = resp.choices[0].message
            latency = round(time.time() - start, 2)
            tin, tout = resp.usage.prompt_tokens, resp.usage.completion_tokens
            return {
                "content": msg.content,
                "tool_calls": msg.tool_calls,
                "provider": p["name"],
                "model": p["model"],
                "latency_s": latency,
                "input_tokens": tin,
                "output_tokens": tout,
                "cost_usd": _log(p, latency, tin, tout),
            }
        except Exception as e:
            _log(p, round(time.time() - start, 2), error=str(e)[:500])
            errors.append(f"{p['name']}: {e}")
    raise RuntimeError("All LLM providers failed: " + " | ".join(errors))


if __name__ == "__main__":
    result = chat([{"role": "user",
                    "content": "In one sentence, what is a 10-K filing?"}])
    for k, v in result.items():
        print(f"{k:>14}: {v}")
