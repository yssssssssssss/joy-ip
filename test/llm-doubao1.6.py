import argparse
import json
import os
import sys
import urllib.request


def _get_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return ""


def _post_json(url: str, api_key: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url=url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
            text = raw.decode("utf-8", errors="replace")
            return json.loads(text)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = str(e)
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def _normalize_content(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [_normalize_content(p) for p in content]
        return "\n".join([p for p in parts if p]).strip()
    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"]
        if isinstance(content.get("value"), str):
            return content["value"]
        if "content" in content:
            return _normalize_content(content.get("content"))
        if "parts" in content:
            return _normalize_content(content.get("parts"))
    return ""


def _parse_text(data: dict) -> str:
    try:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            msg = (choices[0] or {}).get("message") or {}
            text = _normalize_content(msg.get("content"))
            if text:
                return text

        candidates = data.get("candidates")
        if isinstance(candidates, list) and candidates:
            text = _normalize_content((candidates[0] or {}).get("content"))
            if text:
                return text

        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()
    except Exception:
        return ""
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default="你好，请介绍一下你自己")
    parser.add_argument("--model", default="doubao-seed-1-6-thinking-250715")
    parser.add_argument("--system", default="You are a helpful AI assistant. Please answer in Chinese.")
    parser.add_argument("--url", default=_get_env("TEXT_MODEL_API_URL", "VITE_TEXT_MODEL_API_URL") or "https://modelservice.jdcloud.com/v1/chat/completions")
    parser.add_argument("--api-key", default=_get_env("TEXT_MODEL_API_KEY", "VITE_TEXT_MODEL_API_KEY", "AI_API_KEY") or "")
    args = parser.parse_args()

    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": args.system},
            {"role": "user", "content": args.prompt},
        ],
        "stream": False,
    }

    data = _post_json(args.url, args.api_key, payload)
    text = _parse_text(data)
    if not text:
        sys.stderr.write("未能从返回值解析出文本内容。\n")
        sys.stderr.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        return 2
    sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
