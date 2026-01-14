#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
红色区域检测和图片合成工具 - 精简版
保留核心功能，删除冗余代码
"""

import cv2
import numpy as np
import math
import os


def analyze_red_region(image_path):
    """
    分析图片中的红色区域，返回位置和角度信息
    
    Args:
        image_path: 图片路径
        
    Returns:
        dict: 包含红色区域信息的字典，如果未找到则返回None
    """
    # 读取图片
    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if image is None:
        print(f"错误：无法加载图片 {image_path}")
        return None
    
    # 转换为HSV颜色空间进行红色检测
    if image.shape[2] >= 3:
        hsv = cv2.cvtColor(image[:,:,:3], cv2.COLOR_BGR2HSV)
    else:
        print("错误：图片格式不支持")
        return None
    
    # 定义红色的HSV阈值范围
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    
    # 创建红色区域掩码
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    
    # 查找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 找到最大的红色区域
    max_contour = None
    max_area = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > max_area and area > 100:  # 过滤小区域
            max_area = area
            max_contour = contour
    
    if max_contour is None:
        print("警告：未找到足够大的红色区域")
        return None
    
    # 获取边界框信息
    x, y, w, h = cv2.boundingRect(max_contour)
    
    # 获取最小外接矩形和角度信息
    rect = cv2.minAreaRect(max_contour)
    center, (width, height), angle = rect
    
    # 计算倾斜角度 - 使用更稳定的算法
    # OpenCV的minAreaRect返回的角度范围是-90到0度
    # 我们需要将其转换为相对于水平线的角度
    
    # 使用PCA主成分分析来获得更稳定的角度
    # 将轮廓点转换为合适的格式
    points = max_contour.reshape(-1, 2).astype(np.float32)
    
    # 计算主成分分析
    mean = np.empty((0))
    mean, eigenvectors = cv2.PCACompute(points, mean)
    
    # 获取主方向向量
    main_direction = eigenvectors[0]
    
    # 计算角度（相对于水平线）
    angle_radians = np.arctan2(main_direction[1], main_direction[0])
    angle_degrees = np.degrees(angle_radians)
    
    # 将角度标准化到-45到45度范围内
    while angle_degrees > 45:
        angle_degrees -= 90
    while angle_degrees < -45:
        angle_degrees += 90
    
    return {
        'center': (int(center[0]), int(center[1])),
        'bbox': {'x': x, 'y': y, 'width': w, 'height': h},
        'angle': angle_degrees,
        'area': max_area
    }

def analyze_red_region_array(image):
    if image is None:
        return None
    if image.ndim != 3 or image.shape[2] < 3:
        return None
    if image.shape[2] >= 3:
        hsv = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2HSV)
    else:
        return None
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    max_contour = None
    max_area = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > max_area and area > 100:
            max_area = area
            max_contour = contour
    if max_contour is None:
        return None
    x, y, w, h = cv2.boundingRect(max_contour)
    rect = cv2.minAreaRect(max_contour)
    center, (width, height), angle = rect
    points = max_contour.reshape(-1, 2).astype(np.float32)
    mean = np.empty((0))
    mean, eigenvectors = cv2.PCACompute(points, mean)
    main_direction = eigenvectors[0]
    angle_radians = np.arctan2(main_direction[1], main_direction[0])
    angle_degrees = np.degrees(angle_radians)
    while angle_degrees > 45:
        angle_degrees -= 90
    while angle_degrees < -45:
        angle_degrees += 90
    return {
        'center': (int(center[0]), int(center[1])),
        'bbox': {'x': x, 'y': y, 'width': w, 'height': h},
        'angle': angle_degrees,
        'area': max_area
    }

def rotate_image_around_center(image, angle):
    """
    围绕图片中心旋转图片
    
    Args:
        image: 输入图片
        angle: 旋转角度（度）
        
    Returns:
        旋转后的图片
    """
    if abs(angle) < 0.1:  # 角度太小则跳过旋转
        return image
    
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos = np.abs(rotation_matrix[0, 0])
    sin = np.abs(rotation_matrix[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    rotation_matrix[0, 2] += (new_w / 2) - center[0]
    rotation_matrix[1, 2] += (new_h / 2) - center[1]
    if image.shape[2] >= 4:
        bgr = image[:, :, :3].astype(np.float32)
        a = image[:, :, 3].astype(np.float32) / 255.0
        bgr_premul = bgr * a[..., None]
        bgr_rot = cv2.warpAffine(bgr_premul, rotation_matrix, (new_w, new_h),
                                 flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                 borderValue=(0, 0, 0))
        a_rot = cv2.warpAffine(a, rotation_matrix, (new_w, new_h),
                               flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                               borderValue=0)
        eps = 1e-6
        out_bgr = np.zeros_like(bgr_rot, dtype=np.float32)
        mask = a_rot > eps
        out_bgr[mask] = bgr_rot[mask] / a_rot[mask][..., None]
        out_bgr = np.clip(out_bgr, 0, 255).astype(np.uint8)
        out_a = np.clip(a_rot * 255.0, 0, 255).astype(np.uint8)
        return np.dstack([out_bgr, out_a])
    rotated = cv2.warpAffine(image, rotation_matrix, (new_w, new_h),
                             flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                             borderValue=(0, 0, 0))
    return rotated


def crop_to_content(image):
    """
    去除图片周围的空白透明区域
    
    Args:
        image: 输入图片（带透明通道）
        
    Returns:
        裁剪后的图片
    """
    if image.shape[2] < 4:  # 没有alpha通道
        return image
    
    # 获取alpha通道
    alpha = image[:, :, 3]
    
    # 找到非透明区域的边界
    coords = cv2.findNonZero(alpha)
    if coords is None:
        return image
    
    x, y, w, h = cv2.boundingRect(coords)
    
    # 添加一些边距
    margin = 10
    x = max(0, x - margin)
    y = max(0, y - margin)
    w = min(image.shape[1] - x, w + 2 * margin)
    h = min(image.shape[0] - y, h + 2 * margin)
    
    return image[y:y+h, x:x+w]


def ensure_alpha_channel(image):
    """
    确保图片有透明通道
    
    Args:
        image: 输入图片
        
    Returns:
        带透明通道的图片
    """
    if image.shape[2] == 3:
        alpha = np.ones((image.shape[0], image.shape[1]), dtype=image.dtype) * 255
        image = np.dstack([image, alpha])
    return image

def bottom_quarter_bbox(image):
    h, w = image.shape[:2]
    y0 = (3 * h) // 4
    if image.shape[2] >= 4:
        alpha = image[:, :, 3].astype(np.uint8)

        # 1) 先在“下1/4区域”内尝试不同阈值查找非透明像素
        for t in (10, 5, 1):
            region = (alpha[y0:, :] > t).astype(np.uint8)
            pts = cv2.findNonZero(region)
            if pts is not None:
                x, y, bw, bh = cv2.boundingRect(pts)
                return (x, y0 + y, bw, bh)

        # 2) 如果下1/4没有任何非透明像素，回退到全图的非透明区域
        full_mask = (alpha > 1).astype(np.uint8)
        full_pts = cv2.findNonZero(full_mask)
        if full_pts is None:
            return None
        fx, fy, fw, fh = cv2.boundingRect(full_pts)

        # 3) 以全图非透明区域的“底边”构造一个窄条矩形，作为对齐参考
        bottom_y = fy + fh  # 底边y（下方）
        strip_h = max(10, fh // 20)  # 取较窄的一条带，避免过宽影响对齐精度
        rect_y = max(y0, bottom_y - strip_h)
        rect_h = min(strip_h, h - rect_y)
        return (fx, rect_y, fw, rect_h)
    else:
        return (0, y0, w, h - y0)

def remove_uniform_background(img_bgra, border: int = 10, color_thresh: int = 30,
                              s_thresh: int = 40, v_thresh: int = 240, feather_sigma: float = 2.0):
    """
    将头像图的背景区域转为透明，并对边缘进行羽化，避免矩形遮挡身体。

    参数说明：
    - border: 采样边框宽度，用于估计背景主色（像素）
    - color_thresh: 与背景主色的颜色距离阈值（BGR欧氏距离）
    - s_thresh, v_thresh: HSV下的近白背景阈值（S较小、V较大判定为白/近白背景）
    - feather_sigma: 羽化强度（越大边缘越柔和）

    返回：处理后的 BGRA 图像（背景透明，边缘羽化）
    """
    if img_bgra is None or img_bgra.ndim != 3 or img_bgra.shape[2] < 4:
        return img_bgra

    bgr = img_bgra[:, :, :3]
    alpha_orig = img_bgra[:, :, 3]
    h, w = bgr.shape[:2]

    # 1) HSV近白背景检测
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    white_bg_mask = (v >= v_thresh) & (s <= s_thresh)

    # 2) 采样四周边框估计背景主色（适用于非白色纯色背景）
    border = max(2, min(border, min(h, w) // 4))
    top = bgr[0:border, :, :]
    bottom = bgr[h - border:h, :, :]
    left = bgr[:, 0:border, :]
    right = bgr[:, w - border:w, :]
    sample = np.concatenate([top.reshape(-1, 3), bottom.reshape(-1, 3),
                             left.reshape(-1, 3), right.reshape(-1, 3)], axis=0)
    if sample.size > 0:
        bg_color = np.median(sample, axis=0).astype(np.float32)
        diff = np.linalg.norm(bgr.astype(np.float32) - bg_color[None, None, :], axis=2)
        color_bg_mask = diff <= color_thresh
    else:
        color_bg_mask = np.zeros((h, w), dtype=bool)

    # 3) 合并两类背景判定
    bg_mask = (white_bg_mask | color_bg_mask).astype(np.uint8) * 255

    # 4) 形态学清理，去掉小孔、平滑边缘
    kernel = np.ones((5, 5), np.uint8)
    bg_mask = cv2.morphologyEx(bg_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    bg_mask = cv2.morphologyEx(bg_mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # 5) 前景掩码与羽化（soft alpha）
    fg_mask = cv2.bitwise_not(bg_mask)  # 前景为255，背景为0
    soft_alpha = cv2.GaussianBlur(fg_mask, (0, 0), sigmaX=feather_sigma, sigmaY=feather_sigma)

    # 6) 与原alpha合并（保留原有透明信息）
    merged_alpha = np.maximum(alpha_orig, soft_alpha)
    img_bgra[:, :, 3] = merged_alpha
    return img_bgra


def save_debug_image(image, output_dir, filename):
    """
    保存调试图片
    
    Args:
        image: 要保存的图片
        output_dir: 输出目录
        filename: 文件名
    """
    if image is not None:
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        cv2.imwrite(filepath, image)
        print(f"已保存调试图片: {filepath}")


def create_white_background_image(merged_image_path, output_dir):
    """
    创建1024x1200白色背景图，将合图按底边对齐放置
    
    Args:
        merged_image_path: 合图文件路径
        output_dir: 输出目录
        
    Returns:
        str: 白色背景图的文件路径，失败返回None
    """
    try:
        # 读取合图
        merged_img = cv2.imread(merged_image_path, cv2.IMREAD_UNCHANGED)
        if merged_img is None:
            print(f"✗ 无法读取合图文件: {merged_image_path}")
            return None
        
        # 确保图片有alpha通道
        merged_img = ensure_alpha_channel(merged_img)
        merged_h, merged_w = merged_img.shape[:2]
        
        print(f"合图尺寸: {merged_w}x{merged_h}")
        
        # 创建1024x1200的白色背景图 (RGBA格式)
        white_bg = np.ones((1200, 1024, 4), dtype=np.uint8) * 255
        white_bg[:, :, 3] = 255  # 设置alpha通道为不透明
        
        # 计算合图在白色背景上的位置（水平居中，底边对齐）
        bg_h, bg_w = white_bg.shape[:2]
        
        # 水平居中
        start_x = max(0, (bg_w - merged_w) // 2)
        end_x = min(bg_w, start_x + merged_w)
        
        # 底边对齐（合图的底部与白色背景的底部对齐）
        start_y = max(0, bg_h - merged_h)
        end_y = bg_h
        
        # 计算实际可放置的区域
        actual_w = end_x - start_x
        actual_h = end_y - start_y
        
        print(f"合图在白色背景上的位置: x({start_x}-{end_x}), y({start_y}-{end_y})")
        print(f"实际放置尺寸: {actual_w}x{actual_h}")
        
        # 如果合图尺寸超出白色背景，需要缩放
        if merged_w > bg_w or merged_h > bg_h:
            # 计算缩放比例，保持宽高比
            scale_w = bg_w / merged_w if merged_w > bg_w else 1.0
            scale_h = bg_h / merged_h if merged_h > bg_h else 1.0
            scale = min(scale_w, scale_h)
            
            new_w = int(merged_w * scale)
            new_h = int(merged_h * scale)
            
            print(f"合图过大，缩放比例: {scale:.2f}, 新尺寸: {new_w}x{new_h}")
            
            # 缩放合图
            merged_img = cv2.resize(merged_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            merged_h, merged_w = merged_img.shape[:2]
            
            # 重新计算位置
            start_x = max(0, (bg_w - merged_w) // 2)
            end_x = min(bg_w, start_x + merged_w)
            start_y = max(0, bg_h - merged_h)
            end_y = bg_h
            actual_w = end_x - start_x
            actual_h = end_y - start_y
        
        # 将合图放置到白色背景上（使用alpha混合）
        if actual_w > 0 and actual_h > 0:
            # 获取要放置的区域
            merged_region = merged_img[:actual_h, :actual_w]
            bg_region = white_bg[start_y:end_y, start_x:end_x]
            
            # 使用alpha通道进行混合
            alpha = merged_region[:, :, 3:4].astype(np.float32) / 255.0
            
            # 计算混合结果
            blended_rgb = (
                merged_region[:, :, :3].astype(np.float32) * alpha + 
                bg_region[:, :, :3].astype(np.float32) * (1 - alpha)
            ).astype(np.uint8)
            
            # 更新白色背景
            white_bg[start_y:end_y, start_x:end_x, :3] = blended_rgb
            # alpha通道保持白色背景的不透明度
            white_bg[start_y:end_y, start_x:end_x, 3] = np.maximum(
                merged_region[:, :, 3], bg_region[:, :, 3]
            )
            
            print(f"✓ 成功将合图放置到1024x1200白色背景上")
        else:
            print("✗ 计算的放置区域无效")
            return None
        
        # 生成白色背景图的文件名
        base_name = os.path.splitext(os.path.basename(merged_image_path))[0]
        white_bg_filename = f"{base_name}_white_bg.png"
        white_bg_path = os.path.join(output_dir, white_bg_filename)
        
        # 保存白色背景图
        success = cv2.imwrite(white_bg_path, white_bg)
        if success:
            print(f"✓ 白色背景图保存成功: {white_bg_path}")
            print(f"✓ 尺寸: 1024x1200，白色背景，合图底边对齐")
            return white_bg_path
        else:
            print("✗ 保存白色背景图失败")
            return None
            
    except Exception as e:
        print(f"✗ 创建白色背景图时发生错误: {str(e)}")
        return None


def compose_images_new_logic(body_img_path, face_img_path, output_path, action_type=None):
    """
    新的图片合成逻辑：
    1. 识别body_img中红色区域角度a
    2. 将整张body_img按照角度a反向旋转，使红色区域保持水平
    3. 保持face_img原始状态，不需要进行旋转
    4. 在红色区域已经水平的基础上，识别红色区域的中心点
    5. 将face_img底边中心点移动到和红色区域中心点重合
    6. 组合图片为透明背景
    7. 再次按角度a旋转，去掉周围的空白区域，然后重新居中保存到2000x2000透明背景PNG
    
    Args:
        body_img_path: body图片路径
        face_img_path: face图片路径  
        output_path: 输出图片路径
        action_type: 动作类型，用于特殊处理（如"跑动"）
        
    Returns:
        bool: 成功返回True，失败返回False
    """
    print("=== 开始新的图片合成流程 ===")
    print(f"Body图片: {body_img_path}")
    print(f"Face图片: {face_img_path}")
    print(f"输出路径: {output_path}")
    if action_type:
        print(f"动作类型: {action_type}")
    
    print("\n--- 步骤1: 读取head并忽略透明部分 ---")
    face_img = cv2.imread(face_img_path, cv2.IMREAD_UNCHANGED)
    if face_img is None:
        print("错误：无法读取face图片文件")
        return False
    print(f"Face图片原始尺寸: {face_img.shape[:2]}")
    face_img = ensure_alpha_channel(face_img)
    
    print("\n--- 步骤2: 识别head下1/4矩形框 ---")
    face_h0, face_w0 = face_img.shape[:2]
    rect = bottom_quarter_bbox(face_img)
    if rect is None:
        y0 = (3 * face_h0) // 4
        rect = (0, y0, face_w0, face_h0 - y0)
        print("未在head下1/4找到非透明像素，使用整幅下1/4作为矩形框")
    rect_x, rect_y, rect_w, rect_h = rect
    rect_center_x = rect_x + rect_w // 2
    rect_bottom_y = rect_y + rect_h
    print(f"head下1/4矩形框: x={rect_x}, y={rect_y}, w={rect_w}, h={rect_h}")
    print(f"矩形框底边中心点: ({rect_center_x}, {rect_bottom_y})")
    
    # 步骤3: 识别body_img中红色区域相对于水平面的角度a
    print("\n--- 步骤3: 识别红色区域角度 ---")
    red_info = analyze_red_region(body_img_path)
    if red_info is None:
        print("错误：无法在body图片中找到红色区域")
        return False

    angle_a = red_info['angle']
    print(f"红色区域角度a: {angle_a:.1f}°")

    # 步骤4: 将整张body_img按照角度a反向旋转，使红色区域保持水平
    print("\n--- 步骤4: 反向旋转body图片使红色区域水平 ---")
    # 读取图片
    body_img = cv2.imread(body_img_path, cv2.IMREAD_UNCHANGED)
    if body_img is None:
        print("错误：无法读取body图片文件")
        return False

    # 确保图片有透明通道
    body_img = ensure_alpha_channel(body_img)
    print(f"Body图片尺寸: {body_img.shape[:2]}")

    if abs(angle_a) > 0.1:
        # 将body图片按角度a反向旋转（即按-angle_a旋转）
        body_img_rotated = rotate_image_around_center(body_img, angle_a)
        print(f"已将body图片反向旋转 {angle_a:.1f}°，红色区域现在应该水平")
    else:
        body_img_rotated = body_img.copy()
        print("角度太小，跳过旋转")

    # 步骤5: 保持face原始状态，不需要进行旋转
    print("\n--- 步骤5: 保持face原始状态 ---")
    face_img_rotated = face_img.copy()
    print("Face图片保持原始状态，不需要旋转")

    # 步骤6: 在红色区域已经水平的基础上，识别红色区域的中心点
    print("\n--- 步骤6: 识别水平红色区域的中心点 ---")
    # 在旋转后的图片中重新分析红色区域，获取新的中心点
    if abs(angle_a) > 0.1:
        rotated_red_info = analyze_red_region_array(body_img_rotated)
        
        if rotated_red_info is None:
            print("错误：无法在旋转后的body图片中找到红色区域")
            return False
        
        red_center_for_alignment = rotated_red_info['center']
        print(f"水平红色区域中心点: {red_center_for_alignment}")
        print(f"水平红色区域角度: {rotated_red_info['angle']:.1f}° (应该接近0°)")
    else:
        red_center_for_alignment = red_info['center']
        print(f"红色区域中心点: {red_center_for_alignment}")

    # 步骤7: 将矩形框底边中心点移动到和红色区域中心点重合
    print("\n--- 步骤7: 对齐head下1/4矩形框到底边中心 ---")
    face_h, face_w = face_img_rotated.shape[:2]
    
    # 红色区域中心点坐标
    red_center_x = red_center_for_alignment[0]
    red_center_y = red_center_for_alignment[1]
    
    print(f"红色区域中心位置: ({red_center_x}, {red_center_y})")
    print(f"矩形框底边中心将与红色区域中心重合")
    print(f"face图片尺寸: {face_img_rotated.shape[:2]}")



    # 非跑动：不额外偏移；跑动偏移统一在步骤6的画布坐标中处理
    if action_type == "跑动":
        print(f"检测到跑动动作，将在画布坐标中应用水平偏移125px")



    # 步骤8: 将face_img和body_img组合为一张透明背景的完整图片
    print("\n--- 步骤8: 组合图片 ---")
    
    face_left = red_center_x - rect_center_x
    face_top = red_center_y - rect_bottom_y
    face_right = face_left + face_w
    face_bottom = face_top + face_h
    
    # 计算body图片的位置范围
    body_h, body_w = body_img_rotated.shape[:2]
    body_left = 0
    body_right = body_w
    body_top = 0
    body_bottom = body_h
    
    # 计算画布需要的最小尺寸
    canvas_left = min(body_left, face_left) - 50  # 添加边距
    canvas_right = max(body_right, face_right) + 50
    canvas_top = min(body_top, face_top) - 50
    canvas_bottom = max(body_bottom, face_bottom) + 50
    
    canvas_w = canvas_right - canvas_left
    canvas_h = canvas_bottom - canvas_top
    
    print(f"计算画布尺寸: {canvas_w}x{canvas_h}")
    print(f"Face图片范围: ({face_left}, {face_top}) 到 ({face_right}, {face_bottom})")
    print(f"Body图片范围: ({body_left}, {body_top}) 到 ({body_right}, {body_bottom})")
    
    # 创建透明画布
    combined_img = np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)
    
    # 计算身体图在画布上的位置（不立即贴图，稍后置于最上层）
    body_start_x = -canvas_left
    body_start_y = -canvas_top
    
    # 将face图片放置在画布上（考虑偏移）
    face_abs_x = face_left - canvas_left
    face_abs_y = face_top - canvas_top
    
    # 计算矩形框底边中心点在画布中的位置
    face_bottom_center_x = face_abs_x + rect_center_x
    face_bottom_center_y = face_abs_y + rect_bottom_y
    
    # 计算红色区域中心点在画布中的位置
    red_center_in_canvas_x = red_center_for_alignment[0] - canvas_left
    red_center_in_canvas_y = red_center_for_alignment[1] - canvas_top
    
    # 如果是跑动动作，调整目标中心点（仅在画布坐标中右移125px）
    if action_type == "跑动":
        red_center_in_canvas_x += 25
    
    print(f"Body图片在画布中的位置: ({body_start_x}, {body_start_y})")
    print(f"Face图片在画布中的位置: ({face_abs_x}, {face_abs_y})")
    print(f"矩形框底边中心点在画布中的位置: ({face_bottom_center_x}, {face_bottom_center_y})")
    print(f"红色区域中心点在画布中的位置: ({red_center_in_canvas_x}, {red_center_in_canvas_y})")
    
    # 检查初始对齐情况
    initial_x_diff = abs(face_bottom_center_x - red_center_in_canvas_x)
    initial_y_diff = abs(face_bottom_center_y - red_center_in_canvas_y)
    print(f"初始对齐偏差: X={initial_x_diff}, Y={initial_y_diff}")
    
    # 精确调整face图片位置，确保底边中心点与红色区域中心点重合
    x_adjustment = red_center_in_canvas_x - face_bottom_center_x
    y_adjustment = red_center_in_canvas_y - face_bottom_center_y
    print(f"需要调整的偏移量: X={x_adjustment}, Y={y_adjustment}")
    
    face_abs_x += x_adjustment
    face_abs_y += y_adjustment
    
    # 重新计算矩形框底边中心点
    face_bottom_center_x = face_abs_x + rect_center_x
    face_bottom_center_y = face_abs_y + rect_bottom_y
    
    print(f"调整后face图片位置: ({face_abs_x}, {face_abs_y})")
    print(f"调整后face图片底边中心点在画布中的位置: ({face_bottom_center_x}, {face_bottom_center_y})")
    print(f"调整后红色区域中心点在画布中的位置: ({red_center_in_canvas_x}, {red_center_in_canvas_y})")
    
    # 检查是否重合
    x_diff = abs(face_bottom_center_x - red_center_in_canvas_x)
    y_diff = abs(face_bottom_center_y - red_center_in_canvas_y)
    
    if x_diff <= 1 and y_diff <= 1:
        print("✓ 矩形框底边中心点与红色区域中心点重合（误差在1像素内）")
    else:
        print(f"✗ 矩形框底边中心点与红色区域中心点不重合，偏差: ({x_diff}, {y_diff})")
    
    # 确保face图片位置在画布范围内
    if (face_abs_x >= 0 and face_abs_y >= 0 and 
        face_abs_x + face_w <= canvas_w and face_abs_y + face_h <= canvas_h):
        
        # 修改：先放置head图层到画布（在下层）
        combined_img[face_abs_y:face_abs_y+face_h, face_abs_x:face_abs_x+face_w] = face_img_rotated
        print("✓ 已将头像图层置于下层")

        # 修改：将body图层置于最上层（仅覆盖非透明像素）
        body_region = combined_img[body_start_y:body_start_y+body_h, body_start_x:body_start_x+body_w].astype(np.float32)
        src = body_img_rotated.astype(np.float32)
        sa = src[:, :, 3:4] / 255.0
        da = body_region[:, :, 3:4] / 255.0
        out_a = sa + da * (1.0 - sa)
        out_rgb = src[:, :, :3] * sa + body_region[:, :, :3] * da * (1.0 - sa)
        out_rgb = np.divide(out_rgb, out_a, out=np.zeros_like(out_rgb, dtype=np.float32), where=(out_a > 1e-6))
        out = np.concatenate([out_rgb, out_a * 255.0], axis=2)
        out = np.clip(out, 0, 255).astype(np.uint8)
        combined_img[body_start_y:body_start_y+body_h, body_start_x:body_start_x+body_w] = out
        print("✓ 已将身体图层置于最上层（仅覆盖非透明像素）")
        
        print(f"✓ 成功组合图片，画布尺寸: {canvas_w}x{canvas_h}")
    else:
        print("✗ 错误：face图片位置仍然超出画布范围")
        print(f"Face位置: ({face_abs_x}, {face_abs_y}), 尺寸: {face_w}x{face_h}")
        print(f"画布尺寸: {canvas_w}x{canvas_h}")
        return False

    # 步骤9: 将组合后的图片再次按角度a旋转，去掉周围的空白区域，然后重新居中保存到2000x2000透明背景PNG
    print("\n--- 步骤9: 最终旋转并保存到2000x2000画布 ---")
    if abs(angle_a) > 0.1:
        # 正向旋转恢复原始角度
        final_img = rotate_image_around_center(combined_img, -angle_a)
        print(f"已将组合图片正向旋转 {-angle_a:.1f}°，恢复原始倾斜角度")
    else:
        final_img = combined_img.copy()
        print("角度太小，跳过最终旋转")
    
    # 去除周围的空白区域
    cropped_img = crop_to_content(final_img)
    print(f"裁剪后图片尺寸: {cropped_img.shape[:2]}")

    # 创建2000x2000的透明画布
    final_canvas = np.zeros((2000, 2000, 4), dtype=np.uint8)
    
    # 将裁剪后的图片居中放置在2000x2000画布上
    cropped_h, cropped_w = cropped_img.shape[:2]
    start_x = max(0, (2000 - cropped_w) // 2)
    start_y = max(0, (2000 - cropped_h) // 2)
    end_x = min(2000, start_x + cropped_w)
    end_y = min(2000, start_y + cropped_h)
    
    # 计算实际可放置的区域
    actual_w = end_x - start_x
    actual_h = end_y - start_y
    
    final_canvas[start_y:end_y, start_x:end_x] = cropped_img[:actual_h, :actual_w]
    
    print(f"最终图片尺寸: {cropped_w}x{cropped_h}")
    print(f"放置在2000x2000画布的位置: ({start_x}, {start_y})")

    # 保存结果
    print("\n--- 步骤9: 保存结果 ---")
    output_dir = os.path.dirname(output_path)
    if output_dir:  # 只有当目录路径不为空时才创建
        os.makedirs(output_dir, exist_ok=True)

    success = cv2.imwrite(output_path, final_canvas)
    if success:
        print(f"✓ 最终合成图片已保存到: {output_path}")
        print("✓ 尺寸: 2000x2000，透明背景")
        
        # 步骤9: 创建1024x1200白色背景图，将合图按底边对齐放置
        print("\n--- 步骤9: 创建1024x1200白色背景图并底边对齐 ---")
        white_bg_path = create_white_background_image(output_path, output_dir)
        if white_bg_path:
            print(f"✓ 白色背景图已保存到: {white_bg_path}")
            return white_bg_path  # 返回白色背景图的路径，供后续流程使用
        else:
            print("✗ 创建白色背景图失败，返回原始合成图路径")
            return output_path
    else:
        print("✗ 保存图片失败")
        return False


# 保留原有函数作为备用
def compose_images(body_img_path, face_img_path, output_path):
    """
    调用新的图片合成逻辑
    """
    return compose_images_new_logic(body_img_path, face_img_path, output_path)


if __name__ == "__main__":
    data_root = os.path.join(os.path.dirname(__file__), "data")
    body_dir = os.path.join(data_root, "body")
    head_dir = os.path.join(data_root, "head")
    output_root = os.path.join(os.path.dirname(__file__), "output", "batch")
    os.makedirs(output_root, exist_ok=True)
    def list_images(p):
        if not os.path.isdir(p):
            return []
        files = []
        for f in os.listdir(p):
            fp = os.path.join(p, f)
            if os.path.isfile(fp):
                fl = f.lower()
                if fl.endswith(".png") or fl.endswith(".jpg") or fl.endswith(".jpeg"):
                    files.append(fp)
        files.sort()
        return files
    body_files = list_images(body_dir)
    head_files = list_images(head_dir)
    if not body_files or not head_files:
        all_files = list_images(data_root)
        body_files = [os.path.join(data_root, f) for f in os.listdir(data_root) if f.lower().startswith("body") and f.lower().endswith(".png")]
        head_files = [os.path.join(data_root, f) for f in os.listdir(data_root) if f.lower().startswith("head") and f.lower().endswith(".png")]
        if not body_files:
            bf = os.path.join(data_root, "body-1.png")
            if os.path.exists(bf):
                body_files = [bf]
        if not head_files:
            hf = os.path.join(data_root, "head-1.png")
            if os.path.exists(hf):
                head_files = [hf]
    print(f"Body数量: {len(body_files)}")
    print(f"Head数量: {len(head_files)}")
    total = 0
    for b in body_files:
        for h in head_files:
            bname = os.path.splitext(os.path.basename(b))[0]
            hname = os.path.splitext(os.path.basename(h))[0]
            out_path = os.path.join(output_root, f"{bname}__{hname}.png")
            print(f"\n=== 处理组合: {bname} + {hname} ===")
            ok = compose_images_new_logic(b, h, out_path)
            if ok:
                total += 1
    print(f"\n已生成结果数量: {total}")
