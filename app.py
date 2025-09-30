#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP头像和身体姿势匹配系统后端API
基于用户需求分析和图片特征匹配
"""

import os
from flask import Flask, request, jsonify, render_template, Response
from queue import Queue
from flask_cors import CORS
from matchers.head_matcher import HeadMatcher
from matchers.body_matcher import BodyMatcher

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 创建全局匹配器实例
head_matcher = HeadMatcher()
body_matcher = BodyMatcher()

# 简单的SSE日志队列存储（按请求ID）
log_queues = {}

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

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
        'status': 'healthy',
        'head_matcher': {
            'excel_loaded': not head_matcher.df.empty,
            'excel_records': len(head_matcher.df) if not head_matcher.df.empty else 0
        },
        'body_matcher': {
            'excel_loaded': not body_matcher.df.empty,
            'excel_records': len(body_matcher.df) if not body_matcher.df.empty else 0
        }
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

if __name__ == '__main__':
    # 确保模板目录存在
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("启动IP头像和身体姿势匹配系统...")
    print(f"头像数据状态: {'已加载' if not head_matcher.df.empty else '未加载'} ({len(head_matcher.df)}条记录)")
    print(f"身体姿势数据状态: {'已加载' if not body_matcher.df.empty else '未加载'} ({len(body_matcher.df)}条记录)")
    
    app.run(debug=True, host='0.0.0.0', port=5000)