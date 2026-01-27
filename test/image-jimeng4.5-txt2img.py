import argparse
import base64
import json
import os
import pathlib
import re
import sys
import urllib.request


def _get_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return ""


def _guess_image_mime(path: str) -> str:
    ext = pathlib.Path(path).suffix.lower().lstrip(".")
    if ext in ("jpg", "jpeg"):
        return "image/jpeg"
    if ext == "webp":
        return "image/webp"
    if ext == "gif":
        return "image/gif"
    return "image/png"


def _to_data_url_from_path(path: str) -> str:
    p = pathlib.Path(path)
    data = p.read_bytes()
    mime = _guess_image_mime(str(p))
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _normalize_image_value(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    if v.startswith("http://") or v.startswith("https://"):
        return v
    if v.lower().startswith("data:image/"):
        return v
    if pathlib.Path(v).exists():
        return _to_data_url_from_path(v)
    return f"data:image/png;base64,{v}"


def _post_json(url: str, api_key: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url=url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "*/*")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
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


def _ensure_data_url(value: str, mime: str = "image/png") -> str:
    v = (value or "").strip()
    if not v:
        return ""
    if v.startswith("data:") or v.startswith("http://") or v.startswith("https://"):
        return v
    return f"data:{mime};base64,{v}"


def _extract_first_image(data: dict) -> str:
    if isinstance(data.get("data"), list) and data["data"]:
        item = data["data"][0] or {}
        if isinstance(item, dict):
            for key in ("url", "b64_json", "image", "base64", "b64", "data"):
                v = item.get(key)
                if isinstance(v, str) and v.strip():
                    return _ensure_data_url(v.strip(), "image/png")
    if isinstance(data, str) and data.strip():
        return _ensure_data_url(data.strip(), "image/png")
    return ""


def _save_image(value: str, out_path: str) -> None:
    v = (value or "").strip()
    if not v:
        raise RuntimeError("empty image value")
    if v.startswith("http://") or v.startswith("https://"):
        with urllib.request.urlopen(v, timeout=180) as resp:
            pathlib.Path(out_path).write_bytes(resp.read())
        return
    if v.startswith("data:"):
        m = re.match(r"^data:([^;]+);base64,(.*)$", v, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            raise RuntimeError("invalid data url")
        b64 = m.group(2)
        pathlib.Path(out_path).write_bytes(base64.b64decode(b64))
        return
    pathlib.Path(out_path).write_bytes(base64.b64decode(v))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default="一只可爱的猫")
    parser.add_argument("--model", default="doubao-seedream-4-5-251128")
    parser.add_argument("--url", default=_get_env("JIMENG_IMAGE_API_URL", "VITE_GEMINI_IMAGE_API_URL") or "https://modelservice.jdcloud.com/v1/imageEdit/generations")
    parser.add_argument("--api-key", default=_get_env("GEMINI_API_KEY", "VITE_GEMINI_API_KEY", "DOUBAO_IMAGE_API_KEY") or "")
    parser.add_argument("--image", default="")
    parser.add_argument("--out", default="doubao_output.png")
    args = parser.parse_args()

    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "size": "2K",
        "sequential_image_generation": "disabled",
        "response_format": "url",
        "watermark": True,
    }

    if args.image:
        payload["image"] = _normalize_image_value(args.image)

    data = _post_json(args.url, args.api_key, payload)
    image_value = _extract_first_image(data)
    if not image_value:
        sys.stderr.write("未能从返回值解析出图片字段。\n")
        sys.stderr.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        return 2
    _save_image(image_value, args.out)
    sys.stdout.write(f"已保存: {args.out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
