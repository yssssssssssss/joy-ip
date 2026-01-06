import requests
import json
import hmac
from hashlib import sha1
import base64
import time
import uuid


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
 
 
def process_style_image(face_image_url, style_image_url):
    """
    处理风格图片，将用户脸部与风格图片进行融合
    :param face_image_url: 用户脸部图片URL
    :param style_image_url: 风格图片URL
    :return: 处理后的图片URL，如果失败返回None
    """
    generateUuid = ""
    # 生成签名
    sign, timestamp, signature_nonce = make_sign(comfyui_url)
 
    # 准备请求参数
    uri = 'https://openapi.liblibai.cloud/api/generate/comfyui/app'  # 根据API地址更新uri
 
    uri = f"{uri}?AccessKey={ACCESS_KEY}&Signature={sign}&Timestamp={timestamp}&SignatureNonce={signature_nonce}"
    print(f"处理风格图片: {style_image_url}")
 
    headers = {
        'Content-Type': 'application/json'
    }
 
    data = {
        "templateUuid": "4df2efa0f18d46dc9758803e478eb51c",
        "generateParams": {
            "27": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "freckles"
                }
            },
            "28": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "Perfect skin"
                }
            },
            "49": {
                # 脸部图片
                "class_type": "LoadImage",
                "inputs": {
                    "image": face_image_url
                }
            },
            "40": {
                # 身体图片（风格图片）
                "class_type": "LoadImage",
                "inputs": {
                    "image": style_image_url
                }
            },
            "271": {
                "class_type": "LayerMask: PersonMaskUltra V2",
                "inputs": {
                    "face": True,
                    "hair": False
                }
            },
            "workflowUuid": "ae99b8cbe39a4d66a467211f45ddbda5"
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
                    
                    if images:
                        processed_image_url = images[0].get("imageUrl", "")
                        print(f"风格图片处理完成: {processed_image_url}")
                        return processed_image_url
                    else:
                        print("风格图片处理失败：未生成图片")
                        return None
                else:
                    print("风格图片处理失败：生成过程出错")
                    return None
            else:
                print(f"风格图片处理API响应格式错误: {result}")
                return None
        else:
            print(f"风格图片处理API调用失败，状态码: {response.status_code}, 响应: {response.text}")
            return None
    except Exception as e:
        import traceback
        print(f"风格图片处理过程中出错: {e}")
        print(f"错误堆栈: {traceback.format_exc()}")
        return None


def call_liblibai_api():
    generateUuid = ""
    # 生成签名
    sign, timestamp, signature_nonce = make_sign(comfyui_url)
 
    # 准备请求参数
    uri = 'https://openapi.liblibai.cloud/api/generate/comfyui/app'  # 根据API地址更新uri
 
    uri = f"{uri}?AccessKey={ACCESS_KEY}&Signature={sign}&Timestamp={timestamp}&SignatureNonce={signature_nonce}"
    print(uri)
 
    headers = {
        'Content-Type': 'application/json'
    }
 
    data = {
    "templateUuid": "4df2efa0f18d46dc9758803e478eb51c",
    "generateParams": {
        "27": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "freckles"
            }
        },
        "28": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "Perfect skin"
            }
        },
        "49": {
            # 脸部图片
            "class_type": "LoadImage",
            "inputs": {
                "image": "https://s.fukit.cn/autoupload/P9fMWrEzi18lXM6qMBFMfSfNcKcqEnRmcljopnyJoMs/20251015/iaD6/500X500/%E6%B2%9B%E7%8F%88_jpg_NBEqjw.png/webp"
            }
        },
        "40": {
            # 身体图片
            "class_type": "LoadImage",
            "inputs": {
                "image": "https://s.fukit.cn/autoupload/P9fMWrEzi18lXM6qMBFMfSfNcKcqEnRmcljopnyJoMs/20251015/GaPs/1024X1536/%E9%85%B7%E9%A3%9212.png/webp"
            }
        },
        "271": {
            "class_type": "LayerMask: PersonMaskUltra V2",
            "inputs": {
                "face": True,
                "hair": False
            }
        },
        "workflowUuid": "ae99b8cbe39a4d66a467211f45ddbda5"
    }
}
 
    try:
        # 发送POST请求
        response = requests.post(uri, headers=headers, data=json.dumps(data))
        # 处理响应
        if response.status_code == 200:
            result = response.json()
            generateUuid = result['data']['generateUuid']
            print('API调用成功，返回结果：', result)
        else:
            print('API调用失败，状态码：', response.status_code, '，响应内容：', response.text)
    except requests.exceptions.RequestException as e:
        print('请求异常：', e)
 
    return generateUuid
 
 
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
    
    parser = argparse.ArgumentParser(description='LibLibAI 脸部融合处理')
    parser.add_argument('--face-url', required=False, help='脸部图片URL')
    parser.add_argument('--style-url', required=False, help='风格图片URL')
    args = parser.parse_args()
    
    # 如果提供了参数，使用process_style_image函数
    if args.face_url and args.style_url:
        print(f"使用动态参数进行图片处理")
        print(f"脸部图片URL: {args.face_url}")
        print(f"风格图片URL: {args.style_url}")
        
        result_url = process_style_image(args.face_url, args.style_url)
        if result_url:
            print(json.dumps({
                "success": True,
                "processed_image_url": result_url,
                "face_url": args.face_url,
                "style_url": args.style_url
            }, ensure_ascii=False))
        else:
            print(json.dumps({
                "success": False,
                "error": "图片处理失败",
                "face_url": args.face_url,
                "style_url": args.style_url
            }, ensure_ascii=False))
    else:
        # 原有的硬编码逻辑作为备用
        print("使用硬编码参数进行测试")
        generateUuid = call_liblibai_api()
        if generateUuid != "":
            print("generateUuid:", generateUuid)
            # 等待生成完成
            result = wait_for_generation_complete(generateUuid)
            
            if result and result.get('code') == 0:
                data = result.get('data', {})
                images = data.get('images', [])
                
                if images:
                    image_url = images[0].get("imageUrl", "")
                    print(f"generateUuid：{generateUuid}")
                    print(f"图片地址：{image_url}")
                else:
                    print("未生成图片")
            else:
                print("图片生成失败或超时")