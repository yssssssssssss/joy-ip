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

def detect_mime_type(path: str) -> str:
    """根据文件扩展名检测MIME类型"""
    lower = str(path).lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".bmp"):
        return "image/bmp"
    return "image/png"


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


def generate_image_from_3d_render(image_path, prompt_text):
    """
    使用3D渲染图片和提示文本调用API生成最终图片。
    使用 Gemini 3-Pro-Image-Preview 模型（参考 banana-pro-img-jd.py）
    
    参数:
        image_path: 3D渲染图片的路径
        prompt_text: 用户输入的提示文本
    
    返回:
        生成的图片路径，失败返回None
    """
    # API 配置（与 banana-pro-img-jd.py 保持一致）
    api_url = "https://modelservice.jdcloud.com/v1/images/gemini_flash/generations"
    api_key = "pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Trace-Id": "3d-banana-all",
    }

    # 编码3D渲染图片
    print(f"[3D-banana-all] 正在编码图片: {image_path}", flush=True)
    base64_image_data = encode_image_to_base64(image_path)
    if not base64_image_data:
        print(f"[3D-banana-all] 图片编码失败: {image_path}", flush=True)
        return None

    # 检测MIME类型
    mime_type = detect_mime_type(image_path)

    # 构建提示词：基于3D渲染图片和用户描述生成最终图片
    full_prompt = f"基于这张3D渲染图片，{prompt_text}，保持角色的姿态和造型，生成高质量的IP形象图片"
    print(f"[3D-banana-all] 提示词: {full_prompt}", flush=True)
    
    # API请求数据（参考 banana-pro-img-jd.py 的格式）
    payload = {
        "model": "Gemini 3-Pro-Image-Preview",
        "stream": False,
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": full_prompt},
                    {"inlineData": {"mimeType": mime_type, "data": base64_image_data}},
                ],
            }
        ],
        "generation_config": {
            "response_modalities": ["IMAGE"],
        },
    }

    try:
        print(f"[3D-banana-all] 发送请求到 {api_url}...", flush=True)
        print(f"[3D-banana-all] 使用模型: Gemini 3-Pro-Image-Preview", flush=True)
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=120)
        print(f"[3D-banana-all] HTTP状态码: {response.status_code}", flush=True)
        
        # 解析响应
        try:
            json_response = response.json()
        except Exception:
            print("[3D-banana-all] 响应不是合法JSON:", flush=True)
            print(response.text, flush=True)
            return None

        # 提取生成的图片base64
        generated_base64 = extract_generated_image_base64(json_response)

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
                print(f"[3D-banana-all] 图片已保存: {saved_image_path}", flush=True)
                return saved_image_path
        
        print("[3D-banana-all] 响应中未找到生成的图片", flush=True)
        print("Response JSON:", json.dumps(json_response, indent=2, ensure_ascii=False), flush=True)
        return None

    except requests.exceptions.Timeout:
        print("[3D-banana-all] 请求超时", flush=True)
        return None
    except requests.exceptions.HTTPError as http_err:
        print(f"[3D-banana-all] HTTP错误: {http_err}", flush=True)
        if http_err.response:
            print("Response body:", http_err.response.text, flush=True)
        return None
    except Exception as e:
        print(f"[3D-banana-all] 发生错误: {e}", flush=True)
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
