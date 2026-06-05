"""AI 功能权限依赖

提供 AI 相关功能的权限检查依赖项。
"""

from app.shared.dependencies import require_permission


# AI 使用权限检查
require_ai_use = require_permission("ai:use")

# AI 配置权限检查
require_ai_config = require_permission("ai:config")

# AI 合规审核权限检查
require_ai_compliance = require_permission("ai:compliance")