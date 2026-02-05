import argparse
import json
import os
import sys
import time
import uuid
from typing import Any, Dict, Optional, Tuple

# 默认配置
DEFAULT_DOMAIN = "https://modelservice.jdcloud.com"
DEFAULT_BEARER_TOKEN = "pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf"

def _get_token(cli_token: Optional[str]) -> str:
    token = (
        cli_token
        or os.environ.get("JD_MODEL_SERVICE_TOKEN")
        or os.environ.get("MODEL_SERVICE_BEARER_TOKEN")
        or DEFAULT_BEARER_TOKEN
        or ""
    ).strip()
    if not token:
        return ""
    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"

def _build_payload(model: str, text: str, first_frame_url: str, last_frame_url: str, duration: int, mode: str) -> Dict[str, Any]:
    content = [{"type": "text", "text": text}]
    if first_frame_url:
        content.append({"type": "image_url", "role": "first_frame", "image_url": {"url": first_frame_url}})
    if last_frame_url:
        content.append({"type": "image_url", "role": "last_frame", "image_url": {"url": last_frame_url}})
    return {
        "model": model,
        "content": content,
        "parameters": {"mode": mode, "duration": str(int(duration))},
    }

def _request_json(url: str, method: str, payload: Optional[Dict[str, Any]], headers: Dict[str, str], timeout_s: int) -> Tuple[int, str]:
    try:
        import requests  # type: ignore
    except ImportError:
        requests = None

    if requests is not None:
        try:
            if method.upper() == "GET":
                resp = requests.get(url, headers=headers, timeout=timeout_s)
            else:
                resp = requests.post(url, json=payload, headers=headers, timeout=timeout_s)
            return int(resp.status_code), resp.text
        except Exception as e:
            return 500, str(e)

    import urllib.request
    import urllib.error
    
    req = urllib.request.Request(url, method=method.upper())
    for k, v in headers.items():
        req.add_header(k, v)
    
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(getattr(resp, "status", 200)), body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 500, str(e)

def _extract_task_status(obj: Any) -> str:
    if not isinstance(obj, dict):
        return ""
    candidates = [obj.get("status"), obj.get("task_status"), obj.get("state")]
    data = obj.get("data")
    if isinstance(data, dict):
        candidates.extend([data.get("status"), data.get("task_status"), data.get("state")])
        result = data.get("result")
        if isinstance(result, dict):
            candidates.extend([result.get("status"), result.get("task_status"), result.get("state")])
    
    for v in candidates:
        if v is not None:
            s = str(v).strip().lower()
            if s: return s
    return ""

def main():
    parser = argparse.ArgumentParser(description="Kling 首尾帧视频生成与状态查询脚本")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN)
    parser.add_argument("--model", default="Kling-V2-5-Turbo")
    parser.add_argument("--text", default="镜头转起来")
    parser.add_argument("--first-frame-url", default="https://maas-task.s3.cn-north-1.jdcloud-oss.com/test-upload/shenyuede/18488982a9ac47af8feddfc85b8ce514.png")
    parser.add_argument("--last-frame-url", default="https://syd-maas.s3.cn-north-1.jdcloud-oss.com/Wan_%E6%96%87%E7%94%9F%E5%9B%BE_%E7%94%9F%E6%88%90%E4%B8%80%E4%B8%AA%E7%81%AB%E9%94%85%E5%9B%BE%E7%89%87%EF%BC%8C%E5%9B%BE%E7%89%87%E5%B7%A6%E8%BE%B9%E4%BA%8C%E5%88%86%E4%B9%8B%E4%B8%80%E7%95%99%E7%A9%BA%E7%99%BD%EF%BC%8C%E4%B8%8D%E8%A6%81%E6%9C%89%E5%86%85%E5%AE%B9.png?AWSAccessKeyId=JDC_A275CA396CE7EF3C6C96985E32A6&Expires=1796882441&Signature=OKyvJnq%2BFHmI71Ay8JQKf%2FZAra0%3D")
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--mode", default="pro")
    parser.add_argument("--token", default="")
    parser.add_argument("--task-id", default="", help="已有任务ID，若提供则跳过提交直接查询")
    parser.add_argument("--wait-initial", type=int, default=120)
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--no-wait", action="store_true", help="跳过初始等待时间")
    args = parser.parse_args()

    auth = _get_token(args.token)
    headers = {
        "Content-Type": "application/json",
        "Trace-id": uuid.uuid4().hex,
        "Authorization": auth,
    }

    task_id = args.task_id
    if not task_id:
        # 1. 提交
        submit_url = f"{args.domain.rstrip('/')}/v1/task/submit"
        payload = _build_payload(args.model, args.text, args.first_frame_url, args.last_frame_url, args.duration, args.mode)
        
        sys.stdout.write(f"正在提交任务...\n")
        status_code, body = _request_json(submit_url, "POST", payload, headers, 60)
        
        if not (200 <= status_code < 300):
            sys.stderr.write(f"提交失败: {body}\n")
            return 1

        task_id = json.loads(body).get("result", {}).get("task_id")
        if not task_id:
            sys.stderr.write(f"未获取到 Task ID: {body}\n")
            return 1

        sys.stdout.write(f"任务提交成功: {task_id}\n")
        
        if not args.no_wait:
            sys.stdout.write(f"等待 {args.wait_initial} 秒后开始轮询...\n")
            time.sleep(args.wait_initial)
    else:
        sys.stdout.write(f"使用提供的 Task ID 进行查询: {task_id}\n")
        if not args.no_wait:
            sys.stdout.write(f"等待 {args.wait_initial} 秒后开始轮询...\n")
            time.sleep(args.wait_initial)

    # 2. 轮询
    query_url = f"{args.domain.rstrip('/')}/v1/task/{task_id}"
    start_time = time.time()
    while True:
        status_code, body = _request_json(query_url, "GET", None, headers, 60)
        elapsed = int(time.time() - start_time)
        
        if 200 <= status_code < 300:
            data = json.loads(body)
            status = _extract_task_status(data)
            sys.stdout.write(f"[{elapsed}s] 状态: {status}\n")
            if status in ["completed", "success", "succeeded", "failed", "error"]:
                sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
                break
        else:
            sys.stderr.write(f"[{elapsed}s] 查询失败: {status_code}\n")
            
        time.sleep(args.interval)
    return 0

if __name__ == "__main__":
    main()
