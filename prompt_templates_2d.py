#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2D 专用 Prompt 扩展模板
继承基础模板（prompt_templates.py），仅覆盖需要差异化的项
"""

# 继承基础模板
from prompt_templates import (
    SYSTEM_PROMPTS as BASE_SYSTEM_PROMPTS,
    ACCESSORY_INSTRUCTIONS as BASE_ACCESSORY_INSTRUCTIONS,
    GENERAL_CONSTRAINTS as BASE_GENERAL_CONSTRAINTS,
    QUALITY_ENHANCEMENTS as BASE_QUALITY_ENHANCEMENTS,
    get_accessory_instruction as base_get_accessory_instruction,
    get_system_prompt as base_get_system_prompt,
    get_constraints as base_get_constraints
)

# ============================================
# 2D 专属系统提示词（覆盖基础版本）
# ============================================
SYSTEM_PROMPTS_2D = {
    "default": 
"""
你是一个专业的2D图像编辑AI，专门负责为2D卡通角色添加配件。请严格按照以下要求操作：

【核心原则】
1. 绝对保持原图中角色的动作、表情、姿态完全不变
2. 只添加指定的配件，不修改角色本身的任何特征
3. 确保添加的配件符合2D卡通风格
4. 不要添加黑色描边

""",

    "professional": 
"""
作为专业的2D角色设计AI，你需要为卡通角色精确添加指定配件：

【专业要求】
1. 保持角色原有的所有视觉特征（动作、表情、姿态、比例）
2. 配件添加要符合2D动画设计的一致性和专业标准
3. 线条要流畅，色块要干净

【技术标准】
- 配件尺寸要符合2D角色比例
- 颜色搭配要遵循动画色彩理论
- 细节处理要达到商业动画的质量标准""",

    "simple": 
"""
请为2D角色添加指定的配件，保持角色原有的动作和表情不变。

要求：
- 配件大小合适
- 颜色鲜艳协调
- 线条清晰
- 保持2D风格"""
}


# ============================================
# 2D 专属配件指令模板（覆盖需要差异化的项）
# ============================================
ACCESSORY_INSTRUCTIONS_2D = {
    "服装": {
        "template": """【2D服装修改】
- 为角色穿上：{item}
- 服装符合2D动画风格
- 不要添加黑色描边
- 保持服装的色块分明和简洁阴影
- 不要遮挡角色的重要特征（如脸部、手部动作等）
- 如果有上装和下装，要同时添加
- 需要添加适合的鞋子"""
    },
    
    "手拿": {
        "template": """【2D手拿物品】
- 让角色单手自然地拿着：{item}
- 物品大小要符合2D角色手部比例
- 手部姿态要自然，不要显得僵硬
- 物品位置要符合重力和人体工程学"""
    },
    
    "头戴": {
        "template": """【2D头戴物品】
- 为角色戴上：{item}
- 帽子大小要和头部成比例，不要太小
- 无檐帽要戴在两耳之间，有檐帽可以超过两耳
- 不要遮挡眼睛或耳朵
"""
    }
}


# ============================================
# 2D 专属通用约束条件
# ============================================
GENERAL_CONSTRAINTS_2D = [
    "不要添加黑色描边",
    "绝对不要改变角色的动作、表情、姿态",
    "不要出现多余的手指或变形的手部",
    "不要添加任何女性化的服装或配件",
    "保持背景为浅灰色或纯色背景",
    "不要在脸部添加任何装饰（除非明确要求）",
    "保持图像的整体协调性和美观性",
    "不要添加文字、标签或其他无关元素",
    "保持2D扁平化风格",
    "颜色要鲜艳饱和",
    "添加浅灰色背景"
]


# ============================================
# 2D 版本的获取函数
# ============================================

def get_system_prompt_2d(style="default"):
    """获取2D版本的系统提示词"""
    return SYSTEM_PROMPTS_2D.get(style, SYSTEM_PROMPTS_2D["default"])


def get_accessory_instruction_2d(accessory_type, item_name):
    """获取2D版本的配件指令"""
    if accessory_type in ACCESSORY_INSTRUCTIONS_2D:
        template = ACCESSORY_INSTRUCTIONS_2D[accessory_type]["template"]
        return template.format(item=item_name)
    # 没有覆盖的维度，回退到基础模板
    return base_get_accessory_instruction(accessory_type, item_name)


def get_constraints_2d(style="default", include_special=None):
    """获取2D版本的约束条件"""
    from prompt_templates import SPECIAL_CONSTRAINTS
    
    constraints = GENERAL_CONSTRAINTS_2D.copy()
    
    if include_special and include_special in SPECIAL_CONSTRAINTS:
        constraints.extend(SPECIAL_CONSTRAINTS[include_special])
    
    return constraints


# ============================================
# 统一接口（根据模式选择模板）
# ============================================

def get_system_prompt(style="default", mode="3d"):
    """统一接口：根据模式获取系统提示词"""
    if mode == "2d":
        return get_system_prompt_2d(style)
    return base_get_system_prompt(style)


def get_accessory_instruction(accessory_type, item_name, mode="3d"):
    """统一接口：根据模式获取配件指令"""
    if mode == "2d":
        return get_accessory_instruction_2d(accessory_type, item_name)
    return base_get_accessory_instruction(accessory_type, item_name)


def get_constraints(style="default", include_special=None, mode="3d"):
    """统一接口：根据模式获取约束条件"""
    if mode == "2d":
        return get_constraints_2d(style, include_special)
    return base_get_constraints(style, include_special)


# ============================================
# 测试代码
# ============================================
if __name__ == "__main__":
    print("=== 2D 模板测试 ===")
    
    print("\n--- 系统提示词 ---")
    print(get_system_prompt_2d("default")[:100] + "...")
    
    print("\n--- 服装指令 ---")
    print(get_accessory_instruction_2d("服装", "红色圣诞毛衣"))
    
    print("\n--- 约束条件 ---")
    constraints = get_constraints_2d()
    for i, c in enumerate(constraints[:5]):
        print(f"  {i+1}. {c}")
    print(f"  ... 共 {len(constraints)} 条")
    
    print("\n--- 统一接口测试 ---")
    print(f"3D模式: {get_accessory_instruction('服装', '西装', mode='3d')[:50]}...")
    print(f"2D模式: {get_accessory_instruction('服装', '西装', mode='2d')[:50]}...")
