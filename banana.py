import base64
import json

import requests


# --- 函数：将图片文件转换为 Base64 编码 ---
def image_to_base64(image_path):
    """
    将本地图片文件转换为 Base64 编码的字符串。
    :param image_path: 图片文件的路径
    :return: Base64 编码的字符串
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        # DMXAPI 可能需要 data URI 格式
        return f"data:image/png;base64,{encoded_string}"
    except FileNotFoundError:
        print(f"错误：找不到文件 {image_path}")
        return None


# --- API 配置 ---
API_URL = "https://www.dmxapi.com/v1/images/generations"
API_KEY = "sk-73aYhNkXxmCRDCVhAsMlh59d7qs9LRlWqhud1eVuS8bsvrgs"  # 改成你的 DMXAPI 令牌

# --- 将本地图片转换为 Base64 ---
# 请确保这两个图片文件存在于指定的路径
local_image_1_path = r"D:\project\dongdesign\joy_ip\data\joy_head\image 476.png"   # 对应修改你的图片1
local_image_2_path = r"D:\project\dongdesign\joy_ip\data\joy_body_noface\组 19.png"   # 对应修改你的图片2，并且支持更多图片

base64_image_1 = image_to_base64(local_image_1_path)
base64_image_2 = image_to_base64(local_image_2_path)

# --- 构建请求体 ---
# 只有在两个图片都成功转换后才继续
if base64_image_1 and base64_image_2:
    payload = json.dumps(
        {
            "model": "gemini-2.5-flash-image",
            "prompt": "将图1的角色头像，替换到图2身上，不要额外绘制任何内容",
            "image": [
                base64_image_1,
                base64_image_2,
            ],
        }
    )

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    # --- 发送请求 ---
    try:
        response = requests.request("POST", API_URL, headers=headers, data=payload)
        response.raise_for_status()  # 如果请求失败 (状态码不是 2xx), 则会抛出异常
        print(response.text)
    except requests.exceptions.RequestException as e:
        print(f"请求时发生错误: {e}")

else:
    print("由于一个或多个图片文件未能转换为 Base64，请求未发送。")



