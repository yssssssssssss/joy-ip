#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
头像匹配器类
专门处理头像表情分析和匹配
"""

import re
import json
import os
import random
import logging
import threading
from typing import Dict, List, Optional, Callable
from .base_matcher import BaseMatcher
from PIL import Image
from sentence_transformers import SentenceTransformer, util
# 使用全局 CLIP 管理器
from utils.clip_manager import get_clip_model, get_clip_tokenizer
from utils.limits import limit_text

logger = logging.getLogger(__name__)

_FOLDER_CLIP_CACHE_LOCK = threading.Lock()
_FOLDER_CLIP_CACHE: dict[str, dict] = {}


class HeadMatcher(BaseMatcher):
    """头像匹配器类"""

    def __init__(self):
        """初始化头像匹配器"""
        super().__init__()
        self.dimensions = ["眼睛形状", "嘴型", "表情", "脸部动态", "情感强度"]
        # 已移除Excel加载，统一改为基于文件夹的匹配
        # CLIP 模型使用全局共享实例
        self._clip_model_ref = None
    
    def analyze_user_requirement(self, requirement: str) -> Dict[str, str]:
        """分析用户需求，提取五个维度的特征"""
        try:
            enable_en_query = str(os.environ.get("ENABLE_HEAD_CLIP_QUERY_EN", "1")).strip().lower() in ("1", "true", "yes")

            # 优先走 JSON 输出（更稳定；也更容易严格提取“英文检索”）
            if enable_en_query:
                json_prompt = (
                    f"用户需求：\"{requirement}\"\n"
                    "\n"
                    "请提取头像/脸部的视觉特征，并仅输出一个 JSON 对象（不要 Markdown，不要解释）。\n"
                    "JSON 必须包含以下字段（缺失则写\"未识别\"）：\n"
                    "- 眼睛形状\n"
                    "- 嘴型\n"
                    "- 表情\n"
                    "- 脸部动态\n"
                    "- 情感强度\n"
                    "- 英文检索\n"
                    "\n"
                    "其中：\n"
                    "- 英文检索：用于图像检索的英文短语（尽量短，逗号分隔；只描述头像/脸部特征；不要包含中文；不要解释）。\n"
                )
                system_prompt = "你是一个专业的需求分析专家。请严格按要求输出 JSON。"
                analysis_text = self._call_ai(
                    system_prompt,
                    json_prompt,
                    temperature=0.0,
                    max_tokens=256,
                    response_mime_type="application/json",
                )
                parsed = self._parse_requirement_analysis_json(analysis_text)
                if parsed:
                    return parsed

            # 回退：原始“多行文本”解析（在部分模型/网关下更兼容）
            prompt = (
                f"将\"{requirement}\"按照\"眼睛形状、嘴型、表情、脸部动态、情感强度\"五个维度进行分析，精简得到的结果，并将结果按照以下形式输出：\n"
                "眼睛形状：\n"
                "嘴型：\n"
                "表情：\n"
                "脸部动态：\n"
                "情感强度：\n"
            )
            if enable_en_query:
                prompt += (
                    "\n"
                    "再补充一行用于图像检索的英文短语（只输出英文短语，不要解释，不要加引号；尽量短、逗号分隔；只描述头像/脸部特征）：\n"
                    "英文检索：\n"
                )
            system_prompt = "你是一个专业的需求分析专家。请根据用户的需求描述，分析出对应的视觉特征。"
            analysis_text = self._call_ai(system_prompt, prompt, temperature=0.1, max_tokens=200)
            if analysis_text:
                return self._parse_requirement_analysis(analysis_text)
            return {dim: "未识别" for dim in self.dimensions}
        
        except Exception as e:
            logger.info(f"分析用户需求失败: {str(e)}")
            return {dim: "未识别" for dim in self.dimensions}

    def _parse_requirement_analysis_json(self, analysis_text: str) -> Dict[str, str]:
        """解析 JSON 格式的需求分析结果（更稳定）。"""
        try:
            if not isinstance(analysis_text, str) or not analysis_text.strip():
                return {}

            t = analysis_text.strip()
            if t.startswith("```"):
                t = re.sub(r"^```(?:json)?", "", t, flags=re.IGNORECASE).strip()
                t = re.sub(r"```$", "", t).strip()

            # 容错：截取第一个 {...} 区间
            start = t.find("{")
            end = t.rfind("}")
            if start != -1 and end != -1 and end > start:
                t = t[start : end + 1]

            obj = json.loads(t)
            if not isinstance(obj, dict):
                return {}

            def _pick(*keys: str):
                for k in keys:
                    if k in obj:
                        return obj.get(k)
                return None

            def _to_str(v) -> str:
                if v is None:
                    return ""
                if isinstance(v, str):
                    return v.strip()
                if isinstance(v, (int, float)):
                    return str(v)
                if isinstance(v, list):
                    parts = [str(x).strip() for x in v if x is not None and str(x).strip()]
                    return ", ".join(parts)
                return str(v).strip()

            result: Dict[str, str] = {dim: "未识别" for dim in self.dimensions}
            result["眼睛形状"] = _to_str(_pick("眼睛形状", "eye", "eyes", "eye_shape", "eyeShape")) or "未识别"
            result["嘴型"] = _to_str(_pick("嘴型", "mouth", "mouth_shape", "mouthShape")) or "未识别"
            result["表情"] = _to_str(_pick("表情", "expression")) or "未识别"
            result["脸部动态"] = _to_str(_pick("脸部动态", "face_motion", "faceMotion", "facial_motion", "facialMotion")) or "未识别"
            result["情感强度"] = _to_str(_pick("情感强度", "emotion_intensity", "emotionIntensity", "intensity")) or "未识别"
            result["英文检索"] = _to_str(_pick("英文检索", "en_query", "enQuery", "english_query", "englishQuery", "query", "clip_query", "clipQuery"))
            return result

        except Exception:
            return {}
    
    def _parse_requirement_analysis(self, analysis_text: str) -> Dict[str, str]:
        """解析需求分析结果"""
        result = {dim: "" for dim in self.dimensions}
        
        patterns = {
            "眼睛形状": r"眼睛形状[：:]\s*([^\n]+)",
            "嘴型": r"嘴型[：:]\s*([^\n]+)",
            "表情": r"表情[：:]\s*([^\n]+)",
            "脸部动态": r"脸部动态[：:]\s*([^\n]+)",
            "情感强度": r"情感强度[：:]\s*([^\n]+)"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, analysis_text)
            if match:
                result[key] = match.group(1).strip()
            else:
                result[key] = "未识别"

        # 可选：英文检索 query（用于 CLIP 文本嵌入）
        try:
            m = re.search(r"英文检索[：:]\s*([^\n]+)", analysis_text, flags=re.IGNORECASE)
            if m:
                result["英文检索"] = m.group(1).strip()
            else:
                result["英文检索"] = ""
        except Exception:
            result["英文检索"] = ""

        return result

    def _clean_clip_query_text(self, text: str) -> str:
        """清洗 CLIP 检索 query，尽量得到一行短文本。"""
        if not isinstance(text, str):
            return ""
        t = text.strip().strip('"').strip("'").strip()
        if not t:
            return ""
        t = t.replace("\r", " ").replace("\n", " ").strip()
        t = re.sub(r"^(?:英文检索|English\s*(?:query|search|clip\s*query)?)\s*[：:]\s*", "", t, flags=re.IGNORECASE).strip()
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _has_english_letters(self, text: str) -> bool:
        try:
            return bool(re.search(r"[A-Za-z]", text or ""))
        except Exception:
            return False

    def _build_clip_query_text(self, requirement: str, requirement_features: Optional[Dict[str, str]]) -> str:
        """
        构造用于 CLIP 检索的文本 query：
        1) 优先使用 LLM 生成的“英文检索”
        2) 失败回退到旧的表情关键词提取/映射
        3) 再兜底使用原始 requirement
        """
        candidate = ""
        if isinstance(requirement_features, dict):
            candidate = requirement_features.get("英文检索") or ""
        candidate = self._clean_clip_query_text(candidate)
        if candidate and self._has_english_letters(candidate):
            if "face" not in candidate.lower() and "head" not in candidate.lower():
                candidate = f"{candidate} face"
            return candidate

        expr_text = self._clean_clip_query_text(self._extract_expression_text(requirement))
        if expr_text:
            if self._has_english_letters(expr_text):
                if "face" not in expr_text.lower() and "head" not in expr_text.lower():
                    expr_text = f"{expr_text} face"
            return expr_text

        fallback = self._clean_clip_query_text(requirement)
        if fallback and "face" not in fallback.lower() and "head" not in fallback.lower():
            fallback = f"{fallback} face"
        return fallback

    def find_best_matches(self, requirement: str, top_k: int = 3, log_callback: Optional[Callable[[str], None]] = None) -> tuple:
        """找到最匹配的头像图片，返回结果和处理日志；支持日志回调实时输出"""
        if self.df.empty:
            return [], []
        
        # 初始化日志收集
        processing_logs = []
        
        # 分析用户需求
        requirement_features = self.analyze_user_requirement(requirement)
        log_msg = f"头像需求分析结果: {requirement_features}"
        logger.info(log_msg)
        processing_logs.append(log_msg)
        if log_callback:
            log_callback(log_msg)
        
        # 计算每张图片的匹配得分
        scores = []
        processing_logs.append("开始计算头像图片匹配得分...")
        if log_callback:
            log_callback("开始计算头像图片匹配得分...")
        
        for index, row in self.df.iterrows():
            image_features = {dim: str(row.get(dim, '')) for dim in self.dimensions}
            
            dimension_scores = self.calculate_dimension_scores(
                requirement_features, image_features, self.dimensions
            )
            
            # 计算综合得分（五个维度的平均分）
            total_score = sum(dimension_scores.values()) / len(dimension_scores)
            
            # 从Excel中获取图片路径
            image_name = str(row.get('图片名', ''))
            image_path = str(row.get('图片url地址', ''))
            
            # 如果Excel中没有路径，则使用默认路径
            if not image_path or image_path == 'nan':
                image_path = f"data/joy_head/{image_name}"
            
            scores.append({
                "image_name": image_name,
                "image_path": image_path,
                "score": total_score,
                "dimension_scores": dimension_scores,
                "features": image_features,
                "requirement_features": requirement_features,
                "type": "head"
            })
            
            log_msg = f"头像图片 {image_name} 综合得分: {total_score:.1f}, 维度得分: {dimension_scores}"
            logger.info(log_msg)
            processing_logs.append(log_msg)
            if log_callback:
                log_callback(log_msg)
        
        # 按得分排序，返回前top_k个
        scores.sort(key=lambda x: x['score'], reverse=True)
        processing_logs.append(f"头像匹配完成，选择前{top_k}个最佳匹配")
        if log_callback:
            log_callback(f"头像匹配完成，选择前{top_k}个最佳匹配")
        
        return scores[:top_k], processing_logs
    
    def find_best_matches_from_folder(self, requirement: str, folder_path: str, 
                                     top_k: int = 2, log_callback: Optional[Callable[[str], None]] = None) -> tuple:
        """从指定文件夹中找到最匹配的头像图片"""
        import glob
        
        # 初始化日志收集
        processing_logs = []
        
        # 获取文件夹中的所有图片文件
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']
        all_images = []
        
        for extension in image_extensions:
            all_images.extend(glob.glob(os.path.join(folder_path, extension)))
        
        if not all_images:
            log_msg = f"警告：在文件夹 {folder_path} 中没有找到图片文件"
            logger.info(log_msg)
            processing_logs.append(log_msg)
            if log_callback:
                log_callback(log_msg)
            return [], processing_logs
        
        # 使用 CLIP 对“表情”文本与图片进行相似度检索
        requirement_features = self.analyze_user_requirement(requirement)
        query_text = self._build_clip_query_text(requirement, requirement_features)
        logger.info(f"头像CLIP检索文本: {query_text}")
        log_msg = f"头像需求分析结果: {requirement_features}"
        logger.info(log_msg)
        processing_logs.append(log_msg)
        if log_callback:
            log_callback(log_msg)

        processing_logs.append(f"开始计算文件夹 {folder_path} 中头像图片匹配得分（CLIP检索）...")
        if log_callback:
            log_callback(f"开始计算文件夹 {folder_path} 中头像图片匹配得分（CLIP检索）...")

        # 懒加载 CLIP 模型（使用全局共享实例）
        self._ensure_clip_model()

        # 文本嵌入（确保不超过 CLIP 最大序列长度 77）
        try:
            # 先用 CLIP 分词器安全截断，避免 77/82 等长度冲突
            query_text_safe = self._truncate_clip_text(query_text)
            # SentenceTransformer.encode 文本参数为位置参数或 sentences 关键字
            text_emb = self._clip_model_ref.encode([query_text_safe], convert_to_tensor=True, normalize_embeddings=True)
        except Exception as e:
            err = f"文本向量化失败: {str(e)}"
            logger.error(err)
            processing_logs.append(err)
            if log_callback:
                log_callback(err)
            return [], processing_logs

        def _folder_fingerprint(paths: List[str]) -> tuple[int, float]:
            try:
                mt = 0.0
                for p in paths:
                    try:
                        mt = max(mt, os.path.getmtime(p))
                    except Exception:
                        pass
                return (len(paths), mt)
            except Exception:
                return (len(paths), 0.0)

        def _get_or_build_folder_cache(paths: List[str]) -> dict:
            fingerprint = _folder_fingerprint(paths)
            key = os.path.abspath(folder_path)
            with _FOLDER_CLIP_CACHE_LOCK:
                cached = _FOLDER_CLIP_CACHE.get(key)
                if cached and cached.get("fingerprint") == fingerprint:
                    return cached

            # 缓存未命中：批量构建 embeddings（一次性编码，显著降低重复开销）
            images: List[Image.Image] = []
            valid_paths: List[str] = []
            names: List[str] = []
            for p in paths:
                try:
                    with Image.open(p) as im:
                        images.append(im.convert("RGB"))
                    valid_paths.append(p)
                    names.append(os.path.basename(p))
                except Exception as e:
                    err = f"图片加载失败 {os.path.basename(p)}: {str(e)}"
                    logger.error(err)
                    processing_logs.append(err)
                    if log_callback:
                        log_callback(err)

            if not images:
                return {"fingerprint": fingerprint, "paths": [], "names": [], "embeddings": None}

            try:
                img_embs = self._clip_model_ref.encode(images, convert_to_tensor=True, normalize_embeddings=True)
            except Exception as e:
                err = f"文件夹图片向量化失败: {str(e)}"
                logger.error(err)
                processing_logs.append(err)
                if log_callback:
                    log_callback(err)
                return {"fingerprint": fingerprint, "paths": [], "names": [], "embeddings": None}

            built = {"fingerprint": fingerprint, "paths": valid_paths, "names": names, "embeddings": img_embs}
            with _FOLDER_CLIP_CACHE_LOCK:
                _FOLDER_CLIP_CACHE[key] = built
            return built

        folder_cache = _get_or_build_folder_cache(all_images)
        img_embs = folder_cache.get("embeddings")
        img_paths = folder_cache.get("paths") or []
        img_names = folder_cache.get("names") or []

        if img_embs is None or not img_paths:
            return [], processing_logs

        # 图片检索评分（向量化后批量相似度计算）
        try:
            sims = util.cos_sim(img_embs, text_emb).squeeze(1).tolist()
        except Exception as e:
            err = f"相似度计算失败: {str(e)}"
            logger.error(err)
            processing_logs.append(err)
            if log_callback:
                log_callback(err)
            return [], processing_logs

        scores = []
        for idx, img_path in enumerate(img_paths):
            img_name = img_names[idx] if idx < len(img_names) else os.path.basename(img_path)
            try:
                total_score = float(sims[idx])
            except Exception:
                total_score = 0.0

            scores.append({
                "image_name": img_name,
                "image_path": img_path,
                "score": total_score,
                "dimension_scores": {dim: total_score for dim in self.dimensions},
                "features": {dim: "CLIP相似度" for dim in self.dimensions},
                "requirement_features": requirement_features,
                "type": "head"
            })

            log_msg = f"头像图片 {img_name} 相似度: {total_score:.4f}"
            logger.info(log_msg)
            processing_logs.append(log_msg)
            if log_callback:
                log_callback(log_msg)
        
        # 按得分排序并去重，返回前top_k个
        scores.sort(key=lambda x: x['score'], reverse=True)
        unique = []
        seen = set()
        for item in scores:
            p = item.get('image_path')
            if p and p not in seen:
                unique.append(item)
                seen.add(p)
            if len(unique) >= top_k:
                break
        names = [u.get('image_name') for u in unique]
        processing_logs.append(f"头像匹配完成，选择前{top_k}个最佳匹配: {names}")
        if log_callback:
            log_callback(f"头像匹配完成，选择前{top_k}个最佳匹配: {names}")
        
        return unique, processing_logs

    def find_one_best_match_from_folder(self, requirement: str, folder_path: str,
                                        top_k: int = 5, log_callback: Optional[Callable[[str], None]] = None) -> tuple:
        """从文件夹中找到前top_k排序，并从中随机抽取一张返回"""
        top_results, logs = self.find_best_matches_from_folder(requirement, folder_path, top_k=top_k, log_callback=log_callback)
        if not top_results:
            return [], logs
        chosen = random.choice(top_results)
        choose_log = f"从前{top_k}名中随机抽取的图片: {chosen.get('image_name')}"
        logger.info(choose_log)
        logs.append(choose_log)
        if log_callback:
            log_callback(choose_log)
        return [chosen], logs

    def _ensure_clip_model(self):
        """获取全局共享的 CLIP 模型（线程安全）"""
        if self._clip_model_ref is None:
            self._clip_model_ref = get_clip_model()

    def _truncate_clip_text(self, text: str) -> str:
        """将文本安全截断到 CLIP 支持的最大 token 长度（默认 77）。
        若分词器不可用，则返回原始文本。"""
        try:
            tokenizer = get_clip_tokenizer()
            if tokenizer is None:
                return text
            max_len = 77
            encoded = tokenizer(text, truncation=True, max_length=max_len, return_tensors=None)
            ids = encoded.get('input_ids')
            if isinstance(ids, list) and len(ids) > 0:
                first = ids[0] if isinstance(ids[0], list) else ids
                truncated_text = tokenizer.decode(first, skip_special_tokens=True)
                # 打印一次有帮助的日志
                try:
                    original_ids = tokenizer(text).get('input_ids', [])
                    original_len = len(original_ids[0] if original_ids and isinstance(original_ids[0], list) else original_ids)
                    truncated_len = len(first)
                    if original_len > truncated_len:
                        logger.info(f"CLIP文本已截断: 原tokens={original_len} -> 截断后={truncated_len}")
                except Exception:
                    pass
                return truncated_text.strip()
            return text
        except Exception:
            return text

    def _translate_to_english(self, cn_text: str) -> str:
        """将中文表情关键词转为英文短语（用于CLIP检索）。

        默认使用本地词典映射，避免额外大模型调用导致超时与吞吐下降。
        如需启用大模型翻译，可设置环境变量 ENABLE_EXPR_LLM_TRANSLATION=1。
        """
        try:
            if not cn_text or not cn_text.strip():
                return ""

            cn = cn_text.strip()

            # 1) 本地映射（优先）
            mapping = {
                "大笑": "laughing face",
                "哈哈": "laughing face",
                "微笑": "smiling face",
                "笑": "smiling face",
                "开心": "happy face",
                "愉快": "happy face",
                "高兴": "happy face",
                "喜悦": "happy face",
                "兴奋": "excited face",
                "得意": "proud face",
                "调皮": "playful face",
                "疑惑": "confused face",
                "思考": "thinking face",
                "惊讶": "surprised face",
                "震惊": "shocked face",
                "吃惊": "surprised face",
                "害羞": "shy face",
                "脸红": "blushing face",
                "羞涩": "shy face",
                "愤怒": "angry face",
                "生气": "angry face",
                "怒视": "angry face",
                "悲伤": "sad face",
                "难过": "sad face",
                "哭泣": "crying face",
                "伤心": "sad face",
                "哭": "crying face",
                "冷漠": "neutral face",
                "面瘫": "neutral face",
                "无表情": "neutral face",
                "平静": "calm face",
                "紧张": "nervous face",
                "放松": "relaxed face",
                "眨眼": "winking face",
                "闭眼": "eyes closed face",
            }

            for k, v in mapping.items():
                if k in cn:
                    return v

            # 2) 可选：大模型翻译（默认关闭）
            enable_llm = str(os.environ.get("ENABLE_EXPR_LLM_TRANSLATION", "0")).strip().lower() in ("1", "true", "yes")
            if enable_llm:
                from utils.http_client import http_post, parse_ai_response
                payload = {
                    "model": os.environ.get("EXPR_TRANSLATION_MODEL", "doubao-seed-1.6-250615"),
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": f"Translate this Chinese facial expression to English for image search. Output ONLY the English phrase, no explanation.\nChinese: {cn}\nEnglish:"}
                            ]
                        }
                    ],
                    "temperature": 0,
                    "max_tokens": 30,
                    "stream": False
                }
                headers = {
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                }

                with limit_text():
                    connect_timeout = int(os.environ.get("HTTP_CONNECT_TIMEOUT_S", "10"))
                    resp = http_post(self.api_url, json=payload, headers=headers, timeout=(connect_timeout, 30), use_retry=False)
                resp.raise_for_status()
                en_text = parse_ai_response(resp.json())

                if en_text:
                    en_text = en_text.strip().strip('"\'').strip().replace('\n', ' ').strip()
                    if en_text and 'face' not in en_text.lower():
                        en_text = en_text + " face"
                    logger.debug(f"表情翻译(大模型): '{cn}' -> '{en_text}'")
                    return en_text

            # 3) 兜底：中文 + face
            fallback = cn
            if 'face' not in fallback.lower():
                fallback = fallback + " face"
            return fallback
        except Exception as e:
            logger.warning(f"表情翻译异常: {e}，使用原文: '{cn_text}'")
            return cn_text

    def _extract_expression_text(self, requirement: str) -> str:
        """提取表情文本并通过大模型翻译为英文（CLIP英文效果更好）
        
        当没有找到表情描述时，默认使用"开心"
        """
        try:
            # 先尝试从格式化文本中提取
            m = re.search(r"表情[：:]\s*([^\n]+)", requirement)
            cn_expr = ""
            if m:
                cn_expr = m.group(1).strip()
            else:
                # 常见表情关键词列表
                keywords = [
                    "大笑", "微笑", "开心", "愉快", "高兴", "喜悦", "笑", "哈哈",
                    "愤怒", "生气", "怒视", "发火",
                    "悲伤", "难过", "哭泣", "伤心", "哭",
                    "惊讶", "震惊", "吃惊",
                    "害羞", "脸红", "羞涩",
                    "冷漠", "面瘫", "无表情", "平静",
                    "张嘴", "咧嘴", "闭嘴", "嘟嘴",
                    "眨眼", "闭眼", "睁大眼",
                    "调皮", "得意", "疑惑", "思考", "紧张", "放松"
                ]
                for kw in keywords:
                    if kw in requirement:
                        cn_expr = kw
                        break
            
            # 如果找到中文表情，使用大模型翻译为英文
            if cn_expr:
                return self._translate_to_english(cn_expr)
            
            # 如果没有找到特定表情关键词，使用默认表情"开心"
            logger.info(f"未找到表情描述，使用默认表情: 开心")
            return self._translate_to_english("开心")
            
        except Exception as e:
            logger.info(f"提取表情文本异常: {e}，使用默认表情: happy face")
            return "happy face"
