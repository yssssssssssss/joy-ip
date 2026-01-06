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

def generate_image_from_3d_render(image_path, prompt_text):
    """
    使用3D渲染图片和提示文本调用API生成最终图片。
    
    参数:
        image_path: 3D渲染图片的路径
        prompt_text: 用户输入的提示文本
    
    返回:
        生成的图片路径，失败返回None
    """
    # API 配置
    api_url = "https://modelservice.jdcloud.com/v1/images/gemini_flash/generations"
    bearer_token = "pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf"

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Authorization": f"Bearer {bearer_token}",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Trace-id": "test-gemini-3d",
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0"
    }

    # 编码3D渲染图片
    print(f"[3D-banana-all] 正在编码图片: {image_path}")
    base64_image_data = encode_image_to_base64(image_path)
    if not base64_image_data:
        print(f"[3D-banana-all] 图片编码失败: {image_path}")
        return None

    # 构建提示词：基于3D渲染图片和用户描述生成最终图片
    full_prompt = f"基于这张3D渲染图片，{prompt_text}，保持角色的姿态和造型，生成高质量的IP形象图片"
    print(f"[3D-banana-all] 提示词: {full_prompt}")
    
    # API请求数据
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
                    "text": full_prompt
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
        print(f"[3D-banana-all] 发送请求到 {api_url}...")
        response = requests.post(api_url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        
        json_response = response.json()
        print(f"[3D-banana-all] 收到响应")

        # 解析响应，提取生成的图片
        generated_base64 = None
        if 'candidates' in json_response and len(json_response['candidates']) > 0:
            candidate = json_response['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                for part in candidate['content']['parts']:
                    if 'inlineData' in part and 'data' in part['inlineData']:
                        generated_base64 = part['inlineData']['data']
                        break

        if generated_base64:
            # 保存到 generated_images 目录（与API检测目录一致）
            output_dir = Path("generated_images")
            output_dir.mkdir(exist_ok=True)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"3d_generated_{timestamp}.png"
            output_path = output_dir / output_filename

            saved_image_path = base64_to_image(generated_base64, str(output_path))

            if saved_image_path:
                print(f"[3D-banana-all] 图片已保存: {saved_image_path}")
                return saved_image_path
        
        print("[3D-banana-all] 响应中未找到生成的图片")
        print("Response JSON:", json.dumps(json_response, indent=2, ensure_ascii=False))
        return None

    except requests.exceptions.Timeout:
        print("[3D-banana-all] 请求超时")
        return None
    except requests.exceptions.HTTPError as http_err:
        print(f"[3D-banana-all] HTTP错误: {http_err}")
        if http_err.response:
            print("Response body:", http_err.response.text)
        return None
    except Exception as e:
        print(f"[3D-banana-all] 发生错误: {e}")
        return None

if __name__ == "__main__":
    # 命令行：python 3D-banana-all.py <image_path> <prompt_text>
    if len(sys.argv) >= 3:
        image_path = sys.argv[1]
        prompt_text = sys.argv[2]
        
        print(f"[3D-banana-all] ========== 开始处理 ==========")
        print(f"[3D-banana-all] 输入图片: {image_path}")
        print(f"[3D-banana-all] 提示文本: {prompt_text}")
        
        # 检查图片文件是否存在
        if not os.path.exists(image_path):
            print(f"[3D-banana-all] 错误: 图片文件不存在: {image_path}")
            sys.exit(1)
        
        result = generate_image_from_3d_render(image_path, prompt_text)
        
        if result:
            print(f"[3D-banana-all] ========== 生成成功 ==========")
            print(f"[3D-banana-all] 输出文件: {result}")
            sys.exit(0)
        else:
            print(f"[3D-banana-all] ========== 生成失败 ==========")
            sys.exit(1)
    else:
        print("Usage: python 3D-banana-all.py <image_path> <prompt_text>")
        print("  image_path: 3D渲染图片的路径")
        print("  prompt_text: 用户输入的提示文本")
        sys.exit(1)
