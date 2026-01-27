import requests
import uuid
import os

url = "https://modelservice.jdcloud.com/v1/chat/completions"
# 建议传入，用于排查报错
trace_id = str(uuid.uuid4())
headers = {
    "Content-Type": "application/json",
    "Trace-Id": trace_id,
    "Authorization": f"Bearer {os.environ.get('AI_API_KEY', '')}"
}

payload = {
    # "model": "Gemini-3-Flash-Preview",
    "model": "Gemini-2.5-pro",

    "contents": [
        {
            "role": "user",
            "parts": [
                {
                    "text": "北京现在几度"
                }
            ]
        }
    ]
}

try:
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # 检查 HTTP 错误
    
    # 打印响应内容
    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())
    # 如果业务上需要对不同字段内进行处理，建议观察response结构之后，再做处理
    
except requests.exceptions.RequestException as e:
    print("Request Failed:", e)
except ValueError as e:
    print("JSON Decode Error:", e)
    # print("Raw Response:", response.text)
