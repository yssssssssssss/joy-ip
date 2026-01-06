import paddlehub as hub
import cv2
import numpy as np
from pathlib import Path

# --- 配置区域 ---
INPUT_IMAGE_PATH = r"C:\Users\heyunshen\Downloads\170.png"     # <--- 输入图片的路径
OUTPUT_IMAGE_PATH = r"C:\Users\heyunshen\Downloads\170-result.png" # <--- 输出图片的路径
ERODE_ITERATIONS = 1               # <--- 腐蚀迭代次数，1表示只收缩1个像素
PRIMARY_MODEL = "deeplabv3p_xception65_humanseg"  # 首选分割模型（人像）

# Alpha 专用处理配置
USE_ALPHA_IF_PRESENT = True        # 输入含 Alpha 时优先使用原图 Alpha
ALPHA_PRE_BLUR_SIZE = 0            # 腐蚀前是否平滑(0/1 关闭，>=3 为奇数启用)。避免影响中心信息
ALPHA_BINARY_THRESHOLD = None      # 若设定阈值(如 20)，先二值化再处理；None 保留原有半透明
ERODE_KERNEL_SIZE = 3              # 腐蚀结构元素尺寸，3 或 5
SHRINK_ONLY_EDGE = True            # 仅缩小边缘，不影响物体中心的 Alpha
EDGE_MASK_THRESHOLD = 1            # 用于确定“前景”的阈值，1 表示所有非零都算前景
EDGE_FADE_RATIO = 0.0              # 边缘区域透明度衰减比例；0 表示完全移除边缘环，0.5 表示淡化一半
SAVE_GREEN_BG_PREVIEW = True       # 生成绿色背景合成预览图，便于肉眼检查缩圈
GREEN_BG_COLOR = (0, 255, 0)       # 绿色背景色(BGR)
OUTPUT_IMAGE_BG_PATH = r"C:\Users\heyunshen\Downloads\generated_1763045391-result-green.png"
PRIMARY_MODEL = "deeplabv3p_xception65_humanseg"  # 首选分割模型（人像）

# --- 核心功能函数 ---

def erode_mask(mask, iterations=1):
    """
    对掩码图像进行腐蚀操作，使其边缘收缩。

    :param mask: 输入的单通道掩码图像 (numpy array)
    :param iterations: 腐蚀操作的迭代次数，次数越多，收缩越明显
    :return: 腐蚀后的掩码图像
    """
    if iterations <= 0:
        return mask

    # 使用椭圆核以获得更平滑的边缘效果
    k = ERODE_KERNEL_SIZE if isinstance(ERODE_KERNEL_SIZE, int) and ERODE_KERNEL_SIZE > 1 else 3
    if k % 2 == 0:
        k += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))

    # 执行腐蚀操作
    eroded_mask = cv2.erode(mask, kernel, iterations=iterations)

    return eroded_mask


def _to_uint8_mask(arr: np.ndarray) -> np.ndarray:
    """将各种类型的掩码/分数图统一到 uint8 的 [0,255] 掩码。"""
    if arr is None:
        raise RuntimeError("输入掩码为空")
    # 如果是浮点分数图，归一化到 0~255
    if arr.dtype.kind == 'f':
        arr = np.clip(arr, 0.0, 1.0) * 255.0
    # 如果是布尔，转 0/255
    if arr.dtype == np.bool_:
        arr = arr.astype(np.uint8) * 255
    # 如果是大于1的整数，假定已经是 0~255
    if arr.dtype.kind in ['i', 'u']:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    else:
        arr = arr.astype(np.uint8)
    return arr


def extract_mask_from_result(result: dict, fallback_path: str) -> np.ndarray:
    """从 PaddleHub segmentation 结果中尽可能提取掩码。

    优先顺序：
    1) save_path 的 RGBA Alpha 通道
    2) label_map（分类标签图）
    3) score_map（概率图，阈值化）
    4) data 的 Alpha 或二值/三通道图经阈值化
    5) 若 save_path 仅三通道，则灰度>0 阈值化作为掩码
    """
    # 1) 读取保存的输出（可能是 RGBA）
    if isinstance(result, dict) and 'save_path' in result:
        sp = result['save_path']
        rgba = cv2.imread(sp, cv2.IMREAD_UNCHANGED)
        if rgba is not None and rgba.ndim == 3 and rgba.shape[-1] >= 4:
            return rgba[:, :, 3]
        # 若不是 RGBA，则尝试从三通道图阈值化得到掩码
        bgr = cv2.imread(sp, cv2.IMREAD_COLOR)
        if bgr is not None:
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            # 灰度>0 视为前景
            _, mask = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
            return mask

    # 2) label_map 作为掩码
    if isinstance(result, dict) and 'label_map' in result and result['label_map'] is not None:
        lab = result['label_map']
        lab = np.asarray(lab)
        if lab.ndim == 3:
            lab = cv2.cvtColor(lab, cv2.COLOR_BGR2GRAY)
        # 若标签是 0/1，转 0/255
        if lab.max() <= 1:
            lab = (lab > 0).astype(np.uint8) * 255
        return _to_uint8_mask(lab)

    # 3) score_map 作为概率图阈值化
    if isinstance(result, dict) and 'score_map' in result and result['score_map'] is not None:
        sm = np.asarray(result['score_map'])
        if sm.ndim == 3:
            sm = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY)
        # 默认阈值 0.5
        mask = (sm > 0.5).astype(np.uint8) * 255
        return _to_uint8_mask(mask)

    # 4) data 字段
    if isinstance(result, dict) and 'data' in result and result['data'] is not None:
        data = np.asarray(result['data'])
        if data.ndim == 3 and data.shape[-1] >= 4:
            return data[:, :, 3]
        if data.ndim == 2:
            # 二值或灰度
            if data.max() <= 1:
                data = (data > 0).astype(np.uint8) * 255
            return _to_uint8_mask(data)
        if data.ndim == 3 and data.shape[-1] == 3:
            gray = cv2.cvtColor(data, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
            return mask

    # 5) 退回到原图路径进行简单阈值（不推荐，但保证不中断）
    bgr = cv2.imread(fallback_path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise RuntimeError("无法从结果与原图推导掩码：原图读取失败")
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
    return mask


def try_segment_and_extract(module_name: str, image_path: str) -> np.ndarray:
    """运行指定 PaddleHub 模型进行分割，并提取掩码（统一为 uint8）。"""
    print(f"尝试分割模型: {module_name}")
    module = hub.Module(name=module_name)
    results = module.segmentation(data={"image": [image_path]})
    if not results:
        raise RuntimeError(f"模型 {module_name} 返回空结果")
    mask = extract_mask_from_result(results[0], image_path)
    mask = _to_uint8_mask(mask)
    return mask


def process_rgba_alpha(rgba: np.ndarray, iterations: int) -> tuple[np.ndarray, np.ndarray]:
    """对 RGBA 输入的 Alpha 进行平滑/阈值与腐蚀，并返回(最终Alpha, 合成的RGBA)。"""
    if rgba is None or rgba.ndim != 3 or rgba.shape[-1] != 4:
        raise ValueError("输入必须为 RGBA 图像")

    bgr = rgba[:, :, :3]
    alpha = rgba[:, :, 3]

    # 预平滑，减少锯齿
    alpha_work = alpha.copy()
    if isinstance(ALPHA_PRE_BLUR_SIZE, int) and ALPHA_PRE_BLUR_SIZE > 1:
        k = ALPHA_PRE_BLUR_SIZE if ALPHA_PRE_BLUR_SIZE % 2 == 1 else ALPHA_PRE_BLUR_SIZE + 1
        alpha_work = cv2.GaussianBlur(alpha_work, (k, k), 0)

    # 可选阈值化得到“硬边”后再缩圈
    if isinstance(ALPHA_BINARY_THRESHOLD, int):
        _, alpha_work = cv2.threshold(alpha_work, ALPHA_BINARY_THRESHOLD, 255, cv2.THRESH_BINARY)

    # 仅缩小边缘，不影响中心
    if SHRINK_ONLY_EDGE:
        # 生成二值前景掩码
        _, bin_mask = cv2.threshold(alpha_work, EDGE_MASK_THRESHOLD, 255, cv2.THRESH_BINARY)
        eroded_bin = erode_mask(bin_mask, iterations=iterations)
        # 边缘环 = 原始 - 腐蚀后
        ring = cv2.subtract(bin_mask, eroded_bin)
        final_alpha = alpha.copy()
        if EDGE_FADE_RATIO <= 0.0:
            final_alpha[ring > 0] = 0
        else:
            final_alpha[ring > 0] = (final_alpha[ring > 0].astype(np.float32) * (1.0 - EDGE_FADE_RATIO)).astype(np.uint8)
    else:
        # 常规腐蚀（会整体收缩，可能影响中心的半透明）
        final_alpha = erode_mask(alpha_work, iterations=iterations)

    # 合成 RGBA
    b, g, r = cv2.split(bgr)
    result_rgba = cv2.merge((b, g, r, final_alpha))

    return final_alpha, result_rgba

# --- 脚本主程序 ---
def remove_background_with_erosion():
    """使用PaddleHub抠图，并对边缘进行腐蚀处理"""
    try:
        print("正在加载抠图模型...")
        module = hub.Module(name=PRIMARY_MODEL)
        print("模型加载完毕！")

        test_img_path = [INPUT_IMAGE_PATH]
        
        print(f"正在处理图片: {INPUT_IMAGE_PATH}...")
        # 读取原图（优先检查是否为 RGBA）
        orig_rgba = cv2.imread(INPUT_IMAGE_PATH, cv2.IMREAD_UNCHANGED)
        if orig_rgba is None:
            raise FileNotFoundError(f"无法读取原图: {INPUT_IMAGE_PATH}")

        # 如果输入含 Alpha，走 Alpha 专用流程
        if USE_ALPHA_IF_PRESENT and orig_rgba.ndim == 3 and orig_rgba.shape[-1] == 4:
            print("检测到原图含 Alpha，直接对 Alpha 进行缩圈处理...")
            final_alpha, result_rgba = process_rgba_alpha(orig_rgba, ERODE_ITERATIONS)

            # 绿色背景预览（便于肉眼检查缩圈效果）
            if SAVE_GREEN_BG_PREVIEW:
                bgr = orig_rgba[:, :, :3].astype(np.float32)
                mask_f = final_alpha.astype(np.float32) / 255.0
                bg = np.full_like(bgr, GREEN_BG_COLOR, dtype=np.float32)
                comp = (bgr * mask_f[..., None] + bg * (1.0 - mask_f[..., None])).astype(np.uint8)
                Path(OUTPUT_IMAGE_BG_PATH).parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(OUTPUT_IMAGE_BG_PATH, comp)
                coverage = float((final_alpha > 10).sum()) / final_alpha.size
                print(f"Alpha 缩圈后覆盖率: {coverage*100:.2f}% (阈值10)；预览已保存: {OUTPUT_IMAGE_BG_PATH}")

            # 保存 RGBA 结果
            Path(OUTPUT_IMAGE_PATH).parent.mkdir(parents=True, exist_ok=True)
            ok = cv2.imwrite(OUTPUT_IMAGE_PATH, result_rgba)
            if not ok:
                raise RuntimeError(f"写入结果失败: {OUTPUT_IMAGE_PATH}")
            print(f"处理成功！最终 RGBA 已保存到: {OUTPUT_IMAGE_PATH}")
            return

        # 否则走分割/兜底流程
        img = orig_rgba[:, :, :3] if orig_rgba.ndim == 3 and orig_rgba.shape[-1] >= 3 else cv2.imread(INPUT_IMAGE_PATH, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"无法读取原图(BGR): {INPUT_IMAGE_PATH}")

        # 先用首选模型尝试分割
        alpha = try_segment_and_extract(PRIMARY_MODEL, INPUT_IMAGE_PATH)
        coverage = float((alpha > 10).sum()) / alpha.size
        print(f"首选模型掩码覆盖率: {coverage*100:.2f}% (阈值10)")

        # 如果覆盖率过低（模型不适配），启用本地兜底：原图Alpha或GrabCut
        if coverage < 0.5:  # 低于 50% 认为分割不理想（可按需调小，例如 5%）
            print("首选模型效果较差，尝试使用原图 Alpha 通道作为掩码...")
            orig_rgba = cv2.imread(INPUT_IMAGE_PATH, cv2.IMREAD_UNCHANGED)
            if orig_rgba is not None and orig_rgba.ndim == 3 and orig_rgba.shape[-1] == 4:
                alpha = orig_rgba[:, :, 3]
                coverage = float((alpha > 10).sum()) / alpha.size
                print(f"原图 Alpha 覆盖率: {coverage*100:.2f}% (阈值10)")
            else:
                print("原图不含 Alpha，尝试使用 GrabCut 进行通用抠图...")
                # 使用 GrabCut 做粗抠图（全图为可能前景），得到掩码
                mask_gc = np.zeros(img.shape[:2], np.uint8)
                rect = (1, 1, img.shape[1]-2, img.shape[0]-2)  # 全图
                bgdModel = np.zeros((1, 65), np.float64)
                fgdModel = np.zeros((1, 65), np.float64)
                try:
                    cv2.grabCut(img, mask_gc, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
                    alpha = np.where((mask_gc == cv2.GC_FGD) | (mask_gc == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
                except Exception as e:
                    print(f"GrabCut 失败: {e}")
                coverage = float((alpha > 10).sum()) / alpha.size
                print(f"GrabCut 掩码覆盖率: {coverage*100:.2f}% (阈值10)")

        # 调试输出掩码统计
        print(f"掩码形状: {alpha.shape}, dtype: {alpha.dtype}, min/max: {alpha.min()}/{alpha.max()}, mean: {alpha.mean():.2f}")

        # 腐蚀缩圈
        print(f"对掩码进行 {ERODE_ITERATIONS} 次腐蚀操作...")
        final_mask = erode_mask(alpha, iterations=ERODE_ITERATIONS)

        # 合成 RGBA
        b, g, r = cv2.split(img)
        result_img = cv2.merge((b, g, r, final_mask))

        # 输出
        Path(OUTPUT_IMAGE_PATH).parent.mkdir(parents=True, exist_ok=True)
        ok = cv2.imwrite(OUTPUT_IMAGE_PATH, result_img)
        if not ok:
            raise RuntimeError(f"写入结果失败: {OUTPUT_IMAGE_PATH}")
        print(f"处理成功！最终结果已保存到: {OUTPUT_IMAGE_PATH}")

    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    remove_background_with_erosion()