import requests
import json
import base64
from pathlib import Path
import os
import time
import sys

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

def _should_skip_clothes(info: str) -> bool:
    """
    服装配件判定：当上一阶段给出的信息包含否定词时跳过该步骤。
    - None 或空字符串：跳过
    - 否定词（含中英文）：如"无/没有/不穿/不换/原装/无服装/没有服装"等：跳过
    其他情况：不跳过，继续生成。
    """
    if info is None:
        print("[banana-clothes] skip_clothes: info is None")
        return True
    text = str(info).strip()
    print(f"[banana-clothes] _should_skip_clothes info={text!r}")
    if text == "":
        print("[banana-clothes] skip_clothes: empty string")
        return True
    lower = text.lower()
    negative_tokens = [
        # 中文否定
        "无", "没有", "不穿", "不换", "原装", "保持原样",
        "无服装", "没有服装", "无衣服", "没有衣服", "不换衣服", "不穿衣服",
        "原来的衣服", "原有服装", "不改变服装", "不更换服装",
        # 英文否定
        "no clothes", "without clothes", "no clothing", "without clothing",
        "original clothes", "keep original", "no change", "unchanged",
        "none", "null", "undefined",
    ]
    for kw in negative_tokens:
        if kw in text or kw in lower:
            print(f"[banana-clothes] skip_clothes: matched negative token {kw!r}")
            return True
    return False

def generate_image_with_accessories(image_path, accessories_info):
    """
    使用配件信息调用API生成图片。
    """
    # 检查是否应该跳过服装配件生成
    if _should_skip_clothes(accessories_info):
        print(f"[banana-clothes] 服装配件信息缺失或包含否定词，跳过服装处理，沿用上一步结果：{image_path}")
        return image_path
    
    # 恢复使用原始的 API 配置
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

    # 编码用户选择的图片
    base64_image_data = encode_image_to_base64(image_path)
    if not base64_image_data:
        return None

    # 使用用户指定的 prompt 格式
    prompt_text = f"保持图片中角色的姿态完全不变，为角色穿上{accessories_info}，不要帽子，脸上不要添加任何东西，不要出现手指，不要出现任何形式的女装，服装不要包裹手。将背景修改为浅灰色"
    
    # 保持用户要求的 data 结构
    mime_type = "image/png"
    data = {

        "model": "Gemini-2.5-flash-image-preview",
        # "model": "Gemini 3-Pro-Image-Preview",

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

        # 修正响应处理逻辑以匹配API返回的JSON结构
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
                return f"/{output_dir}/{output_filename}"
        
        print("Could not find generated image in response.")
        print("Response JSON:", json.dumps(json_response, indent=2))
        return None

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        if http_err.response:
            print("Response body on error:", http_err.response.text)
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

if __name__ == "__main__":
    # 命令行：python banana-clothes.py <image_path> <accessories_info>
    if len(sys.argv) >= 3:
        image_path = sys.argv[1]
        accessories_info = sys.argv[2]
        print(f"开始处理服装配件生成: {image_path} -> {accessories_info}")
        
        # 检查是否应该跳过
        if _should_skip_clothes(accessories_info):
            print("检测到否定词，跳过服装配件生成步骤")
            sys.exit(0)  # 成功退出，表示跳过
        
        result = generate_image_with_accessories(image_path, accessories_info)
        if result:
            print(f"生成成功: {result}")
        else:
            print("生成失败")
            sys.exit(1)
    else:
        print("Usage: python banana-clothes.py <image_path> <accessories_info>")
        sys.exit(1)