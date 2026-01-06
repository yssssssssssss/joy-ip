import requests
import json
import base64
from pathlib import Path
import os
import time
import sys

def encode_image_to_base64_from_path_or_url(image_path_or_url: str):
    """
    将本地或远程图片编码为Base64字符串。
    """
    try:
        if image_path_or_url.startswith("http://") or image_path_or_url.startswith("https://"):
            r = requests.get(image_path_or_url, timeout=30)
            r.raise_for_status()
            return base64.b64encode(r.content).decode("utf-8")
        else:
            with open(image_path_or_url, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            return encoded_string
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path_or_url}")
        return None
    except Exception as e:
        print(f"Error encoding image {image_path_or_url}: {e}")
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

def generate_image_with_accessories(image_path_or_url: str, background_info: str):
    """
    使用配件信息调用API生成图片。
    """
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

    # 编码用户选择的图片（支持本地或远程）
    base64_image_data = encode_image_to_base64_from_path_or_url(image_path_or_url)
    if not base64_image_data:
        return None

    # 使用用户指定的 prompt 格式
    prompt_text = f"严格保持角色形象一致性，将背景替换为{background_info}"
    
    # 保持用户要求的 data 结构
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
        response = requests.post(api_url, headers=headers, json=data)
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
                # 返回前端可访问的相对路径（由前端路由/代理提供静态访问）
                return f"/generated_images/{output_filename}"
        
        print("Could not find generated image in response.")
        # 避免打印过长的内容，仅输出预览
        try:
            preview = json.dumps(json_response, ensure_ascii=False)[:300]
            print("Response preview:", preview, "...")
        except Exception:
            pass
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
    # 命令行：python background-banana.py <tag_img_url> <background_text>
    if len(sys.argv) >= 3:
        img = sys.argv[1]
        bg = sys.argv[2]
        print(f"开始处理图片生成: {img} -> {bg}")
        result = generate_image_with_accessories(img, bg)
        if result:
            print(f"生成成功: {result}")
        else:
            print("生成失败")
            sys.exit(1)
    else:
        print("Usage: python background-banana.py <tag_img_url> <background_text>")
        sys.exit(1)