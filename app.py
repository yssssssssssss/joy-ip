#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP头像和身体姿势匹配系统后端API
基于用户需求分析和图片特征匹配
"""

import os
import json
import base64
import requests
from flask import Flask, request, jsonify, render_template, Response, send_from_directory
from queue import Queue
from flask_cors import CORS
from matchers.head_matcher import HeadMatcher
from matchers.body_matcher import BodyMatcher

# 导入配饰分析器
from accessory_analyzer import analyze_user_accessories, accessory_analyzer

# 导入图片处理器
from image_processor import ImageProcessor
import importlib.util
import sys

# 导入banana-1、banana-2、banana-3模块
base_dir = os.path.dirname(os.path.abspath(__file__))
banana_1_path = os.path.join(base_dir, "banana-1.py")
banana_2_path = os.path.join(base_dir, "banana-2.py")
banana_3_path = os.path.join(base_dir, "banana-3.py")

spec_1 = importlib.util.spec_from_file_location("banana_1", banana_1_path)
if spec_1 and spec_1.loader:
    banana_1 = importlib.util.module_from_spec(spec_1)
    spec_1.loader.exec_module(banana_1)
else:
    banana_1 = None
    print("无法加载 banana-1.py")

spec_2 = importlib.util.spec_from_file_location("banana_2", banana_2_path)
if spec_2 and spec_2.loader:
    banana_2 = importlib.util.module_from_spec(spec_2)
    spec_2.loader.exec_module(banana_2)
else:
    banana_2 = None
    print("无法加载 banana-2.py")

spec_3 = importlib.util.spec_from_file_location("banana_3", banana_3_path)
if spec_3 and spec_3.loader:
    banana_3 = importlib.util.module_from_spec(spec_3)
    spec_3.loader.exec_module(banana_3)
else:
    banana_3 = None
    print("无法加载 banana-3.py")

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

# 配置 output 文件夹为静态目录


# 创建全局匹配器实例
head_matcher = HeadMatcher()
body_matcher = BodyMatcher()

# 创建图片处理器实例
image_processor = ImageProcessor()

# 简单的SSE日志队列存储（按请求ID）
log_queues = {}

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


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/output/<path:filename>')
def serve_output_file(filename):
    """提供output文件夹中的静态文件访问"""
    return send_from_directory('output', filename)

@app.route('/generated_images/<path:filename>')
def serve_generated_image(filename):
    """提供generated_images文件夹中的静态文件访问"""
    return send_from_directory('generated_images', filename)

@app.route('/api/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        requirement = data.get('requirement', '')
        stream_id = data.get('stream_id')
        
        if not requirement:
            return jsonify({
                'success': False,
                'message': '请输入需求描述'
            })
        
        # 初始化处理步骤记录
        processing_steps = []
        
        # 如果提供了日志流ID，则初始化队列并定义日志回调
        emit_log = None
        if stream_id:
            q = log_queues.get(stream_id)
            if q is None:
                q = Queue()
                log_queues[stream_id] = q
            def emit_log_fn(msg: str):
                try:
                    q.put(msg)
                except Exception:
                    pass
            emit_log = emit_log_fn
        
        # 步骤1：分析用户需求
        processing_steps.append("开始分析用户需求...")
        if emit_log:
            emit_log("开始分析用户需求...")
        
        # 步骤2：调用头像匹配器
        processing_steps.append("正在分析头像特征...")
        if emit_log:
            emit_log("正在分析头像特征...")
        head_matches, head_logs = head_matcher.find_best_matches(requirement, top_k=3, log_callback=emit_log)
        processing_steps.extend(head_logs)
        
        # 步骤3：调用身体姿势匹配器
        processing_steps.append("正在分析身体姿势特征...")
        if emit_log:
            emit_log("正在分析身体姿势特征...")
        body_matches, body_logs = body_matcher.find_best_matches(requirement, top_k=3, log_callback=emit_log)
        processing_steps.extend(body_logs)
        
        # 处理头像匹配结果
        head_results = []
        for match in head_matches:
            image_path = match['image_path']
            image_url = head_matcher.convert_image_to_base64(image_path)
            
            if image_url:
                head_results.append({
                    'image_name': match['image_name'],
                    'image_url': image_url,
                    'image_path': image_path,  # 添加图片路径
                    'score': round(match['score'], 1),
                    'dimension_scores': {k: round(v, 1) for k, v in match['dimension_scores'].items()},
                    'features': match['features'],
                    'requirement_features': match['requirement_features'],
                    'type': 'head'
                })
        
        # 处理身体姿势匹配结果
        body_results = []
        for match in body_matches:
            image_path = match['image_path']
            image_url = body_matcher.convert_image_to_base64(image_path)
            
            if image_url:
                body_results.append({
                    'image_name': match['image_name'],
                    'image_url': image_url,
                    'image_path': image_path,  # 添加图片路径
                    'score': round(match['score'], 1),
                    'dimension_scores': {k: round(v, 1) for k, v in match['dimension_scores'].items()},
                    'features': match['features'],
                    'requirement_features': match['requirement_features'],
                    'type': 'body'
                })
        
        # 步骤4：处理结果完成
        processing_steps.append("所有匹配分析完成！")
        if emit_log:
            emit_log("所有匹配分析完成！")
            # 通知前端日志结束
            emit_log("__DONE__")
        
        return jsonify({
            'success': True,
            'head_results': head_results,
            'body_results': body_results,
            'requirement': requirement,
            'processing_steps': processing_steps
        })
        
    except Exception as e:
        print(f"搜索失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'搜索失败: {str(e)}'
        })

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy'
    })

@app.route('/api/logs/<stream_id>')
def stream_logs(stream_id: str):
    """SSE实时日志流"""
    def event_stream():
        # 若队列未初始化，则创建并注册，避免前端先连接导致未初始化
        q = log_queues.get(stream_id)
        if q is None:
            q = Queue()
            log_queues[stream_id] = q
        while True:
            msg = q.get()
            yield f"data: {msg}\n\n"
            if msg == "__DONE__":
                break
        # 处理完成后清理队列
        try:
            log_queues.pop(stream_id, None)
        except Exception:
            pass
    headers = {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    }
    return Response(event_stream(), mimetype='text/event-stream', headers=headers)

@app.route('/api/combine-images', methods=['POST'])
def combine_images():
    """新的图片组合API端点"""
    try:
        data = request.get_json()
        requirement = data.get('requirement', '')
        
        if not requirement:
            return jsonify({
                'success': False,
                'error': '请提供用户需求描述'
            }), 400
        
        # 使用图片处理器处理需求
        result = image_processor.process_user_requirement(requirement)
        
        if result['success']:
            # 将生成的图片路径转换为URL格式返回
            combined_images_urls = []
            for img_path in result['combined_images']:
                if os.path.exists(img_path):
                    # 将绝对路径转换为相对于output文件夹的路径
                    relative_path = os.path.relpath(img_path, 'output')
                    # 构建URL路径
                    img_url = f"/output/{relative_path.replace(os.sep, '/')}"
                    combined_images_urls.append({
                        'path': img_path,
                        'url': img_url,
                        'filename': os.path.basename(img_path)
                    })
            
            return jsonify({
                'success': True,
                'action_type': result['action_type'],
                'total_generated': result['total_generated'],
                'combined_images': combined_images_urls,
                'body_images_count': len(result['body_images']),
                'head_images_count': len(result['head_images'])
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '处理失败'),
                'action_type': result.get('action_type', '未知')
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/add-accessories', methods=['POST'])
def add_accessories():
    """第一阶段：生成不含帽子的图片"""
    try:
        data = request.get_json()
        requirement = data.get('requirement', '')
        combined_image_paths = data.get('combined_image_paths', [])

        if not combined_image_paths:
            return jsonify({'success': False, 'error': '缺少组合图片路径'}), 400

        # 分析配饰和帽子信息
        accessories_info = analyze_user_accessories(requirement)
        hat_info = accessory_analyzer.analyze_hat_info(requirement)

        # 调用 banana-2.py 生成带配饰的图片
        generated_image_url_stage1 = banana_2.generate_image_with_accessories(
            combined_image_paths[0], 
            accessories_info
        )

        if generated_image_url_stage1:
            return jsonify({
                'success': True,
                # banana_2 返回的已是 '/output/xxx.png' URL，直接返回即可
                'stage1_image_url': generated_image_url_stage1,
                'hat_info': hat_info
            })
        else:
            return jsonify({'success': False, 'error': '第一阶段图片生成失败'}), 500

    except Exception as e:
        print(f"[add-accessories] 端点错误: {e}")
        return jsonify({'success': False, 'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/add-hat', methods=['POST'])
def add_hat():
    """第二阶段：为图片添加帽子"""
    try:
        data = request.get_json()
        stage1_image_url = data.get('stage1_image_url', '')
        hat_info = data.get('hat_info', '')

        if not stage1_image_url or not hat_info:
            return jsonify({'success': False, 'error': '缺少第一阶段图片URL或帽子信息'}), 400

        # 将URL转换回本地文件路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # 第一阶段图片保存在 output 目录，因此从 URL 中取文件名并拼接到 output
        image_filename = os.path.basename(stage1_image_url)
        stage1_image_path = os.path.join(base_dir, 'output', image_filename)

        # 调用 banana-1.py 生成带帽子的图片
        final_image_path = banana_1.generate_image_with_accessories(stage1_image_path, hat_info) if banana_1 else None

        # 同时调用 banana-3.py 的两步流程：将步骤一生成的帽子（img_hat）戴到阶段一结果图的角色头上
        banana3_image_url = None
        if banana_3:
            try:
                # MOCK: 指定参考图片（用于生成 img_hat）——后续可替换为你希望的后端地址
                specified_image_path = r"D:\project\dongdesign\joy_ip_3D\data\clothes\demo.png"

                # 将阶段一的本地路径传入 banana-3 第二步，进行两图叠加
                banana3_image_url = banana_3.generate_two_step_hat_to_stage1(
                    specified_image_path,
                    stage1_image_path,
                    hat_info
                )
            except Exception as e:
                print(f"[add-hat] 调用 banana-3 失败: {e}")

        if final_image_path:
            final_image_url = final_image_path
            return jsonify({
                'success': True,
                'final_image_url': final_image_url,
                'banana3_image_url': banana3_image_url
            })
        else:
            return jsonify({'success': False, 'error': '未能生成最终图片'}), 500

    except Exception as e:
        print(f"[add-hat] 端点错误: {e}")
        return jsonify({'success': False, 'error': f'服务器错误: {str(e)}'}), 500



if __name__ == '__main__':
    # 确保模板目录存在
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("启动IP头像和身体姿势匹配系统...")
    
    app.run(debug=True, host='0.0.0.0', port=6001)
    
    