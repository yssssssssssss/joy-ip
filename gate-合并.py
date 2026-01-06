import os
import json
import base64
import requests
import re
from typing import Optional, List, Dict

# ==========================
# 配置与模型列表
# ==========================

# 统一的图片与提示
CODE_IMAGE_PATH = r"C:\Users\heyunshen\Downloads\test2.png"
# PROMPT_TEXT = "我需要你分析图片中的角色，分析她的左胳膊和左手在做什么，她的右胳膊和右手在做什么，她胸前是否还有胳膊和手，胸前的胳膊和手是否会造成误会，让人觉得有三只胳膊或者手，简洁回答结论"
PROMPT_TEXT = """
        你是一个严格自信的卡通形象分析师，你的任务是分析图片中的卡通形象是否异常，按照一下标准严格检查：

        1、先详细描述这张图片中的卡通角色，包括她的头部、身体、四肢、手、脚等。

        2、图片中的卡通形象有异常吗，例如缺少或者多出四肢、缺少或者多出五官等。如果正常，请回答True，如果不正常，请回答False，简单回复；

        3、图片中的卡通角色有正确的拿着物品吗，如果正确，则则图片为True，如果不正确，则该图片为False，简单回答；

        4、、结合角色的头部大小和偏向，请判断角色的帽子是否正确佩戴，是否存在带歪、过大、过小等情况。如果正确，则该图片为True，如果不正确，则该图片为False，简单回答； 
     
               """

# 网关（OpenAI 客户端）模型列表（来自 local-gate-网关.py）
GATEWAY_MODELS = [
    "Doubao-1.5-vision-pro-32k",
    # "gpt-4o-0806",
    # "anthropic.claude-sonnet-4-20250514-v1:0",
    # "anthropic.claude-opus-4-20250514-v1:0"
]

# JDCloud 模型列表（来自 local-gate-joybuild.py）
JOYBUILD_MODELS = [
    # "doubao-seed-1.6-250615",
    # "Gemini-2.5-pro",
    # "gpt-5",
    "Claude-sonnet-4"    
    ]

# JD Cloud AI API 配置
from utils.ai_client import OpenAICompatibleClient
from config import get_config

config = get_config()
client = OpenAICompatibleClient(
    api_url=config.AI_API_URL,
    api_key=config.AI_API_KEY
)

# JDCloud HTTP API 配置（与 local-gate-joybuild.py 保持一致）
JDCLOUD_API_URL = "https://modelservice.jdcloud.com/v1/chat/completions"
JDCLOUD_BEARER = "pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf"
JDCLOUD_HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Authorization": f"Bearer {JDCLOUD_BEARER}",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
}


# ==========================
# 工具函数
# ==========================

def image_file_to_base64(image_path: str) -> Optional[str]:
    """读取本地图片为Base64字符串。"""
    try:
        if not os.path.isfile(image_path):
            print(f"图片文件不存在: {image_path}")
            return None
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"读取或转换本地图片失败: {e}")
        return None


def detect_mime(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if ext in [".png"]:
        return "image/png"
    if ext in [".webp"]:
        return "image/webp"
    return "image/png"


def _detect_mime_and_kind(path: str):
    """根据文件扩展名返回 MIME 类型和内容类型键（image_url 或 audio_url）。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in [".png"]:
        return "image/png", "image_url"
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg", "image_url"
    if ext in [".webp"]:
        return "image/webp", "image_url"
    if ext in [".wav"]:
        return "audio/wav", "audio_url"
    if ext in [".mp3"]:
        return "audio/mpeg", "audio_url"
    if ext in [".m4a"]:
        return "audio/mp4", "audio_url"
    if ext in [".flac"]:
        return "audio/flac", "audio_url"
    if ext in [".ogg"]:
        return "audio/ogg", "audio_url"
    return "image/png", "image_url"


def _collect_text_fields(obj, allowed_keys=("text", "output_text")) -> List[str]:
    """递归收集对象中所有允许键的字符串值（默认 'text' 与 'output_text'）。"""
    texts = []
    try:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in allowed_keys and isinstance(v, str):
                    texts.append(v)
                else:
                    texts.extend(_collect_text_fields(v, allowed_keys))
        elif isinstance(obj, list):
            for it in obj:
                texts.extend(_collect_text_fields(it, allowed_keys))
    except Exception:
        pass
    return texts

def extract_text_from_response(resp_json: dict, model_name: Optional[str] = None) -> Optional[str]:
    """兼容解析 JDCloud / OpenAI / Gemini 风格响应中的文本内容。
    - OpenAI 兼容：`choices[0].message.content`
    - Gemini：优先 `candidates[0].content.parts[].text`，若缺失，则递归收集 'text' 字段作为回退（不拼接非文本内容）
    - 兜底：`output_text`
    """
    try:
        is_gemini = isinstance(model_name, str) and "gemini" in model_name.lower()

        # OpenAI/兼容风格：choices -> message -> content
        if isinstance(resp_json, dict) and "choices" in resp_json:
            choices = resp_json.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                content = msg.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    pieces = []
                    for item in content:
                        if isinstance(item, str):
                            pieces.append(item)
                        elif isinstance(item, dict):
                            t = item.get("text")
                            if isinstance(t, str):
                                pieces.append(t)
                            ot = item.get("output_text")
                            if isinstance(ot, str):
                                pieces.append(ot)
                    if pieces:
                        return "\n".join(pieces)

        # Gemini 风格：仅提取 parts[].text
        if isinstance(resp_json, dict) and "candidates" in resp_json:
            candidates = resp_json.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                texts = []
                for part in parts:
                    if isinstance(part, dict):
                        t = part.get("text")
                        if isinstance(t, str):
                            texts.append(t)
                if texts:
                    return "\n".join(texts)
                # 若为Gemini且未取到text，回退递归收集 'text' 字段
                if is_gemini:
                    collected = _collect_text_fields(content, allowed_keys=("text",))
                    if collected:
                        return "\n".join([t for t in collected if isinstance(t, str) and t.strip()])

        # 兜底：常见的顶层文本字段
        if isinstance(resp_json.get("output_text"), str):
            return resp_json.get("output_text")

        # 最后回退（仅当Gemini时）：在整个响应中递归收集 'text' 字符串
        if is_gemini:
            collected_all = _collect_text_fields(resp_json, allowed_keys=("text",))
            if collected_all:
                return "\n".join([t for t in collected_all if isinstance(t, str) and t.strip()])
    except Exception:
        return None
    return None


# ==========================
# 检测：网关客户端（OpenAI）
# ==========================

def detect_with_gateway_models(image_path: str, prompt: str) -> List[Dict]:
    base64_image = image_file_to_base64(image_path)
    if not base64_image:
        return [{"model": "(网关集)", "reply": "(读取图片失败)", "error": "读取或转换本地图片失败"}]

    mime = detect_mime(image_path)
    data_url = f"data:{mime};base64,{base64_image}"

    results = []
    for model in GATEWAY_MODELS:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                max_tokens=150,
            )
            if not resp or not getattr(resp, "choices", None):
                content_text = "(无有效响应)"
            else:
                msg = resp.choices[0].message if resp.choices else None
                raw = getattr(msg, "content", None)
                if isinstance(raw, str) and raw.strip():
                    content_text = raw.strip()
                elif isinstance(raw, list):
                    parts = []
                    for seg in raw:
                        if isinstance(seg, dict) and seg.get("type") == "text" and seg.get("text"):
                            parts.append(str(seg.get("text")))
                    content_text = "\n".join(parts).strip() if parts else ""
                else:
                    content_text = ""

            results.append({"model": model, "reply": content_text})
            print(f"🧠 网关模型 {model} 完成")
        except Exception as e:
            err = f"模型调用失败: {e}"
            results.append({"model": model, "reply": "(调用失败或无回复)", "error": err})
            print(f"❌ 网关模型 {model} 失败 - {err}")

    return results


# ==========================
# 检测：JDCloud HTTP
# ==========================

def detect_with_jdcloud_models(image_path: str, prompt: str) -> List[Dict]:
    base64_image = image_file_to_base64(image_path)
    if not base64_image:
        return [{"model": "(JDCloud集)", "reply": "(读取图片失败)", "error": "读取或转换本地图片失败"}]

    mime, kind = _detect_mime_and_kind(image_path)
    data_url = f"data:{mime};base64,{base64_image}"

    results = []
    for model in JOYBUILD_MODELS:
        content_items = [{"type": "text", "text": prompt}]
        if kind == "image_url":
            content_items.append({"type": "image_url", "image_url": {"url": data_url, "detail": "auto"}})
        else:
            content_items.append({"type": "audio_url", "audio_url": {"url": data_url}})

        data = {
            "stream": False,
            "messages": [{"role": "user", "content": content_items}],
            "model": model,
        }
        try:
            resp = requests.post(JDCLOUD_API_URL, headers=JDCLOUD_HEADERS, json=data, timeout=60)
            resp.raise_for_status()
            resp_json = resp.json()
            text = extract_text_from_response(resp_json, model_name=model)
            reply = text.strip() if isinstance(text, str) else ""
            results.append({"model": model, "reply": reply})
            print(f"🧠 JDCloud模型 {model} 完成")
        except requests.exceptions.RequestException as req_err:
            err = f"HTTP错误: {req_err}"
            results.append({"model": model, "reply": "(调用失败或无回复)", "error": err})
            print(f"❌ JDCloud模型 {model} 失败 - {err}")
        except Exception as e:
            err = f"未知错误: {e}"
            results.append({"model": model, "reply": "(调用失败或无回复)", "error": err})
            print(f"❌ JDCloud模型 {model} 失败 - {err}")

    return results


# ==========================
# 聚合裁决（使用 gpt-4o-0806 via 网关客户端）
# ==========================

def aggregate_judgement(all_results: List[Dict]) -> Dict:
    """汇总两套模型的文本结果并由大模型做最终判定。"""
    # 组织文本
    lines = []
    for item in all_results:
        model = item.get("model", "未知模型")
        reply = item.get("reply", "")
        lines.append(f"{model}: {reply}")
    joined = "\n".join(lines)

    aggregate_prompt = (
        "你将看到多个不同模型对同一张图片的分析回复。\n"
        "请仅根据这些文本回复进行判定，不要臆测图片内容。\n"
        "判定规则：只要任一回复明确表示存在异常或问题或者False，则判为 异常；若所有回复均明确表示正常或未见异常或者True，则判为 正常。\n"
        "忽略失败或空回复，不计入异常。\n\n"
        "请用严格的JSON输出（不包含任何解释性文本），格式如下：\n"
        "{\n  \"status\": \"正常/异常\",\n  \"reason\": \"简短中文理由\",\n  \"abnormal_models\": [\"模型名...\"]\n}"
    )

    messages = [
        {"role": "user", "content": [
            {"type": "text", "text": aggregate_prompt},
            {"type": "text", "text": "以下是各模型的回复：\n" + joined},
        ]}
    ]

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-0806",
            messages=messages,
            max_tokens=300,
        )
        agg_content = ""
        if resp and getattr(resp, "choices", None):
            msg = resp.choices[0].message if resp.choices else None
            raw = getattr(msg, "content", None)
            if isinstance(raw, str) and raw.strip():
                agg_content = raw.strip()

        agg_json = None
        try:
            agg_json = json.loads(agg_content)
        except Exception:
            m = re.search(r"\{.*\}", agg_content, re.S)
            if m:
                try:
                    agg_json = json.loads(m.group(0))
                except Exception:
                    agg_json = None

        if not agg_json or not isinstance(agg_json, dict):
            return {
                "status": "异常",
                "reason": "聚合判定失败：响应不可解析",
                "aggregate": {"raw": agg_content},
            }

        final_status = agg_json.get("status", "异常")
        if final_status in ["合格", "通过"]:
            final_status = "正常"
        elif final_status in ["不合格", "未通过"]:
            final_status = "异常"
        final_reason = agg_json.get("reason", "") or ("所有模型分析均未发现异常" if final_status == "正常" else "存在异常")
        abnormal_models = agg_json.get("abnormal_models", [])
        return {
            "status": final_status,
            "reason": final_reason,
            "aggregate": {"abnormal_models": abnormal_models, "raw": agg_content},
        }
    except Exception as e:
        return {"status": "异常", "reason": f"聚合判定调用失败: {e}"}


# ==========================
# 主流程：两套模型检测并汇总
# ==========================

def run_combined_check(image_path: str, prompt: str = PROMPT_TEXT) -> Dict:
    print("▶️ 启动合并检测流程")
    gw_results = detect_with_gateway_models(image_path, prompt)
    jb_results = detect_with_jdcloud_models(image_path, prompt)

    # 汇总所有文本结果
    all_results = []
    all_results.extend([{**r, "source": "网关"} for r in gw_results])
    all_results.extend([{**r, "source": "JDCloud"} for r in jb_results])

    # 聚合裁决
    judgement = aggregate_judgement(all_results)

    final = {
        "status": judgement.get("status", "异常"),
        "reason": judgement.get("reason", ""),
        "details": {
            "prompt": prompt,
            "gateway": {"models": GATEWAY_MODELS, "results": gw_results},
            "jdcloud": {"models": JOYBUILD_MODELS, "results": jb_results},
            "aggregate": judgement.get("aggregate", {}),
        },
    }

    print(f"\n📋 最终判定: {final['status']} ({final['reason']})")
    return final


if __name__ == "__main__":
    result = run_combined_check(CODE_IMAGE_PATH, PROMPT_TEXT)
    print("\n=== 合并检测结果 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))