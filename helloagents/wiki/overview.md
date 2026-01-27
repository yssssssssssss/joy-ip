# Joy IP 2D/3D 生成聊天

> 项目级核心信息。详细模块文档见 `modules/`。

## 1. 项目概述

### 目标与背景
提供一个聊天式交互入口，用户描述想要生成的 Joy IP（2D/3D），系统在后端异步执行分析与生成，并在前端展示排队状态与生成结果。

### 范围
- **范围内:** 聊天输入、预分析预览、异步任务队列、任务状态轮询、图片展示与下载
- **范围外:** 多租户权限体系、持久化任务存储（当前以进程内内存为主）

### 干系人
- **负责人:**（待补充）

## 2. 模块索引

| 模块名称 | 职责 | 状态 | 文档 |
|---------|------|------|------|
| frontend | Next.js 前端 UI 与交互 | 开发中 | [modules/frontend.md](modules/frontend.md) |
| backend | Flask API、任务队列与生成链路 | 开发中 | [modules/backend.md](modules/backend.md) |

## 3. 快速链接
- [技术约定](../project.md)
- [架构设计](arch.md)
- [API 手册](api.md)
- [数据模型](data.md)
- [变更历史](../history/index.md)

