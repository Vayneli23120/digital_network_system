"""
设备命令安全守卫

在所有设备操作执行前调用 validate_commands 检查高危命令。
"""

from typing import List, Tuple
from loguru import logger


# 禁止执行的命令（精确匹配）
DANGEROUS_COMMANDS_EXACT = frozenset({
    "reload",
    "write erase",
    "erase startup-config",
    "erase running-config",
    "format",
    "factory-reset",
    "execute factoryreset",      # Fortinet
    "reset saved-configuration", # Huawei/H3C
    "reset factory-configuration", # Huawei
    "execute cfg reset",         # Fortinet
    "crypto key zeroize",
    "delete flash:",
    "delete nvram:",
})

# 高危命令前缀（匹配开头）
DANGEROUS_COMMAND_PREFIXES = (
    "delete ",
    "format ",
    "erase ",
    "no crypto key",
    "no ip ssh",
    "no ssh",
    "no aaa new-model",
    "no service password-encryption",
)

# 需要二次确认的命令（不直接阻止，但需审计记录）
HIGH_RISK_COMMANDS = frozenset({
    # 接口关闭 - 需特殊处理，不直接阻止
    # "shutdown",  # 在接口配置中常见
    "no service password-encryption",
})

# 每个厂商的特定高危命令
VENDOR_DANGEROUS_COMMANDS = {
    "cisco": {
        "exact": DANGEROUS_COMMANDS_EXACT,
        "prefix": DANGEROUS_COMMAND_PREFIXES,
    },
    "huawei": {
        "exact": DANGEROUS_COMMANDS_EXACT.union({
            "reset saved-configuration",
            "reset factory-configuration",
        }),
        "prefix": DANGEROUS_COMMAND_PREFIXES + ("undo ",),  # Huawei undo 命令
    },
    "h3c": {
        "exact": DANGEROUS_COMMANDS_EXACT.union({
            "reset saved-configuration",
        }),
        "prefix": DANGEROUS_COMMAND_PREFIXES + ("undo ",),
    },
    "fortinet": {
        "exact": DANGEROUS_COMMANDS_EXACT.union({
            "execute factoryreset",
            "execute cfg reset",
        }),
        "prefix": DANGEROUS_COMMAND_PREFIXES,
    },
    "aruba": {
        "exact": DANGEROUS_COMMANDS_EXACT,
        "prefix": DANGEROUS_COMMAND_PREFIXES,
    },
}


class CommandGuardError(Exception):
    """命令安全检查失败"""
    def __init__(self, command: str, reason: str, severity: str = "danger"):
        self.command = command
        self.reason = reason
        self.severity = severity
        super().__init__(f"命令 '{command}' 被安全守卫拒绝: {reason}")


def validate_commands(
    commands: List[str],
    vendor: str = "cisco",
    allow_high_risk: bool = False,
    context: str = ""
) -> Tuple[List[str], List[str]]:
    """
    验证命令列表的安全性

    Args:
        commands: 要执行的命令列表
        vendor: 设备厂商
        allow_high_risk: 是否允许高风险命令（需经审批流程）
        context: 操作上下文（用于日志记录）

    Returns:
        (safe_commands, warnings)

    Raises:
        CommandGuardError: 发现危险命令时抛出
    """
    safe_commands = []
    warnings = []

    # 处理 vendor 为 None 的情况
    if vendor is None:
        vendor = "cisco"
    vendor_lower = vendor.lower()
    vendor_rules = VENDOR_DANGEROUS_COMMANDS.get(vendor_lower, VENDOR_DANGEROUS_COMMANDS["cisco"])

    dangerous_exact = vendor_rules["exact"]
    dangerous_prefixes = vendor_rules["prefix"]

    for cmd in commands:
        cmd_stripped = cmd.strip()
        cmd_lower = cmd_stripped.lower()

        # 跳过空命令和注释
        if not cmd_stripped or cmd_stripped.startswith("!") or cmd_stripped.startswith("#"):
            safe_commands.append(cmd_stripped)
            continue

        # 检查精确匹配危险命令
        if cmd_lower in dangerous_exact:
            logger.warning(f"[COMMAND GUARD] Dangerous command blocked: '{cmd}' (vendor={vendor}, context={context})")
            raise CommandGuardError(cmd, "属于禁止执行命令列表")

        # 检查前缀匹配
        for prefix in dangerous_prefixes:
            if cmd_lower.startswith(prefix.lower()):
                logger.warning(f"[COMMAND GUARD] Dangerous prefix blocked: '{cmd}' (prefix={prefix}, vendor={vendor}, context={context})")
                raise CommandGuardError(cmd, f"命令前缀 '{prefix}' 属于危险操作")

        # 记录高风险命令
        if cmd_lower in HIGH_RISK_COMMANDS:
            warnings.append(f"高风险命令: '{cmd}'")
            if not allow_high_risk:
                logger.warning(f"[COMMAND GUARD] High-risk command blocked: '{cmd}' (vendor={vendor}, context={context})")
                raise CommandGuardError(cmd, "包含高风险命令，请在变更审批通过后执行", severity="high_risk")

        safe_commands.append(cmd_stripped)

    if warnings:
        logger.info(f"[COMMAND GUARD] Warnings for commands: {warnings} (vendor={vendor}, context={context})")

    return safe_commands, warnings


def is_interface_shutdown_command(cmd: str) -> bool:
    """
    检查是否为接口 shutdown 命令

    接口 shutdown 是常见操作，需要特殊处理：
    - 在接口配置模式下是正常的
    - 在全局配置模式下执行可能有风险

    Args:
        cmd: 命令字符串

    Returns:
        是否为 shutdown 相关命令
    """
    cmd_lower = cmd.strip().lower()
    return cmd_lower in ("shutdown", "no shutdown") or cmd_lower.startswith("shutdown ") or cmd_lower.startswith("no shutdown")


def validate_interface_commands(
    commands: List[str],
    allow_shutdown: bool = True,
    context: str = ""
) -> Tuple[List[str], List[str]]:
    """
    验证接口配置命令

    Args:
        commands: 命令列表（应在接口配置模式下）
        allow_shutdown: 是否允许 shutdown 命令
        context: 操作上下文

    Returns:
        (safe_commands, warnings)
    """
    safe_commands = []
    warnings = []

    for cmd in commands:
        cmd_stripped = cmd.strip()

        if is_interface_shutdown_command(cmd_stripped):
            if not allow_shutdown:
                logger.warning(f"[COMMAND GUARD] Interface shutdown blocked: '{cmd}' (context={context})")
                raise CommandGuardError(cmd_stripped, "接口 shutdown 命令被阻止", severity="warning")
            warnings.append(f"接口操作: '{cmd_stripped}'")

        safe_commands.append(cmd_stripped)

    return safe_commands, warnings


def get_command_risk_level(cmd: str, vendor: str = "cisco") -> str:
    """
    获取命令风险级别

    Args:
        cmd: 命令字符串
        vendor: 设备厂商

    Returns:
        risk level: "safe", "warning", "high_risk", "danger"
    """
    cmd_lower = cmd.strip().lower()
    vendor_lower = vendor.lower()
    vendor_rules = VENDOR_DANGEROUS_COMMANDS.get(vendor_lower, VENDOR_DANGEROUS_COMMANDS["cisco"])

    if cmd_lower in vendor_rules["exact"]:
        return "danger"

    for prefix in vendor_rules["prefix"]:
        if cmd_lower.startswith(prefix.lower()):
            return "danger"

    if cmd_lower in HIGH_RISK_COMMANDS:
        return "high_risk"

    if is_interface_shutdown_command(cmd):
        return "warning"

    return "safe"