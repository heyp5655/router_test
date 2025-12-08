"""
串口通信工具类
用于通过串口控制路由器（登录、重启、进入Boot模式、烧录固件等）
支持完整的串口日志记录功能
"""

import time
import serial
import re
import os
from datetime import datetime
from typing import Optional, Tuple


class SerialClient:
    """串口客户端工具类（带完整日志记录）"""

    def __init__(self, port: str, baudrate: int = 115200, timeout: int = 30, log_dir: str = None):
        """
        初始化串口客户端

        Args:
            port: COM端口号（如 "COM7"）
            baudrate: 波特率（默认115200）
            timeout: 读取超时时间（秒）
            log_dir: 日志目录（默认为 logs/serial/）
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

        # 串口配置
        self.data_bits = 8
        self.parity = 'N'  # None
        self.stop_bits = 1

        # 登录凭据
        self.username = "root"
        self.password = "R0uT3&U&s@l1nk46#3"

        # Boot模式密码
        self.boot_password = "ys23#2ls29#4"

        # 提示符（通用匹配，不限制主机名）
        self.login_prompt = "root@"  # 只检查 root@ 前缀
        self.boot_prompt = "=>"

        # TFTP配置（用于固件烧录）
        self.tftp_server_ip = "192.168.3.100"
        self.device_ip_com7 = "192.168.3.7"  # COM7对应的设备IP
        self.device_ip_com8 = "192.168.3.8"  # COM8对应的设备IP
        self.firmware_name = "32.3.0.7.ext2"  # 旧版本固件名

        # 日志配置
        if log_dir is None:
            log_dir = os.path.join("logs", "serial")
        self.log_dir = log_dir
        self.log_file = None
        self.log_file_path = None

        # 创建日志目录
        os.makedirs(self.log_dir, exist_ok=True)

        # 初始化日志文件
        self._init_log_file()

    def _init_log_file(self):
        """初始化日志文件"""
        try:
            # 生成日志文件名：COM7_20251203_143022.log
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"{self.port}_{timestamp}.log"
            self.log_file_path = os.path.join(self.log_dir, log_filename)

            # 打开日志文件（追加模式，实时刷新）
            self.log_file = open(self.log_file_path, 'a', encoding='utf-8', buffering=1)

            # 写入日志头
            self._write_log("="*80)
            self._write_log(f"串口日志开始记录")
            self._write_log(f"串口: {self.port}")
            self._write_log(f"波特率: {self.baudrate}")
            self._write_log(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._write_log("="*80)
            self._write_log("")

            print(f"✅ 串口日志文件已创建: {self.log_file_path}")

        except Exception as e:
            print(f"⚠️ 创建串口日志文件失败: {e}")
            self.log_file = None

    def _write_log(self, message: str, prefix: str = ""):
        """
        写入日志到文件

        Args:
            message: 日志消息
            prefix: 前缀（如 "SEND", "RECV"）
        """
        if self.log_file:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                if prefix:
                    log_line = f"[{timestamp}] [{prefix}] {message}"
                else:
                    log_line = f"[{timestamp}] {message}"

                self.log_file.write(log_line + "\n")
                self.log_file.flush()  # 立即刷新到磁盘
            except Exception as e:
                print(f"⚠️ 写入日志失败: {e}")

    def _log_send(self, data: str):
        """记录发送的数据"""
        # 隐藏密码
        display_data = data
        if self.password in data:
            display_data = data.replace(self.password, "***PASSWORD***")
        if self.boot_password in data:
            display_data = display_data.replace(self.boot_password, "***BOOT_PASSWORD***")

        self._write_log(display_data, "SEND")

    def _log_recv(self, data: str):
        """记录接收的数据"""
        # 分行记录，保持原始格式
        for line in data.split('\n'):
            if line.strip():
                self._write_log(line, "RECV")

    def _log_info(self, message: str):
        """记录信息日志"""
        self._write_log(message, "INFO")

    def _log_error(self, message: str):
        """记录错误日志"""
        self._write_log(message, "ERROR")

    def close_log(self):
        """关闭日志文件"""
        if self.log_file:
            try:
                self._write_log("")
                self._write_log("="*80)
                self._write_log("串口日志记录结束")
                self._write_log("="*80)
                self.log_file.close()
                self.log_file = None
                print(f"✅ 串口日志已保存: {self.log_file_path}")
            except Exception as e:
                print(f"⚠️ 关闭日志文件失败: {e}")

    def open(self) -> bool:
        """
        打开串口连接

        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            self._log_info(f"正在打开串口 {self.port}...")

            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.data_bits,
                parity=self.parity,
                stopbits=self.stop_bits,
                timeout=self.timeout,
                # 流控配置（与CRT保持一致）
                xonxoff=False,   # XON/XOFF软件流控：关闭
                rtscts=False,    # RTS/CTS硬件流控：关闭
                dsrdtr=False     # DTR/DSR流控：关闭
            )

            self._log_info(f"✅ 串口 {self.port} 打开成功")
            print(f"✅ 串口 {self.port} 打开成功")
            return True
        except Exception as e:
            self._log_error(f"❌ 打开串口 {self.port} 失败: {e}")
            print(f"❌ 打开串口 {self.port} 失败: {e}")
            return False

    def close(self):
        """关闭串口连接"""
        if self.serial and self.serial.is_open:
            self._log_info(f"正在关闭串口 {self.port}...")
            self.serial.close()
            self._log_info(f"✅ 串口 {self.port} 已关闭")
            print(f"✅ 串口 {self.port} 已关闭")

        # 关闭日志文件
        self.close_log()

    def read_until(self, expected: str, timeout: int = None) -> Tuple[bool, str]:
        """
        读取串口输出，直到出现期望的字符串

        Args:
            expected: 期望的字符串
            timeout: 超时时间（秒），None表示使用默认超时

        Returns:
            Tuple[bool, str]: (是否找到, 读取到的所有内容)
        """
        if timeout is None:
            timeout = self.timeout

        self._log_info(f"等待串口输出: '{expected}' (超时{timeout}秒)")

        start_time = time.time()
        buffer = ""

        while time.time() - start_time < timeout:
            if self.serial.in_waiting > 0:
                try:
                    data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data

                    # 记录接收的数据
                    self._log_recv(data)

                    print(data, end='', flush=True)  # 实时输出到控制台

                    if expected in buffer:
                        self._log_info(f"✅ 检测到期望字符串: '{expected}'")
                        return True, buffer
                except Exception as e:
                    self._log_error(f"读取串口数据出错: {e}")
                    print(f"⚠️ 读取串口数据出错: {e}")

            time.sleep(0.1)

        self._log_error(f"❌ 超时: 未检测到期望字符串 '{expected}'")
        return False, buffer

    def send_command(self, command: str, wait_time: float = 0.5):
        """
        发送命令到串口并读取输出

        Args:
            command: 要发送的命令
            wait_time: 发送后等待时间（秒）

        Returns:
            str: 命令的输出（等待时间内收到的所有数据）
        """
        if self.serial and self.serial.is_open:
            # 清空输入缓冲区（避免旧数据干扰）
            self.serial.reset_input_buffer()

            # 发送命令
            self.serial.write(f"{command}\r\n".encode('utf-8'))

            # 记录发送的命令（隐藏密码）
            self._log_send(command)

            # 控制台输出（隐藏密码）
            display_cmd = command
            if self.password in command:
                display_cmd = "***PASSWORD***"
            if self.boot_password in command:
                display_cmd = "***BOOT_PASSWORD***"
            print(f">>> {display_cmd}")

            # 等待设备处理命令
            time.sleep(wait_time)

            # 读取所有可用的输出
            output = ""
            if self.serial.in_waiting > 0:
                try:
                    data = self.serial.read(self.serial.in_waiting)
                    output = data.decode('utf-8', errors='ignore')
                    # 记录接收到的数据
                    self._log_recv(output)
                except Exception as e:
                    self._log_error(f"读取命令输出失败: {e}")

            return output
        return None

    def login(self) -> bool:
        """
        登录路由器串口（带已登录状态检测）

        Returns:
            bool: 登录成功返回True
        """
        self._log_info("="*60)
        self._log_info(f"开始登录串口 {self.port}")
        self._log_info("="*60)

        print(f"\n{'='*60}")
        print(f"开始登录串口 {self.port}")
        print(f"{'='*60}")

        # ✅ 关键修改: 先检测是否已经登录，避免重复登录导致命令执行
        self._log_info("步骤1: 检测当前登录状态...")

        # 不清空缓冲区，直接读取现有数据
        time.sleep(0.5)  # 短暂等待让数据进入缓冲区
        existing_data = ""
        if self.serial.in_waiting > 0:
            existing_data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            self._log_recv(existing_data)
            print(existing_data, end='')

        # 发送空命令激活，读取响应
        self.serial.write(b'\r\n')
        self._log_send("")
        time.sleep(1)

        response = ""
        if self.serial.in_waiting > 0:
            response = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            self._log_recv(response)
            print(response, end='')

        # 合并所有输出进行检测
        all_output = existing_data + response

        # 检测1: 已经登录到Linux（最高优先级，避免误操作）
        # 可能的提示符: root@ROUTER:~# 或 root@URSA:~# 或 root@xxx:(unreachable)/root#
        if "root@" in all_output and "#" in all_output:
            # 再次确认不是登录提示（避免误判）
            if "login:" not in all_output:
                self._log_info(f"✅ 串口 {self.port} 已经登录，跳过登录步骤")
                print(f"✅ 串口 {self.port} 已经登录，跳过登录步骤")
                return True

        # 检测2: User Menu状态 - 需要退出到Linux
        if "User Menu" in all_output or "Enter :" in all_output:
            self._log_info("⚠️ 检测到User Menu，正在退出到Linux登录界面...")
            print("⚠️ 检测到User Menu，正在退出到Linux登录界面...")

            # 发送'r'命令重启系统，退出User Menu
            self.serial.write(b'r\r\n')
            self._log_send("r (Reboot)")
            time.sleep(1)

            # 等待系统重启，检测U-Boot倒计时但不拦截
            self._log_info("等待系统重启到Linux登录界面...")
            print("等待系统重启到Linux登录界面...")
            time.sleep(10)  # 等待U-Boot倒计时自然结束

            # 等待Linux启动到登录界面（约30秒）
            found, output = self.read_until("login:", timeout=60)
            if not found:
                self._log_error("❌ 未检测到Linux登录提示")
                print("❌ 未检测到Linux登录提示")
                return False

            self._log_info("✅ 已退出User Menu，进入Linux登录界面")
            print("✅ 已退出User Menu，进入Linux登录界面")

        # 检测3: 登录提示符
        if "login:" in all_output:
            self._log_info(f"ℹ️  检测到登录提示符，需要输入用户名密码")
            print(f"ℹ️  检测到登录提示符，需要输入用户名密码")
        else:
            # 没有明确的状态，尝试激活登录提示
            self._log_info("步骤2: 激活登录提示...")
            self.serial.write(b'\r\n')
            self._log_send("")
            time.sleep(2)

            if self.serial.in_waiting > 0:
                response2 = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                self._log_recv(response2)
                print(response2, end='')

                # 再次检查是否已登录
                if "root@" in response2 and "#" in response2 and "login:" not in response2:
                    self._log_info(f"✅ 串口 {self.port} 已经登录，跳过登录步骤")
                    print(f"✅ 串口 {self.port} 已经登录，跳过登录步骤")
                    return True

        # 发送用户名
        self._log_info("发送用户名...")
        self.send_command(self.username, wait_time=1)

        # 发送密码
        self._log_info("发送密码...")
        self.send_command(self.password, wait_time=2)

        # 验证登录（宽松检测）
        self._log_info("验证登录...")
        start_time = time.time()
        buffer = ""
        timeout = 10

        while time.time() - start_time < timeout:
            if self.serial.in_waiting > 0:
                try:
                    data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                    self._log_recv(data)
                    print(data, end='', flush=True)

                    # 宽松检测: root@ 和 # 都存在就认为登录成功
                    # 不限制主机名（可能是 ROUTER、URSA 或其他）
                    if "root@" in buffer and "#" in buffer:
                        self._log_info(f"✅ 串口 {self.port} 登录成功")
                        print(f"\n✅ 串口 {self.port} 登录成功")
                        return True
                except Exception as e:
                    self._log_error(f"读取串口数据出错: {e}")

            time.sleep(0.1)

        self._log_error(f"❌ 串口 {self.port} 登录失败")
        print(f"❌ 串口 {self.port} 登录失败")
        return False

    def reboot_to_boot_mode(self) -> bool:
        """
        重启路由器并进入Boot模式（带登录状态检测）

        Returns:
            bool: 成功进入Boot模式返回True
        """
        self._log_info("="*60)
        self._log_info(f"重启设备并进入Boot模式 ({self.port})")
        self._log_info("="*60)

        print(f"\n{'='*60}")
        print(f"重启设备并进入Boot模式 ({self.port})")
        print(f"{'='*60}")

        # ✅ 关键修改: 先检测并确保已登录，避免在未登录状态下发送reboot
        self._log_info("步骤0: 检测登录状态...")
        print("步骤0: 检测登录状态...")

        # 读取当前缓冲区数据
        time.sleep(0.5)
        current_status = ""
        if self.serial.in_waiting > 0:
            current_status = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            self._log_recv(current_status)

        # 发送空命令获取当前状态
        self.serial.write(b'\r\n')
        self._log_send("")
        time.sleep(1)

        if self.serial.in_waiting > 0:
            response = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            self._log_recv(response)
            current_status += response

        # 检查是否已登录
        if not ("root@" in current_status and "#" in current_status):
            self._log_info("⚠️ 未登录，先登录到Linux...")
            print("⚠️ 未登录，先登录到Linux...")
            if not self.login():
                self._log_error("❌ 登录失败，无法重启")
                print("❌ 登录失败，无法重启")
                return False
        else:
            self._log_info("✅ 已登录，可以执行reboot")
            print("✅ 已登录，可以执行reboot")

        # 1. 发送reboot命令
        self._log_info("步骤1: 发送reboot命令...")
        print("步骤1: 发送reboot命令...")
        self.send_command("reboot", wait_time=2)

        # 2. 等待U-Boot启动，检测"Normal Boot"
        self._log_info("步骤2: 等待U-Boot启动...")
        print("步骤2: 等待U-Boot启动...")

        # 等待 "Normal Boot" 出现（在倒计时之前）
        found, output = self.read_until("Normal Boot", timeout=30)
        if not found:
            self._log_error("❌ 未检测到Normal Boot")
            print("❌ 未检测到Normal Boot")
            return False

        self._log_info("✅ 检测到Normal Boot")
        print("✅ 检测到Normal Boot")

        # 3. 立即发送'q + 回车'进入User Menu（抢在倒计时结束前）
        self._log_info("步骤3: 立即发送q+回车进入User Menu...")
        print("步骤3: 立即发送q+回车进入User Menu...")
        self.send_command("q", wait_time=1)

        # 5. 等待User Menu显示和"command not found"
        self._log_info("步骤5: 等待User Menu显示...")
        print("步骤5: 等待User Menu显示...")
        found, output = self.read_until("User Menu", timeout=10)
        if not found:
            self._log_error("❌ 未检测到User Menu")
            print("❌ 未检测到User Menu")
            return False

        # 6. 等待"Enter :"提示（User Menu会自然输出多行内容）
        self._log_info("步骤6: 等待Enter提示（User Menu正在输出中...）")
        print("步骤6: 等待Enter提示（User Menu正在输出中...）")

        # 策略: 安静等待，让User Menu自然输出所有内容
        # User Menu会输出多行，最后才显示"Enter :"
        enter_found = False
        buffer = ""
        start_time = time.time()
        check_interval = 0.5  # 每0.5秒检查一次
        max_wait_time = 10    # 最多等待10秒

        while time.time() - start_time < max_wait_time:
            # 安静等待，不发送任何命令
            time.sleep(check_interval)

            # 读取串口输出
            if self.serial.in_waiting > 0:
                data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                buffer += data
                self._log_recv(data)
                print(data, end='', flush=True)

                # 检查是否出现"Enter :"
                if "Enter :" in buffer:
                    enter_found = True
                    elapsed = time.time() - start_time
                    self._log_info(f"✅ 检测到Enter提示（等待了{elapsed:.1f}秒）")
                    print(f"\n✅ 检测到Enter提示（等待了{elapsed:.1f}秒）")
                    break

        if not enter_found:
            self._log_error("❌ 等待10秒后仍未检测到Enter提示")
            print("❌ 等待10秒后仍未检测到Enter提示")
            self._log_info(f"已接收内容:\n{buffer}")
            return False

        # 8. 发送'X + 回车'进入Boot模式
        self._log_info("步骤7: 发送X+回车进入Boot...")
        print("步骤7: 发送X+回车进入Boot...")
        self.serial.write(b'X\r')  # 只发送 X + \r
        self.serial.flush()
        self._log_send("X<CR>")

        # ⚠️ 关键发现：基于CRT测试结果
        # CRT成功方案：发送X后等待1秒，直接发送密码
        # 不需要等待密码提示，不需要检查，直接发送！

        # 等待1秒（让设备进入密码输入模式）
        self._log_info("步骤8: 等待1秒（设备准备密码输入模式）...")
        print("步骤8: 等待1秒...")
        time.sleep(1.0)

        # 9. 直接发送密码（不等待提示，不检查）
        self._log_info("步骤9: 直接发送Boot密码...")
        print(f"步骤9: 发送Boot密码...")

        # 发送密码 + 回车
        complete_string = self.boot_password + '\r'
        self.serial.write(complete_string.encode('utf-8'))
        self.serial.flush()
        self._log_send("***BOOT_PASSWORD***<CR>")

        # 等待密码验证完成
        self._log_info("等待密码验证...")
        time.sleep(3.0)

        # 读取设备响应
        if self.serial.in_waiting > 0:
            response = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            self._log_recv(response)
            print(f"设备响应: {response}")

            # 检查是否成功进入Boot模式
            if "=>" in response:
                self._log_info(f"✅ 成功进入Boot模式 ({self.port})")
                print(f"✅ 成功进入Boot模式 ({self.port})")
                return True  # ← 检测到 => 立即返回成功

        # 如果3秒内没有收到响应，再等待10秒
        self._log_info("⚠️ 3秒内未收到响应，继续等待...")
        print("⚠️ 3秒内未收到响应，继续等待...")
        found, output = self.read_until(self.boot_prompt, timeout=10)
        if found:
            self._log_info(f"✅ 成功进入Boot模式 ({self.port})")
            print(f"✅ 成功进入Boot模式 ({self.port})")
            return True
        else:
            self._log_error(f"❌ 进入Boot模式失败 ({self.port})")
            print(f"❌ 进入Boot模式失败 ({self.port})")
            return False

    def flash_firmware_via_tftp(self) -> bool:
        """
        通过TFTP烧录固件（旧版本32.3.0.7）

        Returns:
            bool: 烧录成功返回True
        """
        print(f"\n{'='*60}")
        print(f"开始通过TFTP烧录固件 ({self.port})")
        print(f"{'='*60}")

        # 确定设备IP（根据COM口）
        device_ip = self.device_ip_com7 if self.port == "COM7" else self.device_ip_com8

        # 1. 设置IP地址
        print(f"步骤1: 设置设备IP为 {device_ip}...")
        self.send_command(f"setenv ipaddr {device_ip}", wait_time=1)

        # 等待 =>
        found, _ = self.read_until(self.boot_prompt, timeout=5)
        if not found:
            print("⚠️ 警告: 未检测到提示符，继续执行...")

        # 2. 设置TFTP服务器IP
        print(f"步骤2: 设置TFTP服务器IP为 {self.tftp_server_ip}...")
        self.send_command(f"setenv serverip {self.tftp_server_ip}", wait_time=1)

        found, _ = self.read_until(self.boot_prompt, timeout=5)
        if not found:
            print("⚠️ 警告: 未检测到提示符，继续执行...")

        # 3. 设置固件文件名
        print(f"步骤3: 设置固件文件名为 {self.firmware_name}...")
        self.send_command(f"setenv imagename {self.firmware_name}", wait_time=1)

        found, _ = self.read_until(self.boot_prompt, timeout=5)
        if not found:
            print("⚠️ 警告: 未检测到提示符，继续执行...")

        # 4. 执行升级命令
        print("步骤4: 执行升级命令 'run updata-image'...")
        self.send_command("run updata-image", wait_time=2)

        # 5. 等待上传开始（检测 "Loading: #####"）
        print("步骤5: 等待固件上传...")
        found, output = self.read_until("Loading:", timeout=30)
        if not found:
            print("❌ 固件上传未开始")
            return False

        # 继续等待上传符号（#####）
        time.sleep(2)
        if self.serial.in_waiting > 0:
            upload_output = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            print(upload_output, end='', flush=True)
            if "#" in upload_output:
                print("\n✅ 固件正在上传中...")

        # 6. 等待烧录完成（检测 "written: OK"）
        print("步骤6: 等待烧录完成...")
        found, output = self.read_until("written: OK", timeout=300)  # 最多等待5分钟
        if not found:
            print("❌ 烧录未完成")
            return False

        print("✅ 烧录完成")

        # 7. 等待返回Boot提示符
        print("步骤7: 等待返回Boot提示符...")
        found, output = self.read_until(self.boot_prompt, timeout=30)
        if not found:
            print("⚠️ 警告: 未检测到Boot提示符，但烧录已完成")

        # 8. 发送reset命令
        print("步骤8: 发送reset命令重启设备...")
        self.send_command("reset", wait_time=2)

        # 9. 验证reset成功（检测 "resetting ..."）
        print("步骤9: 验证reset命令...")
        found, output = self.read_until("resetting", timeout=10)
        if found:
            print("✅ 设备正在重启...")
        else:
            print("⚠️ 警告: 未检测到重启信息，但已发送reset命令")

        # 10. 等待设备重启（120秒 = 2分钟）
        print("步骤10: 等待设备重启（120秒 = 2分钟）...")
        print("  ⏳ 设备重启需要约2分钟，请耐心等待...")
        time.sleep(120)  # 增加到2分钟，确保设备完全重启

        print(f"✅ TFTP烧录流程完成 ({self.port})")
        return True

    def login_after_flash(self) -> bool:
        """
        烧录固件后重新登录串口

        Returns:
            bool: 登录成功返回True
        """
        print(f"\n{'='*60}")
        print(f"烧录后重新登录串口 ({self.port})")
        print(f"{'='*60}")

        # ⚠️ 关键：清空串口缓冲区
        # 设备重启后，缓冲区可能有大量启动日志（Linux内核、系统服务等）
        # 这些日志可能包含旧的 root@ 提示符，导致误判
        self._log_info("清空串口缓冲区...")
        if self.serial.in_waiting > 0:
            old_data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            self._log_info(f"清空了 {len(old_data)} 字节的启动日志")
            print(f"清空了 {len(old_data)} 字节的启动日志")

        time.sleep(1)  # 等待1秒，让设备完全启动到登录界面

        return self.login()

    def set_bridge_ip(self, bridge_ip: str) -> bool:
        """
        设置Bridge0的IP地址

        Args:
            bridge_ip: Bridge IP地址（如 "192.168.50.17"）

        Returns:
            bool: 设置成功返回True
        """
        print(f"\n{'='*60}")
        print(f"设置Bridge0 IP为 {bridge_ip} ({self.port})")
        print(f"{'='*60}")

        # 发送ifconfig命令
        self.send_command(f"ifconfig Bridge0 {bridge_ip}", wait_time=2)

        # 等待提示符
        found, output = self.read_until(self.login_prompt, timeout=10)
        if found:
            print(f"✅ Bridge0 IP设置成功")
            return True
        else:
            print(f"⚠️ 未检测到提示符，但命令已发送")
            return True  # 即使未检测到提示符，也认为成功

    def flash_old_firmware(self, bridge_ip: str) -> bool:
        """
        完整的旧版本固件烧录流程（串口）

        Args:
            bridge_ip: 烧录后要设置的Bridge IP

        Returns:
            bool: 烧录成功返回True
        """
        print(f"\n{'#'*70}")
        print(f"开始串口烧录旧版本固件流程 ({self.port})")
        print(f"{'#'*70}")

        # 0. 确保串口已打开
        if not self.serial or not self.serial.is_open:
            print(f"串口未打开，正在打开 {self.port}...")
            if not self.open():
                print(f"❌ 串口打开失败 ({self.port})")
                return False

        # 1. 登录串口
        if not self.login():
            print(f"❌ 串口登录失败 ({self.port})")
            return False

        # 2. 重启并进入Boot模式
        if not self.reboot_to_boot_mode():
            print(f"❌ 进入Boot模式失败 ({self.port})")
            return False

        # 3. 通过TFTP烧录固件
        if not self.flash_firmware_via_tftp():
            print(f"❌ TFTP烧录固件失败 ({self.port})")
            return False

        # 4. 烧录后重新登录
        if not self.login_after_flash():
            print(f"❌ 烧录后登录失败 ({self.port})")
            return False

        # 5. 设置Bridge IP
        if not self.set_bridge_ip(bridge_ip):
            print(f"❌ 设置Bridge IP失败 ({self.port})")
            return False

        print(f"\n{'#'*70}")
        print(f"✅ 串口烧录旧版本固件流程完成 ({self.port})")
        print(f"{'#'*70}\n")

        return True


# 测试代码
if __name__ == "__main__":
    # 测试COM7
    print("测试COM7...")
    client_com7 = SerialClient("COM7")

    if client_com7.open():
        try:
            # 完整烧录流程
            client_com7.flash_old_firmware(bridge_ip="192.168.50.18")
        finally:
            client_com7.close()
