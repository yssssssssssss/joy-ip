#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Joy IP 3D 图片生成系统 - 主应用
整合所有功能模块
"""

import os
import json
import base64
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import threading
import time
import uuid
from matchers.head_matcher import HeadMatcher
from matchers.body_matcher import BodyMatcher
from content_agent import ContentAgent
from generation_controller import GenerationController
from image_processor import ImageProcessor
import re
from config import get_config

# 获取配置
config = get_config()

# 配置日志
log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO'))
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# 如果指定了日志文件，同时输出到文件和控制台
log_file = os.environ.get('LOG_FILE')
if log_file:
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # 配置日志处理器
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
else:
    # 仅输出到控制台
    logging.basicConfig(
        level=log_level,
        format=log_format
    )

logger = logging.getLogger(__name__)

# 初始化Flask应用
# 如果启用单端口模式，配置静态文件目录
if config.SINGLE_PORT_MODE:
    app = Flask(__name__, 
                static_folder=config.FRONTEND_BUILD_DIR,
                static_url_path='')
    logger.info(f"单端口模式已启用，静态文件目录: {config.FRONTEND_BUILD_DIR}")
else:
    app = Flask(__name__)
    logger.info("前后端分离模式")

# 配置CORS
if config.CORS_ENABLED:
    CORS(app, origins=config.CORS_ORIGINS)
    logger.info(f"CORS已启用，允许的源: {config.CORS_ORIGINS}")
else:
    logger.info("CORS已禁用（单端口模式）")

# 创建全局实例
head_matcher = HeadMatcher()
body_matcher = BodyMatcher()
content_agent = ContentAgent()
generation_controller = GenerationController()
image_processor = ImageProcessor()

def is_valid_accessory(label: str, val: str) -> bool:
    """模块级的配饰值合法性校验，避免跨标签错位和无效值。
    - 过滤空值与非字符串
    - 过滤以其他标签开头的错位值
    - 过滤否定/无值（背景保留“无”）
    - 过滤明显交叉关键词（手拿包含头戴、头戴包含手拿）
    """
    if not isinstance(val, str):
        return False
    v = val.strip()
    if not v:
        return False
    for other in ['服装','手拿','头戴','背景']:
        if other != label and re.match(rf"^{other}[：:]", v):
            return False
    none_words = {"无","没有","未提供","不带","不戴","不拿"}
    if v in none_words and label != '背景':
        return False
    if label == '手拿' and '头戴' in v:
        return False
    if label == '头戴' and '手拿' in v:
        return False
    return True

# =========================
# 简单任务队列（内存版）
# =========================
jobs = {}
jobs_lock = threading.Lock()

def _init_job(requirement: str) -> str:
    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {
            'job_id': job_id,
            'status': 'queued',  # queued | running | succeeded | failed
            'progress': 0,
            'stage': 'queued',
            'requirement': requirement,
            'analysis': None,
            'images': [],
            'error': None,
            'details': {},
            'logs': [],
            'created_at': time.time(),
            'updated_at': time.time(),
        }
    return job_id

def _update_job(job_id: str, **fields):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return
        job.update(fields)
        job['updated_at'] = time.time()

def _append_log(job_id: str, text: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return
        job['logs'].append(text)
        job['updated_at'] = time.time()

def _run_generation_job(job_id: str, requirement: str):
    """在后台线程中执行完整生成流程，并持续更新任务状态"""
    try:
        _update_job(job_id, status='running', stage='analyze', progress=5)
        _append_log(job_id, f"收到生成请求: {requirement}")

        # 为避免线程间共享对象不安全，在线程中创建本地实例
        local_head = HeadMatcher()
        local_body = BodyMatcher()
        local_agent = ContentAgent()
        local_controller = GenerationController()
        local_processor = ImageProcessor()

        # 步骤1: 合规检查和内容分析
        agent_result = local_agent.process_content(requirement)
        if not agent_result['compliant']:
            _update_job(job_id, status='failed', stage='analyze', error=f"内容不合规: {agent_result['reason']}")
            return

        analysis = agent_result['analysis']
        # 统一对分析结果做一次防御性清洗，避免交叉标签误填
        def _sanitize(val: str, label: str) -> str:
            if not isinstance(val, str):
                return ''
            v = val.strip()
            if not v:
                return ''
            # 若以其他标签开头则视为误填
            for other in ['服装','手拿','头戴','背景']:
                if other != label and re.match(rf"^{other}[：:]", v):
                    return ''
            # 否定词处理（背景保留“无”）
            none_words = {"无","没有","未提供","不带","不戴","不拿"}
            if v in none_words:
                return '无' if label == '背景' else ''
            # 特殊交叉关键字
            if label == '手拿' and '头戴' in v:
                return ''
            if label == '头戴' and '手拿' in v:
                return ''
            return v
        try:
            import re
            for k in ['服装','手拿','头戴','背景']:
                if k in analysis:
                    analysis[k] = _sanitize(analysis.get(k, ''), k)
        except Exception:
            pass
        _update_job(job_id, analysis=analysis, progress=15)

        # 步骤2: 表情与动作分析
        _update_job(job_id, stage='match', progress=25)
        expression_info = local_head.analyze_user_requirement(requirement)
        action_type = local_body.classify_action_type(requirement)
        analysis['动作'] = action_type
        _append_log(job_id, f"表情分析: {expression_info}")
        _append_log(job_id, f"动作类型: {action_type}")

        # 步骤3: 选择与组合基础图片
        _update_job(job_id, stage='compose', progress=35)
        processor_result = local_processor.process_user_requirement(requirement)
        if not processor_result['success']:
            _update_job(job_id, status='failed', stage='compose', error=processor_result.get('error', '图片处理失败'), details={
                'action_type': processor_result.get('action_type'),
                'body_images': processor_result.get('body_images', []),
                'head_images': processor_result.get('head_images', []),
                'total_generated': processor_result.get('total_generated', 0)
            })
            return

        combined_images = processor_result['combined_images']
        _append_log(job_id, f"生成基础组合图片 {len(combined_images)} 张")

        # 步骤4-9: 添加配饰
        final_images = combined_images
        _update_job(job_id, stage='decorate', progress=50)

        
        # 使用模块级校验方法，避免局部定义导致其他路由不可用
        # 见文件顶部的 is_valid_accessory()

        clothes = analysis.get('服装', '')
        if is_valid_accessory('服装', clothes):
            _append_log(job_id, f"添加服装: {clothes}")
            final_images = local_controller.process_clothes(final_images, clothes)
            _update_job(job_id, progress=60)

        hands = analysis.get('手拿', '')
        if is_valid_accessory('手拿', hands):
            _append_log(job_id, f"添加手拿物品: {hands}")
            final_images = local_controller.process_hands(final_images, hands)
            _update_job(job_id, progress=70)

        hats = analysis.get('头戴', '')
        if is_valid_accessory('头戴', hats):
            _append_log(job_id, f"添加头戴物品: {hats}")
            final_images = local_controller.process_hats(final_images, hats)
            _update_job(job_id, progress=80)

        # 步骤10: 验证图片并转为URL
        _update_job(job_id, stage='validate', progress=90)
        validated_images = []
        for img_path in final_images:
            if os.path.exists(img_path):
                validated_images.append(img_path)

        if len(validated_images) == 0:
            _update_job(job_id, status='failed', error='图片生成过程中出现问题，没有找到生成的文件', details={
                'generated_count': len(final_images),
                'passed_count': 0,
                'reason': '图片文件不存在'
            })
            return

        image_urls = []
        for img_path in validated_images:
            if img_path.startswith('output/'):
                img_url = f"/{img_path.replace(os.sep, '/')}"
            else:
                relative_path = os.path.relpath(img_path, '.')
                img_url = f"/{relative_path.replace(os.sep, '/')}"
            image_urls.append(img_url)

        _update_job(job_id, images=image_urls, progress=100, stage='done', status='succeeded', details={
            'generated_count': len(final_images),
            'passed_count': len(validated_images)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        _update_job(job_id, status='failed', error=f'服务器错误: {str(e)}')


# 配置output文件夹为静态目录
@app.route('/output/<path:filename>')
def serve_output_file(filename):
    """提供output文件夹中的静态文件访问"""
    return send_from_directory('output', filename)

@app.route('/generated_images/<path:filename>')
def serve_generated_image(filename):
    """提供generated_images文件夹中的静态文件访问"""
    return send_from_directory('generated_images', filename)


@app.route('/api/start_generate', methods=['POST'])
def start_generate():
    """启动生成任务，立即返回 job_id，前端可轮询状态"""
    try:
        data = request.get_json() or {}
        requirement = data.get('requirement', '')
        if not requirement:
            return jsonify({'success': False, 'error': '请输入需求描述'}), 400

        job_id = _init_job(requirement)

        t = threading.Thread(target=_run_generation_job, args=(job_id, requirement), daemon=True)
        t.start()

        return jsonify({'success': True, 'job_id': job_id})
    except Exception as e:
        return jsonify({'success': False, 'error': f'启动任务失败: {str(e)}'}), 500


@app.route('/api/job/<job_id>/status', methods=['GET'])
def job_status(job_id: str):
    """查询任务状态"""
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        # 返回只读视图
        return jsonify({
            'success': True,
            'job': {
                'job_id': job['job_id'],
                'status': job['status'],
                'progress': job['progress'],
                'stage': job['stage'],
                'analysis': job['analysis'],
                'images': job['images'],
                'error': job['error'],
                'details': job['details'],
                'updated_at': job['updated_at'],
            }
        })


@app.route('/api/generate', methods=['POST'])
def generate():
    """
    完整的图片生成API
    1. 接收用户输入
    2. 合规检查和内容分析
    3. 匹配head和body
    4. 生成基础图片
    5. 逐步添加服装、手拿、头戴
    6. 返回最终图片
    """
    try:
        data = request.get_json()
        requirement = data.get('requirement', '')
        
        if not requirement:
            return jsonify({
                'success': False,
                'error': '请输入需求描述'
            }), 400
        
        print(f"\n{'='*60}")
        print(f"收到生成请求: {requirement}")
        print(f"{'='*60}\n")
        
        # 步骤1: 合规检查和内容分析
        print("步骤1: 合规检查和内容分析...")
        agent_result = content_agent.process_content(requirement)
        
        if not agent_result['compliant']:
            return jsonify({
                'success': False,
                'error': f"内容不合规: {agent_result['reason']}"
            }), 400
        
        analysis = agent_result['analysis']
        # 防御性清洗
        def _sanitize(val: str, label: str) -> str:
            if not isinstance(val, str):
                return ''
            v = val.strip()
            if not v:
                return ''
            for other in ['服装','手拿','头戴','背景']:
                if other != label and re.match(rf"^{other}[：:]", v):
                    return ''
            none_words = {"无","没有","未提供","不带","不戴","不拿"}
            if v in none_words:
                return '无' if label == '背景' else ''
            if label == '手拿' and '头戴' in v:
                return ''
            if label == '头戴' and '手拿' in v:
                return ''
            return v
        try:
            import re
            for k in ['服装','手拿','头戴','背景']:
                if k in analysis:
                    analysis[k] = _sanitize(analysis.get(k, ''), k)
        except Exception:
            pass
        print(f"内容分析结果: {analysis}")
        
        # 步骤2: 分析表情和动作（使用matcher）
        print("\n步骤2: 分析表情和动作...")
        
        # 获取表情信息
        expression_info = head_matcher.analyze_user_requirement(requirement)
        print(f"表情分析: {expression_info}")
        
        # 获取动作类型
        action_type = body_matcher.classify_action_type(requirement)
        print(f"动作类型: {action_type}")
        analysis['动作'] = action_type
        
        # 步骤3: 使用image_processor选择和组合图片
        print("\n步骤3: 选择和组合图片...")
        processor_result = image_processor.process_user_requirement(requirement)
        
        # 对于可预期的业务失败（例如未找到合适图片），不再返回500，
        # 而是以200响应并在payload中标识success=false，便于前端友好处理。
        if not processor_result['success']:
            return jsonify({
                'success': False,
                'error': processor_result.get('error', '图片处理失败'),
                'details': {
                    'action_type': processor_result.get('action_type'),
                    'body_images': processor_result.get('body_images', []),
                    'head_images': processor_result.get('head_images', []),
                    'total_generated': processor_result.get('total_generated', 0)
                }
            }), 200
        
        # 获取组合后的基础图片
        combined_images = processor_result['combined_images']
        print(f"生成了 {len(combined_images)} 张基础组合图片")
        
        # 步骤4-9: 逐步添加配饰
        print("\n步骤4-9: 添加配饰...")
        final_images = combined_images
        
        # 处理服装
        if analysis.get('服装'):
            print(f"添加服装: {analysis['服装']}")
            final_images = generation_controller.process_clothes(
                final_images, analysis['服装']
            )
        
        # 处理手拿
        if analysis.get('手拿'):
            print(f"添加手拿物品: {analysis['手拿']}")
            final_images = generation_controller.process_hands(
                final_images, analysis['手拿']
            )
        
        # 处理头戴
        hats = analysis.get('头戴', '')
        if is_valid_accessory('头戴', hats):
            print(f"添加头戴物品: {hats}")
            final_images = generation_controller.process_hats(
                final_images, hats
            )
        
        # 背景处理已暂时移除，但保留接口供后续使用
        # if analysis.get('背景'):
        #     print(f"添加背景: {analysis['背景']}")
        #     final_images = generation_controller.process_background(
        #         final_images, analysis['背景']
        #     )
        
        # 由于在生成过程中已经进行了gate检查，这里只需要验证文件存在性
        print("\n步骤10: 验证最终图片...")
        validated_images = []
        for img_path in final_images:
            if os.path.exists(img_path):
                validated_images.append(img_path)
                print(f"✓ 图片文件存在: {img_path}")
            else:
                print(f"✗ 图片文件不存在: {img_path}")
        
        print(f"文件验证完成，{len(final_images)} 张图片中有 {len(validated_images)} 张文件存在")
        
        # 如果没有图片文件存在，返回相应的错误信息
        if len(validated_images) == 0:
            print("⚠️ 没有找到生成的图片文件")
            return jsonify({
                'success': False,
                'error': '图片生成过程中出现问题，没有找到生成的文件',
                'images': [],
                'analysis': analysis,
                'total': 0,
                'details': {
                    'generated_count': len(final_images),
                    'passed_count': 0,
                    'reason': '图片文件不存在'
                }
            }), 200
        
        # 转换通过检查的图片路径为URL
        image_urls = []
        for img_path in validated_images:
            # 将绝对路径转换为相对URL
            if img_path.startswith('output/'):
                img_url = f"/{img_path.replace(os.sep, '/')}"
            else:
                relative_path = os.path.relpath(img_path, '.')
                img_url = f"/{relative_path.replace(os.sep, '/')}"
            image_urls.append(img_url)
        
        print(f"\n{'='*60}")
        print(f"生成完成! 共 {len(image_urls)} 张图片通过检查")
        print(f"{'='*60}\n")
        
        return jsonify({
            'success': True,
            'images': image_urls,
            'analysis': analysis,
            'total': len(image_urls),
            'details': {
                'generated_count': len(final_images),
                'passed_count': len(validated_images)
            }
        })
        
    except Exception as e:
        print(f"生成失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'service': 'Joy IP 3D Generation System'
    })


# ============================================
# 新增API路由（从Next.js迁移）
# ============================================

@app.route('/api/run-banana', methods=['POST'])
def run_banana():
    """
    执行banana-background.py脚本，添加背景
    
    请求参数:
        tagImgUrl: 图片URL或相对路径
        backgroundText: 背景描述文本
    
    返回:
        success: 是否成功
        resultImages: 结果图片URL列表
        uploadedImages: 上传成功的图片URL列表
        localImages: 本地路径列表
        message: 消息
    """
    from utils import ScriptExecutor, ImageUploader, RemoteFileDownloader
    
    try:
        data = request.get_json() or {}
        tag_img_url = data.get('tagImgUrl', '')
        background_text = data.get('backgroundText', '')
        
        logger.info(f"run-banana API 收到请求: tagImgUrl={tag_img_url}, backgroundText={background_text}")
        
        if not tag_img_url or not background_text:
            return jsonify({
                'success': False,
                'error': '缺少参数: tagImgUrl 或 backgroundText',
                'resultImages': []
            }), 200
        
        # 初始化工具
        downloader = RemoteFileDownloader(temp_dir=config.GENERATED_IMAGES_DIR)
        executor = ScriptExecutor(timeout=config.SCRIPT_TIMEOUT)
        uploader = ImageUploader()
        
        # 处理输入图片路径
        try:
            # 如果是相对路径（/output/或/generated_images/），转换为绝对路径
            if tag_img_url.startswith('/output/') or tag_img_url.startswith('/generated_images/'):
                relative_path = tag_img_url.lstrip('/')
                processed_img_path = os.path.abspath(relative_path)
                logger.info(f"转换相对路径: {tag_img_url} -> {processed_img_path}")
            else:
                # 如果是远程URL，下载到本地
                processed_img_path = downloader.download_if_remote(tag_img_url)
                logger.info(f"处理后的图片路径: {processed_img_path}")
        except Exception as e:
            logger.error(f"处理图片路径失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'处理图片路径失败: {str(e)}',
                'resultImages': []
            }), 200
        
        # 记录执行前的文件列表
        before_files = executor.get_file_list(config.GENERATED_IMAGES_DIR)
        
        # 执行脚本
        script_path = 'banana-background.py'
        try:
            returncode, stdout, stderr = executor.run_script(
                script_path,
                [processed_img_path, background_text]
            )
            
            logger.info(f"脚本执行完成: 返回码={returncode}")
            if stdout:
                logger.debug(f"stdout: {stdout[:500]}")
            if stderr:
                logger.debug(f"stderr: {stderr[:500]}")
                
        except Exception as e:
            logger.error(f"脚本执行失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'脚本执行失败: {str(e)}',
                'resultImages': [],
                'stdout': '',
                'stderr': str(e)
            }), 200
        
        # 检测新生成的文件
        new_files = executor.get_new_files(config.GENERATED_IMAGES_DIR, before_files)
        logger.info(f"检测到 {len(new_files)} 个新文件")
        
        if not new_files:
            return jsonify({
                'success': False,
                'message': '未检测到新增文件，可能脚本未生成输出',
                'resultImages': [],
                'uploadedImages': [],
                'localImages': [],
                'newFiles': [],
                'stdout': stdout,
                'stderr': stderr
            }), 200
        
        # 上传到图床，失败则使用本地路径
        uploaded_urls, local_urls, result_urls = uploader.upload_with_fallback(
            new_files,
            fallback_prefix='/generated_images/'
        )
        
        message = '上传成功，返回远程 URL' if uploaded_urls else '上传失败，已回退到本地路径'
        
        return jsonify({
            'success': True,
            'message': message,
            'resultImages': result_urls,
            'uploadedImages': uploaded_urls,
            'localImages': local_urls,
            'newFiles': [os.path.basename(f) for f in new_files],
            'stdout': stdout,
            'stderr': stderr,
            'inputResolvedPath': processed_img_path,
            'inputWasRemote': downloader.is_remote_url(tag_img_url)
        }), 200
        
    except Exception as e:
        logger.error(f"run-banana API 错误: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'API处理失败: {str(e)}',
            'resultImages': []
        }), 500


@app.route('/api/run-jimeng4', methods=['POST'])
def run_jimeng4():
    """
    执行background-jimeng4.py脚本，使用即梦API添加背景
    
    特殊处理：如果输入是本地路径，需先上传到图床获取URL
    
    请求参数:
        tagImgUrl: 图片URL或相对路径
        backgroundText: 背景描述文本
    
    返回:
        success: 是否成功
        resultImages: 结果图片URL列表
        uploadedImages: 上传成功的图片URL列表
        localImages: 本地路径列表
        message: 消息
    """
    from utils import ScriptExecutor, ImageUploader, RemoteFileDownloader
    
    try:
        data = request.get_json() or {}
        tag_img_url = data.get('tagImgUrl', '')
        background_text = data.get('backgroundText', '')
        
        logger.info(f"run-jimeng4 API 收到请求: tagImgUrl={tag_img_url}, backgroundText={background_text}")
        
        if not tag_img_url or not background_text:
            return jsonify({
                'success': False,
                'error': '缺少参数: tagImgUrl 或 backgroundText',
                'resultImages': []
            }), 200
        
        # 初始化工具
        downloader = RemoteFileDownloader(temp_dir=config.GENERATED_IMAGES_DIR)
        executor = ScriptExecutor(timeout=config.SCRIPT_TIMEOUT)
        uploader = ImageUploader()
        
        # 处理输入图片路径
        # jimeng4需要URL，如果是本地路径，需要先上传到图床
        processed_img_url = tag_img_url
        
        if tag_img_url.startswith('/output/') or tag_img_url.startswith('/generated_images/'):
            # 本地路径，需要上传到图床
            relative_path = tag_img_url.lstrip('/')
            local_path = os.path.abspath(relative_path)
            
            logger.info(f"本地路径，需要上传到图床: {local_path}")
            
            if not os.path.exists(local_path):
                return jsonify({
                    'success': False,
                    'error': f'图片文件不存在: {local_path}',
                    'resultImages': []
                }), 200
            
            # 上传到图床
            upload_result = uploader.upload_file(local_path)
            if not upload_result['success'] or not upload_result['url']:
                return jsonify({
                    'success': False,
                    'error': f"上传图片到图床失败: {upload_result.get('error', '未知错误')}",
                    'resultImages': []
                }), 200
            
            processed_img_url = upload_result['url']
            logger.info(f"上传成功，获得URL: {processed_img_url}")
        
        # 记录执行前的文件列表
        before_files = executor.get_file_list(config.GENERATED_IMAGES_DIR)
        
        # 执行脚本
        script_path = 'background-jimeng4.py'
        try:
            returncode, stdout, stderr = executor.run_script(
                script_path,
                [processed_img_url, background_text]
            )
            
            logger.info(f"脚本执行完成: 返回码={returncode}")
            if stdout:
                logger.debug(f"stdout: {stdout[:500]}")
            if stderr:
                logger.debug(f"stderr: {stderr[:500]}")
                
        except Exception as e:
            logger.error(f"脚本执行失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'脚本执行失败: {str(e)}',
                'resultImages': [],
                'stdout': '',
                'stderr': str(e)
            }), 200
        
        # 检测新生成的文件
        new_files = executor.get_new_files(config.GENERATED_IMAGES_DIR, before_files)
        logger.info(f"检测到 {len(new_files)} 个新文件")
        
        if not new_files:
            return jsonify({
                'success': False,
                'message': '未检测到新增文件，可能脚本未生成输出',
                'resultImages': [],
                'uploadedImages': [],
                'localImages': [],
                'newFiles': [],
                'stdout': stdout,
                'stderr': stderr
            }), 200
        
        # 上传到图床，失败则使用本地路径
        uploaded_urls, local_urls, result_urls = uploader.upload_with_fallback(
            new_files,
            fallback_prefix='/generated_images/'
        )
        
        message = '上传成功，返回远程 URL' if uploaded_urls else '上传失败，已回退到本地路径'
        
        return jsonify({
            'success': True,
            'message': message,
            'resultImages': result_urls,
            'uploadedImages': uploaded_urls,
            'localImages': local_urls,
            'newFiles': [os.path.basename(f) for f in new_files],
            'stdout': stdout,
            'stderr': stderr
        }), 200
        
    except Exception as e:
        logger.error(f"run-jimeng4 API 错误: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'API处理失败: {str(e)}',
            'resultImages': []
        }), 500


@app.route('/api/run-3d-banana', methods=['POST'])
def run_3d_banana():
    """
    执行3D-banana-all.py脚本，处理3D渲染图片
    
    请求参数:
        imagePath: 渲染图片路径
        promptText: 提示文本
    
    返回:
        success: 是否成功
        url: 生成的图片URL
    """
    from utils import ScriptExecutor, ImageUploader
    
    try:
        data = request.get_json() or {}
        image_path = data.get('imagePath', '')
        prompt_text = data.get('promptText', '')
        
        logger.info(f"run-3d-banana API 收到请求: imagePath={image_path}, promptText={prompt_text}")
        
        if not image_path or not prompt_text:
            return jsonify({
                'success': False,
                'error': '缺少参数: imagePath 或 promptText'
            }), 200
        
        # 初始化工具
        executor = ScriptExecutor(timeout=config.SCRIPT_TIMEOUT)
        uploader = ImageUploader()
        
        # 处理图片路径
        if image_path.startswith('/output/'):
            relative_path = image_path.lstrip('/')
            processed_path = os.path.abspath(relative_path)
        else:
            processed_path = image_path
        
        # 记录执行前的文件列表
        before_files = executor.get_file_list(config.GENERATED_IMAGES_DIR)
        
        # 执行脚本
        script_path = '3D-banana-all.py'
        try:
            returncode, stdout, stderr = executor.run_script(
                script_path,
                [processed_path, prompt_text]
            )
            logger.info(f"脚本执行完成: 返回码={returncode}")
        except Exception as e:
            logger.error(f"脚本执行失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'脚本执行失败: {str(e)}'
            }), 200
        
        # 检测新生成的文件
        new_files = executor.get_new_files(config.GENERATED_IMAGES_DIR, before_files)
        
        if not new_files:
            return jsonify({
                'success': False,
                'error': '未生成新文件'
            }), 200
        
        # 上传第一个文件
        upload_result = uploader.upload_file(new_files[0])
        
        if upload_result['success'] and upload_result['url']:
            return jsonify({
                'success': True,
                'url': upload_result['url']
            }), 200
        else:
            # 降级到本地路径
            local_url = f"/generated_images/{os.path.basename(new_files[0])}"
            return jsonify({
                'success': True,
                'url': local_url
            }), 200
        
    except Exception as e:
        logger.error(f"run-3d-banana API 错误: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'API处理失败: {str(e)}'
        }), 500


@app.route('/api/run-banana-pro-img-jd', methods=['POST'])
def run_banana_pro_img_jd():
    """
    执行banana-pro-img-jd.py脚本，高级图像处理
    
    请求参数:
        imageUrl: 图片URL
        prompt: 提示文本
    
    返回:
        success: 是否成功
        url: 生成的图片URL
    """
    from utils import ScriptExecutor, ImageUploader, RemoteFileDownloader
    
    try:
        data = request.get_json() or {}
        image_url = data.get('imageUrl', '')
        prompt = data.get('prompt', '')
        
        logger.info(f"run-banana-pro-img-jd API 收到请求: imageUrl={image_url}, prompt={prompt}")
        
        if not image_url or not prompt:
            return jsonify({
                'success': False,
                'error': '缺少参数: imageUrl 或 prompt'
            }), 200
        
        # 初始化工具
        downloader = RemoteFileDownloader(temp_dir=config.GENERATED_IMAGES_DIR)
        executor = ScriptExecutor(timeout=config.SCRIPT_TIMEOUT)
        uploader = ImageUploader()
        
        # 下载远程图片（如果需要）
        try:
            processed_path = downloader.download_if_remote(image_url)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'下载图片失败: {str(e)}'
            }), 200
        
        # 记录执行前的文件列表
        before_files = executor.get_file_list(config.GENERATED_IMAGES_DIR)
        
        # 执行脚本
        script_path = 'banana-pro-img-jd.py'
        try:
            returncode, stdout, stderr = executor.run_script(
                script_path,
                [processed_path, prompt]
            )
            logger.info(f"脚本执行完成: 返回码={returncode}")
        except Exception as e:
            logger.error(f"脚本执行失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'脚本执行失败: {str(e)}'
            }), 200
        
        # 检测新生成的文件
        new_files = executor.get_new_files(config.GENERATED_IMAGES_DIR, before_files)
        
        if not new_files:
            return jsonify({
                'success': False,
                'error': '未生成新文件'
            }), 200
        
        # 上传第一个文件
        upload_result = uploader.upload_file(new_files[0])
        
        if upload_result['success'] and upload_result['url']:
            return jsonify({
                'success': True,
                'url': upload_result['url']
            }), 200
        else:
            # 降级到本地路径
            local_url = f"/generated_images/{os.path.basename(new_files[0])}"
            return jsonify({
                'success': True,
                'url': local_url
            }), 200
        
    except Exception as e:
        logger.error(f"run-banana-pro-img-jd API 错误: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'API处理失败: {str(e)}'
        }), 500


@app.route('/api/run-turn', methods=['POST'])
def run_turn():
    """
    执行runninghub-turn.py或liblib-turn.py脚本，处理图像角度变换
    
    请求参数:
        imageUrl: 图片URL
        action: 角度描述
    
    返回:
        success: 是否成功
        url: 生成的图片URL
    """
    from utils import ScriptExecutor, ImageUploader, RemoteFileDownloader
    
    try:
        data = request.get_json() or {}
        image_url = data.get('imageUrl', '')
        action = data.get('action', '')
        
        logger.info(f"run-turn API 收到请求: imageUrl={image_url}, action={action}")
        
        if not image_url or not action:
            return jsonify({
                'success': False,
                'error': '缺少参数: imageUrl 或 action'
            }), 200
        
        # 初始化工具
        downloader = RemoteFileDownloader(temp_dir=config.GENERATED_IMAGES_DIR)
        executor = ScriptExecutor(timeout=config.SCRIPT_TIMEOUT)
        uploader = ImageUploader()
        
        # 下载远程图片（如果需要）
        try:
            if image_url.startswith('/output/') or image_url.startswith('/generated_images/'):
                relative_path = image_url.lstrip('/')
                processed_path = os.path.abspath(relative_path)
            else:
                processed_path = downloader.download_if_remote(image_url)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'处理图片失败: {str(e)}'
            }), 200
        
        # 记录执行前的文件列表
        before_files = executor.get_file_list(config.GENERATED_IMAGES_DIR)
        
        # 执行脚本（优先使用runninghub-turn.py）
        script_path = 'runninghub-turn.py' if os.path.exists('runninghub-turn.py') else 'liblib-turn.py'
        try:
            returncode, stdout, stderr = executor.run_script(
                script_path,
                [processed_path, action]
            )
            logger.info(f"脚本执行完成: 返回码={returncode}")
        except Exception as e:
            logger.error(f"脚本执行失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'脚本执行失败: {str(e)}'
            }), 200
        
        # 检测新生成的文件
        new_files = executor.get_new_files(config.GENERATED_IMAGES_DIR, before_files)
        
        if not new_files:
            return jsonify({
                'success': False,
                'error': '未生成新文件'
            }), 200
        
        # 上传第一个文件
        upload_result = uploader.upload_file(new_files[0])
        
        if upload_result['success'] and upload_result['url']:
            return jsonify({
                'success': True,
                'url': upload_result['url']
            }), 200
        else:
            # 降级到本地路径
            local_url = f"/generated_images/{os.path.basename(new_files[0])}"
            return jsonify({
                'success': True,
                'url': local_url
            }), 200
        
    except Exception as e:
        logger.error(f"run-turn API 错误: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'API处理失败: {str(e)}'
        }), 500


@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    """
    上传图片到图床
    
    请求参数:
        image: 图片路径或URL
        customName: 自定义文件名（可选）
    
    返回:
        success: 是否成功
        url: 图片URL
        error: 错误信息（如果失败）
    """
    from utils import ImageUploader
    
    try:
        data = request.get_json() or {}
        image = data.get('image', '')
        custom_name = data.get('customName', 'tag_img')
        
        logger.info(f"upload-image API 收到请求: image={image}, customName={custom_name}")
        
        if not image:
            return jsonify({
                'success': False,
                'error': '缺少图片地址'
            }), 200
        
        # 初始化上传器
        uploader = ImageUploader()
        
        # 上传文件
        result = uploader.upload_file(image, custom_name)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"upload-image API 错误: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'API处理失败: {str(e)}'
        }), 500


@app.route('/api/save-render', methods=['POST'])
def save_render():
    """
    保存3D编辑器渲染的图片（base64）
    
    请求参数:
        dataURL: base64编码的图片数据（data:image/png;base64,...）
    
    返回:
        success: 是否成功
        filePath: 文件路径
        url: 访问URL
        mime: MIME类型
    """
    try:
        data = request.get_json() or {}
        data_url = data.get('dataURL', '')
        
        logger.info("save-render API 收到请求")
        
        if not isinstance(data_url, str) or not data_url.startswith('data:'):
            return jsonify({
                'error': 'Invalid dataURL'
            }), 400
        
        # 解析dataURL
        import re
        match = re.match(r'^data:(image/(png|jpeg));base64,(.*)$', data_url)
        if not match:
            return jsonify({
                'error': 'Unsupported mime or malformed dataURL'
            }), 400
        
        mime = match.group(1)
        ext = 'jpg' if match.group(2) == 'jpeg' else 'png'
        base64_data = match.group(3)
        
        # 确保output目录存在
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        
        # 生成文件名
        filename = f"render_{int(time.time() * 1000)}.{ext}"
        file_path = os.path.join(config.OUTPUT_DIR, filename)
        
        # 解码并保存
        import base64
        buffer = base64.b64decode(base64_data)
        with open(file_path, 'wb') as f:
            f.write(buffer)
        
        logger.info(f"渲染图片已保存: {file_path}")
        
        url = f"/output/{filename}"
        
        return jsonify({
            'success': True,
            'filePath': file_path,
            'url': url,
            'mime': mime
        }), 200
        
    except Exception as e:
        logger.error(f"save-render API 错误: {str(e)}", exc_info=True)
        return jsonify({
            'error': f'保存失败: {str(e)}'
        }), 500


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    仅分析内容，不生成图片
    用于测试和调试
    """
    try:
        data = request.get_json()
        requirement = data.get('requirement', '')
        
        if not requirement:
            return jsonify({
                'success': False,
                'error': '请输入需求描述'
            }), 400
        
        # 合规检查和内容分析
        result = content_agent.process_content(requirement)
        # 对返回的分析结果进行一次防御性清洗
        try:
            import re
            ana = result.get('analysis', {})
            def _sanitize(val: str, label: str) -> str:
                if not isinstance(val, str):
                    return ''
                v = val.strip()
                if not v:
                    return ''
                for other in ['服装','手拿','头戴','背景']:
                    if other != label and re.match(rf"^{other}[：:]", v):
                        return ''
                none_words = {"无","没有","未提供","不带","不戴","不拿"}
                if v in none_words:
                    return '无' if label == '背景' else ''
                if label == '手拿' and '头戴' in v:
                    return ''
                if label == '头戴' and '手拿' in v:
                    return ''
                return v
            for k in ['服装','手拿','头戴','背景']:
                if k in ana:
                    ana[k] = _sanitize(ana.get(k, ''), k)
            # 针对常见错位模式进行强制纠正
            if isinstance(ana.get('服装'), str) and ana['服装'].startswith('手拿'):
                ana['服装'] = ''
            if isinstance(ana.get('手拿'), str) and ana['手拿'].startswith('头戴'):
                ana['手拿'] = ''
            if isinstance(ana.get('头戴'), str) and ana['头戴'].startswith('背景'):
                ana['头戴'] = ''
            # 覆写回结果
            result['analysis'] = ana
        except Exception:
            pass
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'分析失败: {str(e)}'
        }), 500


# ============================================
# 前端路由处理（单端口模式）
# ============================================

@app.route('/')
@app.route('/detail')
@app.route('/joyai')
def serve_frontend():
    """
    提供前端页面
    支持客户端路由，所有前端路由都返回index.html
    """
    if config.SINGLE_PORT_MODE:
        index_path = os.path.join(app.static_folder, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, 'index.html')
        else:
            logger.warning(f"前端构建目录不存在或index.html缺失: {app.static_folder}")
            return """
            <html>
            <head><title>前端未构建</title></head>
            <body>
                <h1>前端应用未构建</h1>
                <p>请先执行以下命令构建前端：</p>
                <pre>
cd frontend
npm install
npm run build
npm run export
                </pre>
                <p>然后重启应用。</p>
            </body>
            </html>
            """, 404
    else:
        return jsonify({
            'error': '前后端分离模式，请访问前端开发服务器（通常是端口3000）'
        }), 404


@app.errorhandler(404)
def not_found(e):
    """
    404错误处理
    - API请求返回JSON错误
    - 前端路由返回index.html（支持客户端路由）
    - 其他返回404页面
    """
    # 如果是API请求，返回JSON
    if request.path.startswith('/api/'):
        return jsonify({'error': 'API端点不存在', 'path': request.path}), 404
    
    # 如果是单端口模式且前端构建存在，返回index.html（支持客户端路由）
    if config.SINGLE_PORT_MODE:
        index_path = os.path.join(app.static_folder, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, 'index.html')
    
    # 其他情况返回404
    return jsonify({'error': '页面不存在', 'path': request.path}), 404


if __name__ == '__main__':
    # 确保必要的目录存在
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.GENERATED_IMAGES_DIR, exist_ok=True)
    
    # 检查前端构建目录（单端口模式）
    if config.SINGLE_PORT_MODE:
        if not os.path.exists(config.FRONTEND_BUILD_DIR):
            logger.warning("="*60)
            logger.warning("警告：前端构建目录不存在！")
            logger.warning(f"目录: {config.FRONTEND_BUILD_DIR}")
            logger.warning("请先执行以下命令构建前端：")
            logger.warning("  cd frontend")
            logger.warning("  npm install")
            logger.warning("  npm run build")
            logger.warning("  npm run export")
            logger.warning("="*60)
        else:
            logger.info(f"前端构建目录已找到: {config.FRONTEND_BUILD_DIR}")
    
    print("="*60)
    print("启动 Joy IP 3D 图片生成系统...")
    print("="*60)
    print(f"运行模式: {'单端口模式' if config.SINGLE_PORT_MODE else '前后端分离模式'}")
    print(f"服务地址: http://{config.HOST}:{config.PORT}")
    if config.SINGLE_PORT_MODE:
        print(f"前端页面: http://{config.HOST}:{config.PORT}/")
    print(f"API端点:")
    print(f"  - POST /api/start_generate  - 启动生成任务")
    print(f"  - GET  /api/job/<id>/status - 查询任务状态")
    print(f"  - POST /api/generate        - 同步生成图片")
    print(f"  - POST /api/analyze         - 分析内容")
    print(f"  - GET  /api/health          - 健康检查")
    print("="*60)
    
    # 启动应用
    app.run(
        debug=config.DEBUG,
        host=config.HOST,
        port=config.PORT,
        use_reloader=False  # 关闭自动重载，避免生成过程中被重启
    )

