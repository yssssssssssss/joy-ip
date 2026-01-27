# 违规词检测系统说明文档

## 概述

违规词检测系统用于过滤用户输入中的敏感内容，确保生成的内容符合规范。系统采用**两层检测机制**：
1. **本地违规词库检查**（快速）
2. **AI敏感内容检查**（智能）

## 核心文件

### 1. 违规词库管理模块
**文件**: `utils/banned_words.py`

**功能**:
- 加载和缓存违规词库
- 检查内容是否包含违规词
- 动态添加/删除违规词
- 支持普通词汇和正则表达式

**主要函数**:
```python
# 检查内容是否包含违规词
check_banned_words(content: str) -> Tuple[bool, str]

# 重新加载违规词库
reload_banned_words()

# 添加违规词
add_banned_word(word: str) -> bool

# 移除违规词
remove_banned_word(word: str) -> bool
```

### 2. 内容检查代理
**文件**: `content_agent.py`

**功能**:
- 调用违规词库检查
- 调用AI进行敏感内容检查
- 分析内容（表情、动作、装扮等）

**检查流程**:
```python
def check_compliance(self, content: str) -> Tuple[bool, str]:
    # 第一层：违规词库检查（快速）
    is_compliant, reason = self._check_external_banned_words(content)
    if not is_compliant:
        return False, f"违规词检测：{reason}"
    
    # 第二层：AI敏感内容检查（智能）
    is_compliant, reason = self._check_sensitive_content_with_ai(content)
    if not is_compliant:
        return False, reason
    
    return True, ""
```

### 3. 2D内容检查代理
**文件**: `content_agent_2d.py`

**功能**:
- 复用 ContentAgent 的合规检查能力
- 新增"视角"维度的分析

### 4. 应用入口
**文件**: `app_new.py`

**调用位置**:
- `/api/analyze` - 分析阶段检查
- `/api/run-3d-banana` - 3D生成检查

## 违规词库文件

### 文件位置
```
data/sensitive_words.txt
```

### 文件格式
```
# 违规词库文件
# 每行一个词，以#开头的行为注释
# 支持正则表达式，格式：REGEX:正则表达式

# 普通词汇
政治人物
敏感事件
违禁物品

# 正则表达式
REGEX:.*国旗.*
REGEX:.*民族.*服饰.*
```

### 词库类型

#### 1. 普通词汇
直接匹配，区分大小写
```
政治
民族
国旗
```

#### 2. 正则表达式
以 `REGEX:` 开头，支持复杂匹配
```
REGEX:.*政治.*人物.*
REGEX:\d{3}-\d{4}-\d{4}  # 匹配电话号码
```

## 检测流程

### 完整流程图
```
用户输入
    ↓
第一层：本地违规词库检查
    ├─ 检查普通词汇（精确匹配）
    ├─ 检查正则表达式（模式匹配）
    ↓
    ├─ 不合规 → 返回错误
    └─ 合规 → 继续
    ↓
第二层：AI敏感内容检查
    ├─ 政治相关
    ├─ 民族相关
    ├─ 国家相关
    ├─ 女装相关
    ↓
    ├─ 不合规 → 返回错误
    └─ 合规 → 通过
```

### 检查代码示例

#### 基础检查
```python
from utils.banned_words import check_banned_words

content = "用户输入的内容"
is_compliant, reason = check_banned_words(content)

if not is_compliant:
    print(f"违规：{reason}")
else:
    print("合规")
```

#### 完整检查（含AI）
```python
from content_agent import ContentAgent

agent = ContentAgent()
is_compliant, reason = agent.check_compliance(content)

if not is_compliant:
    print(f"不合规：{reason}")
else:
    print("合规")
```

## 管理违规词库

### 1. 查看当前词库
```python
from utils.banned_words import get_banned_words

words, patterns = get_banned_words()
print(f"普通词汇: {len(words)} 个")
print(f"正则表达式: {len(patterns)} 个")
```

### 2. 添加违规词

#### 添加普通词汇
```python
from utils.banned_words import add_banned_word

# 添加单个词
add_banned_word("新违规词")

# 添加多个词
for word in ["词1", "词2", "词3"]:
    add_banned_word(word)
```

#### 添加正则表达式
```python
# 添加正则表达式
add_banned_word("REGEX:.*敏感.*内容.*")
```

### 3. 删除违规词
```python
from utils.banned_words import remove_banned_word

# 删除普通词汇
remove_banned_word("旧违规词")

# 删除正则表达式
remove_banned_word("REGEX:.*旧模式.*")
```

### 4. 重新加载词库
```python
from utils.banned_words import reload_banned_words

# 修改文件后重新加载
reload_banned_words()
```

### 5. 从URL更新词库
```python
from content_agent import ContentAgent

agent = ContentAgent()
url = "https://example.com/sensitive_words.txt"
success = agent.update_banned_words_from_url(url)

if success:
    print("词库更新成功")
else:
    print("词库更新失败")
```

## 性能优化

### 1. 全局缓存
违规词库在首次加载后会缓存在内存中，避免重复读取文件。

```python
# 第一次调用：从文件加载
check_banned_words("内容1")  # 加载文件

# 后续调用：使用缓存
check_banned_words("内容2")  # 使用缓存
check_banned_words("内容3")  # 使用缓存
```

### 2. 正则表达式预编译
正则表达式在加载时预编译，提高匹配速度。

```python
# 加载时预编译
pattern = re.compile(r".*敏感.*", re.IGNORECASE)

# 匹配时直接使用
pattern.search(content)  # 快速匹配
```

### 3. 线程安全
使用锁机制确保多线程环境下的安全性。

```python
_cache_lock = threading.Lock()

with _cache_lock:
    # 线程安全的操作
    _banned_words = load_words()
```

## AI敏感内容检查

### 检查重点
1. **政治相关**: 政治人物、政治事件、政治口号
2. **民族相关**: 特定民族及其传统服饰、民族冲突
3. **国家相关**: 国旗、国徽、政治象征
4. **女装相关**: 女装、裙子、婚纱等女性服装

### 检查逻辑
```python
def _check_sensitive_content_with_ai(self, content: str) -> Tuple[bool, str]:
    prompt = f"""请检查以下内容是否涉及敏感话题：
    内容："{content}"
    
    检查重点：
    1. 政治相关：政治人物、政治事件、政治口号
    2. 民族相关：特定民族及其传统服饰、民族冲突
    3. 国家相关：国旗、国徽、政治象征
    4. 女装相关：女装、裙子、婚纱等女性服装
    
    如果内容合规，回复"合规"。
    如果不合规，回复"不合规：[原因]"。"""
    
    # 调用AI API
    result = call_ai_api(prompt)
    
    if "合规" in result and "不合规" not in result:
        return True, ""
    if "不合规" in result:
        return False, extract_reason(result)
    
    return False, "AI返回不明确结果"
```

## 调试和测试

### 1. 测试违规词检查
```python
# 创建测试脚本 test_banned_words.py
from utils.banned_words import check_banned_words

test_cases = [
    ("正常内容", True),
    ("包含政治的内容", False),
    ("包含民族的内容", False),
]

for content, expected in test_cases:
    is_compliant, reason = check_banned_words(content)
    status = "✅" if is_compliant == expected else "❌"
    print(f"{status} {content}: {is_compliant} ({reason})")
```

### 2. 查看检测日志
```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.INFO)

# 执行检查
check_banned_words("测试内容")

# 查看日志输出
# [INFO] 违规词库加载完成: 100 个词汇, 10 个正则
# [INFO] 检查内容: 测试内容
```

### 3. 性能测试
```python
import time

# 测试检查速度
start = time.time()
for i in range(1000):
    check_banned_words(f"测试内容{i}")
end = time.time()

print(f"1000次检查耗时: {end - start:.2f}秒")
print(f"平均每次: {(end - start) / 1000 * 1000:.2f}毫秒")
```

## 常见问题

### Q1: 如何添加新的违规词？
**方法1**: 直接编辑文件
```bash
echo "新违规词" >> data/sensitive_words.txt
```

**方法2**: 使用API
```python
from utils.banned_words import add_banned_word
add_banned_word("新违规词")
```

### Q2: 违规词库不生效怎么办？
```python
# 重新加载词库
from utils.banned_words import reload_banned_words
reload_banned_words()
```

### Q3: 如何查看当前有哪些违规词？
```python
from utils.banned_words import get_banned_words

words, patterns = get_banned_words()
print("普通词汇:")
for word in words:
    print(f"  - {word}")

print("\n正则表达式:")
for pattern in patterns:
    print(f"  - {pattern.pattern}")
```

### Q4: 正则表达式不匹配怎么办？
检查正则表达式语法：
```python
import re

pattern_str = ".*测试.*"
try:
    pattern = re.compile(pattern_str, re.IGNORECASE)
    print("正则表达式有效")
except re.error as e:
    print(f"正则表达式错误: {e}")
```

### Q5: 如何临时禁用违规词检查？
修改代码跳过检查（仅用于测试）：
```python
# 在 content_agent.py 中
def check_compliance(self, content: str) -> Tuple[bool, str]:
    # 临时禁用
    return True, ""
    
    # 原有逻辑...
```

## 最佳实践

### 1. 定期更新词库
```python
# 每周从中央服务器更新
import schedule

def update_words():
    agent = ContentAgent()
    agent.update_banned_words_from_url("https://central-server/words.txt")

schedule.every().week.do(update_words)
```

### 2. 监控检测效果
```python
# 记录违规检测统计
violations = {
    "total_checks": 0,
    "violations": 0,
    "violation_words": {}
}

def check_and_log(content):
    violations["total_checks"] += 1
    is_compliant, reason = check_banned_words(content)
    
    if not is_compliant:
        violations["violations"] += 1
        word = extract_word_from_reason(reason)
        violations["violation_words"][word] = \
            violations["violation_words"].get(word, 0) + 1
    
    return is_compliant, reason
```

### 3. 分级管理
```python
# 不同级别的违规词
CRITICAL_WORDS = ["极度敏感"]  # 直接拒绝
WARNING_WORDS = ["需要注意"]   # 警告但允许
INFO_WORDS = ["建议修改"]      # 仅提示
```

## 相关文件清单

### 核心文件
- ✅ `utils/banned_words.py` - 违规词库管理
- ✅ `content_agent.py` - 内容检查代理
- ✅ `content_agent_2d.py` - 2D内容检查代理
- ✅ `app_new.py` - 应用入口

### 数据文件
- ✅ `data/sensitive_words.txt` - 违规词库文件

### 配置文件
- ✅ `config.py` - AI API配置

## 总结

违规词检测系统通过**两层检测机制**确保内容安全：
1. **本地词库检查**：快速、高效、可定制
2. **AI智能检查**：灵活、准确、覆盖面广

系统支持：
- ✅ 普通词汇和正则表达式
- ✅ 动态添加/删除违规词
- ✅ 全局缓存和性能优化
- ✅ 线程安全
- ✅ 详细的日志记录

建议定期更新词库，监控检测效果，确保系统持续有效运行。
