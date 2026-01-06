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

def _should_skip_hands(info: str) -> bool:
    """
    手部配件判定：当上一阶段给出的信息包含否定词时跳过该步骤。
    - None 或空字符串：跳过
    - 否定词（含中英文）：如"无/没有/不拿/不持/空手/无手持物品"等：跳过
    其他情况：不跳过，继续生成。
    """
    if info is None:
        print("[banana-hands] skip_hands: info is None")
        return True
    text = str(info).strip()
    print(f"[banana-hands] _should_skip_hands info={text!r}")
    if text == "":
        print("[banana-hands] skip_hands: empty string")
        return True
    lower = text.lower()
    negative_tokens = [
        # 中文否定
        "无", "没有", "不拿", "不持", "空手",
        "无手持", "没有手持", "无配件", "没有配件", "不拿东西", "不持物品",
        "无手持物品", "没有手持物品", "无物品", "没有物品",
        # 英文否定
        "no hands", "without hands", "no holding", "without holding",
        "empty hands", "no items", "without items", "no accessories", "without accessories",
        "none", "null", "undefined",
    ]
    for kw in negative_tokens:
        if kw in text or kw in lower:
            print(f"[banana-hands] skip_hands: matched negative token {kw!r}")
            return True
    return False

def generate_image_with_accessories(image_path, accessories_info):
    """
    使用配件信息调用API生成图片。
    """
    print(f"[banana-hands] === 开始处理 ===", flush=True)
    print(f"[banana-hands] 输入图片: {image_path}", flush=True)
    print(f"[banana-hands] 配件信息: {accessories_info}", flush=True)
    
    # 检查是否应该跳过手部配件生成
    if _should_skip_hands(accessories_info):
        print(f"[banana-hands] 手部配件信息缺失或包含否定词，跳过手部处理，沿用上一步结果：{image_path}", flush=True)
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
    prompt_text = f"严格保持角色动作、表情、服饰的一致性，让角色单手拿着{accessories_info}，不要出现手指"
    
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
        print(f"[banana-hands] 发送API请求到 {api_url}...", flush=True)
        print(f"[banana-hands] Prompt: {prompt_text}", flush=True)
        start_time = time.time()
        
        response = requests.post(api_url, headers=headers, json=data, timeout=120)
        
        elapsed = time.time() - start_time
        print(f"[banana-hands] API响应耗时: {elapsed:.2f}秒, 状态码: {response.status_code}", flush=True)
        
        response.raise_for_status()
        
        json_response = response.json()
        print(f"[banana-hands] 解析响应JSON成功", flush=True)

        # 修正响应处理逻辑以匹配API返回的JSON结构
        generated_base64 = None
        if 'candidates' in json_response and len(json_response['candidates']) > 0:
            candidate = json_response['candidates'][0]
            print(f"[banana-hands] 找到候选结果", flush=True)
            if 'content' in candidate and 'parts' in candidate['content']:
                parts_count = len(candidate['content']['parts'])
                print(f"[banana-hands] 响应包含 {parts_count} 个parts", flush=True)
                for i, part in enumerate(candidate['content']['parts']):
                    if 'inlineData' in part and 'data' in part['inlineData']:
                        generated_base64 = part['inlineData']['data']
                        print(f"[banana-hands] 在part[{i}]找到图片数据", flush=True)
                        break
                    elif 'text' in part:
                        print(f"[banana-hands] part[{i}]是文本: {part['text'][:100]}...", flush=True)
        else:
            print(f"[banana-hands] 响应中没有candidates", flush=True)

        if generated_base64:
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"generated_{timestamp}.png"
            output_path = output_dir / output_filename

            saved_image_path = base64_to_image(generated_base64, str(output_path))

            if saved_image_path:
                print(f"[banana-hands] ✓ 保存图片成功: {saved_image_path}", flush=True)
                return f"/{output_dir}/{output_filename}"
        
        print("[banana-hands] ✗ 响应中未找到图片数据", flush=True)
        print(f"[banana-hands] 响应内容: {json.dumps(json_response, indent=2, ensure_ascii=False)[:500]}", flush=True)
        return None

    except requests.exceptions.Timeout as timeout_err:
        print(f"[banana-hands] ✗ 请求超时: {timeout_err}", flush=True)
        return None
    except requests.exceptions.HTTPError as http_err:
        print(f"[banana-hands] ✗ HTTP错误: {http_err}", flush=True)
        if http_err.response:
            print(f"[banana-hands] 错误响应: {http_err.response.text[:500]}", flush=True)
        return None
    except Exception as e:
        print(f"[banana-hands] ✗ 未知错误: {type(e).__name__}: {e}", flush=True)
        return None

if __name__ == "__main__":
    # 命令行：python banana-hands.py <image_path> <accessories_info>
    if len(sys.argv) >= 3:
        image_path = sys.argv[1]
        accessories_info = sys.argv[2]
        print(f"开始处理手部配件生成: {image_path} -> {accessories_info}")
        
        # 检查是否应该跳过
        if _should_skip_hands(accessories_info):
            print("检测到否定词，跳过手部配件生成步骤")
            sys.exit(0)  # 成功退出，表示跳过
        
        result = generate_image_with_accessories(image_path, accessories_info)
        if result:
            print(f"生成成功: {result}")
        else:
            print("生成失败")
            sys.exit(1)
    else:
        print("Usage: python banana-hands.py <image_path> <accessories_info>")
        sys.exit(1)