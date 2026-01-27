# CLIP 模型本地路径说明

## 项目根目录
当前项目位于：`/data/joy-ip`

## CLIP 模型路径

### 1. clip-ViT-B-32 模型
**完整路径：**
```
/data/joy-ip/models/clip-ViT-B-32/
```

**目录结构：**
```
models/
└── clip-ViT-B-32/
    ├── config.json
    ├── pytorch_model.bin
    ├── sentence_bert_config.json
    ├── special_tokens_map.json
    ├── tokenizer_config.json
    ├── tokenizer.json
    ├── vocab.txt
    └── modules.json
```

### 2. clip-vit-base-patch32 分词器（可选）
**完整路径：**
```
/data/joy-ip/models/clip-vit-base-patch32/
```

**目录结构：**
```
models/
└── clip-vit-base-patch32/
    ├── config.json
    ├── merges.txt
    ├── special_tokens_map.json
    ├── tokenizer_config.json
    ├── tokenizer.json
    └── vocab.json
```

## 创建目录

```bash
# 在项目根目录下创建 models 目录
cd /data/joy-ip
mkdir -p models/clip-ViT-B-32
mkdir -p models/clip-vit-base-patch32
```

## 下载模型

### 方法一：使用下载脚本（推荐）
```bash
cd /data/joy-ip
python download_clip_model.py
```

### 方法二：手动下载
```python
from sentence_transformers import SentenceTransformer
from transformers import CLIPTokenizerFast

# 下载 CLIP 模型到指定路径
model = SentenceTransformer('clip-ViT-B-32')
model.save('/data/joy-ip/models/clip-ViT-B-32')

# 下载分词器到指定路径
tokenizer = CLIPTokenizerFast.from_pretrained('openai/clip-vit-base-patch32')
tokenizer.save_pretrained('/data/joy-ip/models/clip-vit-base-patch32')
```

### 方法三：从其他服务器复制
如果其他服务器已有模型：
```bash
# 从其他服务器复制
scp -r user@other-server:/path/to/models/clip-ViT-B-32 /data/joy-ip/models/
scp -r user@other-server:/path/to/models/clip-vit-base-patch32 /data/joy-ip/models/
```

## 验证安装

### 检查文件是否存在
```bash
ls -lh /data/joy-ip/models/clip-ViT-B-32/
ls -lh /data/joy-ip/models/clip-vit-base-patch32/
```

### 检查文件大小
```bash
du -sh /data/joy-ip/models/clip-ViT-B-32/
# 应该显示约 600MB

du -sh /data/joy-ip/models/clip-vit-base-patch32/
# 应该显示约 500KB
```

### 测试加载
```bash
cd /data/joy-ip
python -c "from utils.clip_manager import get_clip_model; model = get_clip_model(); print('✅ CLIP 模型加载成功')"
```

## 代码中的路径配置

在 `utils/clip_manager.py` 中：

```python
# CLIP 模型路径（相对于项目根目录）
local_model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'clip-ViT-B-32')
# 实际路径：/data/joy-ip/models/clip-ViT-B-32

# 分词器路径（相对于项目根目录）
local_tokenizer_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'clip-vit-base-patch32')
# 实际路径：/data/joy-ip/models/clip-vit-base-patch32
```

## 权限设置

确保应用有读取权限：
```bash
chmod -R 755 /data/joy-ip/models/
```

## 磁盘空间

确保有足够的磁盘空间：
```bash
df -h /data/joy-ip
# 至少需要 1GB 可用空间
```

## 常见问题

### Q: 模型下载到哪里？
A: `/data/joy-ip/models/clip-ViT-B-32/`

### Q: 如何确认模型已正确安装？
A: 运行验证命令，检查文件大小约 600MB

### Q: 可以使用软链接吗？
A: 可以，例如：
```bash
ln -s /other/path/to/models/clip-ViT-B-32 /data/joy-ip/models/clip-ViT-B-32
```

### Q: 模型文件损坏怎么办？
A: 删除后重新下载：
```bash
rm -rf /data/joy-ip/models/clip-ViT-B-32
python download_clip_model.py
```

## 日志检查

查看模型加载日志：
```bash
tail -f /data/joy-ip/logs/app.log | grep CLIP
```

应该看到：
```
[INFO] 使用本地 CLIP 模型: /data/joy-ip/models/clip-ViT-B-32
[INFO] ✅ 全局 CLIP 模型加载完成
```
