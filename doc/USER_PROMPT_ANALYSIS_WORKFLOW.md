# Joy IP 3D系统 - 用户Prompt分析详细流程

## 概述

本文档详细描述了Joy IP 3D图像生成系统中用户prompt的完整分析流程，从用户输入到最终的六维度分析结果的每一个步骤。

## 流程架构图

```
用户输入 → 合规检查 → 内容分析 → 六维度提取 → 服装补全 → 最终结果
    ↓         ↓         ↓         ↓         ↓         ↓
  原始文本   安全过滤   语义理解   结构化数据  智能补全   生成参数
```

---

## 第一阶段：输入接收与预处理

### 1.1 用户输入接收
**位置**: `app_new.py` → `/api/start_generate` 端点

```python
@app.route('/api/start_generate', methods=['POST'])
def start_generate():
    data = request.get_json()
    requirement = data.get('requirement', '').strip()
```

**处理步骤**:
1. 接收POST请求中的JSON数据
2. 提取`requirement`字段作为用户prompt
3. 去除首尾空白字符
4. 基础验证（非空检查）

**输入示例**:
```json
{
  "requirement": "生成一个穿着红色夹克，牛仔裤，戴帽子，拿着气球的开心joy"
}
```

### 1.2 任务初始化
```python
job_id = str(uuid.uuid4())
jobs[job_id] = {
    'status': 'processing',
    'progress': 0,
    'stage': 'analyze',
    'requirement': requirement,
    'created_at': time.time()
}
```

---

## 第二阶段：多层合规检查

### 2.1 合规检查入口
**位置**: `content_agent.py` → `process_content()` 方法

```python
def process_content(self, content: str) -> Dict:
    # 1. 合规检查
    is_compliant, reason = self.check_compliance(content)
    
    if not is_compliant:
        return {
            "success": False,
            "compliant": False,
            "reason": reason,
            "analysis": None
        }
```

### 2.2 三层合规检查体系

#### 第一层：违规词库检查
**方法**: `_check_external_banned_words()`

```python
def _check_external_banned_words(self, content: str) -> Tuple[bool, str]:
    # 检查普通违规词汇
    for word in self.banned_words:
        if word in content:
            return False, f"包含违规词汇: {word}"
    
    # 检查正则表达式
    for pattern in self.banned_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return False, f"包含违规内容: {match.group(0)}"
```

**检查内容**:
- 普通违规词汇：从`data/sensitive_words.txt`加载
- 正则表达式：支持复杂模式匹配
- 实时性：毫秒级响应，无网络依赖

**违规词库示例**:
```
# 女装相关
裙
婚纱
比基尼
内衣

# 暴力相关
血腥
暴力
武器

# 正则表达式
REGEX:女[装衣]
REGEX:[暴血].*[力腥]
```

#### 第二层：AI敏感内容检查
**方法**: `_check_sensitive_content_with_ai()`

**检查重点**:
1. **宗教相关**: 宗教符号、人物、建筑、仪式
2. **政治相关**: 政治人物、事件、制度、口号
3. **民族相关**: 特定民族及其传统服饰、冲突
4. **国家相关**: 国旗、国徽、政治象征

**AI提示词**:
```python
prompt = f"""
请检查以下内容是否明确涉及宗教、政治、民族、国家等敏感话题：
内容："{content}"

检查重点（仅标记明确的敏感内容）：
1. 宗教相关：明确的宗教符号、宗教人物、宗教建筑、宗教仪式
2. 政治相关：具体政治人物姓名、政治事件、政治制度
3. 民族相关：明确指定的特定民族及其传统服饰
4. 国家相关：国旗、国徽、具体国家政治象征

如果内容完全不涉及上述明确的敏感话题，请回复"合规"。
如果内容明确涉及上述敏感话题，请回复"不合规：[具体原因]"。
"""
```

#### 第三层：AI通用违规检查
**检查范围**:
1. **暴力内容**: 暴力行为、血腥场面、武器使用
2. **色情内容**: 性暗示、裸体、情色描述
3. **毒品相关**: 吸毒、贩毒、毒品制造
4. **赌博相关**: 赌博行为、博彩活动
5. **违法犯罪**: 盗窃、诈骗、其他犯罪行为
6. **自残自杀**: 自杀、自残、抑郁等负面内容
7. **歧视仇恨**: 基于性别、年龄等的歧视言论

### 2.3 合规检查结果处理
```python
# 合规通过
if is_compliant:
    analysis = self.analyze_content(content)
    return {
        "success": True,
        "compliant": True,
        "reason": "",
        "analysis": analysis
    }

# 合规失败
else:
    return {
        "success": False,
        "compliant": False,
        "reason": reason,  # 具体的不合规原因
        "analysis": None
    }
```

---

## 第三阶段：六维度内容分析

### 3.1 分析框架初始化
**位置**: `content_agent.py` → `analyze_content()` 方法

```python
def analyze_content(self, content: str) -> Dict[str, str]:
    result = {
        "表情": "",    # 面部表情特征
        "动作": "",    # 身体动作姿态
        "服装": "",    # 服装搭配信息
        "手拿": "",    # 手持物品信息
        "头戴": "",    # 头部配饰信息
        "背景": ""     # 背景环境信息
    }
```

### 3.2 直接字段提取
**方法**: `_extract_direct_fields()`

**提取策略**: 使用正则表达式识别用户明确指定的信息

```python
patterns = {
    "服装": [
        r"(?:服装|衣服|穿着|穿戴)(?:是|为|:|：)?\s*([^。;；\n]+?)(?:，(?:戴|拿)|的|，的|的joy|joy|$)",
        r"穿(?:上|着)?\s*([^。;；\n]+?)(?:，(?:戴|拿)|的|，的|的joy|joy|$)"
    ],
    "手拿": [
        r"(?:手拿|手持|拿着)(?:是|为|:|：)?\s*([^。;；\n]+?)(?:的|，的|的joy|joy|$)",
        r"拿(?:着)?\s*([^。;；\n]+?)(?:的|，的|的joy|joy|$)"
    ],
    "头戴": [
        r"(?:头戴|戴着|戴)(?:是|为|:|：)?\s*([^。;；\n]+?)(?:的|，的|的joy|joy|$)",
        r"戴(?:上|着)?\s*([^。;；\n]+?)(?:帽|的|，的|的joy|joy|$)"
    ]
}
```

**提取示例**:
```
输入: "穿着红色夹克，牛仔裤，戴帽子，拿着气球的joy"
提取结果: {
    "服装": "红色夹克，牛仔裤",
    "手拿": "气球", 
    "头戴": "帽子"
}
```

### 3.3 表情分析
**位置**: `matchers/head_matcher.py` → `analyze_user_requirement()`

**分析维度**:
1. **眼睛形状**: 大眼、小眼、圆眼、细长眼等
2. **嘴型**: 微笑、张嘴、抿嘴、撅嘴等
3. **表情**: 开心、悲伤、惊讶、愤怒等
4. **脸部动态**: 静态、动态、扭头、侧脸等
5. **情感强度**: 强烈、中等、轻微、无表情等

**AI分析提示词**:
```python
prompt = f"""将"{requirement}"按照"眼睛形状、嘴型、表情、脸部动态、情感强度"五个维度进行分析，精简得到的结果，并将结果按照以下形式输出：
眼睛形状：
嘴型：
表情：
脸部动态：
情感强度：
"""
```

**分析示例**:
```
输入: "开心的joy"
分析结果: {
    "眼睛形状": "弯曲",
    "嘴型": "上扬",
    "表情": "开心",
    "脸部动态": "静态",
    "情感强度": "中等"
}
```

### 3.4 动作分析
**位置**: `matchers/body_matcher.py` → `classify_action_type()`

**动作分类系统**:
```python
def classify_action_type(self, requirement: str) -> str:
    # 关键词映射
    action_keywords = {
        "跑动": ["跑", "奔跑", "跑步", "冲刺", "奔跑着"],
        "跳跃": ["跳", "跳跃", "蹦跳", "跳起", "腾空"],
        "坐姿": ["坐", "坐着", "坐下", "端坐", "盘坐"],
        "欢快": ["开心", "快乐", "兴奋", "愉快", "欢乐"],
        "站姿": ["站", "站着", "站立", "直立"]
    }
```

**分析维度**:
1. **手部姿势**: 挥手、握拳、张开、放松等
2. **腿部姿势**: 站立、跑动、跳跃、坐着等
3. **整体姿势**: 直立、前倾、后仰、蹲下等
4. **姿势意义**: 运动、休息、兴奋、专注等
5. **情感偏向**: 积极、消极、中性、活跃等

### 3.5 AI补全机制
**触发条件**: 当直接提取无法获得完整信息时

**补全流程**:
```python
missing = [label for label in ["服装", "手拿", "头戴"] if not result[label]]
if missing:
    # 第一次补全：保守模式
    analysis_text = self._request_ai_fields(content, missing, enforce_guess=False)
    
    # 第二次补全：推断模式
    if still_missing:
        fallback_text = self._request_ai_fields(content, still_missing, enforce_guess=True)
```

**AI补全提示词**:
```python
# 保守模式
requirement = f"重点补充以下维度：{focus}。若描述未涉及，可填写"无"。"

# 推断模式  
requirement = f"必须结合上下文或常识推断 {focus}，尽量给出合理猜测，实在无法判断时才填写"未知"。"

prompt = f"""用户的整体描述如下：
{content}

{requirement}
请严格按照下列格式输出（即使某项为空也要保留该行）：
服装：xxx
手拿：xxx
头戴：xxx
"""
```

### 3.6 结果规范化
**方法**: `_normalize_value()` 和 `_extract_fields()`

**规范化规则**:
1. **空值处理**: 统一处理"无"、"没有"、"未提供"等否定词
2. **交叉验证**: 防止不同维度信息混淆
3. **格式统一**: 确保输出格式一致性
4. **特殊处理**: 头戴信息自动添加"的帽子"后缀

```python
def _normalize_value(label: str, value: str) -> str:
    # 空值和否定词处理
    none_words = {
        "无", "没有", "未提供", "不带", "不戴", "不拿", "未知",
        "无帽子", "没有帽子", "无头戴", "没有头戴",
        "无服装", "没有服装", "无背景", "没有背景"
    }
    if v in none_words:
        return "无" if label == "背景" else ""
    
    # 交叉标签检查
    other_labels = ["服装", "手拿", "头戴", "背景"]
    other_labels.remove(label)
    for ol in other_labels:
        if re.match(rf"^{ol}[：:]", v):
            return ""
    
    # 头戴特殊处理
    if label == "头戴":
        if "帽子" not in v and "帽" in v:
            return v.replace("帽", "的帽子")
```

---

## 第四阶段：智能服装补全

### 4.1 服装类型分析
**方法**: `_analyze_clothing_type()`

**分类逻辑**:
```python
# 上装关键词
top_keywords = [
    "夹克", "外套", "上衣", "衬衫", "t恤", "毛衣", "卫衣", "背心",
    "马甲", "西装", "风衣", "大衣", "棉衣", "羽绒服", "开衫", "针织衫"
]

# 下装关键词  
bottom_keywords = [
    "裤子", "牛仔裤", "长裤", "短裤", "运动裤", "休闲裤", "西裤", "工装裤",
    "裙子", "连衣裙", "短裙", "长裙", "半身裙", "百褶裙", "a字裙"
]

# 判断补全需求
needs_completion = (has_top and not has_bottom) or (has_bottom and not has_top)
```

### 4.2 AI智能补全
**触发条件**: 只有上装或只有下装时

**补全策略**:
```python
def _request_clothing_completion(self, clothing_info: str, completion_type: str) -> str:
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
```

**补全示例**:
```
输入: "红色夹克"
分析: 只有上装，需要补全下装
AI推荐: "蓝色牛仔裤"
最终结果: "红色夹克，蓝色牛仔裤"
```

---

## 第五阶段：结果整合与输出

### 5.1 最终结果结构
```python
final_result = {
    "success": True,
    "compliant": True,
    "reason": "",
    "analysis": {
        "表情": "开心",
        "动作": "站姿", 
        "服装": "红色夹克，蓝色牛仔裤",
        "手拿": "气球",
        "头戴": "帽子",
        "背景": "",
        "_raw_ai": "AI原始输出记录"  # 调试信息
    }
}
```

### 5.2 日志记录
```python
logger.info("开始分析内容: %s", content)
logger.info("发现用户直接定义: %s", direct_fields)
logger.info("字段缺失，准备调用AI补全: %s", missing)
logger.info("服装补全: '%s' -> '%s'", original, completed)
logger.info("最终分析结果: %s", result)
```

---

## 完整流程示例

### 输入示例
```json
{
  "requirement": "生成一个穿着红色夹克，戴帽子，拿着气球的开心joy"
}
```

### 处理流程
```
1. 输入接收: "生成一个穿着红色夹克，戴帽子，拿着气球的开心joy"
   ↓
2. 合规检查:
   - 违规词检查: ✅ 通过
   - 敏感内容检查: ✅ 通过  
   - 通用违规检查: ✅ 通过
   ↓
3. 直接字段提取:
   - 服装: "红色夹克"
   - 手拿: "气球"
   - 头戴: "帽子"
   ↓
4. 表情分析:
   - 关键词"开心" → 表情: "开心"
   ↓
5. 动作分析:
   - 默认动作 → 动作: "站姿"
   ↓
6. 服装补全:
   - 检测: 只有上装"红色夹克"
   - AI补全: 推荐"蓝色牛仔裤"
   - 结果: "红色夹克，蓝色牛仔裤"
   ↓
7. 最终输出:
   {
     "表情": "开心",
     "动作": "站姿",
     "服装": "红色夹克，蓝色牛仔裤", 
     "手拿": "气球",
     "头戴": "帽子",
     "背景": ""
   }
```

---

## 性能优化策略

### 1. 缓存机制
```python
class AnalysisCache:
    def __init__(self):
        self.cache = {}
    
    def get_cache_key(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_cached_result(self, content: str):
        key = self.get_cache_key(content)
        return self.cache.get(key)
```

### 2. 异步处理
```python
async def analyze_content_async(self, content: str) -> Dict[str, str]:
    # 并行处理不同维度
    tasks = [
        self._analyze_expression_async(content),
        self._analyze_action_async(content),
        self._analyze_clothing_async(content)
    ]
    results = await asyncio.gather(*tasks)
```

### 3. 超时控制
```python
# API调用超时设置
API_TIMEOUT = 60  # 秒
GENERATION_TIMEOUT = 120  # 秒
```

---

## 错误处理机制

### 1. 分层错误处理
```python
try:
    # 主要处理逻辑
    result = self.analyze_content(content)
except requests.exceptions.RequestException as e:
    # 网络错误处理
    logger.error(f"网络请求失败: {e}")
    return self._get_fallback_result()
except Exception as e:
    # 通用错误处理
    logger.error(f"分析失败: {e}")
    return self._get_default_result()
```

### 2. 降级策略
```python
def _get_fallback_result(self) -> Dict[str, str]:
    """当AI分析失败时的降级结果"""
    return {
        "表情": "未识别",
        "动作": "站姿",  # 默认动作
        "服装": "休闲装", # 默认服装
        "手拿": "",
        "头戴": "",
        "背景": ""
    }
```

---

## 质量保证

### 1. 单元测试
```python
def test_analyze_content():
    agent = ContentAgent()
    result = agent.analyze_content("穿红色夹克的开心joy")
    assert result['服装'] == "红色夹克，蓝色牛仔裤"
    assert result['表情'] == "开心"
```

### 2. 集成测试
```python
def test_full_workflow():
    # 测试完整的分析流程
    response = requests.post("/api/start_generate", 
                           json={"requirement": "test prompt"})
    assert response.status_code == 200
```

### 3. 性能测试
```python
def test_analysis_performance():
    start_time = time.time()
    result = agent.analyze_content("test prompt")
    duration = time.time() - start_time
    assert duration < 5.0  # 5秒内完成
```

---

## 监控与日志

### 1. 结构化日志
```python
logger.info("Prompt analysis started", 
           extra={
               "job_id": job_id,
               "prompt_length": len(content),
               "analysis_stage": "compliance_check"
           })
```

### 2. 性能指标
```python
# Prometheus指标
ANALYSIS_DURATION = Histogram('prompt_analysis_duration_seconds')
COMPLIANCE_CHECK_COUNT = Counter('compliance_checks_total', ['result'])
AI_API_CALLS = Counter('ai_api_calls_total', ['type', 'status'])
```

---

## 总结

Joy IP 3D系统的用户prompt分析流程是一个多层次、智能化的处理系统，包含：

1. **安全第一**: 三层合规检查确保内容安全
2. **智能分析**: 六维度结构化分析用户需求
3. **自动补全**: 智能服装搭配补全功能
4. **容错机制**: 完善的错误处理和降级策略
5. **性能优化**: 缓存、异步处理等优化措施

该系统能够将自然语言的用户需求转换为结构化的图像生成参数，为后续的图像生成流程提供准确、完整的输入数据。

---

**文档版本**: v1.0  
**最后更新**: 2024年12月19日  
**维护人员**: Kiro AI Assistant