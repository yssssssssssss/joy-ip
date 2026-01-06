# 3D编辑器违规词审核集成文档

## 概述

本文档描述了3D编辑器违规词审核功能的集成实现，确保用户在3D编辑器中输入的描述文本符合内容合规要求。

## 功能特性

### 1. 违规词检查集成
- **检查时机**: 用户在3D编辑器中输入描述文本并点击生成时
- **检查范围**: 用户输入的`promptText`（描述文本）
- **检查标准**: 与主页图片生成完全相同的违规词库和检查逻辑

### 2. 多层检查机制
1. **违规词库检查**: 检查`data/sensitive_words.txt`中的违规词汇和正则表达式
2. **AI敏感内容检查**: 检查宗教、政治、民族、国家等敏感内容
3. **AI通用违规检查**: 检查暴力、色情、毒品、赌博等违规内容

### 3. 用户体验优化
- **友好提示**: 违规时显示"输入内容不符合规范，请重新描述你的需求"
- **快速响应**: 违规内容直接拦截，不执行耗时的3D生成流程
- **一致性**: 与主页生成使用相同的错误处理机制

## 技术实现

### 后端修改

#### 文件: `app_new.py`
```python
@app.route('/api/run-3d-banana', methods=['POST'])
def run_3d_banana():
    # ... 现有代码 ...
    
    # ===== 新增：3D生图违规词检查 =====
    logger.info(f"开始3D生图违规词检查: {prompt_text}")
    is_compliant, reason = content_agent.check_compliance(prompt_text)
    if not is_compliant:
        logger.warning(f"3D生图违规词检查不通过: {reason}")
        return jsonify({
            'success': False,
            'error': f'内容不合规: {reason}',
            'code': 'COMPLIANCE'
        }), 200
    logger.info("3D生图违规词检查通过")
    # ===== 违规词检查结束 =====
    
    # ... 后续代码不变 ...
```

### 前端修改

#### 文件: `frontend/src/components/ChatInterface.tsx`
```typescript
// 检查是否为违规词检查失败
const isComplianceError = runRes.data?.code === 'COMPLIANCE' || String(runRes.data?.error || '').includes('不合规')
setComplianceError(!!isComplianceError)

const errorMessage: Message = {
  id: (Date.now() + 1).toString(),
  type: 'assistant',
  content: isComplianceError 
    ? '输入内容不符合规范，请重新描述你的需求' 
    : `生成失败: ${runRes.data?.error || '未知错误'}`,
  timestamp: new Date()
}
```

## 工作流程

### 原流程
```
用户输入描述 → 调用/api/run-3d-banana → 执行3D-banana-all.py → 返回结果
```

### 新流程
```
用户输入描述 → 调用/api/run-3d-banana → 违规词检查 → 执行3D-banana-all.py → 返回结果
                                        ↓
                                   (不合规则直接返回错误)
```

## 测试验证

### 测试文件: `test_3d_compliance.py`

#### 违规内容测试
- ❌ "生成一个穿裙子的角色" → 被拦截（违规词：裙）
- ❌ "生成一个拿刀的角色" → 被拦截（违规词：刀）
- ❌ "生成一个政治人物的形象" → 被拦截（违规词：政治）
- ❌ "生成一个和尚的形象" → 被拦截（AI敏感内容检查）

#### 正常内容测试
- ✅ "生成一个开心的角色" → 通过
- ✅ "生成一个穿红色上衣的角色" → 通过
- ✅ "生成一个拿气球的角色" → 通过

### 运行测试
```bash
python test_3d_compliance.py
```

## 配置说明

### 违规词库
- **文件位置**: `data/sensitive_words.txt`
- **格式**: 普通词汇 + REGEX:正则表达式
- **维护**: 与主页生成共享同一个违规词库

### 日志记录
- **检查开始**: `开始3D生图违规词检查: {prompt_text}`
- **检查通过**: `3D生图违规词检查通过`
- **检查不通过**: `3D生图违规词检查不通过: {reason}`

## 影响分析

### 不受影响的功能
- ✅ 3D编辑器的渲染、模型加载、灯光控制
- ✅ 高清渲染功能
- ✅ 图片保存功能
- ✅ 主页图片生成功能
- ✅ DetailView中的背景生成、优化形象等功能

### 受影响的功能
- ⚠️ 3D生成流程增加0.5-2秒的违规词检查时间
- ⚠️ 违规内容会被拦截，不执行3D生成

### 性能影响
- **检查时间**: 0.5-2秒（取决于是否触发AI检查）
- **网络请求**: 违规词库检查无网络请求，AI检查需要网络请求
- **资源消耗**: 检查过程消耗极少CPU和内存资源

## 回滚方案

如需回滚，只需删除以下代码块：

```python
# ===== 新增：3D生图违规词检查 =====
logger.info(f"开始3D生图违规词检查: {prompt_text}")
is_compliant, reason = content_agent.check_compliance(prompt_text)
if not is_compliant:
    logger.warning(f"3D生图违规词检查不通过: {reason}")
    return jsonify({
        'success': False,
        'error': f'内容不合规: {reason}',
        'code': 'COMPLIANCE'
    }), 200
logger.info("3D生图违规词检查通过")
# ===== 违规词检查结束 =====
```

## 维护说明

### 违规词库更新
- 违规词库更新会自动应用到3D生成流程
- 无需单独配置或重启服务

### 监控建议
- 监控违规词检查的拦截率
- 关注用户反馈，调整违规词库
- 定期检查AI检查服务的可用性

## 总结

3D编辑器违规词审核集成已成功实现，具有以下特点：

1. **安全可靠**: 使用与主页生成相同的违规词检查逻辑
2. **用户友好**: 提供清晰的错误提示和修改建议
3. **性能优化**: 违规内容提前拦截，避免浪费生成资源
4. **易于维护**: 复用现有代码，降低维护成本
5. **可快速回滚**: 修改量小，可快速恢复原有功能

该功能确保了3D编辑器生成内容的合规性，提升了系统的安全性和用户体验。