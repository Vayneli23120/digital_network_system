from app.models.device import Device
from app.models.template import ConfigTemplate
from sqlalchemy.orm import Session
import asyncio
from typing import Callable, Optional


class DeployService:
    """配置部署服务"""

    @staticmethod
    async def execute_deploy_with_stream(
        db: Session,
        device_id: int,
        deploy_data: dict,
        cli_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> dict:
        """
        执行设备部署并实时回显CLI输出

        Args:
            db: 数据库会话
            device_id: 设备ID
            deploy_data: 部署数据
            cli_callback: CLI输出回调函数(line, log_type)
            progress_callback: 进度回调函数(progress, message)

        Returns:
            dict: 执行结果
        """
        result = {
            "success": False,
            "message": "",
            "device_id": device_id
        }

        try:
            # 获取设备信息
            device = db.query(Device).filter(Device.id == device_id).first()
            if not device:
                result["message"] = f"设备 {device_id} 不存在"
                return result

            # 模拟CLI回显（实际实现应连接SSH/Telnet到设备）
            if cli_callback:
                await asyncio.sleep(0.5)
                cli_callback(f"Connecting to {device.ip}...", "info")

                await asyncio.sleep(0.5)
                cli_callback("SSH connection established", "success")

                await asyncio.sleep(0.3)
                cli_callback(f"Username: {device.username or 'admin'}", "command")

                await asyncio.sleep(0.3)
                cli_callback("Password: ********", "command")

                await asyncio.sleep(0.5)
                cli_callback("Authentication successful", "success")

            # 更新进度
            if progress_callback:
                progress_callback(10, "已连接到设备")

            # 进入配置模式
            if cli_callback:
                await asyncio.sleep(0.3)
                cli_callback("", "info")
                cli_callback("Device> enable", "command")
                cli_callback("Device# configure terminal", "command")
                cli_callback("Enter configuration commands, one per line. End with CNTL/Z.", "info")
                cli_callback("Device(config)#", "info")

            if progress_callback:
                progress_callback(20, "进入配置模式")

            # 应用配置
            if deploy_data.get("mode") == "template":
                # 模板模式：应用模板配置
                await DeployService._apply_template_config(
                    device, deploy_data, cli_callback, progress_callback
                )
            else:
                # 备份模式：恢复配置
                await DeployService._apply_backup_config(
                    device, deploy_data, cli_callback, progress_callback
                )

            # 保存配置
            if cli_callback:
                await asyncio.sleep(0.3)
                cli_callback("", "info")
                cli_callback("Device(config)# end", "command")
                cli_callback("Device# write memory", "command")
                cli_callback("Building configuration...", "info")
                cli_callback("[OK]", "success")
                cli_callback("", "info")
                cli_callback("Configuration saved successfully", "success")

            if progress_callback:
                progress_callback(100, "配置已保存")

            result["success"] = True
            result["message"] = "配置部署成功"

        except Exception as e:
            result["message"] = f"部署失败: {str(e)}"
            if cli_callback:
                cli_callback(f"[ERROR] {str(e)}", "error")

        return result

    @staticmethod
    async def _apply_template_config(
        device,
        deploy_data: dict,
        cli_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None
    ):
        """应用模板配置"""
        template_id = deploy_data.get("template_id")
        variables = deploy_data.get("variables", {})

        # 获取模板内容
        template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")

        # 替换变量
        config_lines = template.content.split('\n')
        for i, line in enumerate(config_lines):
            # 变量替换
            for key, value in variables.items():
                line = line.replace(f'{{{{{key}}}}}', str(value))

            # 发送CLI回显
            if cli_callback and line.strip():
                await asyncio.sleep(0.2)  # 模拟网络延迟
                cli_callback(f"Device(config)# {line}", "command")

                # 模拟设备响应
                await asyncio.sleep(0.1)

        # 更新进度
        if progress_callback:
            progress = 20 + int((60 / len(config_lines)) * len(config_lines))
            progress_callback(min(progress, 80), f"已应用 {len(config_lines)} 条配置")

    @staticmethod
    async def _apply_backup_config(
        device,
        deploy_data: dict,
        cli_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None
    ):
        """应用备份配置"""
        backup_file = deploy_data.get("backup_file")

        if cli_callback:
            cli_callback(f"Loading configuration from {backup_file}...", "info")

        # 模拟配置恢复
        await asyncio.sleep(1)

        if cli_callback:
            cli_callback("Configuration loaded", "success")

        if progress_callback:
            progress_callback(80, "备份配置已应用")


# 模型导入（避免循环导入）
from app.models.device import Device
from app.models.template import ConfigTemplate
