# ⚠️ 此目录已废弃 (Archived)

**状态**: 自 2026-06-05 起，此目录不再维护，不可运行。

## 说明

此 `backend/` 目录是项目的旧版后端代码，已被 `app/` 目录下的新架构替代。

- **当前活跃后端**: `/app/` 目录
- **主入口**: `/app/main.py`
- **配置文件**: `/app/shared/config.py`

## 保留原因

此目录仅作为历史记录保留，方便查看旧代码逻辑或进行对比。请不要：
- 在此目录下进行任何修改
- 运行此目录下的代码
- 在 CI/CD 流程中依赖此目录

## 迁移说明

如需查看旧版代码的功能实现，可参考以下映射：

| 旧目录 | 新目录 |
|---|---|
| `backend/app/routers/` | `app/routers/` 或 `app/features/*/router.py` |
| `backend/app/models/` | `app/shared/models.py` |
| `backend/app/services/` | `app/services/` 或 `app/features/*/service.py` |
| `backend/app/config.py` | `app/shared/config.py` |

---

**文档生成日期**: 2026-06-05
**参考文档**: REFACTORING_PLAN.md - Phase 1 Task 1.1