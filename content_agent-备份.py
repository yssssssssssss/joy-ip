#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容合规检查和分析Agent
功能：
1. 合规检查：屏蔽违规关键词
2. 内容分析：按照表情、动作、服装、手拿、头戴、背景六个维度分析内容
"""

import os
import re
import logging
from typing import Dict, List, Tuple
from matchers.base_matcher import BaseMatcher
from config import get_config
# 使用优化后的 HTTP 客户端和违规词库
from utils.http_client import http_post, http_get, parse_ai_response
from utils.banned_words import get_banned_words, check_banned_words, reload_banned_words, add_banned_word as add_word_to_cache, remove_banned_word as remove_word_from_cache


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
        # 从统一配置获取 API 信息
        config = get_config()
        self.api_url = config.AI_API_URL
        self.api_token = config.AI_API_KEY
        self.model = config.AI_MODEL
        
        # 使用全局共享的 Matcher 实例（延迟加载）
        # 不再在 __init__ 中创建实例，改用属性访问
        
        # 使用全局缓存的违规词库（不再重复加载）
        # 通过 get_banned_words() 获取
    
    @property
    def body_matcher(self):
        """延迟加载的 BodyMatcher"""
        return _get_body_matcher()
    
    @property
    def head_matcher(self):
        """延迟加载的 HeadMatcher"""
        return _get_head_matcher()
    
    def _check_external_banned_words(self, content: str) -> Tuple[bool, str]:
        """检查外部违规词库（使用全局缓存）"""
        return check_banned_words(content)
    
    def update_banned_words_from_url(self, url: str) -> bool:
        """从在线URL更新违规词库"""
        try:
            response = http_get(url, timeout=30)
            response.raise_for_status()
            
            # 保存到本地文件
            os.makedirs("data", exist_ok=True)
            with open("data/sensitive_words.txt", 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # 重新加载违规词库缓存
            reload_banned_words()
            logger.info("违规词库更新成功")
            return True
        except Exception as e:
            logger.error(f"更新违规词库失败: {e}")
            return False
    
    def add_banned_word(self, word: str) -> bool:
        """动态添加违规词或正则表达式"""
        return add_word_to_cache(word)
    
    def remove_banned_word(self, word: str) -> bool:
        """动态移除违规词或正则表达式"""
        return remove_word_from_cache(word)
    
    def _check_sensitive_content_with_ai(self, content: str) -> Tuple[bool, str]:
        """
        使用AI检查政治、民族、国家、女装等敏感内容
        
        Args:
            content: 待检查的内容
            
        Returns:
            Tuple[bool, str]: (是否合规, 不合规原因)
        """
        try:
            prompt = f"""
            请检查以下内容是否明确涉及政治、民族、国家等敏感话题：
            内容："{content}"

            检查重点（仅标记明确的敏感内容）：
            1. 政治相关：具体政治人物姓名、政治事件、政治制度、政治口号、政治立场
            2. 民族相关：明确指定的特定民族（如"藏族"、"维族"等）及其传统服饰、民族冲突
            3. 国家相关：国旗、国徽、国歌、具体国家政治象征（如天安门、白宫等）
            4. 女装相关：女装、裙子、婚纱等女性服装

            注意事项：
            - 普通的帽子、衣服、运动服等日常物品不算敏感内容
            - 只有明确指向特定政治、民族、国家的内容才标记为敏感
            - 模糊或通用的描述（如"帽子"、"衣服"）不应标记为敏感

            如果内容完全不涉及上述明确的敏感话题，请回复"合规"。
            如果内容明确涉及上述敏感话题，请回复"不合规：[具体原因]"。
            """

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的敏感内容审核专家，专门识别政治、民族、国家等敏感内容。你必须严格执行审核标准，对任何可能涉及敏感话题的内容都要标记为不合规。"},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            resp = http_post(self.api_url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            
            result = parse_ai_response(data)
            
            if not result:
                logger.warning("AI敏感内容检查返回空结果，默认通过")
                return True, ""
            
            if "合规" in result and "不合规" not in result:
                return True, ""
            if "不合规" in result:
                m = re.search(r"不合规[：:]\s*(.+)", result)
                reason = m.group(1).strip() if m else result.strip()
                return False, f"敏感内容检测：{reason}"
            
            # 如果结果不明确，为安全起见返回不合规
            return False, f"敏感内容检测：AI返回不明确结果 - {result}"
                
        except Exception as e:
            logger.error(f"AI敏感内容检查失败: {str(e)}")
            # 错误时为安全起见返回不合规
            return False, "敏感内容检测：检查过程出错，为安全起见拒绝"

    def check_compliance(self, content: str) -> Tuple[bool, str]:
        """
        检查内容是否合规
        
        Args:
            content: 待检查的内容
            
        Returns:
            Tuple[bool, str]: (是否合规, 不合规原因)
        """
        # 第一层：检查外部违规词库（包含所有违规词和正则表达式）
        is_compliant, reason = self._check_external_banned_words(content)
        if not is_compliant:
            return False, f"违规词检测：{reason}"
        
        # 第二层：AI敏感内容检查（宗教、政治、民族、国家）
        is_compliant, reason = self._check_sensitive_content_with_ai(content)
        if not is_compliant:
            return False, reason
        
        # 第三层：使用AI进行通用合规检查（排除已检查的敏感内容）
        try:
            prompt = f"""
            请检查以下内容是否包含违规信息：

            内容："{content}"

            检查重点（排除政治、民族、国家相关内容，这些已单独检查）：
            1. 暴力内容：暴力行为、血腥场面、武器使用等
            2. 色情内容：性暗示、裸体、情色描述等
            3. 毒品相关：吸毒、贩毒、毒品制造等
            4. 赌博相关：赌博行为、博彩活动等
            5. 违法犯罪：盗窃、诈骗、其他犯罪行为等
            6. 自残自杀：自杀、自残、抑郁等负面内容
            7. 歧视仇恨：基于性别、年龄等的歧视言论

            如果内容合规，请回复"合规"。
            如果内容不合规，请回复"不合规：[原因]"。
            """

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的内容审核专家，负责检查除敏感政治内容外的其他违规内容。"},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            resp = http_post(self.api_url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            result = parse_ai_response(data)
            
            if not result:
                return True, ""
            
            if "合规" in result and "不合规" not in result:
                return True, ""
            if "不合规" in result:
                m = re.search(r"不合规[：:]\s*(.+)", result)
                reason = m.group(1).strip() if m else result.strip()
                return False, f"通用违规检测：{reason}"
            return True, ""
                
        except Exception as e:
            logger.warning(f"AI合规检查失败: {str(e)}")
            # 如果AI检查失败，返回通过（保守策略）
            return True, ""
    
    def analyze_content(self, content: str) -> Dict[str, str]:
        """
        分析内容，按照六个维度进行分类
        
        Args:
            content: 待分析的内容
            
        Returns:
            Dict[str, str]: 包含六个维度的分析结果
        """
        result = {
            "表情": "",
            "动作": "",
            "服装": "",
            "手拿": "",
            "头戴": "",
            "背景": ""
        }
        logger.info("开始分析内容: %s", content)
        direct_fields = self._extract_direct_fields(content)
        if direct_fields:
            logger.info("发现用户直接定义: %s", direct_fields)
        
        # 1. 使用head_matcher分析表情
        try:
            expression_features = self.head_matcher.analyze_user_requirement(content)
            # 提取表情相关信息
            if expression_features.get("表情"):
                result["表情"] = expression_features["表情"]
        except Exception as e:
            logger.warning(f"表情分析失败: {str(e)}")
        
        # 2. 使用body_matcher分析动作
        try:
            action_type = self.body_matcher.classify_action_type(content)
            result["动作"] = action_type
        except Exception as e:
            logger.warning(f"动作分析失败: {str(e)}")
        
        # 3-6. 使用AI分析服装、手拿、头戴、背景
        try:
            raw_ai_outputs: List[str] = []
            analysis_text = ""
            user_fields = {"服装": "", "手拿": "", "头戴": ""}
            for raw_line in re.split(r"\r?\n", content):
                line = raw_line.strip()
                if not line:
                    continue
                m = re.match(r"^(服装|手拿|头戴)[：:]\s*(.*)$", line)
                if m:
                    label, val = m.group(1), m.group(2)
                    user_fields[label] = val.strip()
            for k, v in direct_fields.items():
                user_fields[k] = v

            def _norm_user(label: str, value: str) -> str:
                if value is None:
                    return ""
                v = value.strip()
                if not v:
                    return ""
                none_words = {"无", "没有", "未提供", "不带", "不戴", "不拿"}
                if v in none_words:
                    return ""
                if re.fullmatch(rf"{label}[：:]?\s*", v):
                    return ""
                other_labels = ["服装", "手拿", "头戴", "背景"]
                other_labels.remove(label)
                for ol in other_labels:
                    if re.match(rf"^{ol}[：:]", v):
                        return ""
                if label == "手拿" and ("头戴" in v):
                    return ""
                if label == "头戴" and ("手拿" in v):
                    return ""
                return v

            for k in ["服装", "手拿", "头戴"]:
                val = _norm_user(k, user_fields[k])
                if val:
                    result[k] = val

            missing = [label for label in ["服装", "手拿", "头戴"] if not result[label]]
            if missing:
                logger.info("字段缺失，准备调用AI补全: %s", missing)
                analysis_text = self._request_ai_fields(content, missing, enforce_guess=False)
                if analysis_text:
                    raw_ai_outputs.append(analysis_text)
                    logger.info("AI补全原文: %s", analysis_text)
                else:
                    logger.warning("首次AI补全失败或返回空文本")
            else:
                logger.info("无需AI补全，三项全部来自用户输入")

            def _normalize_value(label: str, value: str) -> str:
                """规范化AI提取的字段值，过滤无效/误填内容。
                - 空值、否定词统一归为空（背景保留“无”）
                - 仅有标签本身（如“头戴：”）归为空
                - 交叉标签误填（以其他标签开头或包含其他标签关键词）归为空
                """
                if value is None:
                    return ""
                v = value.strip()
                if not v:
                    return ""
                none_words = {
                    "无", "没有", "未提供", "不带", "不戴", "不拿", "未知",
                    "无帽子", "没有帽子", "无头戴", "没有头戴",
                    "无服装", "没有服装", "无背景", "没有背景"
                }
                if v in none_words:
                    # 背景的“无”需要保留，其他标签置空
                    return "无" if label == "背景" else ""
                if re.fullmatch(rf"{label}[：:]?\s*", v):
                    return ""
                other_labels = ["服装", "手拿", "头戴", "背景"]
                other_labels.remove(label)
                for ol in other_labels:
                    if re.match(rf"^{ol}[：:]", v):
                        return ""
                if label == "手拿" and ("头戴" in v):
                    return ""
                if label == "头戴" and ("手拿" in v):
                    return ""
                if label == "头戴":
                    vh = v
                    if re.search(r"的帽子$", vh):
                        return vh
                    if re.search(r"帽子$", vh):
                        return re.sub(r"帽子$", "的帽子", vh)
                    if re.search(r"帽$", vh):
                        return re.sub(r"帽$", "的帽子", vh)
                    if "帽子" in vh:
                        idx = vh.rfind("帽子")
                        prefix = vh[:idx]
                        prefix = re.sub(r"[的\s]*$", "", prefix)
                        return (prefix + "的帽子") if prefix else "普通的帽子"
                    if "帽" in vh:
                        idx = vh.rfind("帽")
                        prefix = vh[:idx]
                        prefix = re.sub(r"[的\s]*$", "", prefix)
                        return (prefix + "的帽子") if prefix else "普通的帽子"
                    if len(vh) <= 40:
                        return vh + "的帽子"
                    return "普通的帽子"
                return v

            def _extract_fields(text: str) -> dict:
                """稳健提取字段：优先按行解析，其次用分段正则解析。"""
                fields = {"服装": "", "手拿": "", "头戴": "", "背景": ""}
                # 先按行解析
                for raw_line in re.split(r"\r?\n", text):
                    line = raw_line.strip()
                    if not line:
                        continue
                    m = re.match(r"^(服装|手拿|头戴|背景)[：:]\s*(.*)$", line)
                    if m:
                        label, val = m.group(1), m.group(2)
                        fields[label] = _normalize_value(label, val)
                # 若某些字段仍为空，使用分段正则补充（跨行/单段输出）
                segment_pattern = r"(服装|手拿|头戴|背景)[：:]\s*(.*?)(?=(?:服装|手拿|头戴|背景)[：:]|$)"
                for m in re.finditer(segment_pattern, text, flags=re.S):
                    label, val = m.group(1), m.group(2)
                    if not fields[label]:
                        fields[label] = _normalize_value(label, val)
                return fields

            parsed = _extract_fields(analysis_text)
            for k in ["服装", "手拿", "头戴"]:
                v = parsed.get(k, "")
                if v and not result[k]:
                    result[k] = v

            still_missing = [label for label in ["服装", "手拿", "头戴"] if not result[label]]
            if still_missing:
                logger.info("首次AI结果仍缺失，触发推断模式: %s", still_missing)
                fallback_text = self._request_ai_fields(content, still_missing, enforce_guess=True)
                if fallback_text:
                    raw_ai_outputs.append(fallback_text)
                    logger.info("AI推断原文: %s", fallback_text)
                    parsed_fb = _extract_fields(fallback_text)
                    for k in ["服装", "手拿", "头戴"]:
                        v = parsed_fb.get(k, "")
                        if v and not result[k]:
                            result[k] = v
                else:
                    logger.warning("推断模式AI仍返回空文本")

            result["_raw_ai"] = "\n---\n".join(raw_ai_outputs) if raw_ai_outputs else ""
            
            # 服装补全逻辑：如果只有上装或只有下装，则补全另一部分
            if result.get("服装"):
                completed_clothing = self._complete_clothing_if_needed(result["服装"])
                if completed_clothing != result["服装"]:
                    logger.info(f"服装补全: '{result['服装']}' -> '{completed_clothing}'")
                    result["服装"] = completed_clothing
                    
        except Exception as e:
            logger.error(f"内容分析失败: {str(e)}")
        
        logger.info("最终分析结果: %s", result)
        return result

    def _request_ai_fields(self, content: str, missing: List[str], enforce_guess: bool = False) -> str:
        """调用大模型补全或推断服装/手拿/头戴"""
        try:
            focus = "、".join(missing)
            requirement = (
                f"重点补充以下维度：{focus}。若描述未涉及，可填写“无”。"
                if not enforce_guess
                else f"必须结合上下文或常识推断 {focus}，尽量给出合理猜测，实在无法判断时才填写“未知”。"
            )
            prompt = f"""用户的整体描述如下：
                        {content}

                        {requirement}
                        请严格按照下列格式输出（即使某项为空也要保留该行）：
                        服装：xxx
                        手拿：xxx
                        """
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": [
                            {"type": "text", "text": "你是一名资深美术指导，需要从文本中提取或推断角色的服装、手拿物。请尽量给出具体描述，格式必须与要求一致。"}
                        ]
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt}
                        ]
                    }
                ],
                "stream": False
            }
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            resp = http_post(self.api_url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            
            result = parse_ai_response(data)
            if result:
                return result
            
            try:
                # 打印一次原始响应，便于定位返回结构
                import json as _json
                logger.warning("AI补全空响应: %s", _json.dumps(data, ensure_ascii=False)[:1000])
            except Exception:
                pass
            return ""
        except Exception as e:
            logger.error("调用AI补全失败: %s", e)
            return ""

    def _extract_direct_fields(self, content: str) -> Dict[str, str]:
        """直接从用户描述中提取服装/手拿/头戴的清晰定义"""
        patterns = {
            "服装": [
                # 修复：避免在服装描述中的"的"字符处过早停止匹配
                r"(?:服装|衣服|穿着|穿戴)(?:是|为|:|：)?\s*([^。;；\n]+?)(?:，(?:戴|拿)|的joy|joy|$)",
                r"穿(?:上|着)?\s*([^。;；\n]+?)(?:，(?:戴|拿)|的joy|joy|$)"
            ],
            "手拿": [
                r"(?:手拿|手持|拿着)(?:是|为|:|：)?\s*([^。;；\n]+?)(?:的joy|joy|$)",
                r"拿(?:着)?\s*([^。;；\n]+?)(?:的joy|joy|$)"
            ],
            "头戴": [
                r"(?:头戴|戴着|戴)(?:是|为|:|：)?\s*([^。;；\n]+?)(?:的joy|joy|$)",
                r"戴(?:上|着)?\s*([^。;；\n]+?)(?:帽|的joy|joy|$)"
            ]
        }
        extracted: Dict[str, str] = {}
        for label, regs in patterns.items():
            for reg in regs:
                m = re.search(reg, content)
                if m:
                    candidate = m.group(1).strip()
                    if candidate:
                        extracted[label] = candidate
                        break
        return extracted
    
    def _analyze_clothing_type(self, clothing_info: str) -> Dict[str, any]:
        """
        分析服装信息，判断是否只有上装或只有下装
        
        Args:
            clothing_info: 服装信息字符串
            
        Returns:
            dict: 包含分析结果的字典
        """
        if not clothing_info:
            return {"has_top": False, "has_bottom": False, "needs_completion": False}
        
        clothing_lower = clothing_info.lower()
        
        # 上装关键词
        top_keywords = [
            # 中文上装
            "夹克", "外套", "上衣", "衬衫", "t恤", "毛衣", "卫衣", "背心", 
            "马甲", "西装", "风衣", "大衣", "棉衣", "羽绒服", "开衫", "针织衫",
            "polo衫", "吊带", "抹胸", "胸衣", "内衣", "文胸",
            # 英文上装
            "jacket", "coat", "shirt", "t-shirt", "tshirt", "sweater", "hoodie", 
            "vest", "blazer", "cardigan", "top", "blouse", "tank"
        ]
        
        # 下装关键词
        bottom_keywords = [
            # 中文下装
            "裤子", "牛仔裤", "长裤", "短裤", "运动裤", "休闲裤", "西裤", "工装裤",
            "打底裤", "紧身裤", "阔腿裤", "直筒裤", "喇叭裤", "哈伦裤", "七分裤",
            "九分裤", "五分裤", "热裤", "裙子", "连衣裙", "短裙", "长裙", "半身裙",
            "百褶裙", "a字裙", "包臀裙", "蓬蓬裙", "牛仔裙", "纱裙",
            # 英文下装
            "pants", "jeans", "trousers", "shorts", "skirt", "dress", "leggings"
        ]
        
        # 检查是否包含上装
        has_top = any(keyword in clothing_lower for keyword in top_keywords)
        
        # 检查是否包含下装
        has_bottom = any(keyword in clothing_lower for keyword in bottom_keywords)
        
        # 判断是否需要补全
        needs_completion = (has_top and not has_bottom) or (has_bottom and not has_top)
        
        return {
            "has_top": has_top,
            "has_bottom": has_bottom,
            "needs_completion": needs_completion,
            "completion_type": "bottom" if has_top and not has_bottom else "top" if has_bottom and not has_top else "none"
        }
    
    def _request_clothing_completion(self, clothing_info: str, completion_type: str) -> str:
        """
        使用AI补全服装信息
        
        Args:
            clothing_info: 现有服装信息
            completion_type: 补全类型 ("top" 或 "bottom")
            
        Returns:
            str: 补全的服装部分
        """
        try:
            if completion_type == "bottom":
                prompt = f"""
                用户描述了上装：{clothing_info}
                
                请推荐一个最合适的下装搭配。要求：
                1. 只推荐一个下装
                2. 风格协调
                3. 颜色搭配和谐
                4. 用最简洁的词语描述
                
                请只返回一个下装名称，如：牛仔裤、黑色长裤、蓝色短裙
                不要返回多个选项，不要解释。
                """
            elif completion_type == "top":
                prompt = f"""
                用户描述了下装：{clothing_info}
                
                请推荐一个最合适的上装搭配。要求：
                1. 只推荐一个上装
                2. 风格协调
                3. 颜色搭配和谐
                4. 用最简洁的词语描述
                
                请只返回一个上装名称，如：白色T恤、黑色衬衫、红色夹克
                不要返回多个选项，不要解释。
                """
            else:
                return ""

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一名专业的服装搭配师，擅长根据现有服装推荐协调的搭配。请给出简洁准确的搭配建议。"},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            resp = http_post(self.api_url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            
            result = parse_ai_response(data)
            
            # 清理结果，只保留服装描述部分
            if result:
                # 移除可能的解释性文字
                lines = result.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('根据') and not line.startswith('建议') and not line.startswith('推荐'):
                        # 进一步清理，移除冒号后的内容
                        if '：' in line:
                            line = line.split('：')[-1].strip()
                        if ':' in line:
                            line = line.split(':')[-1].strip()
                        
                        # 如果包含多个选项（用顿号、逗号分隔），只取第一个
                        if '、' in line:
                            line = line.split('、')[0].strip()
                        elif '，' in line and len(line.split('，')) > 2:  # 超过2个逗号分隔的项目
                            line = line.split('，')[0].strip()
                        
                        return line
            
            return ""
            
        except Exception as e:
            logger.error(f"服装补全失败: {e}")
            return ""
    
    def _complete_clothing_if_needed(self, clothing_info: str) -> str:
        """
        如果需要，补全服装信息
        
        Args:
            clothing_info: 现有服装信息
            
        Returns:
            str: 补全后的服装信息
        """
        analysis = self._analyze_clothing_type(clothing_info)
        
        if not analysis["needs_completion"]:
            return clothing_info
        
        logger.info(f"检测到需要补全{analysis['completion_type']}装: {clothing_info}")
        
        completion = self._request_clothing_completion(clothing_info, analysis["completion_type"])
        
        if completion:
            if analysis["completion_type"] == "bottom":
                # 补全下装：上装 + 下装
                completed = f"{clothing_info}，{completion}"
            else:
                # 补全上装：上装 + 下装
                completed = f"{completion}，{clothing_info}"
            
            logger.info(f"服装补全成功: {completed}")
            return completed
        else:
            logger.warning("服装补全失败，保持原有信息")
            return clothing_info
    
    def process_content(self, content: str) -> Dict:
        """
        处理内容的主函数
        
        Args:
            content: 待处理的内容
            
        Returns:
            Dict: 处理结果，包含合规检查和内容分析
        """
        # 1. 合规检查
        is_compliant, reason = self.check_compliance(content)
        
        if not is_compliant:
            return {
                "success": False,
                "compliant": False,
                "reason": reason,
                "analysis": None
            }
        
        # 2. 内容分析
        analysis = self.analyze_content(content)
        
        return {
            "success": True,
            "compliant": True,
            "reason": "",
            "analysis": analysis
        }


if __name__ == "__main__":
    # 测试代码
    agent = ContentAgent()
    
    # 测试合规检查
    test_cases = [
        "生成一个符合中秋节氛围的joy形象"
    ]
    
    for test_content in test_cases:
        logger.info("=" * 50)
        logger.info(f"测试内容: {test_content}")
        result = agent.process_content(test_content)
        logger.info(f"处理结果: {result}")

