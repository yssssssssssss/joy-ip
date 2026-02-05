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
    """获取鉴权 Token，优先级：命令行参数 > 环境变量 > 默认值"""
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

def _request_json(url: str, method: str, payload: Optional[Dict[str, Any]], headers: Dict[str, str], timeout_s: int) -> Tuple[int, str]:
    """发送 HTTP 请求并返回状态码和响应内容"""
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

    # 备选：使用内置 urllib
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
    """从响应对象中提取任务状态"""
    if not isinstance(obj, dict):
        return ""
    
    candidates = [
        obj.get("status"),
        obj.get("task_status"),
        obj.get("state"),
    ]
    
    # 检查嵌套的 result 字段
    result = obj.get("result")
    if isinstance(result, dict):
        candidates.extend([
            result.get("status"),
            result.get("task_status"),
            result.get("state"),
        ])
    
    for v in candidates:
        if v is not None:
            s = str(v).strip().lower()
            if s:
                return s
    return ""

def main():
    parser = argparse.ArgumentParser(description="Doubao-seedance 视频生成 (首尾帧模式) 与状态查询脚本")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN, help="API 域名 (默认: https://modelservice.jdcloud.com)")
    parser.add_argument("--token", default="", help="Authorization Bearer Token")
    parser.add_argument("--wait-initial", type=int, default=120, help="提交任务后初始等待时间（秒，默认: 120）")
    parser.add_argument("--interval", type=int, default=30, help="轮询间隔（秒，默认: 30）")
    args = parser.parse_args()

    auth = _get_token(args.token)
    if not auth:
        sys.stderr.write("错误: 缺少鉴权 token。请设置环境变量 JD_MODEL_SERVICE_TOKEN 或使用 --token 参数。\n")
        return 1

    headers = {
        "Content-Type": "application/json",
        "Trace-id": uuid.uuid4().hex,
        "Authorization": auth,
    }

    # 1. 提交任务
    submit_url = f"{args.domain.rstrip('/')}/v1/task/submit"
    payload = {
        "model": "Doubao-Seedance-1.5-pro",
        "content": [
             {
                "type": "text",
                "text": "图中女孩对着镜头说“茄子”，360度环绕运镜"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/seepro_first_frame.jpeg"
                },
                "role": "first_frame"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/seepro_last_frame.jpeg"
                },
                "role": "last_frame"
            }
        ],
        "parameters": {
            "ratio": "1:1",
            "duration": 5,
            "watermark": False
        }
    }

    sys.stdout.write(f"正在向 {submit_url} 提交 Doubao (首尾帧) 视频生成任务...\n")
    status_code, response_text = _request_json(submit_url, "POST", payload, headers, 60)
    
    if not (200 <= status_code < 300):
        sys.stderr.write(f"任务提交失败，状态码: {status_code}, 响应: {response_text}\n")
        return 1

    try:
        response_data = json.loads(response_text)
        # 获取 task_id
        task_id = response_data.get("result", {}).get("task_id") or response_data.get("task_id")
        if not task_id:
            sys.stderr.write(f"未能从响应中获取 task_id: {response_text}\n")
            return 1
    except Exception as e:
        sys.stderr.write(f"解析响应失败: {str(e)}\n")
        return 1

    sys.stdout.write(f"任务提交成功，Task ID: {task_id}\n")

    # 2. 初始等待
    sys.stdout.write(f"按照要求，等待 {args.wait_initial} 秒后开始查询状态...\n")
    time.sleep(args.wait_initial)

    # 3. 轮询状态
    query_url = f"{args.domain.rstrip('/')}/v1/task/{task_id}"
    sys.stdout.write(f"开始轮询任务状态，每 {args.interval} 秒一次...\n")
    
    start_time = time.time()
    while True:
        status_code, response_text = _request_json(query_url, "GET", None, headers, 60)
        
        elapsed = int(time.time() - start_time)
        
        if not (200 <= status_code < 300):
            sys.stderr.write(f"[{elapsed}s] 查询状态请求失败，状态码: {status_code}\n")
        else:
            try:
                response_data = json.loads(response_text)
                task_status = _extract_task_status(response_data)
                sys.stdout.write(f"[{elapsed}s] 当前任务状态: {task_status}\n")
                
                if task_status in ["completed", "success", "succeeded"]:
                    sys.stdout.write("任务执行成功！\n")
                    sys.stdout.write(json.dumps(response_data, ensure_ascii=False, indent=2) + "\n")
                    break
                elif task_status in ["failed", "error", "fail"]:
                    sys.stderr.write("任务执行失败。\n")
                    sys.stdout.write(json.dumps(response_data, ensure_ascii=False, indent=2) + "\n")
                    break
            except Exception as e:
                sys.stderr.write(f"[{elapsed}s] 解析状态响应失败: {str(e)}\n")
        
        time.sleep(args.interval)

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.stdout.write("\n用户中断执行。\n")
        sys.exit(0)
