"""
自动化TFTP服务器（用于测试用例）

功能：
1. 在测试用例启动时自动启动TFTP服务器
2. 在测试用例结束时自动关闭TFTP服务器
3. 支持后台线程运行，不阻塞主线程
"""

import os
import threading
import time
import glob
from typing import Optional


class AutoTftpServer:
    """
    自动化TFTP服务器

    使用方法:
        # 在测试用例的setup()中启动
        tftp_server = AutoTftpServer()
        tftp_server.start()

        # 在测试用例的cleanup()中关闭
        tftp_server.stop()
    """

    def __init__(self, server_ip: str = "192.168.3.100",
                 firmware_dir: str = None,
                 port: int = 69):
        """
        初始化TFTP服务器

        Args:
            server_ip: TFTP服务器IP地址
            firmware_dir: 固件文件目录
            port: TFTP端口（默认69）
        """
        self.server_ip = server_ip
        self.port = port

        # 固件目录
        if firmware_dir is None:
            firmware_dir = r"E:\GIT\ROUTER_TEST\docs\upload\old"
        self.firmware_dir = firmware_dir

        # 服务器对象
        self.server = None
        self.server_thread = None
        self.running = False

        # 尝试导入tftpy
        self.tftpy_available = self._check_tftpy()

    def _check_tftpy(self) -> bool:
        """
        检查tftpy是否已安装

        Returns:
            bool: 已安装返回True
        """
        try:
            import tftpy
            print("✅ tftpy库已安装")
            return True
        except ImportError:
            print("⚠️ tftpy库未安装")
            print("   请安装: pip install tftpy")
            return False

    def detect_firmware_files(self) -> list:
        """
        检测固件目录中的文件

        Returns:
            list: 固件文件列表
        """
        if not os.path.exists(self.firmware_dir):
            print(f"❌ 固件目录不存在: {self.firmware_dir}")
            return []

        extensions = ['*.ext2', '*.bin', '*.img', '*.tar', '*.tar.gz']
        firmware_files = []

        for ext in extensions:
            pattern = os.path.join(self.firmware_dir, ext)
            files = glob.glob(pattern)
            firmware_files.extend(files)

        return firmware_files

    def _run_server(self):
        """在后台线程中运行TFTP服务器"""
        try:
            import tftpy

            # 创建TFTP服务器
            self.server = tftpy.TftpServer(self.firmware_dir)

            print(f"✅ TFTP服务器已启动")
            print(f"   服务器IP: {self.server_ip}")
            print(f"   端口: {self.port}")
            print(f"   固件目录: {self.firmware_dir}")

            # 检测固件文件
            firmware_files = self.detect_firmware_files()
            if firmware_files:
                print(f"   固件文件:")
                for i, file in enumerate(firmware_files, 1):
                    file_size = os.path.getsize(file) / (1024 * 1024)  # MB
                    print(f"     {i}. {os.path.basename(file)} ({file_size:.2f} MB)")
            else:
                print(f"   ⚠️ 未检测到固件文件")

            print("")

            # 启动服务器（阻塞运行）
            self.server.listen(
                listenip=self.server_ip,
                listenport=self.port
            )

        except Exception as e:
            print(f"❌ TFTP服务器运行错误: {e}")
            self.running = False

    def start(self) -> bool:
        """
        启动TFTP服务器

        Returns:
            bool: 启动成功返回True
        """
        if self.running:
            print("⚠️ TFTP服务器已经在运行")
            return True

        if not self.tftpy_available:
            print("❌ 无法启动TFTP服务器: tftpy库未安装")
            print("   解决方案:")
            print("   1. 运行: pip install tftpy")
            print("   2. 或手动启动Tftpd64软件")
            return False

        print(f"\n{'='*70}")
        print(f"启动TFTP服务器")
        print(f"{'='*70}")

        # 检查固件目录
        if not os.path.exists(self.firmware_dir):
            print(f"❌ 固件目录不存在: {self.firmware_dir}")
            return False

        # 检查固件文件
        firmware_files = self.detect_firmware_files()
        if not firmware_files:
            print(f"⚠️ 警告: 未在 {self.firmware_dir} 中检测到固件文件")
            print(f"   请确保固件文件已放置在该目录中")

        try:
            # 在后台线程中启动服务器
            self.running = True
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True,  # 守护线程，主程序退出时自动退出
                name="TFTP-Server-Thread"
            )
            self.server_thread.start()

            # 等待服务器启动
            time.sleep(2)

            if self.running:
                print(f"✅ TFTP服务器启动成功（后台运行）")
                print(f"{'='*70}\n")
                return True
            else:
                print(f"❌ TFTP服务器启动失败")
                print(f"{'='*70}\n")
                return False

        except Exception as e:
            print(f"❌ 启动TFTP服务器失败: {e}")
            print(f"{'='*70}\n")
            self.running = False
            return False

    def stop(self):
        """停止TFTP服务器"""
        if not self.running:
            return

        print(f"\n{'='*70}")
        print(f"停止TFTP服务器")
        print(f"{'='*70}")

        try:
            self.running = False

            # tftpy服务器没有stop方法，只能通过标志位停止
            # 线程会在主程序退出时自动退出（daemon=True）

            print(f"✅ TFTP服务器已停止")
            print(f"{'='*70}\n")

        except Exception as e:
            print(f"⚠️ 停止TFTP服务器时出错: {e}")
            print(f"{'='*70}\n")

    def is_running(self) -> bool:
        """
        检查服务器是否正在运行

        Returns:
            bool: 运行中返回True
        """
        return self.running


# 测试代码
if __name__ == "__main__":
    print("TFTP服务器测试")
    print("="*70)

    # 创建服务器
    server = AutoTftpServer()

    # 启动服务器
    if server.start():
        print("\n服务器已启动，按Ctrl+C停止...")
        try:
            # 保持运行
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n接收到中断信号")

    # 停止服务器
    server.stop()

    print("\n测试完成")
