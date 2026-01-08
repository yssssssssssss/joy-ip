#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompt模板配置文件
用于管理不同场景下的系统提示词和约束条件
"""

# 系统提示词模板
SYSTEM_PROMPTS = {
    "default": 
"""
你是一个专业的图像编辑AI，专门负责为卡通角色添加配件。请严格按照以下要求操作：

【核心原则】
1. 绝对保持原图中角色的动作、表情、姿态完全不变
2. 只添加指定的配件，不修改角色本身的任何特征
3. 确保添加的配件符合角色的整体风格和比例

【质量标准】
- 配件的颜色、材质、大小要与角色协调
- 配件的位置要符合人体工程学和视觉美感
- 保持图像的清晰度和细节质量
""",


    "professional": 
"""
作为专业的角色设计AI，你需要为卡通角色精确添加指定配件：

【专业要求】
1. 保持角色原有的所有视觉特征（动作、表情、姿态、比例）
2. 配件添加要符合角色设计的一致性和专业标准
3. 确保配件的材质、光影、透视关系真实可信

【技术标准】
- 配件尺寸要符合角色比例和透视关系
- 颜色搭配要遵循色彩理论和视觉美学
- 细节处理要达到商业插画的质量标准""",


    "simple": 
"""
请为角色添加指定的配件，保持角色原有的动作和表情不变。

要求：
- 配件大小合适
- 颜色协调
- 位置自然"""
}


# 配件类型的具体指令模板
ACCESSORY_INSTRUCTIONS = {
    "服装": {
        "template": """【服装修改】
- 为角色穿上：{item}
- 服装要贴合角色身形，不要过大或过小
- 保持服装的自然褶皱和质感
- 不要遮挡角色的重要特征（如脸部、手部动作等）
- 服装颜色要与角色整体色调协调
- 确保服装符合角色的年龄和性别特征
- 如果是披风、大衣类，需要给角色上衣和裤子
- 需要添加适合的鞋子""",
        "constraints": [
            "不要添加任何女性化的服装",
            "服装不要包裹或遮挡手部、脚部",
            "保持服装的卡通风格特征"
        ]
    },
    
    "手拿": {
        "template": """【手拿物品】
- 让角色单手自然地拿着：{item}
- 物品大小要符合角色手部比例
- 手部姿态要自然，不要显得僵硬
- 物品位置要符合重力和人体工程学
- 确保物品不会遮挡角色的重要特征""",
        "constraints": [
            "不要出现多余的手指或变形的手部",
            "手拿物品不要过大或过小",
            "保持手部动作的自然性"
        ]
    },
    
    "头戴": {
        "template": """【头戴物品】
- 为角色戴上：{item}
- 头戴物品要戴在头部的中间
- 帽子大小要和头部成比例，不要太小
- 无檐帽要戴在两耳之间，有檐帽可以超过两耳
- 不要遮挡眼睛或耳朵
- 要与角色的头型和发型协调
- 保持头戴物品的立体感和质感""",
        "constraints": [
            "不要遮挡角色的眼睛或重要面部特征",
            "头戴物品要符合角色的头部比例",
            "保持头戴物品的稳定性和真实感"
        ]
    }
}

# 通用约束条件
GENERAL_CONSTRAINTS = [
    "绝对不要改变角色的动作、表情、姿态",
    "不要出现多余的手指或变形的手部",
    "不要添加任何女性化的服装或配件",
    "保持背景为浅灰色或纯色背景",
    "不要在脸部添加任何装饰（除非明确要求）",
    "确保所有配件都符合角色的年龄和性别特征",
    "保持图像的整体协调性和美观性",
    "不要添加文字、标签或其他无关元素",
    "确保配件的材质和光影效果真实自然",
    "保持角色的卡通风格特征",
    "添加浅灰色背景"
]

# 特殊场景的约束条件
SPECIAL_CONSTRAINTS = {
    "formal": [
        "配件要符合正式场合的要求",
        "颜色搭配要庄重得体",
        "避免过于花哨或夸张的设计"
    ],
    
    "casual": [
        "配件要符合休闲风格",
        "可以使用较为鲜艳的颜色",
        "设计可以更加活泼有趣"
    ],
    
    "sports": [
        "配件要符合运动风格",
        "材质要看起来轻便透气",
        "设计要体现运动感和活力"
    ]
}

# 质量优化提示词
QUALITY_ENHANCEMENTS = [
    "确保图像分辨率和清晰度",
    "优化光影效果和3D立体感",
    "保持色彩饱和度和对比度",
    "细化纹理和材质表现",
    "确保透视关系的准确性"
]

def get_system_prompt(style="default"):
    """获取系统提示词"""
    return SYSTEM_PROMPTS.get(style, SYSTEM_PROMPTS["default"])

def get_accessory_instruction(accessory_type, item_name):
    """获取配件指令"""
    if accessory_type in ACCESSORY_INSTRUCTIONS:
        template = ACCESSORY_INSTRUCTIONS[accessory_type]["template"]
        return template.format(item=item_name)
    return f"为角色添加：{item_name}"

def get_constraints(style="default", include_special=None):
    """获取约束条件"""
    constraints = GENERAL_CONSTRAINTS.copy()
    
    if include_special and include_special in SPECIAL_CONSTRAINTS:
        constraints.extend(SPECIAL_CONSTRAINTS[include_special])
    
    return constraints