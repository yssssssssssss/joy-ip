# CLIP 模型本地化配置指南

## 问题描述

当系统无法连接到 HuggingFace 时，会出现以下错误：
```
MaxRetryError("HTTPSConnectionPool(host='huggingface.co', port=443): 
Max retries exceeded with url: /sentence-transformers/clip-ViT-B-32/resolve/main/README.md 
(Caused by NewConnectionError('<urllib3.connection.HTTPSConnection object at 0x...>: 
Failed to establish a new connection: [Errno 111] Connection refused'))
```

## 解决方案

将 CLIP 模型下载到本地，避免依赖网络连接。

## 方法一：自动下载（推荐）

### 1. 运行下载脚本

```bash
python download_clip_model.py
```

### 2. 等待下载完成

脚本会自动：
- 创建 `models/` 目录
- 下载 `clip-ViT-B-32` 模型
- 下载 `clip-vit-base-patch32` 分词器

### 3. 重启应用

下载完成后，重启应用即可自动使用本地模型。

## 方法二：手动下载

### 1. 创建模型目录

```bash
mkdir -p models
```

### 2. 使用 Python 下载模型

```python
from sentence_transformers import SentenceTransformer

# 下载 CLIP 模型
model = SentenceTransformer('clip-ViT-B-32')
model.save('models/clip-ViT-B-32')

# 下载分词器（可选）
from transformers import CLIPTokenizerFast
tokenizer = CLIPTokenizerFast.from_pretrained('openai/clip-vit-base-patch32')
tokenizer.save_pretrained('models/clip-vit-base-patch32')
```

### 3. 重启应用

## 方法三：使用代理下载

如果网络受限，可以配置代理：

```bash
# 设置代理环境变量
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port

# 运行下载脚本
python download_clip_model.py
```

## 验证安装

### 检查模型文件

```bash
ls -la models/clip-ViT-B-32/
ls -la models/clip-vit-base-patch32/
```

应该看到模型文件和配置文件。

### 测试加载

```python
from utils.clip_manager import get_clip_model

# 尝试加载模型
model = get_clip_model()
print("✅ CLIP 模型加载成功")
```

## 工作原理

系统会按以下顺序查找模型：

1. **本地模型**：`models/clip-ViT-B-32/`
2. **HuggingFace 缓存**：`~/.cache/huggingface/`
3. **在线下载**：从 HuggingFace 下载（需要网络）

如果本地模型存在，系统会优先使用，完全避免网络请求。

## 目录结构

```
项目根目录/
├── models/                          # 本地模型目录（不提交到 Git）
│   ├── clip-ViT-B-32/              # CLIP 模型
│   │   ├── config.json
│   │   ├── pytorch_model.bin
│   │   └── ...
│   └── clip-vit-base-patch32/      # CLIP 分词器（可选）
│       ├── tokenizer_config.json
│       ├── vocab.json
│       └── ...
├── utils/
│   └── clip_manager.py             # CLIP 模型管理器
└── download_clip_model.py          # 下载脚本
```

## 常见问题

### Q: 模型文件有多大？
A: 约 600MB，请确保有足够的磁盘空间。

### Q: 可以删除模型吗？
A: 可以。删除 `models/` 目录后，系统会尝试在线下载。

### Q: 多个项目可以共享模型吗？
A: 可以。将 `models/` 目录软链接到其他项目即可。

### Q: 下载失败怎么办？
A: 
1. 检查网络连接
2. 尝试使用代理
3. 手动从 HuggingFace 网站下载模型文件

## 相关文件

- `utils/clip_manager.py` - CLIP 模型管理器（支持本地加载）
- `download_clip_model.py` - 自动下载脚本
- `.gitignore` - 已配置忽略 `models/` 目录

## 技术支持

如有问题，请检查日志输出：
```bash
tail -f logs/app.log | grep CLIP
```
