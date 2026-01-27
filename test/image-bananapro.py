import requests
import base64
import json
import os

url = "https://modelservice.jdcloud.com/v1/images/gemini_flash/generations"
headers = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Authorization": f"Bearer {os.environ.get('AI_API_KEY', '')}",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Trace-id": "test-gemini-23"
}
data = {
    "model": "Gemini-2.5-flash-image-preview",
    "contents": {
        "role": "USER",
        "parts": [
            {
                "file_data": {
                    "mime_type": "image/png",
                    "file_uri": "https://starbot.s3.cn-north-1.jdcloud-oss.com/%E4%B8%89%E6%96%87%E9%B1%BC.jpg"
                }
            },
            {
                "text": "Convert this photo to black and white, in a cartoonish style."
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

# 发送POST请求
response = requests.post(url, headers=headers, json=data)

response_data = response.json()
# 提取响应中的candidate字段
candidate = response_data["candidates"][0]
parts = candidate["content"]["parts"]

# 检查响应
if response.status_code == 200:
    resp_json = response.json()
    # 提取图片数据
    # 比较健壮的做法是先判断有没有，再获取
    text_response=''
    image_base64=''
    for part in parts:
        # 提取文本响应
        # 先判断有没有，再赋值
        if "text" in part:
            text_response += part["text"]
            print("\n文本响应:")
            print(text_response)
        # 提取图片数据
        if "inlineData" in part:
            image_base64 = part["inlineData"]["data"]
    
    # 解码并写入文件
    with open('generated_image.png', 'wb') as f:
        f.write(base64.b64decode(image_base64))
    print("图片已保存为 generated_image.png")
else:
    print("请求失败:", response.status_code)
    print(response.text)
