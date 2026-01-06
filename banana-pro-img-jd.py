import requests
import json
import base64
import time
from pathlib import Path
from prompt_templates import get_system_prompt, get_accessory_instruction, get_constraints

# 尝试导入带重试机制的http_client
try:
    from utils.http_client import http_post
    USE_HTTP_CLIENT = True
except ImportError:
    USE_HTTP_CLIENT = False

# API 地址与鉴权
URL = "https://modelservice.jdcloud.com/v1/images/gemini_flash/generations"
API_KEY = "pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf"

# 在此配置本地图片路径（作为默认值，可被命令行参数覆盖）
IMG1_PATH = r"C:\Users\heyunshen\Downloads\badcase\generated_1763630969.png"
IMG2_PATH = None  # 可选第二张图片，默认不使用

# 生成结果默认保存到项目根目录下的 output/ 目录
OUTPUT_DIR = Path("output")

PROMPT_TEXT = (
    "严格保持图片1中角色的动作、表情一致性，进行品牌风格优化"
)

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


def generate_image_with_accessories(image_path, accessories_info, style="default"):
    """
    统一的配件生成接口，兼容原有的三个模块接口
    
    Args:
        image_path: 输入图片路径
        accessories_info: 配件信息（可以是服装、手拿、头戴的组合描述）
        style: prompt风格 ("default", "professional", "simple")
        
    Returns:
        str: 生成的图片路径（格式：/output/xxx.png）或原图片路径（跳过时）
    """
    # 检查是否应该跳过处理
    if _should_skip_processing(accessories_info):
        print(f"[banana-pro-img-jd] 配件信息缺失或包含否定词，跳过处理，沿用上一步结果：{image_path}")
        return image_path
    
    # 智能检测场景风格
    scene_style = _detect_scene_style(accessories_info)
    
    # 构建综合prompt
    prompt = _build_comprehensive_prompt(accessories_info, style, scene_style)
    
    # 调试输出：显示生成的prompt
    print(f"[banana-pro-img-jd] 使用风格: {style}, 场景: {scene_style}")
    print(f"[banana-pro-img-jd] 生成的Prompt:")
    print("=" * 50)
    print(prompt)
    print("=" * 50)
    
    # 执行图片生成
    result_path = _generate_single_image(image_path, prompt)
    return result_path if result_path else image_path

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
    negative_tokens = [
        # 中文否定
        "无", "没有", "不穿", "不换", "不拿", "不持", "不带", "不戴", "原装", "保持原样", "空手",
        "无服装", "没有服装", "无衣服", "没有衣服", "无手持", "没有手持", "无帽子", "没有帽子",
        "无头戴", "没有头戴", "无配件", "没有配件", "无物品", "没有物品",
        # 英文否定
        "no clothes", "without clothes", "no clothing", "without clothing",
        "no hands", "without hands", "no holding", "without holding", "empty hands",
        "no hat", "without hat", "no headwear", "without headwear",
        "original clothes", "keep original", "no change", "unchanged",
        "none", "null", "undefined",
    ]
    
    for kw in negative_tokens:
        if kw in text or kw in lower:
            print(f"[banana-pro-img-jd] skip_processing: matched negative token {kw!r}")
            return True
    return False

def _build_comprehensive_prompt(accessories_info: str, style="default", scene_style=None) -> str:
    """
    构建综合的prompt，整合服装、手拿、头戴信息
    
    Args:
        accessories_info: 配件信息
        style: 系统提示词风格 ("default", "professional", "simple")
        scene_style: 场景风格 ("formal", "casual", "sports")
    """
    # 获取系统提示词
    system_prompt = get_system_prompt(style)
    
    # 解析配件信息
    parsed_accessories = _parse_accessories_info(accessories_info)
    
    # 构建具体的修改指令
    modification_instructions = _build_modification_instructions_v2(parsed_accessories)
    
    # 获取约束条件
    constraints = get_constraints(style, scene_style)
    constraints_text = '\n'.join([f"- {constraint}" for constraint in constraints])
    
    # 组合最终prompt
    full_prompt = f"""{system_prompt}

【本次任务】
{modification_instructions}

【约束条件】
{constraints_text}"""
    
    return full_prompt

def _build_modification_instructions_v2(accessories: dict) -> str:
    """
    使用模板系统构建修改指令
    """
    instructions = []
    
    # 服装处理指令
    if accessories['服装']:
        instruction = get_accessory_instruction('服装', accessories['服装'])
        instructions.append(instruction)
    
    # 手拿物品处理指令
    if accessories['手拿']:
        instruction = get_accessory_instruction('手拿', accessories['手拿'])
        instructions.append(instruction)
    
    # 头戴物品处理指令
    if accessories['头戴']:
        instruction = get_accessory_instruction('头戴', accessories['头戴'])
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
    
    for part in parts:
        part = part.strip()
        if '服装：' in part or '上装：' in part or '下装：' in part:
            accessories['服装'] = part.split('：', 1)[1] if '：' in part else part
        elif '手拿：' in part or '手持：' in part:
            accessories['手拿'] = part.split('：', 1)[1] if '：' in part else part
        elif '头戴：' in part or '帽子：' in part:
            accessories['头戴'] = part.split('：', 1)[1] if '：' in part else part
        else:
            # 其他未分类的配件信息
            accessories['其他'].append(part)
    
    return accessories



def _generate_single_image(image_path: str, prompt: str) -> str:
    """
    生成单张图片的核心逻辑
    支持429错误重试
    """
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

    max_retries = 3
    retry_delay = 2  # 初始重试延迟（秒）

    for attempt in range(max_retries):
        try:
            print(f"发送请求...{f' (重试 {attempt})' if attempt > 0 else ''}")
            
            # 使用带重试机制的http_client（如果可用）
            if USE_HTTP_CLIENT:
                response = http_post(URL, json=payload, headers=headers, timeout=120)
            else:
                response = requests.post(URL, headers=headers, json=payload, timeout=120)
            
            print("HTTP", response.status_code)

            # 处理429频率限制错误
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # 指数退避
                    print(f"遇到频率限制(429)，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    print("频率限制(429)：已达最大重试次数")
                    return None

            # 优先解析为 JSON，提取 base64 图片
            try:
                resp_json = response.json()
            except Exception:
                print("响应不是合法 JSON：")
                print(response.text)
                return None

            b64 = extract_generated_image_base64(resp_json)
            if not b64:
                print("未在响应中找到生成图片的 base64 数据：")
                print(json.dumps(resp_json, ensure_ascii=False, indent=2))
                return None

            # 保存到 output 目录
            OUTPUT_DIR.mkdir(exist_ok=True)
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = OUTPUT_DIR / f"generated_{ts}.png"
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
        response = requests.post(URL, headers=headers, json=payload, timeout=120)
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
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = OUTPUT_DIR / f"generated_{ts}.png"
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