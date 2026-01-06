# 文档索引

## 快速导航

### 我想...

#### 🚀 快速部署
→ 运行 `./deploy.sh`  
→ 查看 `QUICK_REFERENCE.md`

#### 📖 了解完整流程
→ 阅读 `DEVELOPMENT_WORKFLOW.md`  
→ 阅读 `README_DEPLOYMENT.md`

#### 🔧 修改前端代码
→ 开发: `cd frontend && npm run dev:local`  
→ 部署: `./deploy.sh`  
→ 详见 `DEVELOPMENT_WORKFLOW.md` 第2章

#### 🐍 修改后端代码
→ 重启服务即可，无需构建前端  
→ 详见 `DEVELOPMENT_WORKFLOW.md` 第3章

#### ✅ 检查部署状态
→ 运行 `./check_deployment.sh`

#### 🧪 测试 API
→ 运行 `python test_start_generate.py`

#### 📝 查看日志
→ 运行 `./monitor.sh` 或 `tail -f logs/app.log`  
→ 详见 `LOG_MONITORING_GUIDE.md`

#### 🆘 解决问题
→ 查看 `DEVELOPMENT_WORKFLOW.md` 第6章  
→ 查看 `USER_ACTION_GUIDE.md` 高级排查部分

---

## 文档列表

### 核心文档
| 文档 | 用途 | 适合人群 |
|------|------|---------|
| `QUICK_REFERENCE.md` | 快速参考卡片 | 所有人 ⭐ |
| `README_DEPLOYMENT.md` | 部署总览 | 所有人 ⭐ |
| `DEVELOPMENT_WORKFLOW.md` | 完整工作流程 | 开发者 |

### 用户指南
| 文档 | 用途 |
|------|------|
| `USER_ACTION_GUIDE.md` | 用户清除缓存指南 |

### 技术报告
| 文档 | 用途 |
|------|------|
| `FRONTEND_REBUILD_REPORT.md` | 前端重建报告 |
| `DEPLOYMENT_STATUS.md` | 部署状态记录 |

### 工具脚本
| 脚本 | 用途 |
|------|------|
| `deploy.sh` | 一键部署 |
| `check_deployment.sh` | 状态检查 |
| `monitor.sh` | 实时监控 |
| `test_start_generate.py` | API 测试 |

---

## 常见问题快速跳转

### Q: 修改前端需要重新编译吗？
→ `README_DEPLOYMENT.md` 核心问题解答

### Q: 如何清除浏览器缓存？
→ `USER_ACTION_GUIDE.md`

### Q: 前端修改没生效怎么办？
→ `DEVELOPMENT_WORKFLOW.md` 故障排查

### Q: 如何查看日志？
→ `LOG_MONITORING_GUIDE.md` 完整指南  
→ 运行 `./monitor.sh` 快速查看

---

**建议**: 先阅读 `QUICK_REFERENCE.md`，再根据需要查看其他文档
