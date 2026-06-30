# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [2.1.0] - 2026-06-30

### Added
- 训练代码和数据迁移（`training/`，来自 Coins-main 项目）
- 11,033 张钱币训练图片恢复（`data/images/`，14 GB）
- `classification_full.json` 完整 8 大类分类体系
- `SETUP.md` 环境配置指南
- `docs/数据集文档.md`（37,245 条记录，精度 99.7%）
- `docs/分类体系文档.md`（8 大类 92 叶子类）
- `docs/知识库统计报告.md`（500 条知识库统计）
- `.env.example` 环境变量模板
- `pyproject.toml` 现代 Python 项目配置
- `LICENSE`（MIT）
- `Makefile` 统一命令入口
- `Dockerfile` + `docker-compose.yml`
- `.github/workflows/ci.yml` CI/CD
- `.pre-commit-config.yaml` pre-commit hooks
- `CHANGELOG.md`

### Fixed
- 修复注册提权漏洞（`auth.py`：userRole 强制为 user）
- 移除硬编码 SECRET_KEY fallback
- debug 模式改为环境变量控制
- 统一 JWT 认证装饰器（`report.py`）
- 补全前端 Bearer token 前缀
- 修复蓝图注册 bug（`register_blueprints()` 移到模块级）
- Q&A prompt 优化，去除多余问候语
- PDF 字体跨平台支持（Windows/Linux/macOS）

### Changed
- 清理前端脚手架文件（HelloWorld, TheWelcome 等）
- 删除 `app_old_backup.py`

---

## [2.0.0] - 2026-03-01

### Added
- 初始提交：知识图谱智能问答系统
- Flask 后端 + Vue 3 前端
- YOLOv8 钱币检测 + ONNX 92 类分类
- GraphRAG 本地/全局/联网搜索
- Neo4j 知识图谱可视化
- 用户认证（JWT + bcrypt）
- 钱币鉴定报告 PDF 导出
- 批量鉴定 + 价格历史追踪
