import requests
import sys
import os
import json
from urllib.parse import urlparse

def _read_bytes_from_path_or_url(image_path_or_url: str):
    """读取本地或远程图片为字节，并返回(内容字节, 文件名, MIME)。"""
    if image_path_or_url.startswith("http://") or image_path_or_url.startswith("https://"):
        r = requests.get(image_path_or_url, timeout=30)
        r.raise_for_status()
        parsed = urlparse(image_path_or_url)
        filename = os.path.basename(parsed.path) or "tag_img"
        ext = os.path.splitext(filename)[1].lower()
        mime_type = 'image/jpeg'
        if ext == '.png':
            mime_type = 'image/png'
        elif ext in ('.jpg', '.jpeg'):
            mime_type = 'image/jpeg'
        elif ext == '.gif':
            mime_type = 'image/gif'
        elif ext == '.webp':
            mime_type = 'image/webp'
        return r.content, filename, mime_type
    else:
        if not os.path.exists(image_path_or_url):
            raise FileNotFoundError(f"文件不存在: {image_path_or_url}")
        filename = os.path.basename(image_path_or_url)
        ext = os.path.splitext(filename)[1].lower()
        mime_type = 'image/jpeg'
        if ext == '.png':
            mime_type = 'image/png'
        elif ext in ('.jpg', '.jpeg'):
            mime_type = 'image/jpeg'
        elif ext == '.gif':
            mime_type = 'image/gif'
        elif ext == '.webp':
            mime_type = 'image/webp'
        with open(image_path_or_url, 'rb') as f:
            return f.read(), filename, mime_type


def upload_image_to_imgbed(image_path, custom_name=None):
    """
    上传图片到图床（优先 playground.z.wiki，失败后回退 sm.ms），始终返回 JSON。

    Args:
        image_path (str): 图片文件路径或远程 URL
        custom_name (str): 自定义文件名（保留原扩展名）

    Returns:
        dict: { success, url, data, message | error }
    """

    # 读取本地或远程字节
    try:
        content, filename, mime_type = _read_bytes_from_path_or_url(image_path)
    except Exception as e:
        return {"success": False, "error": str(e)}

    # 覆盖文件名（保留扩展名）
    if custom_name:
        ext = os.path.splitext(filename)[1]
        filename = custom_name + ext

    def _parse_upload_response(resp):
        """尽可能从响应中解析出图片 URL，返回 (success, url, raw)."""
        try:
            data = resp.json()
        except Exception:
            # 非 JSON 响应，记录原文
            return False, "", resp.text

        url = ""
        if isinstance(data, dict):
            # playground.z.wiki 可能直接返回 { url: "..." }
            if 'url' in data and isinstance(data.get('url'), str):
                url = data.get('url') or ""
            # sm.ms 风格 { success: true, data: { url: "..." } }
            elif 'data' in data and isinstance(data['data'], dict):
                url = data['data'].get('url', '')
            # 其他兼容格式
            elif data.get('success') and isinstance(data.get('data'), dict):
                url = data['data'].get('url', '')

        return (bool(url), url, data)

    # 构造文件与表单
    files_primary = { 'file': (filename, content, mime_type) }
    data_primary = { 'fileName': filename, 'uid': 'heyunshenys@163.com' }

    try:
        # 1) 首选 playground.z.wiki
        try:
            resp = requests.post(
                'https://playground.z.wiki/img/api/upload',
                files=files_primary,
                data=data_primary,
                timeout=30
            )
            ok, url, raw = _parse_upload_response(resp) if resp.status_code == 200 else (False, "", resp.text)
            if ok:
                return {"success": True, "url": url, "data": raw, "message": "上传成功(playground)"}
        except requests.exceptions.RequestException:
            # 直接进入回退
            pass

        # 2) 回退 sm.ms（不带 token 情况下可能失败，但尽力）
        files_backup = { 'smfile': (filename, content, mime_type) }
        try:
            resp2 = requests.post(
                'https://sm.ms/api/v2/upload',
                files=files_backup,
                timeout=30
            )
            ok2, url2, raw2 = _parse_upload_response(resp2) if resp2.status_code == 200 else (False, "", resp2.text)
            if ok2:
                return {"success": True, "url": url2, "data": raw2, "message": "上传成功(sm.ms)"}
            else:
                return {"success": False, "error": f"上传失败，状态码: {resp2.status_code}", "response": raw2}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"网络请求失败: {str(e)}"}

    except Exception as e:
        return {"success": False, "error": f"上传过程中发生错误: {str(e)}"}

def main():
    """
    命令行入口函数
    """
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "请提供图片文件路径"
        }))
        sys.exit(1)
    
    image_path = sys.argv[1]
    custom_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = upload_image_to_imgbed(image_path, custom_name)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()