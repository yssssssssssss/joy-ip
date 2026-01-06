# 快速参考卡片

## 核心问题答案

### 修改前端后需要重新编译吗？
**是的！必须重新编译！**

---

## 一行命令速查

### 完整部署
```bash
./deploy.sh
```

### 手动部署
```bash
cd frontend && npm run export && cd .. && pkill -f 'python.*app_new.py' && python app_new.py
```

### 检查状态
```bash
./check_deployment.sh
```

---

## 修改类型速查表

| 修改内容 | 需要做什么 | 命令 |
|---------|-----------|------|
| 前端组件/样式/逻辑 | 构建+重启+清缓存 | `./deploy.sh` |
| 后端逻辑 | 仅重启 | `pkill -f python.*app_new && python app_new.py` |

---

## 标准工作流程

### 开发阶段
```bash
# 终端1: 后端
python app_new.py

# 终端2: 前端（热重载）
cd frontend && npm run dev:local
```

### 部署阶段
```bash
./deploy.sh
```

---

## 重要提醒

1. 前端修改必须重新构建
2. 构建后必须重启服务
3. 部署后用户必须清除缓存（Ctrl+Shift+R）

---

详细文档: `DEVELOPMENT_WORKFLOW.md`
