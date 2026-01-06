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
            # 使用相对路径，确保在项目根目录下运行时正确保存
            output_dir = Path(__file__).parent / "generated_images"
            output_dir.mkdir(exist_ok=True)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"generated_{timestamp}.png"
            output_path = output_dir / output_filename

            saved_image_path = base64_to_image(generated_base64, str(output_path))
            if saved_image_path:
                print(f"Saved generated image to {saved_image_path}")
                return str(output_path), f"/generated_images/{output_filename}"

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

def _should_skip_background(background_info):
    """
    判断是否应该跳过背景处理
    """
    if not background_info or background_info.strip() == "":
        return True
    
    # 否定词列表
    negative_keywords = [
        "无", "没有", "不需要", "跳过", "不要", "none", "no", "skip", "empty"
    ]
    
    background_lower = background_info.lower().strip()
    for keyword in negative_keywords:
        if keyword in background_lower:
            return True
    
    return False

def generate_image_with_accessories(image_path, accessories_info):
    """
    添加背景处理：给图片添加指定的背景
    返回 '/output/xxx.png' 或 None。
    当 accessories_info 不明确或不可用时，跳过此步骤并直接返回上一阶段图片。
    """
    # 若无法解析出具体"背景"内容，跳过并返回上一阶段结果
    if _should_skip_background(accessories_info):
        print("[banana-background] 背景信息缺失或不明确，跳过背景处理，沿用上一步结果：", image_path)
        return image_path

    prompt_text = f"给画面添加{accessories_info}背景，保持角色的动作、表情、服饰不变，只改变背景环境。"
    print(f"[banana-background] prompt_text={prompt_text}")
    _, public_url = _call_api_with_image(image_path, prompt_text)
    return public_url

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        image_path = sys.argv[1]
        background_info = sys.argv[2]
        
        # 检查是否应该跳过背景处理
        if _should_skip_background(background_info):
            print(f"[banana-background] 背景信息缺失或包含否定词，跳过背景处理，沿用上一步结果：{image_path}")
            print(f"生成成功: {image_path}")
        else:
            result = generate_image_with_accessories(image_path, background_info)
            if result:
                print(f"生成成功: {result}")
            else:
                print("生成失败")
    else:
        print("Usage: python banana-background.py <image_path> <background_info>")