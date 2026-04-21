"""
Console 串口服务 - 用于通过 Console 口配置设备
"""

from typing import Optional, List, Callable
import time
import re

import serial
from serial.tools import list_ports
from loguru import logger

from app.shared.config import get_config


class ConsoleService:
    """Console 串口服务"""

    def __init__(self):
        self.config = get_config()
        self.serial_conn: Optional[serial.Serial] = None
        self.port: Optional[str] = None

    def list_ports(self) -> List[dict]:
        """列出可用的串口"""
        ports = []
        for port in list_ports.comports():
            ports.append({
                "device": port.device,
                "description": port.description,
                "hwid": port.hwid,
            })
        return ports

    def connect(self, port: str, baudrate: int = 9600,
                timeout: float = 1.0) -> bool:
        """
        连接到 Console 口

        Args:
            port: COM 端口号，如 "COM3" 或 "/dev/ttyUSB0"
            baudrate: 波特率，默认 9600
            timeout: 超时时间 (秒)

        Returns:
            bool: 连接是否成功
        """
        try:
            self.serial_conn = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=self.config.console.bytesize,
                parity=self.config.console.parity,
                stopbits=self.config.console.stopbits,
                timeout=timeout,
            )
            self.port = port
            logger.info(f"已连接到 Console 口：{port}")
            return True
        except serial.SerialException as e:
            logger.error(f"连接 Console 口 {port} 失败：{e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("已断开 Console 连接")
        self.port = None

    def send_command(self, command: str, delay: float = 0.5) -> str:
        """
        发送单条命令并读取响应

        Args:
            command: 命令内容
            delay: 发送后等待时间 (秒)

        Returns:
            str: 命令输出
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            raise RuntimeError("未连接到 Console 口")

        # 清空缓冲区
        self.serial_conn.reset_input_buffer()

        # 发送命令（带回车）
        cmd = command + "\r\n"
        self.serial_conn.write(cmd.encode())
        time.sleep(delay)

        # 读取响应
        response = ""
        while self.serial_conn.in_waiting:
            response += self.serial_conn.read(self.serial_conn.in_waiting).decode(errors='ignore')
            time.sleep(0.1)

        return response

    def send_commands(self, commands: List[str],
                      progress_callback: Optional[Callable[[str, int, int], None]] = None):
        """
        批量发送配置命令

        Args:
            commands: 命令列表
            progress_callback: 进度回调函数 callback(current_cmd, index, total)
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            raise RuntimeError("未连接到 Console 口")

        total = len(commands)

        for i, cmd in enumerate(commands):
            logger.debug(f"发送命令 [{i+1}/{total}]: {cmd}")

            output = self.send_command(cmd, delay=self.config.console.command_delay)

            if progress_callback:
                progress_callback(cmd, i + 1, total)

            # 检查是否有错误
            if "Invalid input" in output or "% Incomplete" in output:
                logger.warning(f"命令执行可能有误：{cmd}")

    def enter_config_mode(self) -> bool:
        """
        进入配置模式

        Returns:
            bool: 是否成功进入
        """
        logger.debug("进入配置模式")

        # 按几次回车唤醒 CLI
        self.serial_conn.write(b"\r\n\r\n")
        time.sleep(0.5)

        # 进入 enable 模式
        self.send_command("enable", delay=1.0)

        # 进入配置模式
        self.send_command("configure terminal", delay=1.0)

        return True

    def exit_config_mode(self) -> bool:
        """退出配置模式"""
        logger.debug("退出配置模式")
        self.send_command("end", delay=1.0)
        return True

    def save_config(self) -> bool:
        """保存配置"""
        logger.debug("保存配置")
        self.send_command("write memory", delay=2.0)
        return True

    def deploy_config(self, commands: List[str],
                      progress_callback: Optional[Callable] = None) -> dict:
        """
        部署配置到设备

        Args:
            commands: 配置命令列表
            progress_callback: 进度回调

        Returns:
            dict: 部署结果
        """
        result = {
            "success": False,
            "total_commands": len(commands),
            "executed_commands": 0,
            "errors": []
        }

        try:
            # 进入配置模式
            self.enter_config_mode()

            # 发送命令
            self.send_commands(commands, progress_callback)
            result["executed_commands"] = len(commands)

            # 退出配置模式
            self.exit_config_mode()

            # 保存配置
            self.save_config()

            result["success"] = True
            logger.info(f"配置部署成功，共执行 {len(commands)} 条命令")

        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"配置部署失败：{e}")

        return result


def find_console_port() -> Optional[str]:
    """
    自动查找 Console 端口

    Returns:
        str: 找到的 COM 端口，未找到返回 None
    """
    service = ConsoleService()
    ports = service.list_ports()

    # 常见的 Console 芯片
    console_chips = ["FTDI", "CP210", "PL2303", "CH340"]

    for port in ports:
        # 检查设备描述是否包含 Console 芯片关键词
        for chip in console_chips:
            if chip.upper() in port["description"].upper():
                logger.info(f"找到 Console 设备：{port['device']} ({port['description']})")
                return port["device"]

    # 如果没有找到特征芯片，返回第一个可用串口
    if ports:
        logger.info(f"使用第一个可用串口：{ports[0]['device']}")
        return ports[0]["device"]

    return None
