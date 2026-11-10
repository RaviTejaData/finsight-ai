import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
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
            })
    return out


def _client(p):
    if p["name"] not in _clients:
        _clients[p["name"]] = OpenAI(
            api_key=p["key"], base_url=p["base_url"], timeout=60, max_retries=2
        )
    return _clients[p["name"]]


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
            return {
                "content": msg.content,
                "tool_calls": msg.tool_calls,
                "provider": p["name"],
                "model": p["model"],
                "latency_s": round(time.time() - start, 2),
                "input_tokens": resp.usage.prompt_tokens,
                "output_tokens": resp.usage.completion_tokens,
            }
        except Exception as e:
            errors.append(f"{p['name']}: {e}")
    raise RuntimeError("All LLM providers failed: " + " | ".join(errors))


if __name__ == "__main__":
    result = chat([{"role": "user",
                    "content": "In one sentence, what is a 10-K filing?"}])
    for k, v in result.items():
        print(f"{k:>14}: {v}")
