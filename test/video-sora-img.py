import argparse
import json
import os
import sys
import time
import uuid
from typing import Any, Dict, Optional, Tuple

DEFAULT_BEARER_TOKEN = "pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf"
DEFAULT_DOMAIN = "https://modelservice.jdcloud.com"

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

def _request_json(
    url: str,
    method: str,
    payload: Optional[Dict[str, Any]],
    headers: Dict[str, str],
    timeout_s: int,
) -> Tuple[int, str]:
    sys.stderr.write(f"正在 {method} 请求 URL: {url}\n")
    try:
        import requests  # type: ignore
    except Exception:
        requests = None

    if requests is not None:
        if method.upper() == "GET":
            resp = requests.get(url, headers=headers, timeout=timeout_s)
        else:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout_s)
        return int(resp.status_code), resp.text

    import urllib.error
    import urllib.request

    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        
    req = urllib.request.Request(url, data=data, method=method.upper())
    for k, v in headers.items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(getattr(resp, "status", 200)), body
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = str(e)
        return int(getattr(e, "code", 500) or 500), body
    except Exception as e:
        return 500, str(e)

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Sora-2 video task script")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN)
    parser.add_argument("--model", default="Sora-2")
    parser.add_argument("--text", default="生成一女孩跟狐狸跳舞的视频")
    parser.add_argument("--image-url", default="https://maas-task.s3.cn-north-1.jdcloud-oss.com/test-upload/shenyuede/6a158b5c5796f29aeef72ef2f2ed353a.png")
    parser.add_argument("--seconds", default="8")
    parser.add_argument("--token", default="")
    parser.add_argument("--trace-id", default="")
    parser.add_argument("--wait-before-query", type=int, default=120, help="提交后等待多少秒开始查询")
    parser.add_argument("--poll-interval", type=int, default=30, help="查询间隔秒数")
    parser.add_argument("--query-only", help="仅查询指定的任务 ID")
    
    args = parser.parse_args(argv)
    auth = _get_token(args.token)
    if not auth:
        sys.stderr.write("缺少鉴权 token。\n")
        return 2

    trace_id = str(args.trace_id or "").strip() or uuid.uuid4().hex
    headers = {
        "Content-Type": "application/json",
        "Trace-id": trace_id,
        "Authorization": auth,
    }

    task_id = args.query_only
    
    if not task_id:
        # 步骤 1: 提交任务
        submit_url = f"{args.domain.rstrip('/')}/v1/task/submit"
        payload = {
            "model": args.model,
            "content": [
                {"type": "text", "text": args.text},
                {"type": "image_url", "image_url": {"url": args.image_url}}
            ],
            "parameters": {
                "seconds": args.seconds
            }
        }
        
        status_code, body_text = _request_json(submit_url, "POST", payload, headers, 180)
        
        try:
            resp_data = json.loads(body_text)
            if 200 <= status_code < 300:
                # 兼容不同响应格式获取 task_id
                task_id = resp_data.get("result", {}).get("task_id") or resp_data.get("task_id")
                if not task_id:
                    sys.stderr.write(f"任务提交成功但未获取到 task_id: {body_text}\n")
                    return 1
                sys.stdout.write(f"任务提交成功, task_id: {task_id}\n")
            else:
                sys.stderr.write(f"任务提交失败: {body_text}\n")
                return 1
        except Exception as e:
            sys.stderr.write(f"解析响应失败: {str(e)}, 原始响应: {body_text}\n")
            return 1

        # 步骤 2: 等待指定时间
        sys.stdout.write(f"等待 {args.wait_before_query} 秒后开始查询状态...\n")
        time.sleep(args.wait_before_query)

    # 步骤 3: 轮询查询
    query_url = f"{args.domain.rstrip('/')}/v1/task/{{task_id}}"
    
    while True:
        current_query_url = query_url.replace("{task_id}", task_id)
        status_code, body_text = _request_json(current_query_url, "GET", None, headers, 60)
        
        if 200 <= status_code < 300:
            try:
                data = json.loads(body_text)
                # 状态字段可能为 task_status 或 status
                task_status = (data.get("task_status") or data.get("status") or data.get("data", {}).get("status") or "").lower()
                sys.stdout.write(f"当前任务状态: {task_status}\n")
                
                if task_status in ["success", "completed", "failed", "error"]:
                    sys.stdout.write("任务已结束，最终结果:\n")
                    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
                    break
            except Exception as e:
                sys.stderr.write(f"查询结果解析异常: {str(e)}\n")
        else:
            sys.stderr.write(f"查询请求失败 (状态码: {status_code}): {body_text}\n")
            # 失败时不立即退出，尝试下一次轮询
            
        sys.stdout.write(f"等待 {args.poll_interval} 秒后再次查询...\n")
        time.sleep(args.poll_interval)

    return 0

if __name__ == "__main__":
    sys.exit(main())
