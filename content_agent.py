#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容合规检查和分析Agent
功能：
1. 合规检查：屏蔽违规关键词
2. 内容分析：按照表情、动作、上装、下装、头戴、手持六个维度分析内容
"""

import os
import re
import logging
from typing import Dict, List, Tuple
from config import get_config
# 使用优化后的 HTTP 客户端和违规词库
from utils.http_client import http_post, http_get, parse_ai_response
from utils.banned_words import (
    check_banned_words, reload_banned_words,
    add_banned_word as add_word_to_cache,
    remove_banned_word as remove_word_from_cache
)
# 导入分析结果缓存
from utils.analysis_cache import analysis_cache


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='[ContentAgent] %(message)s')


# 延迟导入 Matcher，避免循环依赖和重复实例化
_body_matcher = None
_head_matcher = None


def _get_body_matcher():
    """获取全局共享的 BodyMatcher 实例"""
    global _body_matcher
    if _body_matcher is None:
        from matchers.body_matcher import BodyMatcher
        _body_matcher = BodyMatcher()
    return _body_matcher


def _get_head_matcher():
    """获取全局共享的 HeadMatcher 实例"""
    global _head_matcher
    if _head_matcher is None:
        from matchers.head_matcher import HeadMatcher
        _head_matcher = HeadMatcher()
    return _head_matcher


class ContentAgent:
    """内容合规检查和分析Agent"""
    
    def __init__(self):
        """初始化Agent"""
        config = get_config()
        self.api_url = config.AI_API_URL
        self.api_token = config.AI_API_KEY
        self.model = config.AI_MODEL
        # 合并AI分析专用模型（如果未配置则使用默认模型）
        self.analysis_model = config.AI_ANALYSIS_MODEL if config.AI_ANALYSIS_MODEL else config.AI_MODEL
    
    @property
    def body_matcher(self):
        """延迟加载的 BodyMatcher"""
        return _get_body_matcher()
    
    @property
    def head_matcher(self):
        """延迟加载的 HeadMatcher"""
        return _get_head_matcher()
    
    def _check_external_banned_words(self, content: str) -> Tuple[bool, str]:
        """检查外部违规词库"""
        return check_banned_words(content)
    
    def update_banned_words_from_url(self, url: str) -> bool:
        """从在线URL更新违规词库"""
        try:
            response = http_get(url, timeout=30)
            response.raise_for_status()
            os.makedirs("data", exist_ok=True)
            with open("data/sensitive_words.txt", 'w', encoding='utf-8') as f:
                f.write(response.text)
            reload_banned_words()
            logger.info("违规词库更新成功")
            return True
        except Exception as e:
            logger.error(f"更新违规词库失败: {e}")
            return False
    
    def add_banned_word(self, word: str) -> bool:
        """动态添加违规词"""
        return add_word_to_cache(word)
    
    def remove_banned_word(self, word: str) -> bool:
        """动态移除违规词"""
        return remove_word_from_cache(word)

    def _check_sensitive_content_with_ai(self, content: str) -> Tuple[bool, str]:
        """使用AI检查敏感内容"""
        try:
            prompt = f"""请检查以下内容是否涉及敏感话题：
内容："{content}"

检查重点：
1. 政治相关：政治人物、政治事件、政治口号
2. 民族相关：特定民族及其传统服饰、民族冲突
3. 国家相关：国旗、国徽、政治象征
4. 女装相关：女装、裙子、婚纱等女性服装

如果内容合规，回复"合规"。
如果不合规，回复"不合规：[原因]"。"""

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是敏感内容审核专家。"},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            resp = http_post(self.api_url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            result = parse_ai_response(resp.json())
            
            if not result:
                return True, ""
            if "合规" in result and "不合规" not in result:
                return True, ""
            if "不合规" in result:
                m = re.search(r"不合规[：:]\s*(.+)", result)
                reason = m.group(1).strip() if m else result.strip()
                return False, f"敏感内容检测：{reason}"
            return False, f"敏感内容检测：AI返回不明确结果"
                
        except Exception as e:
            logger.error(f"AI敏感内容检查失败: {e}")
            return False, "敏感内容检测：检查过程出错"

    def check_compliance(self, content: str) -> Tuple[bool, str]:
        """检查内容是否合规"""
        # 第一层：违规词库检查
        is_compliant, reason = self._check_external_banned_words(content)
        if not is_compliant:
            return False, f"违规词检测：{reason}"
        
        # 第二层：AI敏感内容检查
        is_compliant, reason = self._check_sensitive_content_with_ai(content)
        if not is_compliant:
            return False, reason
        
        return True, ""

    def analyze_content(self, content: str) -> Dict[str, str]:
        """
        分析内容，按照六个维度进行分类：表情、动作、上装、下装、头戴、手持
        
        Args:
            content: 待分析的内容
            
        Returns:
            Dict[str, str]: 包含六个维度的分析结果
        """
        result = {
            "表情": "",
            "动作": "",
            "上装": "",
            "下装": "",
            "头戴": "",
            "手持": ""
        }
        logger.info("开始分析内容: %s", content)
        
        # 1. 使用head_matcher分析表情
        try:
            expression_features = self.head_matcher.analyze_user_requirement(content)
            if expression_features.get("表情"):
                result["表情"] = expression_features["表情"]
        except Exception as e:
            logger.warning(f"表情分析失败: {e}")
        
        # 2. 使用body_matcher分析动作
        try:
            action_type = self.body_matcher.classify_action_type(content)
            result["动作"] = action_type
        except Exception as e:
            logger.warning(f"动作分析失败: {e}")
        
        # 3. 使用大模型分析上装、下装、头戴、手持
        try:
            ai_result = self._analyze_with_ai(content)
            if ai_result:
                for key in ["上装", "下装", "头戴", "手持"]:
                    if ai_result.get(key):
                        result[key] = ai_result[key]
                
                # 检查是否需要补全
                result = self._complete_fields_if_needed(content, result)
                
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
        
        logger.info("最终分析结果: %s", result)
        return result
    
    def _analyze_with_ai(self, content: str) -> Dict[str, str]:
        """使用大模型分析用户描述，提取上装、下装、头戴、手持"""
        try:
            prompt = f"""请分析以下用户描述，提取角色的装扮信息：

            用户描述："{content}"

            请按照以下四个维度进行分析：
            - 上装：上半身穿着的衣物（如夹克、T恤、衬衫等）
            - 下装：下半身穿着的衣物（如裤子、短裤等，不包括裙子）
            - 头戴：头上佩戴的物品（如帽子、头饰等）
            - 手持：手中拿着的物品（如道具、工具等）

            规则：
            1. 如果用户明确描述了某个维度，直接提取
            2. 如果用户未提及某个维度，填写"无"
            3. 不要自行推测用户未提及的内容

            请严格按以下格式输出：
            上装：xxx
            下装：xxx
            头戴：xxx
            手持：xxx
            """

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是专业的美术指导，擅长从文本中提取角色装扮信息。"},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            resp = http_post(self.api_url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            ai_text = parse_ai_response(resp.json())
            
            if not ai_text:
                logger.warning("AI分析返回空结果")
                return {}
            
            logger.info(f"AI分析原文: {ai_text}")
            
            # 解析结果
            result = {"上装": "", "下装": "", "头戴": "", "手持": ""}
            for line in ai_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                for key in result.keys():
                    if line.startswith(f"{key}：") or line.startswith(f"{key}:"):
                        value = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                        if value and value not in ["无", "没有", "未提及", "未知"]:
                            result[key] = value
                        break
            
            return result
            
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            return {}

    def _complete_fields_if_needed(self, content: str, result: Dict[str, str]) -> Dict[str, str]:
        """
        根据需要补全字段
        
        补全规则：
        1. 如果上装和下装都为空，不补全
        2. 如果只有上装或只有下装，补全另一个
        3. 如果用户描述包含节日/活动/风格等概括性需求，补全所有空字段
        """
        has_top = bool(result.get("上装"))
        has_bottom = bool(result.get("下装"))
        has_head = bool(result.get("头戴"))
        has_hand = bool(result.get("手持"))
        
        # 检测是否为概括性需求
        theme_keywords = [
            # 节日
            "圣诞", "新年", "春节", "元旦", "情人节", "万圣节", "复活节", "感恩节",
            "中秋", "端午", "元宵", "七夕", "国庆", "劳动节", "儿童节",
            # 活动/场景
            "派对", "聚会", "生日", "毕业", "运动会", "音乐节",
            "野餐", "露营", "旅行", "度假", "海滩", "滑雪",
            # 风格
            "休闲", "正式", "商务", "运动", "街头", "复古", "嘻哈",
            "可爱", "酷炫", "优雅", "时尚", "潮流",
            # 营销活动
            "促销", "双十一", "618", "年货节", "开学季",
            "氛围", "主题", "风格", "造型"
        ]
        
        is_theme_request = any(kw in content for kw in theme_keywords)
        
        # 判断需要补全的字段
        fields_to_complete = []
        
        if is_theme_request:
            # 概括性需求：补全所有空字段
            if not has_top:
                fields_to_complete.append("上装")
            if not has_bottom:
                fields_to_complete.append("下装")
            if not has_head:
                fields_to_complete.append("头戴")
            if not has_hand:
                fields_to_complete.append("手持")
            if fields_to_complete:
                logger.info(f"检测到概括性需求，准备补全: {fields_to_complete}")
        else:
            # 非概括性需求：只补全上下装
            if has_top and not has_bottom:
                fields_to_complete.append("下装")
                logger.info("检测到只有上装，准备补全下装")
            elif has_bottom and not has_top:
                fields_to_complete.append("上装")
                logger.info("检测到只有下装，准备补全上装")
        
        if not fields_to_complete:
            return result
        
        # 调用AI补全
        completed = self._request_completion(content, result, fields_to_complete)
        
        for key in fields_to_complete:
            if completed.get(key):
                result[key] = completed[key]
                logger.info(f"补全 {key}: {completed[key]}")
        
        return result
    
    def _request_completion(self, content: str, current: Dict[str, str], fields: List[str]) -> Dict[str, str]:
        """请求AI补全指定字段"""
        try:
            existing_info = []
            for key in ["上装", "下装", "头戴", "手持"]:
                if current.get(key):
                    existing_info.append(f"{key}: {current[key]}")
            
            existing_str = "、".join(existing_info) if existing_info else "暂无"
            fields_str = "、".join(fields)
            
            prompt = f"""用户描述："{content}"

            已确定的装扮：{existing_str}

            请根据用户描述的整体风格/主题，补充以下装扮：{fields_str}

            要求：
            1. 与用户描述的主题/风格保持一致
            2. 与已有装扮协调搭配
            3. 描述要简洁具体（如"红色圣诞帽"）
            4. 下装只能是裤子类，不能是裙子

            请按格式输出：
            """
            for field in fields:
                prompt += f"{field}：xxx\n"

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是专业的服装搭配师，擅长根据主题风格搭配协调的装扮。"},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            resp = http_post(self.api_url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            ai_text = parse_ai_response(resp.json())
            
            if not ai_text:
                return {}
            
            logger.info(f"AI补全原文: {ai_text}")
            
            result = {}
            for line in ai_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                for field in fields:
                    if line.startswith(f"{field}：") or line.startswith(f"{field}:"):
                        value = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                        if value and value not in ["无", "没有", "未知"]:
                            result[field] = value
                        break
            
            return result
            
        except Exception as e:
            logger.error(f"AI补全失败: {e}")
            return {}

    def process_content(self, content: str) -> Dict:
        """
        处理内容的主函数（优化版：合并AI调用）
        
        Args:
            content: 待处理的内容
            
        Returns:
            Dict: 处理结果，包含合规检查和内容分析
        """
        # 1. 先进行本地违规词检查（快速）
        is_compliant, reason = self._check_external_banned_words(content)
        if not is_compliant:
            return {
                "success": False,
                "compliant": False,
                "reason": f"违规词检测：{reason}",
                "analysis": None
            }
        
        # 2. 合并AI调用：同时进行敏感检查和内容分析
        try:
            analysis = self._analyze_content_combined(content)
            if analysis.get("_compliance_failed"):
                return {
                    "success": False,
                    "compliant": False,
                    "reason": analysis.get("_compliance_reason", "内容不合规"),
                    "analysis": None
                }
            
            # 移除内部标记
            analysis.pop("_compliance_failed", None)
            analysis.pop("_compliance_reason", None)
            
            return {
                "success": True,
                "compliant": True,
                "reason": "",
                "analysis": analysis
            }
        except Exception as e:
            logger.error(f"内容处理失败: {e}")
            return {
                "success": False,
                "compliant": True,
                "reason": "",
                "analysis": {
                    "表情": "",
                    "动作": "站姿",
                    "上装": "",
                    "下装": "",
                    "头戴": "",
                    "手持": ""
                }
            }

    def _analyze_content_combined(self, content: str) -> Dict[str, str]:
        """
        合并的内容分析（一次AI调用完成：敏感检查 + 六维度分析 + 智能补全）
        优化：将所有AI分析合并为一次调用，大幅减少API调用次数
        支持缓存：相同输入直接返回缓存结果
        """
        result = {
            "表情": "",
            "动作": "",
            "上装": "",
            "下装": "",
            "头戴": "",
            "手持": ""
        }
        
        logger.info("开始合并分析内容: %s", content)
        
        # 0. 检查缓存（优先使用缓存结果）
        cached_result = analysis_cache.get(content)
        if cached_result:
            logger.info("✅ 命中缓存，跳过AI分析")
            return cached_result
        
        # 1. 先用关键词快速分析动作（不需要AI）
        action_type = self._quick_action_match(content)
        result["动作"] = action_type
        
        # 2. 检测是否为概括性需求（节日/主题等）
        is_theme_request = self._is_theme_request(content)
        
        # 3. 一次AI调用完成：敏感检查 + 装扮分析 + 智能补全
        try:
            # 根据是否为主题请求，调整prompt
            if is_theme_request:
                prompt = f"""请分析以下用户描述，完成三个任务：

用户描述："{content}"

【任务1：合规检查】
检查内容是否涉及以下敏感话题：
- 政治相关：政治人物、政治事件、政治口号
- 民族相关：特定民族及其传统服饰、民族冲突
- 国家相关：国旗、国徽、政治象征
- 女装相关：女装、裙子、婚纱等女性服装

【任务2：装扮提取与补全】
这是一个主题/节日/风格类需求，请：
1. 提取用户明确描述的装扮
2. 根据主题风格，为未提及的维度补全合适的装扮

维度说明：
- 表情：面部表情（如开心、微笑、惊讶等）
- 上装：上半身穿着的衣物
- 下装：下半身穿着的衣物（只能是裤子类，不能是裙子）
- 头戴：头上佩戴的物品
- 手持：手中拿着的物品

请严格按以下格式输出（每个维度都要填写，根据主题补全）：
合规：是/否
不合规原因：xxx（如果合规则填"无"）
表情：xxx
上装：xxx
下装：xxx
头戴：xxx
手持：xxx"""
            else:
                prompt = f"""请分析以下用户描述，完成两个任务：

用户描述："{content}"

【任务1：合规检查】
检查内容是否涉及以下敏感话题：
- 政治相关：政治人物、政治事件、政治口号
- 民族相关：特定民族及其传统服饰、民族冲突
- 国家相关：国旗、国徽、政治象征
- 女装相关：女装、裙子、婚纱等女性服装

【任务2：装扮提取与补全】
提取角色的装扮信息：
- 表情：面部表情（如开心、微笑、惊讶等），未提及填"无"
- 上装：上半身穿着的衣物
- 下装：下半身穿着的衣物（只能是裤子类）
- 头戴：头上佩戴的物品，未提及填"无"
- 手持：手中拿着的物品，未提及填"无"

重要规则：
- 如果用户只提到上装没提到下装，请根据上装风格补全一个协调的下装
- 如果用户只提到下装没提到上装，请根据下装风格补全一个协调的上装
- 下装只能是裤子类（如牛仔裤、休闲裤等），不能是裙子

请严格按以下格式输出：
合规：是/否
不合规原因：xxx（如果合规则填"无"）
表情：xxx
上装：xxx
下装：xxx
头戴：xxx
手持：xxx"""

            # 使用专用的分析模型（可独立配置）
            payload = {
                "model": self.analysis_model,
                "messages": [
                    {"role": "system", "content": "你是专业的内容审核和美术指导，擅长检查内容合规性、提取角色装扮信息并进行风格搭配。"},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"合并AI分析使用模型: {self.analysis_model}")
            resp = http_post(self.api_url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            ai_text = parse_ai_response(resp.json())
            
            if ai_text:
                logger.info(f"AI合并分析原文: {ai_text}")
                
                # 解析合规检查结果
                if "合规：否" in ai_text or "合规:否" in ai_text:
                    reason_match = re.search(r"不合规原因[：:]\s*([^\n]+)", ai_text)
                    reason = reason_match.group(1).strip() if reason_match else "内容不合规"
                    if reason != "无":
                        result["_compliance_failed"] = True
                        result["_compliance_reason"] = f"敏感内容检测：{reason}"
                        return result
                
                # 解析装扮信息
                field_patterns = {
                    "表情": r"表情[：:]\s*([^\n]+)",
                    "上装": r"上装[：:]\s*([^\n]+)",
                    "下装": r"下装[：:]\s*([^\n]+)",
                    "头戴": r"头戴[：:]\s*([^\n]+)",
                    "手持": r"手持[：:]\s*([^\n]+)"
                }
                
                for key, pattern in field_patterns.items():
                    match = re.search(pattern, ai_text)
                    if match:
                        value = match.group(1).strip()
                        if value and value not in ["无", "没有", "未提及", "未知", "未设置"]:
                            # 清理markdown格式标记
                            value = re.sub(r'\*\*([^*]+)\*\*', r'\1', value)  # 移除 **粗体**
                            value = re.sub(r'\*([^*]+)\*', r'\1', value)      # 移除 *斜体*
                            value = re.sub(r'^[\*\-\+]\s*', '', value)        # 移除列表标记
                            value = value.strip()
                            result[key] = value
            
        except Exception as e:
            logger.error(f"AI合并分析失败: {e}")
        
        # 4. 存入缓存（只缓存成功且有效的结果）
        # 检查是否有有效的分析结果（至少有一个非空字段）
        has_valid_result = any(
            result.get(key) for key in ["表情", "上装", "下装", "头戴", "手持"]
        )
        
        if not result.get("_compliance_failed") and has_valid_result:
            analysis_cache.set(content, result)
            logger.info("✅ 分析结果已缓存")
        elif not has_valid_result:
            logger.warning("⚠️ 分析结果为空，不缓存")
        
        logger.info("最终分析结果: %s", result)
        return result
    
    def _is_theme_request(self, content: str) -> bool:
        """检测是否为概括性需求（节日/主题/风格等）"""
        theme_keywords = [
            # 节日
            "圣诞", "新年", "春节", "元旦", "情人节", "万圣节", "复活节", "感恩节",
            "中秋", "端午", "元宵", "七夕", "国庆", "劳动节", "儿童节",
            # 活动/场景
            "派对", "聚会", "生日", "毕业", "运动会", "音乐节",
            "野餐", "露营", "旅行", "度假", "海滩", "滑雪",
            # 风格
            "休闲", "正式", "商务", "运动", "街头", "复古", "嘻哈",
            "可爱", "酷炫", "优雅", "时尚", "潮流",
            # 营销活动
            "促销", "双十一", "618", "年货节", "开学季",
            "氛围", "主题", "风格", "造型"
        ]
        return any(kw in content for kw in theme_keywords)

    def _quick_action_match(self, content: str) -> str:
        """快速关键词匹配动作类型（不需要AI）"""
        content_lower = content.lower()
        
        keyword_mapping = {
            "跑动": ["跑", "奔跑", "跑步", "奔", "冲刺"],
            "跳跃": ["跳", "跳跃", "蹦", "蹦跳", "跳起"],
            "坐姿": ["坐", "坐着", "坐下", "坐姿"],
            "欢快": ["欢快", "开心", "快乐", "兴奋", "愉快", "高兴"],
            "站姿": ["站", "站立", "站着", "站姿"]
        }
        
        for action_type, keywords in keyword_mapping.items():
            for keyword in keywords:
                if keyword in content_lower:
                    logger.info(f"快速匹配动作: {action_type}")
                    return action_type
        
        return "站姿"  # 默认站姿


if __name__ == "__main__":
    # 测试代码
    agent = ContentAgent()
    
    # 测试指定的内容
    test_content = "我要一个穿着披风，跳起来，带着贝雷帽的形象"
    
    logger.info("=" * 60)
    logger.info(f"测试内容: {test_content}")
    logger.info("=" * 60)
    
    try:
        result = agent.process_content(test_content)
        logger.info("处理结果:")
        logger.info(f"  成功: {result.get('success')}")
        logger.info(f"  合规: {result.get('compliant')}")
        logger.info(f"  原因: {result.get('reason')}")
        if result.get('analysis'):
            logger.info("  分析结果:")
            for key, value in result['analysis'].items():
                logger.info(f"    {key}: {value}")
        else:
            logger.info("  分析结果: None")
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
