import json
import sys
import os
import base64
import datetime
import hashlib
import hmac
import requests


method = 'POST'
host = 'visual.volcengineapi.com'
region = 'cn-north-1'
endpoint = 'https://visual.volcengineapi.com'
service = 'cv'

def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

def getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = sign(key.encode('utf-8'), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, 'request')
    return kSigning

def formatQuery(parameters):
    request_parameters_init = ''
    for key in sorted(parameters):
        request_parameters_init += key + '=' + parameters[key] + '&'
    request_parameters = request_parameters_init[:-1]
    return request_parameters

def _guess_ext_by_magic(data: bytes) -> str:
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if data.startswith(b'\xff\xd8'):
        return 'jpg'
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'
    if data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
        return 'gif'
    if data.startswith(b'BM'):
        return 'bmp'
    return 'bin'

def _decode_base64(s: str):
    if not isinstance(s, str):
        return None
    try:
        if s.startswith('data:image/'):
            comma = s.find(',')
            if comma != -1:
                s = s[comma+1:]
        return base64.b64decode(s, validate=False)
    except Exception:
        try:
            return base64.urlsafe_b64decode(s)
        except Exception:
            return None

def _collect_base64_candidates(obj):
    results = []
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str):
                    key_hit = any(name in k.lower() for name in ['base64','image','binary'])
                    long_text = len(v) >= 512 and all(ch not in v for ch in ['\n',' ','\r'])
                    if key_hit or long_text:
                        results.append(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for it in x:
                if isinstance(it, str):
                    # 列表中的直接字符串也作为候选
                    if len(it) >= 512 and all(ch not in it for ch in ['\n',' ','\r']):
                        results.append(it)
                else:
                    walk(it)
        elif isinstance(x, str):
            if len(x) >= 512 and all(ch not in x for ch in ['\n',' ','\r']):
                results.append(x)
    walk(obj)
    return results

def save_images_from_response(resp_json: dict, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    candidates = _collect_base64_candidates(resp_json)
    saved_paths = []
    ts = int(datetime.datetime.utcnow().timestamp())
    idx = 0
    for s in candidates:
        data = _decode_base64(s)
        if not data:
            continue
        ext = _guess_ext_by_magic(data)
        fname = f'generated_{ts}_{idx}.{ext}'
        path = os.path.join(out_dir, fname)
        try:
            with open(path, 'wb') as f:
                f.write(data)
            saved_paths.append(path)
            idx += 1
        except Exception:
            continue
    return saved_paths

def _guess_ext_from_url(url: str) -> str | None:
    low = url.lower()
    for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp']:
        if ext in low:
            return ext.strip('.')
    return None

def _collect_url_candidates(obj):
    urls = []
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str):
                    key_hit = any(name in k.lower() for name in ['url','image_url','image_urls'])
                    looks_like = v.startswith('http://') or v.startswith('https://')
                    if key_hit or looks_like:
                        urls.append(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for it in x:
                if isinstance(it, str):
                    if it.startswith('http://') or it.startswith('https://'):
                        urls.append(it)
                else:
                    walk(it)
    walk(obj)
    # 去重保持顺序
    seen = set()
    ordered = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered

def download_images_from_response(resp_json: dict, out_dir: str, timeout_sec: int = 30):
    os.makedirs(out_dir, exist_ok=True)
    urls = _collect_url_candidates(resp_json)
    saved = []
    ts = int(datetime.datetime.utcnow().timestamp())
    for idx, url in enumerate(urls):
        try:
            resp = requests.get(url, timeout=timeout_sec)
            if resp.status_code != 200:
                continue
            data = resp.content
            # 先根据URL猜扩展名，再用魔数兜底
            ext = _guess_ext_from_url(url) or _guess_ext_by_magic(data)
            fname = f'downloaded_{ts}_{idx}.{ext}'
            path = os.path.join(out_dir, fname)
            with open(path, 'wb') as f:
                f.write(data)
            saved.append(path)
        except Exception:
            continue
    return saved

def signV4Request(access_key, secret_key, service, req_query, req_body):
    if access_key is None or secret_key is None:
        print('No access key is available.')
        sys.exit()

    t = datetime.datetime.utcnow()
    current_date = t.strftime('%Y%m%dT%H%M%SZ')
    # current_date = '20210818T095729Z'
    datestamp = t.strftime('%Y%m%d')  # Date w/o time, used in credential scope
    canonical_uri = '/'
    canonical_querystring = req_query
    signed_headers = 'content-type;host;x-content-sha256;x-date'
    payload_hash = hashlib.sha256(req_body.encode('utf-8')).hexdigest()
    content_type = 'application/json'
    canonical_headers = 'content-type:' + content_type + '\n' + 'host:' + host + \
        '\n' + 'x-content-sha256:' + payload_hash + \
        '\n' + 'x-date:' + current_date + '\n'
    canonical_request = method + '\n' + canonical_uri + '\n' + canonical_querystring + \
        '\n' + canonical_headers + '\n' + signed_headers + '\n' + payload_hash
    # print(canonical_request)
    algorithm = 'HMAC-SHA256'
    credential_scope = datestamp + '/' + region + '/' + service + '/' + 'request'
    string_to_sign = algorithm + '\n' + current_date + '\n' + credential_scope + '\n' + hashlib.sha256(
        canonical_request.encode('utf-8')).hexdigest()
    # print(string_to_sign)
    signing_key = getSignatureKey(secret_key, datestamp, region, service)
    # print(signing_key)
    signature = hmac.new(signing_key, (string_to_sign).encode(
        'utf-8'), hashlib.sha256).hexdigest()
    # print(signature)

    authorization_header = algorithm + ' ' + 'Credential=' + access_key + '/' + \
        credential_scope + ', ' + 'SignedHeaders=' + \
        signed_headers + ', ' + 'Signature=' + signature
    # print(authorization_header)
    headers = {'X-Date': current_date,
               'Authorization': authorization_header,
               'X-Content-Sha256': payload_hash,
               'Content-Type': content_type
               }
    # print(headers)

    # ************* SEND THE REQUEST *************
    request_url = endpoint + '?' + canonical_querystring

    print('\nBEGIN REQUEST++++++++++++++++++++++++++++++++++++')
    print('Request URL = ' + request_url)
    try:
        r = requests.post(request_url, headers=headers, data=req_body)
    except Exception as err:
        print(f'error occurred: {err}')
        raise
    else:
        print('\nRESPONSE++++++++++++++++++++++++++++++++++++')
        print(f'Response code: {r.status_code}\n')
        # 使用 replace 方法将 \u0026 替换为 &，仅打印预览，避免输出完整base64
        resp_str = r.text.replace("\\u0026", "&")
        preview = resp_str[:300].replace('\n',' ')
        print(f'Response preview (truncated): {preview} ...\n')

        # 保存返回中的图片base64到本地
        out_dir = os.path.join(os.path.dirname(__file__), 'generated_images')
        try:
            resp_json = r.json()
        except Exception:
            try:
                resp_json = json.loads(resp_str)
            except Exception:
                resp_json = None
        if isinstance(resp_json, dict):
            saved = save_images_from_response(resp_json, out_dir)
            if saved:
                print({'saved_files': saved})
                return True  # 成功保存文件
            else:
                print({'saved_files': [], 'message': 'no base64 images found in response'})

            # 若没有base64，尝试直接下载URL
            saved_url_files = download_images_from_response(resp_json, out_dir)
            if saved_url_files:
                print({'downloaded_files': saved_url_files})
                return True  # 成功下载文件
            elif not saved:
                print({'downloaded_files': [], 'message': 'no image urls found in response'})
                return False  # 没有找到任何图片
        else:
            print("Failed to parse response JSON")
            return False


if __name__ == "__main__":
    # 请求凭证，从环境变量读取
    access_key = os.environ.get('VOLC_ACCESS_KEY', 'YOUR_ACCESS_KEY')
    secret_key = os.environ.get('VOLC_SECRET_KEY', 'YOUR_SECRET_KEY')

    # 请求Query，按照接口文档中填入即可
    query_params = {
        'Action': 'CVProcess',
        'Version': '2022-08-31',
    }
    formatted_query = formatQuery(query_params)

    # 请求Body，按照接口文档中填入即可
    body_params = {
        "req_key": "jimeng_t2i_v40",
        "image_urls": [
            "https://2.z.wiki/autoupload/P9fMWrEzi18lXM6qMBFMfSfNcKcqEnRmcljopnyJoMs/20251112/91gN/928X1120/generated_1762921507128.png/webp"
        ],
        # 默认占位，支持命令行覆盖
        "prompt": "背景换成演唱会现场",
        "scale": 0.5
    }

    # 命令行参数支持：python background-jimeng4.py <tag_img_url> <background_text>
    if len(sys.argv) >= 3:
        tag_img_url = sys.argv[1]
        background_text = sys.argv[2]
        print(f"开始处理图片生成: {tag_img_url} -> {background_text}")
        body_params["image_urls"] = [tag_img_url]
        body_params["prompt"] = f"严格保持角色表情、动作的绝对一致，并参考角色风格，将背景替换为{background_text}，同时对角色和背景进行整体光影重绘"
    else:
        print("Usage: python background-jimeng4.py <tag_img_url> <background_text>")
        sys.exit(1)
        
    formatted_body = json.dumps(body_params)
    
    try:
        success = signV4Request(access_key, secret_key, service,
                      formatted_query, formatted_body)
        if success:
            print("生成成功")
        else:
            print("生成失败")
            sys.exit(1)
    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)