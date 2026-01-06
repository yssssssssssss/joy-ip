import requests
import json
import hmac
from hashlib import sha1
import base64
import time
import uuid
import os
import re


# 配置信息
ACCESS_KEY = os.environ.get('LIBLIB_ACCESS_KEY', 'YOUR_ACCESS_KEY')  # 从环境变量读取
SECRET_KEY = os.environ.get('LIBLIB_SECRET_KEY', 'YOUR_SECRET_KEY')  # 从环境变量读取


# 请求API接口的uri地址
comfyui_url = "/api/generate/comfyui/app"
comfyui_result_url = "/api/generate/comfy/status"
 
 
def make_sign(uri):
    """
    生成签名
    """
    # 当前毫秒时间戳
    timestamp = str(int(time.time() * 1000))
    # 随机字符串
    signature_nonce = str(uuid.uuid4()).replace('-', '')
    # 拼接请求数据
    content = '&'.join((uri, timestamp, signature_nonce))
 
    # 生成签名
    digest = hmac.new(SECRET_KEY.encode(), content.encode(), sha1).digest()
    # 移除为了补全base64位数而填充的尾部等号
    sign = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
    return sign, timestamp, signature_nonce
 
 
def process_style_image(image_url):
    """
    根据单一参考图片URL触发工作流生成角度变化结果。
    :param image_url: 参考图片的远程URL或可访问路径
    :return: 处理后的图片URL，如果失败返回None
    """
    generateUuid = ""
    # 生成签名
    sign, timestamp, signature_nonce = make_sign(comfyui_url)
 
    # 准备请求参数
    uri = 'https://openapi.liblibai.cloud/api/generate/comfyui/app'  # 根据API地址更新uri
 
    uri = f"{uri}?AccessKey={ACCESS_KEY}&Signature={sign}&Timestamp={timestamp}&SignatureNonce={signature_nonce}"
    print(f"处理图片: {image_url}")
 
    headers = {
        'Content-Type': 'application/json'
    }
 
    data = {
            "templateUuid": "4df2efa0f18d46dc9758803e478eb51c",
            "generateParams": {
                "329": {
                    "class_type": "LoadImage",
                    "inputs": {
                        "image": image_url
                    }
                },
                "334": {
                    "class_type": "ImpactInt",
                    "inputs": {
                        "value": 1536
                    }
                },
                "workflowUuid": "068f8b20880f4018acd8987fbf0eaa3b"
            }
}
 
    try:
        # 发送POST请求
        response = requests.post(uri, headers=headers, data=json.dumps(data))
        # 处理响应
        if response.status_code == 200:
            result = response.json()
            print(f"DEBUG: API响应结果: {result}")
            if result and isinstance(result, dict) and 'data' in result and result['data'] is not None and 'generateUuid' in result['data']:
                generateUuid = result['data']['generateUuid']
                print('风格图片处理API调用成功')
                
                # 等待生成完成
                print(f"DEBUG: 开始等待生成完成，generateUuid: {generateUuid}")
                final_result = wait_for_generation_complete(generateUuid)
                print(f"DEBUG: final_result type: {type(final_result)}, value: {final_result}")
                
                if final_result is not None and isinstance(final_result, dict) and final_result.get('code') == 0:
                    data = final_result.get('data', {})
                    images = data.get('images', [])

                    # 下载所有生成图片到本地 output 目录
                    def ensure_output_dir():
                        # 保证输出目录为项目根目录下的 output
                        root_dir = os.path.dirname(os.path.abspath(__file__))
                        out_dir = os.path.join(root_dir, 'output')
                        os.makedirs(out_dir, exist_ok=True)
                        return out_dir

                    def infer_ext(url: str) -> str:
                        m = re.search(r"\.(png|jpg|jpeg|webp|gif)(?:\?|$)", url, re.IGNORECASE)
                        if m:
                            ext = m.group(1).lower()
                            return 'jpg' if ext == 'jpeg' else ext
                        return 'png'

                    saved_urls = []  # 以 '/output/xxx.ext' 形式返回，便于前端直接显示
                    if images and isinstance(images, list):
                        out_dir = ensure_output_dir()
                        base_ts = int(time.time())
                        for idx, item in enumerate(images):
                            try:
                                remote = item.get('imageUrl') if isinstance(item, dict) else None
                                if not remote or not isinstance(remote, str) or len(remote) == 0:
                                    continue
                                ext = infer_ext(remote)
                                file_name = f"generated_{base_ts}_{idx}.{ext}"
                                file_path = os.path.join(out_dir, file_name)

                                resp = requests.get(remote, timeout=30)
                                if resp.status_code == 200:
                                    with open(file_path, 'wb') as f:
                                        f.write(resp.content)
                                    saved_urls.append(f"/output/{file_name}")
                                else:
                                    print(f"下载失败: {remote}，状态码: {resp.status_code}")
                            except Exception as e:
                                print(f"下载异常: {e}")

                    if saved_urls:
                        print(f"图片处理完成，共保存 {len(saved_urls)} 张")
                        # 返回列表，主流程将选取第一张作为 processed_image_url，同时输出完整 images 数组
                        return saved_urls
                    else:
                        print("图片处理失败：未生成图片")
                        return []
                else:
                    print("图片处理失败：生成过程出错")
                    return []
            else:
                print(f"图片处理API响应格式错误: {result}")
                return []
        else:
            print(f"图片处理API调用失败，状态码: {response.status_code}, 响应: {response.text}")
            return []
    except Exception as e:
        import traceback
        print(f"图片处理过程中出错: {e}")
        print(f"错误堆栈: {traceback.format_exc()}")
        return []



def get_cd_laowang_img(generateUuid):
    result = {}
    # 生成签名
    sign, timestamp, signature_nonce = make_sign(comfyui_result_url)
 
    # 准备请求参数
    uri = 'https://openapi.liblibai.cloud/api/generate/comfy/status'  # 根据API地址更新uri
 
    uri = f"{uri}?AccessKey={ACCESS_KEY}&Signature={sign}&Timestamp={timestamp}&SignatureNonce={signature_nonce}"
    print(uri)
 
    headers = {
        'Content-Type': 'application/json'
    }
 
    data = {
        "generateUuid": generateUuid,
    }
 
    try:
        # 发送POST请求
        response = requests.post(uri, headers=headers, data=json.dumps(data))
        # 处理响应
        if response.status_code == 200:
            result = response.json()
            print('API调用成功，返回结果：', result)
        else:
            print('API调用失败，状态码：', response.status_code, '，响应内容：', response.text)
    except requests.exceptions.RequestException as e:
        print('请求异常：', e)
 
    return result
 
 
def wait_for_generation_complete(generateUuid, max_wait_time=300, poll_interval=5):
    """
    等待图片生成完成
    :param generateUuid: 生成UUID
    :param max_wait_time: 最大等待时间（秒）
    :param poll_interval: 轮询间隔（秒）
    :return: 生成结果或None
    """
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        result = get_cd_laowang_img(generateUuid)
        print(f"DEBUG: get_cd_laowang_img返回结果类型: {type(result)}, 值: {result}")
        
        if result and result.get('code') == 0:
            data = result.get('data', {})
            generate_status = data.get('generateStatus', 0)
            images = data.get('images', [])
            
            print(f"生成状态: {generate_status}, 完成度: {data.get('percentCompleted', 0)}")
            print(f"DEBUG: images数据: {images}")
            print(f"DEBUG: generate_status类型: {type(generate_status)}, 值: {generate_status}")
            
            # 确保generate_status不为None
            if generate_status is None:
                print("generate_status为None，设置为默认值0")
                generate_status = 0
            
            # 生成状态: 1-等待中, 2-生成中, 3-生成完成, 4-生成失败, 5-其他完成状态?
            if generate_status in [3, 5]:  # 生成完成(包括状态5)
                if images:
                    print(f"DEBUG: 生成完成，返回结果: {result}")
                    return result
                else:
                    print("生成完成但未返回图片")
                    return result
            elif generate_status == 4:  # 生成失败
                print("图片生成失败")
                return result
            elif generate_status in [1, 2]:  # 等待中或生成中
                print(f"等待生成完成... ({int(time.time() - start_time)}秒)")
                time.sleep(poll_interval)
            else:
                print(f"未知生成状态: {generate_status}")
                # 检查是否有图片返回，如果有则直接返回
                if images:
                    print(f"DEBUG: 未知状态但有图片，返回结果: {result}")
                    return result
                time.sleep(poll_interval)
        else:
            print(f"获取生成状态失败，result: {result}")
            if result:
                print(f"DEBUG: result存在但code不为0，code值: {result.get('code')}")
            time.sleep(poll_interval)
    
    print("等待超时")
    return None
 
 
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='LibLibAI 角度变换处理')
    parser.add_argument('--image-url', required=False, help='参考图片URL')
    args = parser.parse_args()
    
    # 如果提供了参数，使用process_style_image函数
    if args.image_url:
        print("使用动态参数进行图片处理")
        print(f"参考图片URL: {args.image_url}")

        result_list = process_style_image(args.image_url)
        if isinstance(result_list, list) and len(result_list) > 0:
            first_url = result_list[0]
            print(json.dumps({
                "success": True,
                "processed_image_url": first_url,
                "images": result_list,
                "image_url": args.image_url
            }, ensure_ascii=False))
        else:
            print(json.dumps({
                "success": False,
                "error": "图片处理失败",
                "images": [],
                "image_url": args.image_url
            }, ensure_ascii=False))
    else:
        # 缺少必要参数，直接返回错误JSON，避免未定义函数调用
        print(json.dumps({
            "success": False,
            "error": "缺少参数: image_url",
        }, ensure_ascii=False))