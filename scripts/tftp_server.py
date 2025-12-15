"""
TFTP服务器配置和启动脚本

功能：
1. 自动检测固件文件
2. 配置TFTP服务器
3. 启动TFTP服务（需要第三方TFTP软件）

使用方法：
    python scripts/tftp_server.py --check      # 检查配置
    python scripts/tftp_server.py --start      # 启动服务器（需要Tftpd64）
"""

import os
import sys
import glob
import argparse
import subprocess
from pathlib import Path


class TftpServerManager:
    """TFTP服务器管理器"""

    def __init__(self):
        """初始化TFTP服务器管理器"""
        # 默认配置
        self.server_ip = "192.168.3.100"
        self.firmware_dir = r"E:\GIT\ROUTER_TEST\docs\upload\old"
        self.tftpd64_path = None  # Tftpd64.exe路径

    def detect_firmware_files(self):
        """
        检测固件目录中的文件

        Returns:
            list: 固件文件列表
        """
        print(f"\n{'='*70}")
        print(f"检测固件文件")
        print(f"{'='*70}")
        print(f"固件目录: {self.firmware_dir}")

        if not os.path.exists(self.firmware_dir):
            print(f"❌ 固件目录不存在: {self.firmware_dir}")
            return []

        # 支持的固件文件扩展名
        extensions = ['*.ext2', '*.bin', '*.img', '*.tar', '*.tar.gz']
        firmware_files = []

        for ext in extensions:
            pattern = os.path.join(self.firmware_dir, ext)
            files = glob.glob(pattern)
            firmware_files.extend(files)

        if firmware_files:
            print(f"✅ 找到 {len(firmware_files)} 个固件文件:")
            for i, file in enumerate(firmware_files, 1):
                file_size = os.path.getsize(file) / (1024 * 1024)  # MB
                print(f"  {i}. {os.path.basename(file)} ({file_size:.2f} MB)")
        else:
            print(f"❌ 未找到固件文件")

        print(f"{'='*70}\n")
        return firmware_files

    def check_tftpd64(self):
        """
        检查Tftpd64是否安装

        Returns:
            str: Tftpd64.exe的路径，如果未找到则返回None
        """
        print(f"\n{'='*70}")
        print(f"检查TFTP服务器软件")
        print(f"{'='*70}")

        # 常见的Tftpd64安装位置
        possible_paths = [
            r"C:\Program Files\Tftpd64\tftpd64.exe",
            r"C:\Program Files (x86)\Tftpd64\tftpd64.exe",
            r"C:\Tftpd64\tftpd64.exe",
            r"E:\Tftpd64\tftpd64.exe",
            r"D:\Tftpd64\tftpd64.exe",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                print(f"✅ 找到Tftpd64: {path}")
                self.tftpd64_path = path
                print(f"{'='*70}\n")
                return path

        print(f"❌ 未找到Tftpd64")
        print(f"")
        print(f"请下载并安装Tftpd64:")
        print(f"  下载地址: https://pjo2.github.io/tftpd64/")
        print(f"  或者: http://tftpd32.jounin.net/tftpd32_download.html")
        print(f"{'='*70}\n")
        return None

    def generate_config(self):
        """
        生成TFTP服务器配置说明

        Returns:
            str: 配置说明文本
        """
        config_text = f"""
{'='*70}
TFTP服务器配置指南
{'='*70}

1. 服务器配置
   - 服务器IP: {self.server_ip}
   - 固件目录: {self.firmware_dir}

2. 网络配置要求
   - PC网卡需要配置静态IP: {self.server_ip}
   - 子网掩码: 255.255.255.0
   - 路由器设备IP:
     - COM7设备: 192.168.3.7
     - COM8设备: 192.168.3.8

3. Tftpd64配置步骤
   a) 打开Tftpd64软件
   b) 设置"Current Directory"为固件目录:
      {self.firmware_dir}
   c) 设置"Server interfaces"为网卡IP:
      {self.server_ip}
   d) 在"TFTP"标签页，确保TFTP服务已启用
   e) 点击"Settings" → "TFTP"，配置：
      - Base Directory: {self.firmware_dir}
      - TFTP Security: None (无)
      - 勾选"Show Progress bar"（显示进度条）

4. 验证配置
   - 在Tftpd64日志窗口中，应该显示"TFTP服务器启动"
   - 确保Windows防火墙允许Tftpd64（UDP 69端口）

5. 固件文件
"""
        # 添加固件文件列表
        firmware_files = self.detect_firmware_files()
        if firmware_files:
            config_text += "   已检测到的固件文件:\n"
            for i, file in enumerate(firmware_files, 1):
                config_text += f"   {i}. {os.path.basename(file)}\n"
        else:
            config_text += "   ❌ 未检测到固件文件，请将固件文件放到固件目录中\n"

        config_text += f"\n{'='*70}\n"

        return config_text

    def check_network_config(self):
        """
        检查网络配置

        Returns:
            bool: 网络配置是否正确
        """
        print(f"\n{'='*70}")
        print(f"检查网络配置")
        print(f"{'='*70}")

        try:
            # 使用ipconfig检查网卡IP
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=5)
            output = result.stdout

            # 检查是否有192.168.3.100的IP
            if self.server_ip in output:
                print(f"✅ 检测到网卡配置: {self.server_ip}")
                print(f"{'='*70}\n")
                return True
            else:
                print(f"⚠️ 未检测到网卡配置: {self.server_ip}")
                print(f"")
                print(f"请手动配置网卡:")
                print(f"  1. 打开\"网络和共享中心\"")
                print(f"  2. 点击\"更改适配器设置\"")
                print(f"  3. 右键点击网卡 → 属性")
                print(f"  4. 双击\"Internet协议版本4 (TCP/IPv4)\"")
                print(f"  5. 选择\"使用下面的IP地址\"")
                print(f"  6. IP地址: {self.server_ip}")
                print(f"  7. 子网掩码: 255.255.255.0")
                print(f"{'='*70}\n")
                return False

        except Exception as e:
            print(f"❌ 检查网络配置失败: {e}")
            print(f"{'='*70}\n")
            return False

    def start_tftpd64(self):
        """
        启动Tftpd64（如果已安装）

        Returns:
            bool: 启动成功返回True
        """
        if not self.tftpd64_path:
            print("❌ 未找到Tftpd64，无法自动启动")
            print("请手动下载并安装Tftpd64")
            return False

        print(f"\n{'='*70}")
        print(f"启动Tftpd64")
        print(f"{'='*70}")
        print(f"执行: {self.tftpd64_path}")
        print(f"")
        print(f"⚠️ 注意:")
        print(f"  1. Tftpd64窗口打开后，请手动配置固件目录和服务器IP")
        print(f"  2. 固件目录: {self.firmware_dir}")
        print(f"  3. 服务器IP: {self.server_ip}")
        print(f"{'='*70}\n")

        try:
            # 启动Tftpd64（不等待，让它在后台运行）
            subprocess.Popen([self.tftpd64_path])
            print("✅ Tftpd64已启动，请在窗口中完成配置")
            return True
        except Exception as e:
            print(f"❌ 启动Tftpd64失败: {e}")
            return False

    def run_check(self):
        """执行配置检查"""
        print(f"\n{'#'*70}")
        print(f"TFTP服务器配置检查")
        print(f"{'#'*70}\n")

        # 1. 检测固件文件
        firmware_files = self.detect_firmware_files()

        # 2. 检查Tftpd64
        self.check_tftpd64()

        # 3. 检查网络配置
        self.check_network_config()

        # 4. 生成配置说明
        config = self.generate_config()
        print(config)

        # 5. 总结
        print(f"\n{'#'*70}")
        print(f"检查完成")
        print(f"{'#'*70}")
        print(f"")
        print(f"下一步操作:")
        print(f"  1. 如果Tftpd64未安装，请先下载安装")
        print(f"  2. 如果网卡IP未配置，请手动配置")
        print(f"  3. 启动Tftpd64: python scripts/tftp_server.py --start")
        print(f"  4. 在Tftpd64中配置固件目录和服务器IP")
        print(f"  5. 运行测试用例")
        print(f"{'#'*70}\n")

        return len(firmware_files) > 0

    def run_start(self):
        """执行启动服务器"""
        print(f"\n{'#'*70}")
        print(f"启动TFTP服务器")
        print(f"{'#'*70}\n")

        # 1. 检查Tftpd64
        if not self.check_tftpd64():
            print("❌ 无法启动TFTP服务器：Tftpd64未安装")
            return False

        # 2. 检测固件文件
        firmware_files = self.detect_firmware_files()
        if not firmware_files:
            print("⚠️ 警告：未检测到固件文件")

        # 3. 检查网络配置
        self.check_network_config()

        # 4. 启动Tftpd64
        return self.start_tftpd64()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="TFTP服务器配置和启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/tftp_server.py --check       # 检查配置
  python scripts/tftp_server.py --start       # 启动服务器
        """
    )

    parser.add_argument('--check', action='store_true', help='检查TFTP服务器配置')
    parser.add_argument('--start', action='store_true', help='启动TFTP服务器（需要Tftpd64）')

    args = parser.parse_args()

    # 创建管理器
    manager = TftpServerManager()

    # 如果没有指定参数，默认执行检查
    if not args.check and not args.start:
        args.check = True

    # 执行操作
    if args.check:
        manager.run_check()
    elif args.start:
        manager.run_start()


if __name__ == "__main__":
    main()
