import requests
import json
import base64
from pathlib import Path
import os
import time
from typing import Optional, Dict
 

 

def encode_image_to_base64(image_path):
    """
    将本地图片文件编码为Base64字符串。
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}")
        return None
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

def base64_to_image(base64_string, save_path):
    """
    将Base64字符串解码并保存为图片文件。
    """
    try:
        img_data = base64.b64decode(base64_string)
        with open(save_path, "wb") as f:
            f.write(img_data)
        return save_path
    except Exception as e:
        print(f"Error decoding and saving image: {e}")
        return None

def _call_api_with_image(image_path, prompt_text):
    """
    单图调用：读取一张图片、拼装请求、保存输出。
    返回 (local_path, public_url)；失败返回 (None, None)。
    """
    api_url = "https://modelservice.jdcloud.com/v1/images/gemini_flash/generations"
    bearer_token = "pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf"

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Authorization": f"Bearer {bearer_token}",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Trace-id": "test-gemini-23",
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0"
    }

    base64_image_data = encode_image_to_base64(image_path)
    if not base64_image_data:
        return None, None

    mime_type = "image/png"
    data = {
        "model": "Gemini-2.5-flash-image-preview",
        "contents": {
            "role": "USER",
            "parts": [
                {
                    "inline_data": {
                        "mimeType": mime_type,
                        "data": base64_image_data
                    }
                },
                {
                    "text": prompt_text
                }
            ]
        },
        "generation_config": {
            "response_modalities": [
                "TEXT",
                "IMAGE"
            ]
        },
        "safety_settings": {
            "method": "PROBABILITY",
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        "stream": False
    }

    try:
        print(f"Sending request to {api_url}...")
        response = requests.post(api_url, headers=headers, json=data, timeout=120)
        response.raise_for_status()

        json_response = response.json()
        generated_base64 = None
        if 'candidates' in json_response and len(json_response['candidates']) > 0:
            candidate = json_response['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                for part in candidate['content']['parts']:
                    if 'inlineData' in part and 'data' in part['inlineData']:
                        generated_base64 = part['inlineData']['data']
                        break

        if generated_base64:
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"generated_{timestamp}.png"
            output_path = output_dir / output_filename

            saved_image_path = base64_to_image(generated_base64, str(output_path))
            if saved_image_path:
                print(f"Saved generated image to {saved_image_path}")
                # 质量评估由上层 generation_controller 统一控制；此处直接返回生成的路径
                return str(output_path), f"/output/{output_filename}"

        print("Could not find generated image in response.")
        print("Response JSON:", json.dumps(json_response, indent=2))
        return None, None

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        if http_err.response:
            print("Response body on error:", http_err.response.text)
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, None


# 质量检测开关与流程由 generation_controller 统一管理。
# 此模块不再内置 gate-合并.py 检测逻辑，仅负责生成并返回图片路径。

def _should_skip_hat(info: str) -> bool:
    """
    头戴判定：当上一阶段给出的信息包含否定词时跳过步骤8。
    - None 或空字符串：跳过
    - 否定词（含中英文）：如“无/没有/不带/不戴/无帽子/没有帽子”等：跳过
    其他情况：不跳过，继续生成。
    """
    if info is None:
        print("[banana-hats] skip_hat: info is None")
        return True
    text = str(info).strip()
    print(f"[banana-hats] _should_skip_hat info={text!r}")
    if text == "":
        print("[banana-hats] skip_hat: empty string")
        return True
    lower = text.lower()
    negative_tokens = [
        # 中文否定
        "无", "没有", "不带", "不戴",
        "无帽子", "没有帽子", "无头戴", "没有头戴", "不带帽子", "不戴帽子",
        # 英文否定
        "no hat", "without hat", "no headwear", "without headwear",
        "none", "null", "undefined",
    ]
    for kw in negative_tokens:
        if kw in text or kw in lower:
            print(f"[banana-hats] skip_hat: matched negative token {kw!r}")
            return True
    return False


def generate_image_with_accessories(image_path, accessories_info):
    """
    保留原单步接口：给图中的角色带上 accessories_info。
    返回 '/output/xxx.png' 或 None。
    当 accessories_info 不明确或不可用时，跳过此步骤并直接返回上一阶段图片。
    """
    # 若无法解析出具体“头戴”内容，跳过并返回上一阶段结果
    if _should_skip_hat(accessories_info):
        print("[banana-hats] 头戴信息缺失或不明确，跳过头戴处理，沿用上一步结果：", image_path)
        return image_path

    prompt_text = (
        f"严格保持角色动作、表情、服饰和背景完全一致，只在原图的头部添加{accessories_info}。"
        f"{accessories_info}要戴在两耳之间，不要太小，也不要太大"
        f"不要改变背景、场景、光线或其他任何内容，不要重绘或替换其他区域；"
        f"注意不要遮挡耳朵，不要遮挡眼睛。"
    )
    print(f"[banana-hats] prompt_text={prompt_text}")
    local_path, public_url = _call_api_with_image(image_path, prompt_text)
    if not local_path or not public_url:
        print("[banana-hats] 生成图片失败或未返回路径，跳过展示")
        return None
    # 质量检测由上层控制器统一执行；此处直接返回生成的 public_url
    return public_url