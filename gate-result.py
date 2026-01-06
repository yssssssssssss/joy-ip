import os
import sys
import json
import base64
import mimetypes
import re
import requests

"""
合并脚本说明：
此文件合并了以下两个脚本的功能，并提供单一入口：
- local/test-single-local.py（Gemini Flash 图像生成接口，使用 inlineData，提取所有 text 片段并拼接）
- local/local-gate-joybuild-prompttest1.py（多模型分析接口，逐模型输出并进行聚合裁决）

通过 RUN_MODE 选择运行模式：
- RUN_MODE = "multi" 运行多模型分析与聚合裁决
- RUN_MODE = "single" 运行单模型 Gemini Flash 接口并输出合并文本
"""

# ---------------------- 通用配置与提示 ----------------------

# 默认图片路径（可修改）
CODE_IMAGE_PATH = r"C:\Users\heyunshen\Downloads\badcase\generated_1763631010.png"

# Prompt（用于 chat/completions 的多模型：Gemini-2.5-pro、Claude-opus-4）
PROMPT_CHAT = '''
# Task Description (任务描述)
你需要审核 AI 生成的 3D 卡通形象，角色的手为圆形、球形是正常状态，不要使用人类的解剖学知识。

# Role Definition (角色设定)
你是一位 **AI 图像生成质量控制与视觉法医学专家 (AI Visual Forensics & QA Specialist)**。你的核心职责是审核 AI 生成的 3D 卡通角色图像，精准识别生成伪影（Artifacts）、逻辑崩坏。

# Core Philosophy (核心理念)
**“相信像素，不要相信常识。”**
AI 模型经常生成违反物理和生物规律的图像。你的任务不是解释这些图像“试图”表达什么，而是冷酷地指出它们在“现实逻辑”上哪里失败了。不要自动脑补合理的解释，如果视觉上是错误的，它就是错误的。

# Audit Checklist (详细审计清单)
在分析图像时，必须严格扫描以下 5 个核心维度：
## 1. 肢体与解剖结构 (Limb & Anatomy Forensic)
* **多肢体幻觉 (Multi-Limb Hallucination)**：这是重中之重。检查是否有“重影”肢体。
    * *特征*：一组手在执行动作（如拿东西），而在腋下、肩膀后方或腰部又长出了额外的、无意义的肢体末端。
* **连接点**：肢体是否正确连接在肩膀或胯部？是否有肢体像“浮游炮”一样悬浮在身体旁？

## 2. 五官与面部对称性 (Facial & Feature Integrity)
* **对称性崩坏**：除非是特定的眨眼表情、星星眼，否则左右眼睛的大小、形状（正圆 vs 椭圆）、倾斜度必须一致。AI 常生成“大小眼”。
* **漂浮五官**：眼睛、眉毛或嘴巴是否错位、异常，或者看起来在不合逻辑的位置上？

## 3. 物体互动与抓握逻辑 (Object Interaction & Grip)
* **悬浮物品 (Hovering Objects)**：角色是否真的“拿”住了物品？还是物品仅仅是悬浮在手掌前方？（这是极其常见的错误）。
* **穿模 (Clipping)**：手指是否穿透了物品实体？或者物品是否嵌入了角色的肉体里？

## 4. 服装与配饰物理 (Clothing & Accessories Physics)
* **帽子/头饰逻辑**：
    * *大小适配*：帽子是否过小，像一个小碟子平衡在头顶？
    * *物理接触*：帽子是戴在头上，还是漂浮在头顶上方？或者是切入了头骨内部？
* **衣物连贯性**：衣领、袖口是否在空间上连续？是否有袖子消失在半空中的情况？

---

# Thinking Protocol (强制思维链路)
在给出最终结论前，请按以下步骤思考（CoT）：
1.  **[ROI 扫描]**：将图像分割为 Head, Torso, Limbs, Props 四个区域。
2.  **[计数与锚定]**：从躯干出发，数出所有肢体的数量。如果数量 > 2 (对于手) 或 > 2 (对于脚)，立即标记为异常。
3.  **[逻辑验证]**：
    * *Check Face*: 左右眼是否为镜像关系？
    * *Check Hat*: 帽子是否遵循重力？
4.  **[报告生成]**：输出客观的缺陷列表。

# Output Format (输出格式)
请直接按照以下结构回答用户：
* **总体评分**：(正常 / 轻微瑕疵 / 严重崩坏)
* **肢体检测**：[数量] - [描述] (例如：检测到 3 条胳膊，左侧腋下有多余肢体)
* **五官分析**：(例如：右眼显著小于左眼，非表情原因)
* **互动逻辑**：(例如：苹果悬浮在手掌前，无接触)
* **其他异常**：(帽子悬浮、透视错误等)
'''

# Prompt（用于 images/gemini_flash/generations 的单模型：Gemini 3-Pro-Image-Preview）
PROMPT_FLASH = '''
# Task（任务）
检查这张图片中的角色：
1、有几条胳膊
2、是否正确的拿着物品
3、比例是否正常
4、五官是否正常
5、帽子是否正常
6、帽子的比例是否正常
7、服装是否存在女装
8、场景是否存在暴力、血腥内容

# Role (角色设定)
你是一个由 Google 训练的高级计算机视觉与图像取证专家 (AI Vision Forensics Expert)。你拥有超越普通人类的像素级观察力，专注于检测 AI 生成图像中的逻辑错误、解剖学异常和视觉伪影。中文回答。

# Objective (目标)
用户会上传一张 AI 生成的图像。你的任务是客观、精确地分析图像中的物理细节，尤其是肢体数量、大小眼、空间关系、物体互动。不要因为图像整体看起来可爱或和谐就忽略细节错误。

# Analysis Protocol (分析协议 - 必须严格执行)
在回答用户的具体问题之前，你必须在内心执行以下“视觉审计流程”：

1.  **Segmentation (分割)**：在思维中将主体与背景分离，不要让背景颜色干扰对肢体边缘的判断。
2.  **Anatomy Tracing (解剖追踪)**：
    * 找到角色的核心躯干（Torso）。
    * 寻找所有从躯干延伸出的“管状结构”或“肢体”。
    * **关键规则**：只要一个物体看起来像胳膊/手/腿，并且连接在身体上，无论它是否合理，都要计数。
    * *注意*：AI 生成图经常会出现“幻觉肢体”（例如：一组手在拿东西，腋下又长出一组手）。如果发现这种情况，必须如实报告，不要自动修正为“正常的生物”。
3.  **Occlusion Check (遮挡检查)**：检查前景物体（如篮子、乐器）后面是否隐藏了断裂的肢体。

# Response Guidelines (回答指南)
* **Fact-Based**: 只描述你看到的像素事实，不要基于常识进行推断（例如：不要说“因为是狗所以是2条腿”，如果图上画了3条，就说3条）。
* **Directness**: 直接回答核心问题，然后提供支持证据。

用中文总结这张图片是否正常，是否存在问题，如果有问题，具体是什么
'''

# 运行模式（保留但不再用于分支选择）
RUN_MODE = "multi"

# 多模型列表（与用户示例一致）
MODELS_TO_CALL = [
    "Gemini-2.5-pro",
    # "Claude-opus-4",
]

# ---------------------- 单模型（Gemini Flash generations）工具 ----------------------

def guess_mime(file_path: str) -> str:
    mime, _ = mimetypes.guess_type(file_path)
    if mime:
        return mime
    ext = os.path.splitext(file_path)[1].lower()
    if ext in {".png"}:
        return "image/png"
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if ext in {".webp"}:
        return "image/webp"
    if ext in {".bmp"}:
        return "image/bmp"
    return "application/octet-stream"


def encode_image_to_base64_with_mime(file_path: str) -> tuple[str, str]:
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return encoded, guess_mime(file_path)


def build_payload_gemini_flash(text: str, mime_type: str, base64_data: str) -> dict:
    return {
        "model": "Gemini 3-Pro-Image-Preview",
        "stream": False,
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": text},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64_data,
                        }
                    },
                ],
            }
        ],
    }


def parse_all_texts(obj: dict) -> list[str]:
    """提取响应中所有可能的文本片段。
    优先走 candidates->content->parts->text；若无则回退递归搜索所有 'text' 字段。
    注意：跳过 thought=True 的思考内容，只提取实际答案。
    """
    texts: list[str] = []
    try:
        candidates = obj.get("candidates") or obj.get("Candidates")
        if isinstance(candidates, list):
            for cand in candidates:
                content = cand.get("content") or cand.get("Content")
                if isinstance(content, dict):
                    parts = content.get("parts") or content.get("Parts")
                    if isinstance(parts, list):
                        for p in parts:
                            if isinstance(p, dict) and isinstance(p.get("text"), str):
                                # 跳过思考内容（thought=True）
                                if p.get("thought", False):
                                    continue
                                texts.append(p["text"])
        if texts:
            return texts
    except Exception:
        pass

    # 回退递归搜索（也需要跳过思考内容）
    def walk(o):
        if isinstance(o, dict):
            # 跳过思考内容
            if o.get("thought", False):
                return
            t = o.get("text")
            if isinstance(t, str):
                texts.append(t)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for it in o:
                walk(it)

    try:
        walk(obj)
    except Exception:
        pass
    return texts


def run_gemini_flash_generation(image_path: str, prompt_text: str) -> str:
    """调用 /v1/images/gemini_flash/generations 接口，返回合并的文本。"""
    url = "https://modelservice.jdcloud.com/v1/images/gemini_flash/generations"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Authorization": "Bearer pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Trace-id": "gate-result-single",
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
    }

    # 基础校验
    abs_path = os.path.abspath(image_path)
    if not os.path.isfile(abs_path):
        return f"错误：图片文件不存在 -> {abs_path}"
    if os.path.splitext(abs_path)[1].lower() not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
        return f"错误：不支持的图片格式 -> {os.path.splitext(abs_path)[1].lower()}"

    # 编码并构建 payload
    base64_data, mime_type = encode_image_to_base64_with_mime(abs_path)
    payload = build_payload_gemini_flash(prompt_text, mime_type, base64_data)

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        try:
            resp_json = response.json()
            texts = parse_all_texts(resp_json)
            joined = "\n".join(t.strip() for t in texts if isinstance(t, str) and t.strip())
            return joined if joined else response.text
        except Exception:
            return response.text
    except Exception as e:
        return f"请求失败：{type(e).__name__} - {str(e)}"


# ---------------------- 多模型分析（chat/completions）工具 ----------------------

def encode_image_to_base64_str(image_path: str) -> str | None:
    """将本地图片文件编码为 Base64 字符串。"""
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


def _detect_mime_and_kind(path: str):
    """根据文件扩展名返回 MIME 类型和内容类型键（image_url 或 audio_url）。"""
    ext = os.path.splitext(path)[1].lower()
    # 图片类型
    if ext in [".png"]:
        return "image/png", "image_url"
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg", "image_url"
    if ext in [".webp"]:
        return "image/webp", "image_url"
    # 音频类型
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
    # 兜底
    return "image/png", "image_url"


def extract_text_from_response(resp_json, model_name=None):
    """兼容解析 JDCloud / OpenAI / Gemini 风格响应中的文本内容。
    特别说明：针对 Gemini-2.5-pro，仅提取 parts 中的 text 字段，不做其它类型内容（如 inlineData）的合并。
    """
    try:
        # 针对 Gemini-2.5-pro：优先从 choices[0].message.content.text 提取；否则退回 candidates->content->parts->text
        if isinstance(model_name, str) and model_name.strip().lower() == "gemini-2.5-pro":
            if isinstance(resp_json, dict) and "choices" in resp_json:
                choices = resp_json.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content")
                    if isinstance(content, dict):
                        t = content.get("text")
                        if isinstance(t, str) and t.strip():
                            return t
                    if isinstance(content, str) and content.strip():
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
                        if pieces:
                            return "\n".join(pieces)
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
            return None

        # OpenAI/兼容风格：choices -> message -> content
        if isinstance(resp_json, dict) and "choices" in resp_json:
            choices = resp_json.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                content = msg.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, dict):
                    t = content.get("text")
                    if isinstance(t, str):
                        return t
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

        # Gemini风格：candidates -> content -> parts -> text（仅提取 text 字段）
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

        if isinstance(resp_json.get("output_text"), str):
            return resp_json.get("output_text")
    except Exception:
        return None
    return None


def call_analysis_api(image_path, model_name, prompt_text):
    """
    调用大模型API对图片进行分析。
    """
    api_url = "https://modelservice.jdcloud.com/v1/chat/completions"
    bearer_token = "pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf"

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Authorization": f"Bearer {bearer_token}",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
    }

    base64_image_data = encode_image_to_base64_str(image_path)
    if not base64_image_data:
        return f"无法编码图片: {image_path}"

    mime, kind = _detect_mime_and_kind(image_path)
    data_url = f"data:{mime};base64,{base64_image_data}"

    content_items = [
        {"type": "text", "text": prompt_text},
    ]
    if kind == "image_url":
        content_items.append({"type": "image_url", "image_url": {"url": data_url, "detail": "auto"}})
    else:
        content_items.append({"type": "audio_url", "audio_url": {"url": data_url}})

    data = {
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": content_items,
            }
        ],
        "model": model_name,
    }

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        json_response = response.json()

        text = extract_text_from_response(json_response, model_name=model_name)
        if isinstance(text, str) and text.strip():
            return text.strip()

        if str(model_name).strip().lower() == "gemini-2.5-pro":
            return ""

        return f"模型 {model_name} 未返回有效的文本分析结果。 响应: {json.dumps(json_response, ensure_ascii=False)}"

    except requests.exceptions.SSLError as ssl_err:
        if str(model_name).strip().lower() == "gemini-2.5-pro":
            return ""
        return f"模型 {model_name} 调用失败 (SSL Error): {ssl_err}"
    except requests.exceptions.HTTPError as http_err:
        if str(model_name).strip().lower() == "gemini-2.5-pro":
            return ""
        error_message = f"模型 {model_name} 调用失败 (HTTP Error): {http_err}"
        if http_err.response:
            try:
                error_message += f" - 响应: {http_err.response.text}"
            except Exception:
                pass
        return error_message
    except requests.exceptions.RequestException as req_err:
        if str(model_name).strip().lower() == "gemini-2.5-pro":
            return ""
        return f"模型 {model_name} 调用失败 (Request Error): {req_err}"
    except Exception as e:
        if str(model_name).strip().lower() == "gemini-2.5-pro":
            return ""
        return f"模型 {model_name} 调用时发生未知错误: {e}"


def judge_abnormalities_by_llm(analysis_results, judge_model_name="Gemini-2.5-pro"):
    """
    将各模型的文本结果交由指定大模型进行聚合裁决，返回严格JSON。
    返回示例：
    {"status":"abnormal|normal","reason":"...","abnormal_models":["模型A","模型B"]}
    """
    api_url = "https://modelservice.jdcloud.com/v1/chat/completions"
    bearer_token = "pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Authorization": f"Bearer {bearer_token}",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
    }

    lines = []
    for model, text in analysis_results.items():
        safe_text = str(text) if text is not None else ""
        lines.append(f"{model}: {safe_text}")
    joined = "\n".join(lines)

    prompt = (
        '''
        你是总结分析的专家, 根据以下多个模型的分析文本，汇总整理所有的信息。
        
        请直接按照以下结构回答用户：
        总体评分**：(正常 / 轻微瑕疵 / 严重崩坏)
        肢体检测**：[数量] - [描述] (例如：检测到 3 条胳膊，左侧腋下有多余肢体)
        五官分析**：(例如：右眼显著小于左眼，非表情原因)
        互动逻辑**：(例如：苹果悬浮在手掌前，无接触)
        其他异常**：(帽子悬浮、透视错误等)

        **重要判定规则**：
        - "正常" 或 "轻微瑕疵" -> status 为 "normal"（允许展示）
        - 只有 "严重崩坏" -> status 为 "abnormal"（不允许展示）
        
        请只输出严格的 JSON，不要额外解释：
        {"status":"abnormal|normal","reason":"简短中文原因","abnormal_models":["模型名A","模型名B"]}

        多个模型的分析如下：
        '''
        f"{joined}"
    )

    data = {
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "model": judge_model_name,
    }

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        resp_json = response.json()
        content_text = extract_text_from_response(resp_json, model_name=judge_model_name)
        if isinstance(content_text, str) and content_text.strip():
            try:
                result = json.loads(content_text.strip())
            except json.JSONDecodeError:
                m = re.search(r"\{.*\}", content_text, re.S)
                if m:
                    try:
                        result = json.loads(m.group(0))
                    except Exception:
                        result = None
                else:
                    result = None
        else:
            result = None

        if isinstance(result, dict):
            status = str(result.get("status", "")).lower()
            reason = result.get("reason") or ""
            abnormal_models = result.get("abnormal_models") or []
            if status in ("abnormal", "normal"):
                return {"status": status, "reason": reason, "abnormal_models": abnormal_models}
    except requests.exceptions.RequestException as req_err:
        return {"status": "normal", "reason": f"聚合裁决请求失败: {req_err}", "abnormal_models": []}
    except Exception as e:
        return {"status": "normal", "reason": f"聚合裁决解析失败: {e}", "abnormal_models": []}

    return {"status": "normal", "reason": "未能解析裁决结果，默认判定为正常", "abnormal_models": []}


def check_for_abnormalities(analysis_results):
    judge = judge_abnormalities_by_llm(analysis_results, judge_model_name="gpt-5")
    is_abnormal = judge.get("status") == "abnormal"
    abnormal_models = judge.get("abnormal_models", [])
    return is_abnormal, abnormal_models, judge


def analyze_image_with_multiple_models(image_path, prompt_text, models):
    analysis_results = {}
    for model in models:
        result = call_analysis_api(image_path, model, prompt_text)
        analysis_results[model] = result
        print("\n" + "#" * 20)
        print(f"模型 {model} 的分析结果: {result}")

    is_abnormal, abnormal_models, judge = check_for_abnormalities(analysis_results)

    print("\n--- 最终结论 ---")
    if is_abnormal:
        print(f"图片不合格。检测到异常的模型: {', '.join(abnormal_models)}")
    else:
        print("图片合格。所有模型均未报告明显异常。")
    if isinstance(judge, dict):
        reason = judge.get("reason")
        if isinstance(reason, str) and reason.strip():
            print(f"聚合裁决原因: {reason.strip()}")

    return not is_abnormal, analysis_results


# 新增：统一图片入参，按三个模型分别调用原始方式，再聚合裁决
def analyze_image_with_three_models(image_path: str):
    """
    使用三个模型分析图片质量，返回 (is_ok, analysis_results)
    """
    import sys
    
    def _log(msg: str):
        """带前缀的日志输出，确保立即刷新"""
        print(f"[Gate检查] {msg}", flush=True)
        sys.stdout.flush()
    
    _log(f"开始检查图片: {image_path}")
    analysis_results: dict[str, str] = {}

    # 1) Gemini Flash generations（保持原始调用方式与 Prompt）
    _log("1/2 调用 Gemini 3-Pro-Image-Preview...")
    res_flash = run_gemini_flash_generation(image_path, PROMPT_FLASH)
    _log(f"1/2 完成 - 结果长度: {len(res_flash) if res_flash else 0} 字符")
    analysis_results["Gemini 3-Pro-Image-Preview"] = res_flash

    # 2) Gemini-2.5-pro（chat/completions，使用 PROMPT_CHAT）
    # _log("2/2 调用 Gemini-2.5-pro...")
    # res_gemini_chat = call_analysis_api(image_path, "Gemini-2.5-pro", PROMPT_CHAT)
    # _log(f"2/2 完成 - 结果长度: {len(res_gemini_chat) if res_gemini_chat else 0} 字符")
    # analysis_results["Gemini-2.5-pro"] = res_gemini_chat

    # 3) Claude-opus-4（暂时禁用）
    # _log("3/3 调用 Claude-opus-4...")
    # res_claude = call_analysis_api(image_path, "Claude-opus-4", PROMPT_CHAT)
    # _log(f"3/3 完成 - 结果长度: {len(res_claude) if res_claude else 0} 字符")
    # analysis_results["Claude-opus-4"] = res_claude

    # 聚合裁决（保持原始 judge 方式）
    _log("聚合裁决中...")
    is_abnormal, abnormal_models, judge = check_for_abnormalities(analysis_results)

    if is_abnormal:
        _log(f"结果: ❌ 不合格 - 异常模型: {', '.join(abnormal_models)}")
    else:
        _log("结果: ✅ 合格")
    
    if isinstance(judge, dict):
        reason = judge.get("reason")
        if isinstance(reason, str) and reason.strip():
            _log(f"裁决原因: {reason.strip()}")

    return not is_abnormal, analysis_results


# ---------------------- 主入口 ----------------------

def main():
    image_path = CODE_IMAGE_PATH
    # 统一图片入参，按三个模型分别调用，不合并 Prompt、保持原始调用方式
    analyze_image_with_three_models(image_path)


if __name__ == "__main__":
    main()