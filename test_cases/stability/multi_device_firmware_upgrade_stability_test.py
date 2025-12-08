"""
多设备反复升级稳定性测试（串口烧录 + Web升级）

测试ID: 21
测试项: 稳定性
测试点: 串口烧录旧版本 → Web升级新版本循环测试

测试流程:
1. 串口烧录旧版本固件32.3.0.7（通过Boot模式 + TFTP）
2. 设置Bridge IP（COM7→192.168.3.7, COM8→192.168.3.8）
3. Web登录，处理修改密码弹窗
4. 检查版本号是否为32.3.0.7
5. Web上传新版本固件32.3.0.9（等待5分钟上传）
6. 确认升级对话框，等待路由器重启（60秒）
7. ⚠️ 升级后IP恢复默认，通过串口重新配置Bridge IP
8. 验证升级后版本号
9. 循环1000次

关键步骤说明:
- 步骤7是关键：Web升级后路由器IP恢复到出厂默认值
- 必须通过串口执行 ifconfig Bridge0 192.168.3.X 重新配置IP
- 配置IP后才能通过Web重新登录验证版本号

注意事项:
- 串口在整个1000次循环中保持连接，不断开
- 串口日志持续记录到文件（logs/serial/COM{X}_YYYYMMDD_HHMMSS.log）
- 每次使用串口前检测登录状态，未登录则重新登录

两台设备并行测试（threading），效率提升50%
支持分屏显示：左侧显示设备1，右侧显示设备2
"""

import os
import time
import glob
import threading
from typing import List, Tuple, Dict
from test_cases.base_test import BaseTest
from models.test_config import TestConfig, RouterConfig
from core.router_client import RouterClient
from utils.serial_client import SerialClient
from utils.split_console import get_console_manager, start_split_console, close_split_console


class MultiDeviceFirmwareUpgradeStabilityTest(BaseTest):
    """多设备固件升级稳定性测试（串口烧录 + Web升级）"""

    @property
    def test_name(self) -> str:
        return "多设备反复升级稳定性测试（串口烧录 + Web升级）"

    @property
    def description(self) -> str:
        return "串口烧录旧版本 → Web升级新版本的循环稳定性测试（1000次）"

    @property
    def category(self) -> str:
        return "稳定性用例"

    @property
    def is_regression(self) -> bool:
        return True

    def __init__(self, config: TestConfig = None):
        if config is None:
            from models.test_config import TestMode
            config = TestConfig(
                router_config=RouterConfig(
                    router_ip="192.168.50.17",
                    username="admin",
                    password="password",
                    model="UR35"
                ),
                test_mode=TestMode.SPECIFIC
            )

        self.config = config
        self.router_client = None

        # 状态管理标志
        self._state_saved = False
        self._auto_restore = True

        # 固件配置
        self.new_firmware_dir = r"E:\GIT\ROUTER_TEST\docs\upload\new"
        self.old_version = "32.3.0.7"  # 串口烧录的旧版本（TFTP）
        self.new_version = "32.3.0.9"  # Web升级的新版本

        # 测试配置
        self.upgrade_cycles = 1000  # 升级循环次数

        # 设备1配置（COM7）
        self.device1_com_port = "COM7"
        self.device1_bridge_ip = "192.168.3.7"
        self.device1_web_ip = "192.168.3.7"
        self.device1_web_username = "admin"
        self.device1_web_password = "password"

        # 设备2配置（COM8）
        self.device2_com_port = "COM8"
        self.device2_bridge_ip = "192.168.3.8"
        self.device2_web_ip = "192.168.3.8"
        self.device2_web_username = "admin"
        self.device2_web_password = "password"

        # 串口客户端
        self.device1_serial = None
        self.device2_serial = None

        # Web客户端
        self.device1_web = None
        self.device2_web = None

        # 固件文件路径（在setup中初始化）
        self.new_firmware_path = None

        # 统计信息
        self.device1_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "failed_cycles": []
        }

        self.device2_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "failed_cycles": []
        }

    def log_info(self, message: str):
        """记录信息日志"""
        print(f"INFO - {self.__class__.__name__}: {message}")

    def log_error(self, message: str):
        """记录错误日志"""
        print(f"ERROR - {self.__class__.__name__}: {message}")

    def log_warning(self, message: str):
        """记录警告日志"""
        print(f"WARNING - {self.__class__.__name__}: {message}")

    def log_debug(self, message: str):
        """记录调试日志"""
        print(f"DEBUG - {self.__class__.__name__}: {message}")

    def setup(self):
        """测试前置条件"""
        self.log_info(f"\n{'='*70}")
        self.log_info(f"开始执行测试: {self.test_name}")
        self.log_info(f"{'='*70}\n")

        # 1. 检查新版本固件文件
        self.log_info("步骤1: 检查新版本固件文件...")
        new_firmware = self._get_firmware_file(self.new_firmware_dir)
        if not new_firmware:
            raise Exception(f"新版本固件文件不存在: {self.new_firmware_dir}")
        self.new_firmware_path = new_firmware
        self.log_info(f"  ✅ 找到新版本固件: {os.path.basename(new_firmware)}\n")

        # 2. 创建串口客户端并打开连接（持久连接，不断开）
        self.log_info("步骤2: 创建串口客户端...")
        self.device1_serial = SerialClient(self.device1_com_port)
        self.device2_serial = SerialClient(self.device2_com_port)

        # 打开串口连接（整个测试过程保持连接）
        if not self.device1_serial.open():
            raise Exception(f"无法打开串口 {self.device1_com_port}")
        if not self.device2_serial.open():
            raise Exception(f"无法打开串口 {self.device2_com_port}")

        self.log_info(f"  ✅ 串口连接已建立: {self.device1_com_port}, {self.device2_com_port}")
        self.log_info(f"  📝 日志文件: {self.device1_serial.log_file_path}")
        self.log_info(f"  📝 日志文件: {self.device2_serial.log_file_path}\n")

        # 3. 创建Web客户端
        self.log_info("步骤3: 创建Web客户端...")
        device1_config = RouterConfig(
            router_ip=self.device1_web_ip,
            username=self.device1_web_username,
            password=self.device1_web_password,
            model="UR35"
        )
        device2_config = RouterConfig(
            router_ip=self.device2_web_ip,
            username=self.device2_web_username,
            password=self.device2_web_password,
            model="UR35"
        )
        self.device1_web = RouterClient(device1_config)
        self.device2_web = RouterClient(device2_config)
        self.log_info("  ✅ Web客户端创建完成\n")

        self.log_info("="*70)
        self.log_info("测试前置条件检查完成")
        self.log_info("="*70 + "\n")

    def execute(self):
        """执行测试（线程并行模式 + 分屏显示）"""
        self.log_info(f"\n{'='*70}")
        self.log_info(f"开始执行稳定性测试（线程并行模式 + 分屏显示）")
        self.log_info(f"{'='*70}")
        self.log_info(f"升级模式: 串口烧录旧版本 → Web升级新版本")
        self.log_info(f"设备1: {self.device1_com_port} → Bridge {self.device1_bridge_ip} → Web {self.device1_web_ip}")
        self.log_info(f"设备2: {self.device2_com_port} → Bridge {self.device2_bridge_ip} → Web {self.device2_web_ip}")
        self.log_info(f"升级循环次数: {self.upgrade_cycles}")
        self.log_info(f"旧版本: {self.old_version} (串口烧录)")
        self.log_info(f"新版本: {self.new_version} (Web升级)")
        self.log_info(f"⚠️  注意: 串口保持持久连接，持续记录日志")
        self.log_info(f"🚀 两台设备将并行测试，效率提升50%！\n")

        # 启动分屏显示
        self.log_info("📺 启动分屏监控窗口...")
        split_enabled = start_split_console()

        if split_enabled:
            self.log_info("✅ 分屏显示已启动")
            self.log_info("   请手动调整两个窗口位置：")
            self.log_info("   - 左侧窗口：设备1 (COM7 → 192.168.3.7)")
            self.log_info("   - 右侧窗口：设备2 (COM8 → 192.168.3.8)")
            self.log_info("")
            time.sleep(3)  # 等待窗口启动
        else:
            self.log_info("⚠️ 分屏显示未启用，使用控制台输出")
            self.log_info("")

        # 记录开始时间
        start_time = time.time()

        # 创建线程1：测试设备1
        thread1 = threading.Thread(
            target=self._test_device,
            args=(
                "设备1",
                self.device1_serial,
                self.device1_web,
                self.device1_bridge_ip,
                self.device1_stats
            ),
            name="Device1-Thread"
        )

        # 创建线程2：测试设备2
        thread2 = threading.Thread(
            target=self._test_device,
            args=(
                "设备2",
                self.device2_serial,
                self.device2_web,
                self.device2_bridge_ip,
                self.device2_stats
            ),
            name="Device2-Thread"
        )

        # 启动两个线程
        self.log_info("🚀 启动设备1测试线程...")
        thread1.start()
        time.sleep(5)  # 错开5秒，避免同时操作

        self.log_info("🚀 启动设备2测试线程...")
        thread2.start()

        self.log_info("\n✅ 两个测试线程已启动，正在并行执行...")
        self.log_info("=" * 70 + "\n")

        # 等待两个线程完成
        self.log_info("⏳ 等待设备1测试线程完成...")
        thread1.join()
        self.log_info("✅ 设备1测试线程已完成\n")

        self.log_info("⏳ 等待设备2测试线程完成...")
        thread2.join()
        self.log_info("✅ 设备2测试线程已完成\n")

        # 计算总耗时
        total_time = time.time() - start_time
        self.log_info(f"\n{'='*70}")
        self.log_info(f"并行测试总耗时: {total_time/60:.1f} 分钟 ({total_time/3600:.1f} 小时)")
        self.log_info(f"{'='*70}\n")

        # 输出统计结果
        self._print_statistics()

        # 验证测试结果
        self._verify_results()

    def cleanup(self):
        """测试清理"""
        self.log_info(f"\n{'='*70}")
        self.log_info(f"测试清理: {self.test_name}")
        self.log_info(f"{'='*70}\n")

        # 关闭分屏显示
        try:
            close_split_console()
        except:
            pass

        # 关闭串口
        if self.device1_serial:
            try:
                self.device1_serial.close()
            except:
                pass

        if self.device2_serial:
            try:
                self.device2_serial.close()
            except:
                pass

        # 关闭Web浏览器
        if self.device1_web:
            try:
                self.device1_web.close()
            except:
                pass

        if self.device2_web:
            try:
                self.device2_web.close()
            except:
                pass

        self.log_info(f"\n✅ {self.test_name} 清理完成\n")

    def _get_firmware_file(self, directory: str) -> str:
        """从目录中获取固件文件"""
        extensions = ['*.bin', '*.img', '*.tar', '*.tar.gz', '*.zip', '*.ext2']

        for ext in extensions:
            pattern = os.path.join(directory, ext)
            files = glob.glob(pattern)
            if files:
                return files[0]

        return None

    def _test_device(self, device_name: str, serial_client: SerialClient,
                     web_client: RouterClient, bridge_ip: str, stats: dict):
        """测试单个设备的升级循环（串口烧录 + Web升级）"""
        # 获取分屏控制台管理器
        console_mgr = get_console_manager()

        # 确定是设备1还是设备2
        is_device1 = (device_name == "设备1")
        log_func = console_mgr.log_device1 if is_device1 else console_mgr.log_device2

        log_func(f"{'='*60}")
        log_func(f"{device_name} 开始升级循环测试")
        log_func(f"{'='*60}")
        log_func(f"串口: {serial_client.port}")
        log_func(f"Web IP: {web_client.router_ip}")
        log_func(f"Bridge IP: {bridge_ip}")
        log_func(f"循环次数: {self.upgrade_cycles}")
        log_func(f"⚠️  串口持久连接，日志持续记录")
        log_func("")

        start_time = time.time()

        for cycle in range(1, self.upgrade_cycles + 1):
            log_func(f"{'='*60}")
            log_func(f"升级循环 {cycle}/{self.upgrade_cycles}")
            log_func(f"{'='*60}")

            try:
                # === 步骤1: 检查串口登录状态 ===
                log_func(f"步骤1: 检查串口登录状态...")
                if not self._ensure_serial_login(serial_client, log_func):
                    raise Exception("串口登录失败")
                log_func(f"✅ 串口已登录")
                log_func("")

                # === 步骤2: 串口烧录旧版本 ===
                log_func(f"步骤2: 串口烧录旧版本 {self.old_version}...")

                # flash_old_firmware() 内部会自动重启并烧录
                # 注意：烧录后串口会断开连接，需要重新登录
                log_func(f"  🔄 开始Boot模式烧录流程...")
                log_func(f"     1) 重启并进入Boot模式")
                log_func(f"     2) TFTP下载固件到内存 (约30-60秒)")
                log_func(f"     3) 写入Flash (约60-120秒)")
                log_func(f"     4) 等待系统启动 (约30-40秒)")
                log_func(f"     5) 设置Bridge IP")
                log_func(f"  ⏳ 预计总耗时: 约3-5分钟，请耐心等待...")
                log_func("")

                # 启动烧录（在后台线程中显示进度）
                import threading
                flash_complete = threading.Event()
                flash_result = [False]  # 使用列表避免闭包问题

                def flash_thread():
                    try:
                        result = serial_client.flash_old_firmware(bridge_ip=bridge_ip)
                        flash_result[0] = result
                    finally:
                        flash_complete.set()

                flash_worker = threading.Thread(target=flash_thread)
                flash_worker.start()

                # 显示进度（每30秒输出一次）
                elapsed = 0
                while not flash_complete.is_set():
                    flash_complete.wait(timeout=30)
                    if not flash_complete.is_set():
                        elapsed += 30
                        log_func(f"  ⏱️  烧录进行中... 已耗时 {elapsed} 秒")

                # 等待线程结束
                flash_worker.join(timeout=10)

                if not flash_result[0]:
                    raise Exception("串口烧录失败")

                log_func(f"✅ 串口烧录完成")
                log_func("")

                # === 步骤3: 串口重新登录（烧录后需要重新登录）===
                log_func(f"步骤3: 串口重新登录...")
                time.sleep(10)  # 等待路由器启动
                if not self._ensure_serial_login(serial_client, log_func):
                    raise Exception("烧录后串口重新登录失败")
                log_func(f"✅ 串口重新登录成功")
                log_func("")

                # === 步骤4: Web登录 ===
                log_func(f"步骤4: Web登录路由器...")
                time.sleep(5)  # 额外等待Web服务启动

                if not web_client.login_web():
                    raise Exception("Web登录失败")

                log_func(f"✅ Web登录成功")
                log_func("")

                # === 步骤5: 检查旧版本号 ===
                log_func(f"步骤5: 检查固件版本...")

                if not web_client.check_firmware_version(self.old_version):
                    raise Exception(f"版本号验证失败，不是 {self.old_version}")

                log_func(f"✅ 旧版本验证成功")
                log_func("")

                # === 步骤6: Web上传新版本固件 ===
                log_func(f"步骤6: Web上传新版本固件 {self.new_version}...")
                log_func(f"  🔄 开始固件上传流程...")
                log_func(f"     1) 跳转到升级页面")
                log_func(f"     2) 选择固件文件")
                log_func(f"     3) 等待文件上传 (约5分钟)")
                log_func(f"     4) 确认升级对话框")
                log_func(f"     5) 等待路由器重启 (约60秒)")
                log_func(f"  ⏳ 预计总耗时: 约6-7分钟，请耐心等待...")
                log_func("")

                # 启动上传（在后台线程中显示进度）
                upload_complete = threading.Event()
                upload_result = [False]

                def upload_thread():
                    try:
                        # ⚠️ 重要：skip_relogin=True，不尝试重新登录
                        # 因为升级后IP恢复默认，需要先通过串口配置IP再登录
                        result = web_client.upload_and_upgrade_firmware(
                            self.new_firmware_path,
                            skip_relogin=True
                        )
                        upload_result[0] = result
                    finally:
                        upload_complete.set()

                upload_worker = threading.Thread(target=upload_thread)
                upload_worker.start()

                # 显示进度（每30秒输出一次）
                elapsed = 0
                while not upload_complete.is_set():
                    upload_complete.wait(timeout=30)
                    if not upload_complete.is_set():
                        elapsed += 30
                        log_func(f"  ⏱️  上传/重启中... 已耗时 {elapsed} 秒")

                # 等待线程结束
                upload_worker.join(timeout=10)

                if not upload_result[0]:
                    raise Exception("Web固件上传失败")

                log_func(f"✅ 固件上传完成，路由器已开始重启")
                log_func(f"  ℹ️  注意：升级后路由器IP会恢复到出厂默认值")
                log_func(f"  ℹ️  需要通过串口重新配置IP: {bridge_ip}")
                log_func("")

                # === 步骤7: 串口重新登录（升级后需要重新登录）===
                log_func(f"步骤7: 等待路由器启动完成并重新登录串口...")
                # upload_and_upgrade_firmware已等待60秒，这里再等30秒确保完全启动
                time.sleep(30)

                if not self._ensure_serial_login(serial_client, log_func):
                    log_func(f"❌ 致命错误：升级后串口重新登录失败")
                    log_func(f"❌ 这表明固件升级失败，路由器可能未正常启动")
                    log_func(f"❌ 停止测试，避免继续错误操作")
                    raise AssertionError("固件升级失败：升级后串口无法登录（路由器未启动）")

                log_func(f"✅ 升级后串口登录成功")
                log_func("")

                # === 步骤8: 串口配置Bridge IP（升级后IP恢复默认）===
                log_func(f"步骤8: 串口配置Bridge IP为 {bridge_ip}...")

                # 先检测串口登录状态（升级后可能已退出登录）
                log_func(f"  检查串口登录状态...")
                if not self._ensure_serial_login(serial_client, log_func):
                    log_func(f"❌ 致命错误：配置IP前串口登录失败")
                    log_func(f"❌ 这表明固件升级失败，路由器系统不稳定")
                    log_func(f"❌ 停止测试，避免继续错误操作")
                    raise AssertionError("固件升级失败：配置IP前串口无法登录（系统不稳定）")

                log_func(f"  ✅ 串口已登录，准备配置IP")

                # 执行ifconfig命令配置Bridge IP（带重试机制）
                cmd = f"ifconfig Bridge0 {bridge_ip}"
                max_retries = 3
                retry_delay = 3  # 每次重试间隔3秒
                ip_configured = False

                for attempt in range(1, max_retries + 1):
                    log_func(f"  尝试配置IP ({attempt}/{max_retries}): {cmd}")
                    serial_client.send_command(cmd, wait_time=3)  # 增加到3秒

                    # 等待配置生效
                    time.sleep(retry_delay)

                    # 验证IP配置是否成功
                    log_func(f"  验证IP配置...")
                    verify_output = serial_client.send_command("ifconfig Bridge0", wait_time=3)  # 增加到3秒

                    # 检查IP是否配置成功
                    if verify_output and bridge_ip in str(verify_output):
                        ip_configured = True
                        log_func(f"✅ Bridge IP配置成功: {bridge_ip} (第{attempt}次尝试)")
                        break
                    else:
                        log_func(f"⚠️ 第{attempt}次验证失败，IP未配置成功")
                        log_func(f"   实际输出: {verify_output}")
                        if attempt < max_retries:
                            log_func(f"   等待{retry_delay}秒后重试...")
                            time.sleep(retry_delay)

                # 最终检查
                if not ip_configured:
                    log_func(f"❌ 致命错误：IP配置失败（已重试{max_retries}次）")
                    log_func(f"❌ 执行 'ifconfig Bridge0' 未检测到IP: {bridge_ip}")
                    log_func(f"❌ 最后一次输出: {verify_output}")
                    log_func(f"❌ 这表明固件升级可能失败，或网络配置异常")
                    log_func(f"❌ 停止测试，避免继续错误操作")
                    raise AssertionError(f"固件升级失败：无法配置IP {bridge_ip}（已重试{max_retries}次，网络配置失败）")
                log_func("")

                # === 步骤9: 等待IP生效，重新Web登录 ===
                log_func(f"步骤9: 等待IP生效和Web服务启动...")
                log_func(f"  等待IP配置生效...")
                time.sleep(10)  # 等待IP配置生效

                log_func(f"  等待Web服务启动...")
                time.sleep(15)  # 额外等待Web服务启动（总共25秒）

                log_func(f"  尝试Web登录 {web_client.router_ip}...")

                # 尝试Web登录（带超时控制）
                login_success = False
                login_error = None
                try:
                    import signal

                    # 定义超时处理函数（仅限Linux）
                    def timeout_handler(signum, frame):
                        raise TimeoutError("Web登录超时")

                    # Windows不支持signal.alarm，使用threading.Timer代替
                    login_timer = None
                    login_timeout = 60  # 60秒超时

                    def login_with_timeout():
                        nonlocal login_success, login_error
                        try:
                            login_success = web_client.login_web_force()
                        except Exception as e:
                            login_error = e

                    # 启动登录线程
                    login_thread = threading.Thread(target=login_with_timeout)
                    login_thread.start()
                    login_thread.join(timeout=login_timeout)

                    if login_thread.is_alive():
                        # 超时了
                        log_func(f"❌ 致命错误：Web登录超时（{login_timeout}秒）")
                        log_func(f"❌ 这表明固件升级可能失败，Web服务无响应")
                        log_func(f"❌ 停止测试，避免继续错误操作")
                        raise AssertionError(f"固件升级失败：Web登录超时{login_timeout}秒（Web服务异常）")

                    if login_error:
                        # 登录过程中出错
                        log_func(f"❌ 致命错误：Web登录异常")
                        log_func(f"❌ 错误信息: {login_error}")
                        log_func(f"❌ 这表明固件升级可能失败，Web服务异常")
                        log_func(f"❌ 停止测试，避免继续错误操作")
                        raise AssertionError(f"固件升级失败：Web登录异常（{login_error}）")

                    if not login_success:
                        # 登录失败
                        log_func(f"❌ 致命错误：Web登录失败")
                        log_func(f"❌ 可能原因：")
                        log_func(f"   1. IP配置未生效（路由器不在 {web_client.router_ip}）")
                        log_func(f"   2. Web服务未启动（固件升级失败）")
                        log_func(f"   3. 网络不通（PC与路由器不在同一网段）")
                        log_func(f"❌ 停止测试，避免继续错误操作")
                        raise AssertionError(f"固件升级失败：Web无法登录 {web_client.router_ip}（连接失败）")

                except AssertionError:
                    # 重新抛出AssertionError，直接停止测试
                    raise
                except Exception as e:
                    log_func(f"❌ 致命错误：Web登录过程异常")
                    log_func(f"❌ 异常信息: {e}")
                    log_func(f"❌ 停止测试，避免继续错误操作")
                    raise AssertionError(f"固件升级失败：Web登录过程异常（{e}）")

                log_func(f"✅ Web重新登录成功")
                log_func("")

                # === 步骤10: 验证新版本号 ===
                log_func(f"步骤10: 验证新版本号...")

                if not web_client.check_firmware_version(self.new_version):
                    raise Exception(f"新版本号验证失败，不是 {self.new_version}")

                log_func(f"✅ 新版本验证成功")
                log_func(f"✅ 第{cycle}次升级成功！")
                log_func("")

                # 更新统计
                stats["success"] += 1
                stats["total"] = cycle

            except AssertionError as ae:
                # AssertionError表示固件升级失败，需要立即停止测试
                log_func(f"")
                log_func(f"{'='*60}")
                log_func(f"❌❌❌ 致命错误：固件升级失败 ❌❌❌")
                log_func(f"{'='*60}")
                log_func(f"循环次数: {cycle}/{self.upgrade_cycles}")
                log_func(f"失败原因: {ae}")
                log_func(f"")
                log_func(f"⚠️  检测到固件升级失败的致命错误：")
                log_func(f"   - 升级后串口无法登录")
                log_func(f"   - 无法配置IP地址")
                log_func(f"   - Web登录超时或失败")
                log_func(f"")
                log_func(f"🛑 为避免继续错误操作，立即停止测试")
                log_func(f"🛑 请检查路由器状态和固件文件")
                log_func(f"{'='*60}")
                log_func(f"")

                # 更新统计
                stats["failed"] += 1
                stats["failed_cycles"].append(cycle)
                stats["total"] = cycle

                # 重新抛出，停止测试
                raise

            except Exception as e:
                log_func(f"❌ 循环 {cycle} 失败: {e}")
                stats["failed"] += 1
                stats["failed_cycles"].append(cycle)
                stats["total"] = cycle

                # ⚠️ 不关闭串口！保持持久连接
                # 只关闭Web浏览器
                try:
                    if web_client.driver:
                        web_client.driver.quit()
                        web_client.driver = None
                except:
                    pass

                continue

            # 输出进度
            elapsed = time.time() - start_time
            log_func(f"进度: {cycle}/{self.upgrade_cycles}, "
                    f"成功: {stats['success']}, 失败: {stats['failed']}, "
                    f"耗时: {elapsed/60:.1f}分钟")
            log_func("")

        total_time = time.time() - start_time
        log_func(f"{'='*60}")
        log_func(f"✅ 测试完成")
        log_func(f"总耗时: {total_time/60:.1f}分钟")
        log_func(f"成功: {stats['success']}, 失败: {stats['failed']}")
        log_func(f"{'='*60}")

    def _ensure_serial_login(self, serial_client: SerialClient, log_func) -> bool:
        """
        确保串口已登录

        Args:
            serial_client: 串口客户端
            log_func: 日志函数

        Returns:
            bool: 登录成功返回True，失败返回False
        """
        try:
            # 发送回车检查是否已登录
            serial_client.serial.write(b'\r\n')
            time.sleep(1)

            # 读取当前缓冲区
            if serial_client.serial.in_waiting > 0:
                output = serial_client.serial.read(serial_client.serial.in_waiting).decode('utf-8', errors='ignore')
                serial_client._log_recv(output)

                # 检查是否包含提示符（root@）
                if "root@" in output and "#" in output:
                    log_func(f"  ℹ️  已登录（检测到提示符）")
                    return True

            # 未登录，尝试登录
            log_func(f"  ℹ️  未登录，正在登录...")
            return serial_client.login()

        except Exception as e:
            log_func(f"  ⚠️  登录检查失败: {e}")
            # 尝试登录
            try:
                return serial_client.login()
            except:
                return False

    def _print_statistics(self):
        """输出统计信息"""
        self.log_info(f"\n{'='*70}")
        self.log_info(f"测试统计结果")
        self.log_info(f"{'='*70}\n")

        # 设备1统计
        self.log_info(f"设备1 (COM{self.device1_com_port} → {self.device1_web_ip}):")
        self.log_info(f"  总循环次数: {self.device1_stats['total']}")
        self.log_info(f"  成功次数: {self.device1_stats['success']}")
        self.log_info(f"  失败次数: {self.device1_stats['failed']}")
        if self.device1_stats['failed_cycles']:
            self.log_info(f"  失败的循环: {self.device1_stats['failed_cycles']}")

        # 设备2统计
        self.log_info(f"\n设备2 (COM{self.device2_com_port} → {self.device2_web_ip}):")
        self.log_info(f"  总循环次数: {self.device2_stats['total']}")
        self.log_info(f"  成功次数: {self.device2_stats['success']}")
        self.log_info(f"  失败次数: {self.device2_stats['failed']}")
        if self.device2_stats['failed_cycles']:
            self.log_info(f"  失败的循环: {self.device2_stats['failed_cycles']}")

        # 汇总
        total_success = self.device1_stats['success'] + self.device2_stats['success']
        total_failed = self.device1_stats['failed'] + self.device2_stats['failed']

        self.log_info(f"\n总体统计:")
        self.log_info(f"  总升级次数: {total_success + total_failed}")
        self.log_info(f"  成功: {total_success}")
        self.log_info(f"  失败: {total_failed}")
        if (total_success + total_failed) > 0:
            success_rate = (total_success / (total_success + total_failed)) * 100
            self.log_info(f"  成功率: {success_rate:.2f}%")

        self.log_info(f"\n{'='*70}\n")

    def _verify_results(self):
        """验证测试结果"""
        # 检查是否有失败
        if self.device1_stats['failed'] > 0 or self.device2_stats['failed'] > 0:
            total_failed = self.device1_stats['failed'] + self.device2_stats['failed']
            raise AssertionError(f"稳定性测试失败: 共有 {total_failed} 次升级失败")

        # 检查是否完成了所有循环
        if self.device1_stats['total'] < self.upgrade_cycles:
            raise AssertionError(f"设备1未完成所有循环: {self.device1_stats['total']}/{self.upgrade_cycles}")

        if self.device2_stats['total'] < self.upgrade_cycles:
            raise AssertionError(f"设备2未完成所有循环: {self.device2_stats['total']}/{self.upgrade_cycles}")

        self.log_info("✅ 稳定性测试通过：所有升级循环均成功完成")


# 测试入口
if __name__ == "__main__":
    from models.test_config import TestConfig, TestMode

    test_config = TestConfig(
        router_config=None,
        test_mode=TestMode.SPECIFIC,
        timeout=300,
        restore_default=False
    )

    test = MultiDeviceFirmwareUpgradeStabilityTest(test_config)

    try:
        test.setup()
        test.execute()
        print("\n✅ 测试通过")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test.cleanup()
