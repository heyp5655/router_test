"""
分屏控制台管理工具
用于多设备并行测试时的实时日志分屏显示
"""

import threading
import queue
import os
import sys
import time
from typing import Optional


class SplitConsoleManager:
    """分屏控制台管理器"""

    def __init__(self):
        """初始化分屏控制台"""
        self.device1_queue = queue.Queue()
        self.device2_queue = queue.Queue()
        self.device1_log_file = None
        self.device2_log_file = None
        self.device1_window = None
        self.device2_window = None

        # 创建日志目录
        self.log_dir = os.path.join("logs", "console")
        os.makedirs(self.log_dir, exist_ok=True)

        # 初始化日志文件
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.device1_log_path = os.path.join(self.log_dir, f"device1_{timestamp}.log")
        self.device2_log_path = os.path.join(self.log_dir, f"device2_{timestamp}.log")

        self.device1_log_file = open(self.device1_log_path, 'w', encoding='utf-8', buffering=1)
        self.device2_log_file = open(self.device2_log_path, 'w', encoding='utf-8', buffering=1)

        # 写入文件头
        self._write_header(self.device1_log_file, "设备1 (COM7 -> 192.168.3.7)")
        self._write_header(self.device2_log_file, "设备2 (COM8 -> 192.168.3.8)")

        print(f"✅ 设备1日志文件: {self.device1_log_path}")
        print(f"✅ 设备2日志文件: {self.device2_log_path}")

    def _write_header(self, log_file, device_name):
        """写入日志文件头"""
        log_file.write("=" * 80 + "\n")
        log_file.write(f"  {device_name} - 测试日志\n")
        log_file.write(f"  开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write("=" * 80 + "\n\n")
        log_file.flush()

    def log_device1(self, message: str):
        """记录设备1日志"""
        timestamp = time.strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"

        # 写入日志文件
        if self.device1_log_file:
            self.device1_log_file.write(log_line)
            self.device1_log_file.flush()

        # 添加到队列（保留，未来可能用于GUI）
        self.device1_queue.put(log_line)

    def log_device2(self, message: str):
        """记录设备2日志"""
        timestamp = time.strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"

        # 写入日志文件
        if self.device2_log_file:
            self.device2_log_file.write(log_line)
            self.device2_log_file.flush()

        # 添加到队列（保留，未来可能用于GUI）
        self.device2_queue.put(log_line)

    def start_windows(self):
        """启动两个独立的控制台窗口"""
        try:
            import subprocess

            # 获取Python可执行文件路径
            python_exe = sys.executable

            # 启动设备1监控窗口
            # 使用PowerShell的Get-Content -Wait实现实时tail效果
            # 关键：设置UTF-8编码解决中文乱码
            device1_cmd = [
                "powershell", "-NoExit", "-Command",
                f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
                f"$host.ui.RawUI.WindowTitle='Device1 - COM7 -> 192.168.3.7'; "
                f"Write-Host '============================================================' -ForegroundColor Cyan; "
                f"Write-Host '  Device 1 Test Log (COM7 -> 192.168.3.7)' -ForegroundColor Green; "
                f"Write-Host '============================================================' -ForegroundColor Cyan; "
                f"Write-Host ''; "
                f"Get-Content '{self.device1_log_path}' -Encoding UTF8 -Wait -Tail 0"
            ]

            device2_cmd = [
                "powershell", "-NoExit", "-Command",
                f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
                f"$host.ui.RawUI.WindowTitle='Device2 - COM8 -> 192.168.3.8'; "
                f"Write-Host '============================================================' -ForegroundColor Cyan; "
                f"Write-Host '  Device 2 Test Log (COM8 -> 192.168.3.8)' -ForegroundColor Yellow; "
                f"Write-Host '============================================================' -ForegroundColor Cyan; "
                f"Write-Host ''; "
                f"Get-Content '{self.device2_log_path}' -Encoding UTF8 -Wait -Tail 0"
            ]

            # 启动设备1窗口（新控制台）
            subprocess.Popen(device1_cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            time.sleep(0.5)

            # 启动设备2窗口（新控制台）
            subprocess.Popen(device2_cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            time.sleep(0.5)

            print("\n[Split Console] Two monitoring windows started successfully")
            print("   Tips: Please manually adjust window positions")
            print("   Left:  Device 1 (COM7 -> 192.168.3.7)")
            print("   Right: Device 2 (COM8 -> 192.168.3.8)")
            print("\nNote: Please manually close the two monitoring windows after testing\n")

            return True

        except Exception as e:
            print(f"[Warning] Failed to start monitoring windows: {e}")
            print("   Will use console output")
            return False

    def close(self):
        """关闭日志文件"""
        if self.device1_log_file:
            self.device1_log_file.write("\n" + "=" * 80 + "\n")
            self.device1_log_file.write(f"Test End Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.device1_log_file.write("=" * 80 + "\n")
            self.device1_log_file.close()

        if self.device2_log_file:
            self.device2_log_file.write("\n" + "=" * 80 + "\n")
            self.device2_log_file.write(f"Test End Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.device2_log_file.write("=" * 80 + "\n")
            self.device2_log_file.close()

        print("\n[Split Console] Log files saved")
        print(f"   Device 1: {self.device1_log_path}")
        print(f"   Device 2: {self.device2_log_path}")


# 全局单例管理器
_console_manager: Optional[SplitConsoleManager] = None


def get_console_manager() -> SplitConsoleManager:
    """获取全局控制台管理器单例"""
    global _console_manager
    if _console_manager is None:
        _console_manager = SplitConsoleManager()
    return _console_manager


def log_device1(message: str):
    """设备1日志快捷方法"""
    get_console_manager().log_device1(message)


def log_device2(message: str):
    """设备2日志快捷方法"""
    get_console_manager().log_device2(message)


def start_split_console() -> bool:
    """启动分屏控制台"""
    return get_console_manager().start_windows()


def close_split_console():
    """关闭分屏控制台"""
    if _console_manager:
        _console_manager.close()


# 监控进程入口点（用于subprocess调用）
if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "monitor":
        device_id = sys.argv[2]
        log_file = sys.argv[3]

        print(f"监控设备{device_id}日志文件: {log_file}")

        # 实时读取日志文件
        import subprocess
        subprocess.run([
            "powershell", "-Command",
            f"Get-Content '{log_file}' -Wait"
        ])
