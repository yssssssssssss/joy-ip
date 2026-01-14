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
import re
import threading
import time
import uuid
from typing import Dict

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from matchers.head_matcher import HeadMatcher
from matchers.body_matcher import BodyMatcher
from content_agent import ContentAgent
from generation_controller import GenerationController
from image_processor import ImageProcessor
from config import get_config
from utils.generation_log import log_generation

# 2D素材生成相关导入
from content_agent_2d import ContentAgent2D
from generation_controller_2d import GenerationController2D

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

# 屏蔽 Werkzeug 的轮询请求日志（/api/job/xxx/status）
class WerkzeugFilter(logging.Filter):
    """过滤掉频繁的轮询请求日志"""
    def filter(self, record):
        msg = record.getMessage()
        # 屏蔽 job status 轮询日志
        if '/api/job/' in msg and '/status' in msg:
            return False
        return True

# 应用过滤器到 Werkzeug logger
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(WerkzeugFilter())

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

# 确保 Gate 模块可用
try:
    if getattr(generation_controller, 'gate_check', None) is None:
        import importlib.util, sys
        _base_dir = os.path.dirname(os.path.abspath(__file__))
        _gate_path = os.path.join(_base_dir, 'gate-result.py')
        _spec = importlib.util.spec_from_file_location('gate_check', _gate_path)
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            sys.modules['gate_check'] = _mod
            _spec.loader.exec_module(_mod)
            setattr(generation_controller, 'gate_check', _mod)
except Exception:
    pass

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
    for other in ['上装', '下装', '头戴', '手持']:
        if other != label and re.match(rf"^{other}[：:]", v):
            return False
    none_words = {"无", "没有", "未提供", "不带", "不戴", "不拿"}
    if v in none_words:
        return False
    if label == '手持' and '头戴' in v:
        return False
    if label == '头戴' and '手持' in v:
        return False
    return True


def sanitize_accessory_value(val: str, label: str) -> str:
    """
    规范化配饰字段值，过滤无效/误填内容
    
    Args:
        val: 原始值
        label: 字段标签（服装/手拿/头戴/背景）
    
    Returns:
        str: 清洗后的值，无效时返回空字符串
    """
    if not isinstance(val, str):
        return ''
    v = val.strip()
    if not v:
        return ''
    
    # 否定词处理（背景保留"无"）
    none_words = {"无", "没有", "未提供", "不带", "不戴", "不拿"}
    if v in none_words:
        return '无' if label == '背景' else ''
    
    # 检查是否以其他标签开头（误填）
    for other in ['上装', '下装', '头戴', '手持']:
        if other != label and re.match(rf"^{other}[：:]", v):
            return ''
    
    # 交叉关键词检查
    if label == '手持' and '头戴' in v:
        return ''
    if label == '头戴' and '手持' in v:
        return ''
    
    return v


def sanitize_analysis_result(analysis: Dict) -> Dict:
    """
    批量清洗分析结果中的配饰字段
    
    Args:
        analysis: 原始分析结果字典
    
    Returns:
        Dict: 清洗后的分析结果
    """
    if not analysis:
        return analysis
    
    for key in ['上装', '下装', '头戴', '手持']:
        if key in analysis:
            analysis[key] = sanitize_accessory_value(analysis.get(key, ''), key)
    
    return analysis


# =========================
# 使用 JobManager 管理任务（带队列控制和 TTL 自动清理）
# =========================
from utils.job_manager import job_manager
from utils.resource_manager import resources

# 保留旧接口的兼容性
jobs = {}  # 已废弃，使用 job_manager
jobs_lock = threading.Lock()  # 已废弃

def _init_job(requirement: str) -> str:
    """创建新任务（使用 JobManager）"""
    return job_manager.create_job(requirement)

def _submit_job(job_id: str, requirement: str) -> dict:
    """提交任务到执行队列"""
    return job_manager.submit_job(job_id, lambda jid, req: _run_generation_job(jid, req))

def _update_job(job_id: str, **fields):
    """更新任务状态（使用 JobManager）"""
    job_manager.update_job(job_id, **fields)

def _append_log(job_id: str, text: str):
    """追加任务日志（使用 JobManager）"""
    job_manager.append_log(job_id, text)

def _run_generation_job(job_id: str, requirement: str):
    """在后台线程中执行完整生成流程，并持续更新任务状态"""
    try:
        _update_job(job_id, status='running', stage='analyze', progress=5)
        _append_log(job_id, f"收到生成请求: {requirement}")

        # 检查生成模式
        job_data = job_manager.get_job_dict(job_id)
        mode = job_data.get('mode', '3D') if job_data else '3D'
        perspective = job_data.get('perspective', '正视角') if job_data else '正视角'
        pre_analysis = job_data.get('pre_analysis') if job_data else None
        
        logger.info(f"[Job {job_id}] 生成模式: {mode}, 视角: {perspective}")
        
        # 2D模式使用独立的生成流程
        if mode == '2D':
            _append_log(job_id, f"使用2D素材生成流程，视角: {perspective}")
            logger.info(f"[Job {job_id}] 开始2D生成流程")
            
            # 创建2D生成控制器
            controller_2d = GenerationController2D()
            
            # 调用2D完整生成流程（传入预分析结果）
            result = controller_2d.generate_complete_flow(
                requirement, perspective, output_dir="output", pre_analysis=pre_analysis
            )
            
            if result.get('success') and result.get('images'):
                # 转换图片路径为URL
                image_urls = []
                for img_path in result['images']:
                    if img_path.startswith('output/'):
                        img_url = f"/{img_path.replace(os.sep, '/')}"
                    else:
                        relative_path = os.path.relpath(img_path, '.')
                        img_url = f"/{relative_path.replace(os.sep, '/')}"
                    image_urls.append(img_url)
                
                _update_job(job_id, images=image_urls, progress=100, stage='done', status='succeeded', 
                           analysis=result.get('analysis'), details={
                    'generated_count': len(result['images']),
                    'passed_count': len(image_urls),
                    'mode': '2D',
                    'perspective': perspective
                })
                return
            else:
                error_msg = result.get('error', '2D生成失败')
                _update_job(job_id, status='failed', stage='generate', error=error_msg)
                return

        # 3D模式：使用原有的生成流程
        _append_log(job_id, "使用3D素材生成流程")
        
        # 使用全局共享的资源实例（避免重复创建和加载模型）
        local_head = resources.get_head_matcher()
        local_body = resources.get_body_matcher()
        local_agent = resources.get_content_agent()
        local_controller = resources.get_generation_controller()
        local_processor = resources.get_image_processor()

        if pre_analysis:
            # 使用预分析结果，跳过分析步骤
            _append_log(job_id, "使用用户确认的预分析结果")
            logger.info(f"[Job {job_id}] 使用预分析结果: {pre_analysis}")
            
            # 仍需进行合规检查
            is_compliant, reason = local_agent.check_compliance(requirement)
            if not is_compliant:
                _update_job(job_id, status='failed', stage='analyze', error=f"内容不合规: {reason}")
                return
            
            analysis = pre_analysis.copy()
            # 确保所有字段存在
            for key in ['表情', '动作', '上装', '下装', '头戴', '手持']:
                if key not in analysis:
                    analysis[key] = ''
        else:
            # 步骤1: 合规检查和内容分析
            agent_result = local_agent.process_content(requirement)
            if not agent_result['compliant']:
                _update_job(job_id, status='failed', stage='analyze', error=f"内容不合规: {agent_result['reason']}")
                return

            analysis = agent_result['analysis']
        
        # 使用统一的清洗函数处理分析结果
        analysis = sanitize_analysis_result(analysis)
        _update_job(job_id, analysis=analysis, progress=15)

        # 步骤2: 表情与动作分析
        _update_job(job_id, stage='match', progress=25)
        expression_info = local_head.analyze_user_requirement(requirement)
        
        # 如果预分析中有动作，使用预分析的动作；否则重新分析
        if not analysis.get('动作'):
            action_type = local_body.classify_action_type(requirement)
            analysis['动作'] = action_type
        else:
            action_type = analysis['动作']
            
        _append_log(job_id, f"表情分析: {expression_info}")
        _append_log(job_id, f"动作类型: {action_type}")

        # 步骤3: 选择与组合基础图片
        _update_job(job_id, stage='compose', progress=35)
        processor_result = local_processor.process_user_requirement(requirement, log_callback=lambda t: _append_log(job_id, t))
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

        # 步骤4-9: 统一处理配饰（服装、手拿、头戴）
        final_images = combined_images
        _update_job(job_id, stage='decorate', progress=50)

        # 构建配饰信息字典
        accessories_info = {}
        
        # 处理上装+下装（合并为服装）
        top_clothes = analysis.get('上装', '')
        bottom_clothes = analysis.get('下装', '')
        clothes_parts = []
        if is_valid_accessory('上装', top_clothes):
            clothes_parts.append(top_clothes)
        if is_valid_accessory('下装', bottom_clothes):
            clothes_parts.append(bottom_clothes)
        
        if clothes_parts:
            accessories_info['服装'] = '，'.join(clothes_parts)
            _append_log(job_id, f"服装信息: {accessories_info['服装']}")

        # 处理手持物品
        hands = analysis.get('手持', '')
        if is_valid_accessory('手持', hands):
            accessories_info['手拿'] = hands
            _append_log(job_id, f"手持信息: {hands}")

        # 处理头戴物品
        hats = analysis.get('头戴', '')
        if is_valid_accessory('头戴', hats):
            accessories_info['头戴'] = hats
            _append_log(job_id, f"头戴信息: {hats}")

        # 使用统一配件处理方法
        if accessories_info:
            _append_log(job_id, f"开始统一配件处理: {list(accessories_info.keys())}")
            logger.debug(f"[统一配件处理] 开始处理配件: {accessories_info}")
            final_images = local_controller.process_accessories_unified(final_images, accessories_info)
            logger.debug(f"[统一配件处理] 处理完成，图片数: {len(final_images)}")
            _update_job(job_id, progress=80)
            
            # 检查是否有图片通过处理
            if len(final_images) == 0:
                _append_log(job_id, "配件处理阶段Gate未通过，整组图片不展示")
        else:
            logger.debug(f"[统一配件处理] 跳过配件处理（无有效配件信息）")
            _update_job(job_id, progress=80)
        
        # 最终 Gate 检查
        logger.debug(f"[配饰处理] 开始最终 Gate 检查，待检查图片数: {len(final_images)}")
        final_images = local_controller.final_gate_check(final_images)
        logger.debug(f"[配饰处理] Gate 检查完成，通过图片数: {len(final_images)}")

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
    """
    启动生成任务，支持排队机制，返回队列位置和预估等待时间
    
    请求参数:
        requirement: 用户输入的需求描述
        analysis: (可选) 预分析的六维度结果，如果提供则跳过分析步骤
            - 表情: 表情描述
            - 动作: 动作类型
            - 上装: 上半身服装
            - 下装: 下半身服装
            - 头戴: 头部配饰
            - 手持: 手持物品
    """
    logger.info("=== 收到 start_generate 请求 ===")
    logger.info(f"请求来源: {request.remote_addr}")
    
    try:
        data = request.get_json() or {}
        requirement = data.get('requirement', '')
        pre_analysis = data.get('analysis', None)  # 预分析结果（可选）
        
        logger.info(f"请求参数: requirement='{requirement}'")
        if pre_analysis:
            logger.info(f"使用预分析结果: {pre_analysis}")
        
        # 获取2D/3D模式和视角参数
        mode = data.get('mode', '3D')  # 默认3D模式
        perspective = data.get('perspective', '正视角')  # 默认正视角
        logger.info(f"生成模式: {mode}, 视角: {perspective}")
        
        if not requirement:
            logger.warning("请求参数为空，返回400错误")
            return jsonify({'success': False, 'error': '请输入需求描述'}), 400

        # 创建任务
        job_id = _init_job(requirement)
        logger.info(f"✓ 任务创建成功: job_id={job_id}")
        
        # 存储模式和视角信息到任务中
        _update_job(job_id, mode=mode, perspective=perspective)
        
        # 如果有预分析结果，存储到任务中
        if pre_analysis:
            _update_job(job_id, pre_analysis=pre_analysis)
        
        # 提交到执行队列
        submit_result = _submit_job(job_id, requirement)
        if not submit_result.get('success'):
            logger.warning(f"任务提交失败: {submit_result.get('error')}")
            return jsonify({
                'success': False, 
                'error': submit_result.get('error', '队列已满')
            }), 503
        
        # 获取队列统计
        queue_stats = job_manager.get_queue_stats()
        
        response_data = {
            'success': True, 
            'job_id': job_id,
            'queue_position': submit_result.get('queue_position', 0),
            'estimated_wait': submit_result.get('estimated_wait', 0),
            'queue_stats': queue_stats
        }
        logger.info(f"✓ 任务已提交: job_id={job_id}, 队列位置={submit_result.get('queue_position')}, 预估等待={submit_result.get('estimated_wait')}秒")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"✗ start_generate 异常: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'启动任务失败: {str(e)}'}), 500


@app.route('/api/queue/stats', methods=['GET'])
def queue_stats():
    """获取队列统计信息"""
    stats = job_manager.get_queue_stats()
    return jsonify({
        'success': True,
        'stats': stats
    })


@app.route('/api/job/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id: str):
    """取消排队中的任务"""
    success = job_manager.cancel_job(job_id)
    if success:
        return jsonify({'success': True, 'message': '任务已取消'})
    else:
        return jsonify({'success': False, 'error': '无法取消该任务（可能已在执行中）'}), 400


@app.route('/api/job/<job_id>/status', methods=['GET'])
def job_status(job_id: str):
    """查询任务状态（使用 JobManager）"""
    logger.debug(f"查询任务状态: job_id={job_id}")
    job_dict = job_manager.get_job_dict(job_id)
    if not job_dict:
        logger.warning(f"任务不存在: job_id={job_id}")
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    # 返回任务状态
    status_data = {
        'success': True,
        'job': job_dict
    }
    logger.debug(f"任务状态: {job_dict.get('status')}, 进度: {job_dict.get('progress')}%, 阶段: {job_dict.get('stage')}")
    return jsonify(status_data)


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
        
        
        logger.info(f"收到生成请求: {requirement}")
        
        
        # 步骤1: 合规检查和内容分析
        logger.info("步骤1: 合规检查和内容分析...")
        agent_result = content_agent.process_content(requirement)
        
        if not agent_result['compliant']:
            return jsonify({
                'success': False,
                'error': f"内容不合规: {agent_result['reason']}"
            }), 400
        
        analysis = agent_result['analysis']
        # 使用统一的清洗函数处理分析结果
        analysis = sanitize_analysis_result(analysis)
        logger.info(f"内容分析结果: {analysis}")
        
        # 步骤2: 分析表情和动作（使用matcher）
        logger.info("步骤2: 分析表情和动作...")
        
        # 获取表情信息
        expression_info = head_matcher.analyze_user_requirement(requirement)
        logger.debug(f"表情分析: {expression_info}")
        
        # 获取动作类型
        action_type = body_matcher.classify_action_type(requirement)
        logger.debug(f"动作类型: {action_type}")
        analysis['动作'] = action_type
        
        # 步骤3: 使用image_processor选择和组合图片
        logger.info("步骤3: 选择和组合图片...")
        try:
            processor_result = image_processor.process_user_requirement(requirement)
        except TypeError:
            processor_result = image_processor.process_user_requirement(requirement, log_callback=None)
        
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
        logger.info(f"生成了 {len(combined_images)} 张基础组合图片")
        
        # 步骤4-9: 统一处理配饰
        logger.info("步骤4-9: 统一处理配饰...")
        final_images = combined_images
        
        # 构建配饰信息字典
        accessories_info = {}
        
        # 处理上装+下装（合并为服装）
        top_clothes = analysis.get('上装', '')
        bottom_clothes = analysis.get('下装', '')
        clothes_parts = []
        if top_clothes and is_valid_accessory('上装', top_clothes):
            clothes_parts.append(top_clothes)
        if bottom_clothes and is_valid_accessory('下装', bottom_clothes):
            clothes_parts.append(bottom_clothes)
        
        if clothes_parts:
            accessories_info['服装'] = '，'.join(clothes_parts)
            logger.info(f"服装信息: {accessories_info['服装']}")

        # 处理手持物品
        hands = analysis.get('手持', '')
        if hands and is_valid_accessory('手持', hands):
            accessories_info['手拿'] = hands
            logger.info(f"手持信息: {hands}")

        # 处理头戴物品
        hats = analysis.get('头戴', '')
        if hats and is_valid_accessory('头戴', hats):
            accessories_info['头戴'] = hats
            logger.info(f"头戴信息: {hats}")

        # 使用统一配件处理方法
        if accessories_info:
            logger.info(f"开始统一配件处理: {list(accessories_info.keys())}")
            final_images = generation_controller.process_accessories_unified(final_images, accessories_info)
            logger.info(f"统一配件处理完成，图片数: {len(final_images)}")
        else:
            logger.info("跳过配件处理（无有效配件信息）")
        
        # 背景处理已暂时移除，但保留接口供后续使用
        # if analysis.get('背景'):
        #     print(f"添加背景: {analysis['背景']}")
        #     final_images = generation_controller.process_background(
        #         final_images, analysis['背景']
        #     )
        
        # 由于在生成过程中已经进行了gate检查，这里只需要验证文件存在性
        logger.info("步骤10: 验证最终图片...")
        validated_images = []
        for img_path in final_images:
            if os.path.exists(img_path):
                validated_images.append(img_path)
                logger.debug(f"图片文件存在: {img_path}")
            else:
                logger.warning(f"图片文件不存在: {img_path}")
        
        logger.info(f"文件验证完成，{len(final_images)} 张图片中有 {len(validated_images)} 张文件存在")
        
        # 如果没有图片文件存在，返回相应的错误信息
        if len(validated_images) == 0:
            logger.warning("没有找到生成的图片文件")
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
        
        
        logger.info(f"生成完成! 共 {len(image_urls)} 张图片通过检查")
        
        # 记录生成日志（prompt与图片关联）
        try:
            log_generation(
                prompt=requirement,
                images=validated_images,
                analysis=analysis,
                status="success",
                extra={"image_urls": image_urls}
            )
        except Exception as log_err:
            logger.warning(f"记录生成日志失败: {log_err}")
        
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
        logger.error(f"生成失败: {str(e)}")
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
        
        logger.info(f"========== 3D生图流程开始 ==========")
        logger.info(f"run-3d-banana API 收到请求: imagePath={image_path}, promptText={prompt_text}")
        
        if not image_path or not prompt_text:
            return jsonify({
                'success': False,
                'error': '缺少参数: imagePath 或 promptText'
            }), 200
        
        # ===== 新增：3D生图违规词检查 =====
        logger.info(f"开始3D生图违规词检查: {prompt_text}")
        is_compliant, reason = content_agent.check_compliance(prompt_text)
        if not is_compliant:
            logger.warning(f"3D生图违规词检查不通过: {reason}")
            return jsonify({
                'success': False,
                'error': f'内容不合规: {reason}',
                'code': 'COMPLIANCE'
            }), 200
        logger.info("3D生图违规词检查通过")
        # ===== 违规词检查结束 =====
        
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
        
        logger.info("========== 3D渲染图片保存 ==========")
        logger.info(f"save-render API 收到请求, dataURL长度: {len(data_url) if data_url else 0}")
        
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
        from datetime import datetime
        filename = f"render_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
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


# ============================================
# 生成历史查询 API
# ============================================

@app.route('/api/generation-history', methods=['GET'])
def get_generation_history():
    """
    获取生成历史记录
    
    查询参数:
        limit: 返回数量（默认50）
        keyword: 按prompt关键词搜索（可选）
        image: 按图片名搜索（可选）
    
    返回:
        success: 是否成功
        records: 记录列表
        total: 记录总数
    """
    from utils.generation_log import query_by_prompt, query_by_image, get_recent_records
    
    try:
        limit = request.args.get('limit', 50, type=int)
        keyword = request.args.get('keyword', '')
        image_name = request.args.get('image', '')
        
        if image_name:
            # 按图片名查询
            record = query_by_image(image_name)
            records = [record] if record else []
        elif keyword:
            # 按关键词查询
            records = query_by_prompt(keyword, limit=limit)
        else:
            # 获取最近记录
            records = get_recent_records(limit=limit)
        
        return jsonify({
            'success': True,
            'records': records,
            'total': len(records)
        })
        
    except Exception as e:
        logger.error(f"获取生成历史失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'查询失败: {str(e)}'
        }), 500


@app.route('/api/generation-stats', methods=['GET'])
def get_generation_stats():
    """
    获取生成统计信息
    
    返回:
        success: 是否成功
        stats: 统计信息
            - total_jobs: 总任务数
            - success_jobs: 成功任务数
            - failed_jobs: 失败任务数
            - total_images: 总图片数
            - avg_duration: 平均耗时
    """
    from utils.generation_log import get_statistics
    
    try:
        stats = get_statistics()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'查询失败: {str(e)}'
        }), 500


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    分析用户输入，返回六维度分析结果（表情、动作、上装、下装、头戴、手持）
    用于预览和编辑，用户确认后再进行生成
    
    请求参数:
        requirement: 用户输入的需求描述
        mode: 生成模式（'2D' 或 '3D'），默认'3D'
        perspective: 视角（仅对2D模式），默认'正视角'
        async: 是否异步处理，默认false
    
    返回:
        success: 是否成功
        compliant: 是否合规
        reason: 不合规原因（如果不合规）
        analysis: 分析结果
            - 表情: 表情描述
            - 动作: 动作类型（站姿/坐姿等）
            - 上装: 上半身服装
            - 下装: 下半身服装
            - 头戴: 头部配饰
            - 手持: 手持物品
            - 视角: （仅对2D模式）视角信息
        job_id: （异步模式）任务ID
    """
    import time
    start_time = time.time()
    
    try:
        data = request.get_json()
        requirement = data.get('requirement', '')
        mode = data.get('mode', '3D')  # 默认3D模式
        perspective = data.get('perspective', '正视角')  # 默认正视角
        is_async = data.get('async', False)  # 是否异步处理
        
        logger.info(f"=== 收到 analyze 请求 ===")
        logger.info(f"请求来源: {request.remote_addr}")
        logger.info(f"请求参数: requirement='{requirement}', mode='{mode}', perspective='{perspective}', async={is_async}")
        logger.info(f"请求开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
        
        if not requirement:
            return jsonify({
                'success': False,
                'error': '请输入需求描述'
            }), 400
        
        # 异步处理模式
        if is_async:
            job_id = str(uuid.uuid4())
            logger.info(f"启动异步分析任务: {job_id}")
            
            def async_analyze():
                try:
                    # 根据模式选择不同的内容分析器
                    if mode == '2D':
                        logger.info("使用2D内容分析器")
                        content_agent_2d = ContentAgent2D()
                        result = content_agent_2d.process_content_2d(requirement, perspective)
                    else:
                        logger.info("使用3D内容分析器")
                        result = content_agent.process_content(requirement)
                    
                    # 对返回的分析结果进行清洗
                    if result.get('analysis'):
                        result['analysis'] = sanitize_analysis_result(result['analysis'])
                    
                    end_time = time.time()
                    processing_time = end_time - start_time
                    logger.info(f"异步分析完成，耗时: {processing_time:.2f}秒")
                    
                    # 保存结果到任务状态
                    result['processing_time'] = round(processing_time, 2)
                    job_manager.update_job_status(job_id, 'completed', result=result)
                    
                except Exception as e:
                    end_time = time.time()
                    processing_time = end_time - start_time
                    logger.error(f"异步分析失败 (耗时: {processing_time:.2f}秒): {str(e)}", exc_info=True)
                    job_manager.update_job_status(job_id, 'failed', error=str(e))
            
            # 启动后台任务
            import threading
            thread = threading.Thread(target=async_analyze)
            thread.daemon = True
            thread.start()
            
            # 立即返回任务ID
            job_manager.create_job(job_id, 'analyzing', {
                'requirement': requirement,
                'mode': mode,
                'perspective': perspective
            })
            
            return jsonify({
                'success': True,
                'async': True,
                'job_id': job_id,
                'message': '分析任务已启动，请使用job_id查询结果'
            })
        
        # 同步处理模式（原有逻辑）
        # 根据模式选择不同的内容分析器
        if mode == '2D':
            logger.info("使用2D内容分析器")
            content_agent_2d = ContentAgent2D()
            result = content_agent_2d.process_content_2d(requirement, perspective)
        else:
            logger.info("使用3D内容分析器")
            result = content_agent.process_content(requirement)
        
        # 对返回的分析结果进行清洗
        if result.get('analysis'):
            result['analysis'] = sanitize_analysis_result(result['analysis'])
        
        end_time = time.time()
        processing_time = end_time - start_time
        logger.info(f"分析完成，耗时: {processing_time:.2f}秒")
        logger.info(f"分析结果: {result}")
        
        # 添加处理时间到响应中（用于调试）
        result['processing_time'] = round(processing_time, 2)
        
        return jsonify(result)
        
    except Exception as e:
        end_time = time.time()
        processing_time = end_time - start_time
        logger.error(f"analyze API 错误 (耗时: {processing_time:.2f}秒): {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'分析失败: {str(e)}',
            'processing_time': round(processing_time, 2)
        }), 500


@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """
    提交用户反馈
    
    请求参数:
        message: 反馈内容
        contact: 联系方式（可选）
    """
    try:
        data = request.get_json() or {}
        message = data.get('message', '')
        contact = data.get('contact', '')
        
        if not message:
            return jsonify({
                'success': False,
                'error': '请输入反馈内容'
            }), 400
            
        feedback_entry = {
            'id': str(uuid.uuid4()),
            'message': message,
            'contact': contact,
            'timestamp': int(time.time()),
            'formatted_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 确保数据目录存在
        feedback_file = os.path.join('data', 'feedback.json')
        os.makedirs('data', exist_ok=True)
        
        current_feedback = []
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file, 'r', encoding='utf-8') as f:
                    current_feedback = json.load(f)
                    if not isinstance(current_feedback, list):
                        current_feedback = []
            except Exception:
                current_feedback = []
        
        current_feedback.append(feedback_entry)
        
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(current_feedback, f, ensure_ascii=False, indent=2)
            
        logger.info(f"收到用户反馈: {message[:20]}...")
        
        return jsonify({
            'success': True,
            'message': '感谢您的反馈！'
        })
        
    except Exception as e:
        logger.error(f"处理反馈失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'提交失败: {str(e)}'
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


@app.route('/')
def index():
    """
    根路径路由
    - 如果是单端口模式且前端构建存在，返回index.html
    - 否则返回提示信息
    """
    if config.SINGLE_PORT_MODE:
        index_path = os.path.join(app.static_folder, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, 'index.html')
        else:
            return f"前端构建文件未找到: {index_path}", 404
    else:
        return "前后端分离模式，请访问前端开发服务器（通常是端口3000）"


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
    
    
    logger.info("启动 Joy IP 3D 图片生成系统...")
    
    logger.info(f"运行模式: {'单端口模式' if config.SINGLE_PORT_MODE else '前后端分离模式'}")
    logger.info(f"服务地址: http://{config.HOST}:{config.PORT}")
    if config.SINGLE_PORT_MODE:
        logger.info(f"前端页面: http://{config.HOST}:{config.PORT}/")
    logger.info("API端点:")
    logger.info("  - POST /api/start_generate  - 启动生成任务")
    logger.info("  - GET  /api/job/<id>/status - 查询任务状态")
    logger.info("  - POST /api/generate        - 同步生成图片")
    logger.info("  - POST /api/analyze         - 分析内容")
    logger.info("  - GET  /api/health          - 健康检查")
    
    
    # 启动应用
    app.run(
        debug=config.DEBUG,
        host=config.HOST,
        port=config.PORT,
        use_reloader=False  # 关闭自动重载，避免生成过程中被重启
    )

