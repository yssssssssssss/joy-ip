import requests
import json
import base64
import time
import os
import threading
import shutil
from pathlib import Path
# 导入2D/3D统一接口
from prompt_templates_2d import get_system_prompt, get_accessory_instruction, get_constraints
from utils.limits import limit_image

# 尝试导入带重试机制的http_client
try:
    from utils.http_client import http_post
    USE_HTTP_CLIENT = True
except ImportError:
    USE_HTTP_CLIENT = False

# API 地址与鉴权
URL = "https://modelservice.jdcloud.com/v1/images/gemini_flash/generations"
API_KEY = os.environ.get("AI_API_KEY", "")

# 在此配置本地图片路径（作为默认值，可被命令行参数覆盖）
IMG1_PATH = r"C:\Users\heyunshen\Downloads\badcase\generated_1763630969.png"
IMG2_PATH = None  # 可选第二张图片，默认不使用

# 生成结果默认保存到项目根目录下的 output/ 目录
OUTPUT_DIR = Path("output")

PROMPT_TEXT = (
    "严格保持图片1中角色的动作、表情一致性，进行品牌风格优化"
)

_JD_IMG_SERIALIZE = str(os.environ.get("JD_IMG_SERIALIZE", "0")).strip().lower() in ("1", "true", "yes")
_JD_IMG_MIN_INTERVAL_S = float(os.environ.get("JD_IMG_MIN_INTERVAL_S", "0.0"))
_JD_IMG_LOCK = threading.Lock()
_JD_IMG_LAST_AT = 0.0

def detect_mime_type(path: str) -> str:
    lower = str(path).lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".bmp"):
        return "image/bmp"
    return "image/png"


def encode_image_to_base64(image_path: str) -> str | None:
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        print(f"错误：找不到图片文件 -> {image_path}")
        return None
    except Exception as e:
        print(f"错误：读取或编码图片失败 -> {image_path}: {e}")
        return None


def base64_to_image(base64_string: str, save_path: Path) -> Path | None:
    try:
        img_bytes = base64.b64decode(base64_string)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(img_bytes)
        return save_path
    except Exception as e:
        print(f"错误：解码或保存图片失败 -> {e}")
        return None


def build_payload_two_images(prompt: str, img1_path: str, img2_path: str) -> dict | None:
    b64_img1 = encode_image_to_base64(img1_path)
    b64_img2 = encode_image_to_base64(img2_path)
    if not b64_img1 or not b64_img2:
        return None

    mime1 = detect_mime_type(img1_path)
    mime2 = detect_mime_type(img2_path)

    parts = [
        {"text": prompt},
        {"inlineData": {"mimeType": mime1, "data": b64_img1}},
        {"inlineData": {"mimeType": mime2, "data": b64_img2}},
    ]

    payload = {
        "model": "Gemini 3-Pro-Image-Preview",
        "stream": False,
        "contents": [
            {
                "role": "user",
                "parts": parts,
            }
        ],
        # 明确要求返回图片
        "generation_config": {
            "response_modalities": ["IMAGE"],
            
            },

    }
    return payload

def build_payload_one_image(prompt: str, img1_path: str) -> dict | None:
    b64_img1 = encode_image_to_base64(img1_path)
    if not b64_img1:
        return None

    mime1 = detect_mime_type(img1_path)
    parts = [
        {"text": prompt},
        {"inlineData": {"mimeType": mime1, "data": b64_img1}},
    ]

    payload = {
        "model": "Gemini 3-Pro-Image-Preview",
        "stream": False,
        "contents": [
            {
                "role": "user",
                "parts": parts,
            }
        ],
        "generation_config": {
            "response_modalities": ["IMAGE"],
        },
    }
    return payload


def extract_generated_image_base64(resp_json: dict) -> str | None:
    """从响应 JSON 中提取生成图片的 base64 数据。"""
    try:
        candidates = resp_json.get("candidates") or []
        for cand in candidates:
            content = cand.get("content") or {}
            parts = content.get("parts") or []
            for part in parts:
                inline_data = part.get("inlineData")
                if isinstance(inline_data, dict):
                    data = inline_data.get("data")
                    if isinstance(data, str) and data.strip():
                        return data
    except Exception:
        pass
    return None


def _extract_api_error(resp_json: object) -> dict | None:
    if not isinstance(resp_json, dict):
        return None
    err = resp_json.get("error")
    if not isinstance(err, dict):
        return None

    code = err.get("code")
    status = err.get("status")
    message = err.get("message")

    if isinstance(message, str):
        try:
            nested = json.loads(message)
        except Exception:
            nested = None
        if isinstance(nested, dict) and isinstance(nested.get("error"), dict):
            nerr = nested.get("error") or {}
            return {
                "code": nerr.get("code") if nerr.get("code") is not None else code,
                "status": nerr.get("status") if nerr.get("status") is not None else status,
                "message": nerr.get("message") if nerr.get("message") is not None else message,
                "raw": err,
            }

    return {"code": code, "status": status, "message": message, "raw": err}


def _should_retry_response(status_code: int, resp_json: object) -> tuple[bool, dict | None]:
    retryable_http = {429, 500, 502, 503, 504}
    err = _extract_api_error(resp_json)

    if status_code in retryable_http:
        return True, err

    if err:
        try:
            err_code = int(err.get("code")) if err.get("code") is not None else None
        except Exception:
            err_code = None

        if err_code in retryable_http:
            return True, err

        status = err.get("status")
        if isinstance(status, str) and status.strip().upper() in {"RESOURCE_EXHAUSTED"}:
            return True, err

        message = err.get("message")
        if isinstance(message, str) and "resource exhausted" in message.lower():
            return True, err

    return False, err


def generate_image_with_accessories(image_path, accessories_info, style="default", mode="3d"):
    """
    统一的配件生成接口，兼容原有的三个模块接口
    
    Args:
        image_path: 输入图片路径
        accessories_info: 配件信息（可以是服装、手拿、头戴的组合描述）
        style: prompt风格 ("default", "professional", "simple")
        mode: 模式 ("2d" 或 "3d")，决定使用哪套模板
        
    Returns:
        str | None: 生成的图片路径（格式：/output/xxx.png）；跳过时返回原图片路径；生成失败返回 None
    """
    # 检查是否应该跳过处理
    if _should_skip_processing(accessories_info):
        print(f"[banana-pro-img-jd] 配件信息缺失或包含否定词，跳过处理，沿用上一步结果：{image_path}")
        return image_path
    
    # 智能检测场景风格
    scene_style = _detect_scene_style(accessories_info)
    
    # 构建综合prompt（传递mode参数）
    prompt = _build_comprehensive_prompt(accessories_info, style, scene_style, mode)
    
    # 调试输出：显示生成的prompt
    print(f"[banana-pro-img-jd] 使用风格: {style}, 场景: {scene_style}, 模式: {mode.upper()}")
    print(f"[banana-pro-img-jd] 生成的Prompt:")
    print("=" * 50)
    print(prompt)
    print("=" * 50)
    
    # 执行图片生成
    result_path = _generate_single_image(image_path, prompt)
    return result_path if result_path else None

def _detect_scene_style(accessories_info: str) -> str:
    """
    智能检测场景风格
    """
    info_lower = accessories_info.lower()
    
    # 正式场合关键词
    formal_keywords = ['西装', '领带', '正装', '礼服', '商务', '正式']
    if any(keyword in accessories_info for keyword in formal_keywords):
        return "formal"
    
    # 运动场合关键词
    sports_keywords = ['运动', '球', '跑步', '健身', '篮球', '足球', '网球', '运动鞋', '运动服']
    if any(keyword in accessories_info for keyword in sports_keywords):
        return "sports"
    
    # 默认为休闲风格
    return "casual"

def _should_skip_processing(info: str) -> bool:
    """
    统一的跳过判定：当信息包含否定词时跳过该步骤
    """
    if info is None:
        print("[banana-pro-img-jd] skip_processing: info is None")
        return True
    text = str(info).strip()
    print(f"[banana-pro-img-jd] _should_skip_processing info={text!r}")
    if text == "":
        print("[banana-pro-img-jd] skip_processing: empty string")
        return True
    
    lower = text.lower()
    strong_skip_phrases = [
        "保持原样", "原装", "不换", "不变", "不做处理",
        "keep original", "no change", "unchanged",
    ]
    for kw in strong_skip_phrases:
        if kw in text or kw in lower:
            print(f"[banana-pro-img-jd] skip_processing: matched strong phrase {kw!r}")
            return True

    def _normalize_token(s: str) -> str:
        return str(s).strip().strip(" \t\r\n,，.。;；:：!！?？\"'“”‘’()（）[]【】{}<>《》")

    def _is_negative_value(v: str) -> bool:
        t = _normalize_token(v)
        if not t:
            return True
        tl = t.lower()
        if tl in {"none", "null", "undefined"}:
            return True
        if t in {"无", "没有", "无需", "不需要", "不穿", "不拿", "不持", "不带", "不戴", "空手"}:
            return True
        if t in {
            "无服装", "没有服装", "无衣服", "没有衣服",
            "无手持", "没有手持", "无手拿", "没有手拿",
            "无帽子", "没有帽子", "无头戴", "没有头戴",
            "无配件", "没有配件", "无物品", "没有物品",
        }:
            return True
        if "no clothes" in tl or "without clothes" in tl or "no clothing" in tl or "without clothing" in tl:
            return True
        if "no holding" in tl or "without holding" in tl or "empty hands" in tl:
            return True
        if "no hat" in tl or "without hat" in tl or "no headwear" in tl or "without headwear" in tl:
            return True
        return False

    try:
        parsed = _parse_accessories_info(text)
    except Exception:
        parsed = None

    if isinstance(parsed, dict):
        candidates = []
        for k in ("服装", "手拿", "头戴"):
            v = parsed.get(k)
            if isinstance(v, str) and v.strip():
                candidates.append(v)
        others = parsed.get("其他")
        if isinstance(others, list):
            candidates.extend([x for x in others if isinstance(x, str) and x.strip()])

        has_positive = any(not _is_negative_value(v) for v in candidates)
        if has_positive:
            return False

        if candidates:
            print("[banana-pro-img-jd] skip_processing: no positive accessory after parsing")
            return True

    fallback_negative_tokens = [
        "没有", "不穿", "不拿", "不持", "不带", "不戴", "空手",
        "无服装", "没有服装", "无衣服", "没有衣服", "无手持", "没有手持",
        "无帽子", "没有帽子", "无头戴", "没有头戴", "无配件", "没有配件", "无物品", "没有物品",
        "no clothes", "without clothes", "no clothing", "without clothing",
        "no hands", "without hands", "no holding", "without holding", "empty hands",
        "no hat", "without hat", "no headwear", "without headwear",
        "none", "null", "undefined",
    ]
    for kw in fallback_negative_tokens:
        if kw in text or kw in lower:
            print(f"[banana-pro-img-jd] skip_processing: matched negative token {kw!r}")
            return True

    return False

def _build_comprehensive_prompt(accessories_info: str, style="default", scene_style=None, mode="3d") -> str:
    """
    构建综合的prompt，整合服装、手拿、头戴信息
    
    Args:
        accessories_info: 配件信息
        style: 系统提示词风格 ("default", "professional", "simple")
        scene_style: 场景风格 ("formal", "casual", "sports")
        mode: 模式 ("2d" 或 "3d")，决定使用哪套模板
    """
    # 获取系统提示词（传递mode）
    system_prompt = get_system_prompt(style, mode=mode)
    
    # 解析配件信息
    parsed_accessories = _parse_accessories_info(accessories_info)
    
    # 构建具体的修改指令（传递mode）
    modification_instructions = _build_modification_instructions_v2(parsed_accessories, mode)
    
    # 获取约束条件（传递mode）
    constraints = get_constraints(style, scene_style, mode=mode)
    constraints_text = '\n'.join([f"- {constraint}" for constraint in constraints])
    
    # 组合最终prompt
    full_prompt = f"""{system_prompt}

【本次任务】
{modification_instructions}

【约束条件】
{constraints_text}"""
    
    return full_prompt

def _build_modification_instructions_v2(accessories: dict, mode="3d") -> str:
    """
    使用模板系统构建修改指令
    
    Args:
        accessories: 解析后的配件字典
        mode: 模式 ("2d" 或 "3d")
    """
    instructions = []
    
    # 服装处理指令
    if accessories['服装']:
        instruction = get_accessory_instruction('服装', accessories['服装'], mode=mode)
        instructions.append(instruction)
    
    # 手拿物品处理指令
    if accessories['手拿']:
        instruction = get_accessory_instruction('手拿', accessories['手拿'], mode=mode)
        instructions.append(instruction)
    
    # 头戴物品处理指令
    if accessories['头戴']:
        instruction = get_accessory_instruction('头戴', accessories['头戴'], mode=mode)
        instructions.append(instruction)
    
    # 其他配件处理
    if accessories['其他']:
        other_instruction = f"""【其他配件】
- 根据描述添加：{', '.join(accessories['其他'])}
- 确保所有配件都与角色整体风格一致
- 配件之间要相互协调，不要产生冲突"""
        instructions.append(other_instruction)
    
    return '\n\n'.join(instructions)

def _parse_accessories_info(accessories_info: str) -> dict:
    """
    解析配件信息，提取服装、手拿、头戴等具体内容
    """
    accessories = {
        '服装': None,
        '手拿': None,
        '头戴': None,
        '其他': []
    }
    
    # 按逗号分割信息
    parts = accessories_info.split('，')
    
    # 用于收集服装信息（上装+下装）
    clothing_parts = []
    
    for part in parts:
        part = part.strip()
        if '服装：' in part:
            clothing_parts.append(part.split('：', 1)[1] if '：' in part else part)
        elif '上装：' in part:
            clothing_parts.append(f"上装：{part.split('：', 1)[1]}" if '：' in part else part)
        elif '下装：' in part:
            clothing_parts.append(f"下装：{part.split('：', 1)[1]}" if '：' in part else part)
        elif '手拿：' in part or '手持：' in part:
            accessories['手拿'] = part.split('：', 1)[1] if '：' in part else part
        elif '头戴：' in part or '帽子：' in part:
            accessories['头戴'] = part.split('：', 1)[1] if '：' in part else part
        else:
            # 其他未分类的配件信息
            accessories['其他'].append(part)
    
    # 合并所有服装信息
    if clothing_parts:
        accessories['服装'] = '，'.join(clothing_parts)
    
    return accessories



def _generate_single_image(image_path: str, prompt: str) -> str:
    """
    生成单张图片的核心逻辑
    支持429错误重试
    """
    offline = str(os.environ.get("OFFLINE_MODE", "0")).strip().lower() in ("1", "true", "yes")
    if offline:
        try:
            ms = int(str(os.environ.get("OFFLINE_IMAGE_LATENCY_MS", "")).strip() or "0")
        except Exception:
            ms = 0
        if ms > 0:
            time.sleep(ms / 1000.0)
        try:
            if not image_path or not os.path.exists(image_path):
                return None
            OUTPUT_DIR.mkdir(exist_ok=True)
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            microsec = datetime.now().microsecond // 1000
            rand_suffix = int(time.time() * 1000) % 1000
            out_path = OUTPUT_DIR / f"offline_generated_{ts}_{microsec:03d}_{rand_suffix}.png"
            shutil.copyfile(image_path, str(out_path))
            return f"/output/{out_path.name}"
        except Exception as e:
            print(f"[banana-pro-img-jd] OFFLINE_MODE=1 生成模拟失败: {e}")
            return None

    payload = build_payload_one_image(prompt, image_path)
    if payload is None:
        print("构建请求失败：请检查本地图片路径是否正确，以及文件是否可读。")
        return None

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Trace-Id": "banana-pro-img-jd-unified",
    }

    max_retries = int(os.environ.get("LLM_IMAGE_MAX_RETRIES", "2"))
    retry_delay = float(os.environ.get("LLM_IMAGE_RETRY_DELAY_S", "2.0"))
    request_timeout = int(os.environ.get("LLM_IMAGE_TIMEOUT_S", "60"))
    connect_timeout = int(os.environ.get("HTTP_CONNECT_TIMEOUT_S", "10"))
    timeout = (connect_timeout, request_timeout)

    for attempt in range(max_retries):
        try:
            print(f"发送请求...{f' (重试 {attempt})' if attempt > 0 else ''}")

            if _JD_IMG_SERIALIZE:
                global _JD_IMG_LAST_AT
                with _JD_IMG_LOCK:
                    now = time.monotonic()
                    delta = now - _JD_IMG_LAST_AT
                    if delta < _JD_IMG_MIN_INTERVAL_S:
                        time.sleep(_JD_IMG_MIN_INTERVAL_S - delta)
                    _JD_IMG_LAST_AT = time.monotonic()

                    if USE_HTTP_CLIENT:
                        response = http_post(URL, json=payload, headers=headers, timeout=timeout, use_retry=False)
                    else:
                        response = requests.post(URL, headers=headers, json=payload, timeout=timeout)
            else:
                # 全局外部生图并发/速率控制（避免高并发下触发超时/429雪崩）
                with limit_image():
                    if USE_HTTP_CLIENT:
                        response = http_post(URL, json=payload, headers=headers, timeout=timeout, use_retry=False)
                    else:
                        response = requests.post(URL, headers=headers, json=payload, timeout=timeout)
            
            print("HTTP", response.status_code)

            # 优先解析为 JSON，提取 base64 图片
            try:
                resp_json = response.json()
            except Exception:
                print("响应不是合法 JSON：")
                print(response.text)
                return None

            should_retry, err = _should_retry_response(response.status_code, resp_json)
            if should_retry:
                if attempt < max_retries - 1:
                    import random

                    retry_after = response.headers.get("Retry-After")
                    try:
                        retry_after_s = int(retry_after) if retry_after is not None else None
                    except Exception:
                        retry_after_s = None

                    wait_time = min(30, retry_delay * (2 ** attempt))
                    if retry_after_s is not None:
                        wait_time = max(wait_time, retry_after_s)
                    wait_time += random.uniform(0, min(1.0, wait_time * 0.2))

                    detail = ""
                    if err and err.get("message"):
                        detail = f"（{str(err.get('message'))[:200]}）"
                    print(f"遇到可重试错误，等待 {wait_time:.1f} 秒后重试...{detail}")
                    time.sleep(wait_time)
                    continue
                else:
                    if err:
                        print("可重试错误：已达最大重试次数")
                        print(json.dumps({"error": err, "requestId": resp_json.get("requestId")}, ensure_ascii=False, indent=2))
                    else:
                        print("可重试错误：已达最大重试次数")
                    return None

            if response.status_code != 200:
                err = _extract_api_error(resp_json)
                if err:
                    print("API 返回错误：")
                    print(json.dumps({"error": err, "requestId": resp_json.get("requestId")}, ensure_ascii=False, indent=2))
                else:
                    print("API 返回非 200 响应：")
                    print(json.dumps(resp_json, ensure_ascii=False, indent=2))
                return None

            b64 = extract_generated_image_base64(resp_json)
            if not b64:
                err = _extract_api_error(resp_json)
                if err:
                    print("API 返回错误：")
                    print(json.dumps({"error": err, "requestId": resp_json.get("requestId")}, ensure_ascii=False, indent=2))
                else:
                    print("未在响应中找到生成图片的 base64 数据：")
                    print(json.dumps(resp_json, ensure_ascii=False, indent=2))
                return None

            # 保存到 output 目录
            OUTPUT_DIR.mkdir(exist_ok=True)
            from datetime import datetime
            import random
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 添加微秒和随机数避免并发时文件名冲突
            microsec = datetime.now().microsecond // 1000  # 毫秒级精度
            rand_suffix = random.randint(100, 999)
            out_path = OUTPUT_DIR / f"generated_{ts}_{microsec:03d}_{rand_suffix}.png"
            saved = base64_to_image(b64, out_path)
            if saved:
                print(f"生成图片已保存：{saved}")
                return f"/output/{out_path.name}"
            else:
                print("保存图片失败。")
                return None

        except requests.exceptions.RequestException as req_err:
            print(f"请求错误：{req_err}")
            if hasattr(req_err, "response") and req_err.response is not None:
                print("错误响应：", req_err.response.text)
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                return None
        except Exception as e:
            print(f"运行异常：{e}")
            return None
    
    return None

def main():
    # 支持命令行参数：
    # python banana-pro-img-jd.py <IMG1_PATH> <keyword可选> [IMG2_PATH可选]
    import sys
    img1 = IMG1_PATH
    keyword = None
    img2 = IMG2_PATH
    if len(sys.argv) >= 2:
        img1 = sys.argv[1]
    if len(sys.argv) >= 3:
        keyword = sys.argv[2]
    if len(sys.argv) >= 4:
        img2 = sys.argv[3]

    prompt = (keyword or PROMPT_TEXT).strip()

    if img2:
        payload = build_payload_two_images(prompt, img1, img2)
    else:
        payload = build_payload_one_image(prompt, img1)

    if payload is None:
        print("构建请求失败：请检查本地图片路径是否正确，以及文件是否可读。")
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Trace-Id": "banana-pro-img-jd-local",
    }

    try:
        print("发送请求...")
        response = requests.post(URL, headers=headers, json=payload, timeout=90)  # 90秒超时
        print("HTTP", response.status_code)

        # 优先解析为 JSON，提取 base64 图片
        try:
            resp_json = response.json()
        except Exception:
            print("响应不是合法 JSON：")
            print(response.text)
            return

        b64 = extract_generated_image_base64(resp_json)
        if not b64:
            print("未在响应中找到生成图片的 base64 数据：")
            print(json.dumps(resp_json, ensure_ascii=False, indent=2))
            return

        # 保存到 output 目录
        OUTPUT_DIR.mkdir(exist_ok=True)
        from datetime import datetime
        import random
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 添加微秒和随机数避免并发时文件名冲突
        microsec = datetime.now().microsecond // 1000  # 毫秒级精度
        rand_suffix = random.randint(100, 999)
        out_path = OUTPUT_DIR / f"generated_{ts}_{microsec:03d}_{rand_suffix}.png"
        saved = base64_to_image(b64, out_path)
        if saved:
            # 额外输出 /output 路径，便于前端静态代理识别
            print(f"生成图片已保存：{saved}")
            print(f"/output/{out_path.name}")
        else:
            print("保存图片失败。")

    except requests.exceptions.RequestException as req_err:
        print(f"请求错误：{req_err}")
        if hasattr(req_err, "response") and req_err.response is not None:
            print("错误响应：", req_err.response.text)
    except Exception as e:
        print(f"运行异常：{e}")


if __name__ == "__main__":
    main()
