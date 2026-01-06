#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片选择和组合处理器
根据用户需求选择身体和头像图片，并进行组合
"""

import os
import random
import glob
import time
import uuid
from typing import List, Tuple, Dict, Optional, Callable
from PIL import Image, ImageDraw
from matchers.body_matcher import BodyMatcher
from matchers.head_matcher import HeadMatcher
import importlib.util
import sys

# 动态导入per-data.py模块
current_dir = os.path.dirname(os.path.abspath(__file__))
per_data_path = os.path.join(current_dir, "per-data.py")
spec = importlib.util.spec_from_file_location("per_data", per_data_path)
if spec is not None and spec.loader is not None:
    per_data = importlib.util.module_from_spec(spec)
    sys.modules["per_data"] = per_data
    spec.loader.exec_module(per_data)
    
    # 从模块中导入函数
    compose_images_new_logic = per_data.compose_images_new_logic
else:
    raise ImportError("无法加载per-data.py模块")


class ImageProcessor:
    """图片选择和组合处理器"""
    
    def __init__(self):
        """初始化图片处理器"""
        self.body_matcher = BodyMatcher()
        self.head_matcher = HeadMatcher()
        
        # 动作类型到文件夹的映射
        self.body_folder_mapping = {
            "站姿": "data/body_stand",
            "欢快": "data/body_happy", 
            "坐姿": "data/body_sit",
            "跳跃": "data/body_jump",
            "跑动": "data/body_run"
        }
        
        # 动作类型到头像文件夹的映射
        self.head_folder_mapping = {
            "站姿": "data/face_front_per",
            "欢快": "data/face_front_per",
            "坐姿": "data/face_front_per", 
            "跳跃": "data/face_front_per",
            "跑动": "data/face_left_turn_per"
        }
        
        # 动作类型到图片数量的映射
        self.body_count_mapping = {
            "站姿": 2,
            "欢快": 2,
            "坐姿": 2,
            "跳跃": 1,
            "跑动": 2
        }
    
    def select_body_images(self, action_type: str) -> List[str]:
        """根据动作类型选择身体图片"""
        folder_path = self.body_folder_mapping.get(action_type, "data/body_stand")
        count = self.body_count_mapping.get(action_type, 2)
        
        # 获取文件夹中的所有图片文件
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']
        all_images = []
        
        for extension in image_extensions:
            all_images.extend(glob.glob(os.path.join(folder_path, extension)))
        
        if not all_images:
            print(f"警告：在文件夹 {folder_path} 中没有找到图片文件")
            return []
        
        # 随机选择指定数量的图片
        selected_images = random.sample(all_images, min(count, len(all_images)))
        
        print(f"从 {folder_path} 中选择了 {len(selected_images)} 张身体图片")
        return selected_images
    
    def select_head_images(self, action_type: str, requirement: str, log_callback: Optional[Callable[[str], None]] = None) -> List[Dict]:
        """根据动作类型选择头像图片，通过head_matcher分析"""
        folder_path = self.head_folder_mapping.get(action_type, "data/face_front_per")
        
        # 使用head_matcher从指定文件夹中选择最佳匹配的头像
        selected_heads, logs = self.head_matcher.find_best_matches_from_folder(
            requirement, folder_path, top_k=2, log_callback=log_callback
        )
        
        msg = f"从 {folder_path} 中选择了 {len(selected_heads)} 张头像图片"
        print(msg)
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        try:
            debug = [(h.get('image_name'), round(float(h.get('score', 0.0)), 4)) for h in selected_heads]
            print(f"头像选择详情: {debug}")
        except Exception:
            pass
        return selected_heads
    
    def _combine_normal_images(self, body_path: str, head_path: str, 
                              output_dir: str, suffix: str) -> Optional[str]:
        """普通组合：使用高级图片合成逻辑，基于红色区域检测和角度校正"""
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成输出路径
            output_path = os.path.join(output_dir, f"combined_normal_{suffix}.png")
            
            # 使用per-data.py中的新图片合成逻辑（普通动作）
            result = compose_images_new_logic(body_path, head_path, output_path)
            
            if result:
                # result现在可能是白色背景图的路径或原始合成图路径
                if isinstance(result, str) and os.path.exists(result):
                    print(f"成功组合图片：{result}")
                    return result
                else:
                    print(f"成功组合图片：{output_path}")
                    return output_path
            else:
                print(f"高级图片合成失败")
                return None
            
        except Exception as e:
            print(f"组合图片失败：{str(e)}")
            return None
    
    def _combine_jump_images(self, body_path: str, head_path: str, 
                            output_dir: str, suffix: str) -> Optional[str]:
        """跳跃组合：使用高级图片合成逻辑，基于红色区域检测和角度校正"""
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成输出路径
            output_path = os.path.join(output_dir, f"combined_jump_{suffix}.png")
            
            # 使用per-data.py中的新图片合成逻辑（跳跃动作）
            result = compose_images_new_logic(body_path, head_path, output_path, action_type="跳跃")
            
            if result:
                # result现在可能是白色背景图的路径或原始合成图路径
                if isinstance(result, str) and os.path.exists(result):
                    print(f"成功组合跳跃图片：{result}")
                    return result
                else:
                    print(f"成功组合跳跃图片：{output_path}")
                    return output_path
            else:
                print(f"高级图片合成失败")
                return None
            
        except Exception as e:
            print(f"组合跳跃图片失败：{str(e)}")
            return None
    
    def combine_images(self, body_images: List[str], head_images: List[Dict], 
                      action_type: str, output_dir: str = "output", log_callback: Optional[Callable[[str], None]] = None) -> List[str]:
        """组合身体和头像图片"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        combined_images = []
        # 为本次组合生成唯一标签，避免文件名重名
        from datetime import datetime
        unique_tag = datetime.now().strftime("%Y%m%d_%H%M%S") + '_' + uuid.uuid4().hex[:4]
        
        # 所有动作类型都进行body和face图片的两两组合
        for i, body_path in enumerate(body_images):
            for j, head_data in enumerate(head_images):
                if action_type == "跳跃":
                    combined_path = self._combine_jump_images(
                        body_path, head_data["image_path"], 
                        output_dir, f"{unique_tag}_{i}_{j}"
                    )
                elif action_type == "跑动":
                    combined_path = self._combine_running_images(
                        body_path, head_data["image_path"], 
                        output_dir, f"{unique_tag}_{i}_{j}"
                    )
                else:
                    combined_path = self._combine_normal_images(
                        body_path, head_data["image_path"], 
                        output_dir, f"{unique_tag}_{i}_{j}"
                    )
                if combined_path:
                    combined_images.append(combined_path)
                    if log_callback:
                        try:
                            log_callback(f"生成组合图片: {combined_path}")
                        except Exception:
                            pass
        
        return combined_images

    def process_user_requirement(self, requirement: str, output_dir: str = "output", log_callback: Optional[Callable[[str], None]] = None) -> Dict:
        msg0 = f"开始处理用户需求：{requirement}"
        print(msg0)
        if log_callback:
            try:
                log_callback(msg0)
            except Exception:
                pass
        action_type = self.body_matcher.classify_action_type(requirement)
        msg1 = f"分析得到的动作类型：{action_type}"
        print(msg1)
        if log_callback:
            try:
                log_callback(msg1)
            except Exception:
                pass
        body_images = self.select_body_images(action_type)
        if log_callback:
            try:
                log_callback(f"从身体库选择了 {len(body_images)} 张图片")
            except Exception:
                pass
        if not body_images:
            return {
                "success": False,
                "error": "没有找到合适的身体图片",
                "action_type": action_type
            }
        head_images = self.select_head_images(action_type, requirement, log_callback=log_callback)
        if not head_images:
            return {
                "success": False,
                "error": "没有找到合适的头像图片",
                "action_type": action_type
            }
        combined_images = self.combine_images(body_images, head_images, action_type, output_dir, log_callback=log_callback)
        if log_callback:
            try:
                log_callback(f"组合生成基础图片 {len(combined_images)} 张")
            except Exception:
                pass
        return {
            "success": True,
            "action_type": action_type,
            "body_images": body_images,
            "head_images": [img["image_path"] for img in head_images],
            "combined_images": combined_images,
            "total_generated": len(combined_images)
        }

    def _combine_running_images(self, body_path: str, head_path: str, 
                               output_dir: str, suffix: str) -> Optional[str]:
        """跑步组合：使用高级图片合成逻辑，基于红色区域检测和角度校正，face图片水平向右移动125px"""
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成输出路径
            output_path = os.path.join(output_dir, f"combined_running_{suffix}.png")
            
            # 使用per-data.py中的新图片合成逻辑（跑步动作）
            result = compose_images_new_logic(body_path, head_path, output_path, action_type="跑动")
            
            if result:
                # result现在可能是白色背景图的路径或原始合成图路径
                if isinstance(result, str) and os.path.exists(result):
                    print(f"成功组合跑步图片：{result}")
                    return result
                else:
                    print(f"成功组合跑步图片：{output_path}")
                    return output_path
            else:
                print(f"高级图片合成失败")
                return None
            
        except Exception as e:
            print(f"组合跑步图片失败：{str(e)}")
            return None

    def stack_images_vertically(self, image_paths: List[str], output_dir: str = "output") -> Optional[str]:
        """将多张图片沿垂直方向拼接为一张图片，返回输出路径"""
        print(f"\n=== 开始垂直拼接图片 ===")
        print(f"输入图片路径列表: {image_paths}")
        print(f"输出目录: {output_dir}")
        
        try:
            # 检查有效路径
            valid_paths = [p for p in image_paths if p and os.path.exists(p)]
            print(f"有效图片路径数量: {len(valid_paths)}/{len(image_paths)}")
            
            if not valid_paths:
                print("错误: 没有有效的图片路径")
                return None

            # 检查每个图片文件
            for i, path in enumerate(valid_paths):
                print(f"图片 {i+1}: {path}")
                if os.path.exists(path):
                    file_size = os.path.getsize(path)
                    print(f"  - 文件大小: {file_size} bytes")
                else:
                    print(f"  - 文件不存在!")

            from PIL import Image
            print(f"开始加载图片...")
            images = []
            for i, path in enumerate(valid_paths):
                try:
                    img = Image.open(path).convert('RGBA')
                    print(f"图片 {i+1} 加载成功: {img.size} (宽x高)")
                    images.append(img)
                except Exception as e:
                    print(f"图片 {i+1} 加载失败: {e}")
                    continue
            
            if not images:
                print("错误: 没有成功加载的图片")
                return None
            
            # 统一宽度为最大宽度，等比缩放
            max_width = max(img.width for img in images)
            print(f"最大宽度: {max_width}px")
            
            resized = []
            for i, img in enumerate(images):
                if img.width != max_width:
                    new_height = int(img.height * (max_width / img.width))
                    print(f"图片 {i+1} 需要缩放: {img.size} -> ({max_width}, {new_height})")
                    # 使用正确的重采样方法
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                else:
                    print(f"图片 {i+1} 无需缩放: {img.size}")
                resized.append(img)

            total_height = sum(img.height for img in resized)
            print(f"拼接后总高度: {total_height}px")
            
            # 创建透明背景
            print(f"创建画布: {max_width}x{total_height}")
            stacked = Image.new('RGBA', (max_width, total_height))
            # 将透明背景设置为完全透明
            stacked.putalpha(0)

            y_offset = 0
            for i, img in enumerate(resized):
                print(f"粘贴图片 {i+1} 到位置 (0, {y_offset})")
                stacked.paste(img, (0, y_offset), img)
                y_offset += img.height

            os.makedirs(output_dir, exist_ok=True)
            from datetime import datetime
            unique_tag = datetime.now().strftime("%Y%m%d_%H%M%S") + '_' + uuid.uuid4().hex[:4]
            output_path = os.path.join(output_dir, f"accessories_stack_{unique_tag}.png")
            print(f"保存拼接图片到: {output_path}")
            
            stacked.save(output_path)
            
            # 验证保存结果
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"拼接图片保存成功，文件大小: {file_size} bytes")
            else:
                print("错误: 拼接图片保存失败")
                return None
                
            return output_path
        except Exception as e:
            print(f"垂直拼接图片失败: {e}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            return None


if __name__ == "__main__":
    # 测试代码
    processor = ImageProcessor()
    
    # 测试不同的需求
    test_requirements = [
        "我需要一个开心站立的角色",
        "创建一个坐着思考的人物",
        "生成一个跳跃的快乐角色",
        "制作一个奔跑的运动员"
    ]
    
    for req in test_requirements:
        print(f"\n{'='*50}")
        result = processor.process_user_requirement(req)
        print(f"处理结果：{result}")
