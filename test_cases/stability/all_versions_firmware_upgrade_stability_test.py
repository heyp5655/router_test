"""
遍历历史所有版本升级到最新稳定性测试（串口烧录 + Web升级）⚡ 固件分片优化版

测试ID: 22
测试项: 稳定性
测试点: 遍历old_all目录所有旧版本 → Web升级新版本测试

测试流程:
1. 🆕 动态扫描固件文件
   - 扫描old_all目录获取所有旧版本固件列表
   - 扫描new目录获取新版本固件文件
   - 自动从文件名提取版本号（无需手动配置）
2. 🆕 固件分片优化：将固件列表分成两部分，两台设备分工测试
   - 设备1 (COM7): 测试前半部分固件
   - 设备2 (COM8): 测试后半部分固件
3. 对每个旧版本固件执行：
   a) 串口烧录旧版本固件（通过Boot模式 + TFTP）
   b) 设置Bridge IP（COM7→192.168.3.7, COM8→192.168.3.8）
   c) Web登录，处理修改密码弹窗
   d) 检查版本号
   e) Web上传新版本固件32.3.0.9（等待5分钟上传）
   f) 确认升级对话框，等待路由器重启（60秒）
   g) ⚠️ 升级后IP恢复默认，通过串口重新配置Bridge IP
   h) 验证升级后版本号为32.3.0.9
4. 直到所有旧版本都测试完成

关键步骤说明:
- Web升级后路由器IP恢复到出厂默认值
- 必须通过串口执行 ifconfig Bridge0 192.168.3.X 重新配置IP
- 配置IP后才能通过Web重新登录验证版本号

注意事项:
- 旧版本固件目录: E:/GIT/ROUTER_TEST/docs/upload/old_all
- 新版本固件目录: E:/GIT/ROUTER_TEST/docs/upload/new
- 串口日志持续记录到文件（logs/serial/COM{X}_YYYYMMDD_HHMMSS.log）
- 每次使用串口前检测登录状态，未登录则重新登录

🚀 优化特性:
- 🔄 动态版本检测：每次运行自动扫描固件文件，自动提取版本号
- 📦 固件分片：两台设备分工协作，避免重复测试
- ⚡ 并行测试：两台设备同时工作，充分利用硬件资源
- 🚀 效率提升：相比旧版本（重复测试）节省50%时间
- 📺 分屏显示：左侧显示设备1，右侧显示设备2
- 🎯 灵活部署：更换固件文件无需修改代码
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


class AllVersionsFirmwareUpgradeStabilityTest(BaseTest):
    """遍历历史所有版本升级到最新稳定性测试（串口烧录 + Web升级）"""

    @property
    def test_name(self) -> str:
        return "遍历历史所有版本升级到最新稳定性测试（串口烧录 + Web升级）"

    @property
    def description(self) -> str:
        return "遍历old_all目录所有旧版本 → Web升级新版本32.3.0.9的稳定性测试"

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
        self.old_firmware_dir = r"E:\GIT\ROUTER_TEST\docs\upload\old_all"

        # 🆕 动态配置（在setup中初始化）
        self.new_version = None  # 动态从固件文件名提取
        self.new_firmware_path = None  # 动态获取新版本固件路径

        # 测试配置（扫描old_all目录获取所有旧版本固件列表）
        self.old_firmware_list = []  # 在setup中初始化

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

        # 1. 提示用户启动TFTP服务器
        self.log_info("步骤1: 准备TFTP服务器...")
        self.log_info("  ⚠️ 请确保TFTP服务器已启动:")
        self.log_info("     - 方式1: 双击运行 '启动TFTP服务器.bat'")
        self.log_info("     - 方式2: 手动启动Tftpd64软件")
        self.log_info("     - 服务器IP: 192.168.3.100")
        self.log_info("     - ⚠️⚠️⚠️ 固件目录: E:\\GIT\\ROUTER_TEST\\docs\\upload\\old_all")
        self.log_info("     - ⚠️ 注意：ID22使用old_all目录（与ID21的old目录不同）")
        self.log_info("")

        # 2. 扫描old_all目录获取所有旧版本固件列表
        self.log_info("步骤2: 扫描old_all目录获取旧版本固件列表...")
        self.old_firmware_list = self._get_all_firmware_files(self.old_firmware_dir)
        if not self.old_firmware_list:
            raise Exception(f"old_all目录中没有固件文件: {self.old_firmware_dir}")

        self.log_info(f"  ✅ 找到 {len(self.old_firmware_list)} 个旧版本固件:")
        for i, firmware_path in enumerate(self.old_firmware_list, 1):
            firmware_name = os.path.basename(firmware_path)
            file_size = os.path.getsize(firmware_path) / (1024 * 1024)  # MB
            self.log_info(f"     {i}. {firmware_name} ({file_size:.1f} MB)")
        self.log_info("")

        # 3. 动态检查新版本固件文件并提取版本号
        self.log_info("步骤3: 动态检查新版本固件文件...")
        new_firmware = self._get_firmware_file(self.new_firmware_dir)
        if not new_firmware:
            raise Exception(f"新版本固件文件不存在: {self.new_firmware_dir}")

        self.new_firmware_path = new_firmware
        new_firmware_name = os.path.basename(new_firmware)

        # 🆕 从文件名自动提取版本号
        self.new_version = self._extract_version_from_filename(new_firmware_name)
        if not self.new_version:
            raise Exception(f"无法从固件文件名提取版本号: {new_firmware_name}")

        self.log_info(f"  ✅ 找到新版本固件: {new_firmware_name}")
        self.log_info(f"  🔢 自动提取版本号: {self.new_version}")
        self.log_info(f"  📁 固件路径: {new_firmware}\n")

        # 4. 创建串口客户端并打开连接（持久连接，不断开）
        self.log_info("步骤4: 创建串口客户端...")
        # ⚠️ 关键：指定TFTP固件目录为old_all（而非默认的old）
        self.device1_serial = SerialClient(
            self.device1_com_port,
            tftp_firmware_dir=self.old_firmware_dir
        )
        self.device2_serial = SerialClient(
            self.device2_com_port,
            tftp_firmware_dir=self.old_firmware_dir
        )

        # 打开串口连接（整个测试过程保持连接）
        if not self.device1_serial.open():
            raise Exception(f"无法打开串口 {self.device1_com_port}")
        if not self.device2_serial.open():
            raise Exception(f"无法打开串口 {self.device2_com_port}")

        self.log_info(f"  ✅ 串口连接已建立: {self.device1_com_port}, {self.device2_com_port}")
        self.log_info(f"  📝 日志文件: {self.device1_serial.log_file_path}")
        self.log_info(f"  📝 日志文件: {self.device2_serial.log_file_path}\n")

        # 5. 创建Web客户端
        self.log_info("步骤5: 创建Web客户端...")
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
        """执行测试（线程并行模式 + 分屏显示 + 固件分片优化）"""
        self.log_info(f"\n{'='*70}")
        self.log_info(f"开始执行稳定性测试（线程并行模式 + 分屏显示 + 固件分片优化）")
        self.log_info(f"{'='*70}")
        self.log_info(f"测试模式: 遍历old_all所有旧版本 → Web升级新版本")
        self.log_info(f"设备1: {self.device1_com_port} → Bridge {self.device1_bridge_ip} → Web {self.device1_web_ip}")
        self.log_info(f"设备2: {self.device2_com_port} → Bridge {self.device2_bridge_ip} → Web {self.device2_web_ip}")
        self.log_info(f"旧版本固件数量: {len(self.old_firmware_list)} 个")
        self.log_info(f"旧版本目录: {self.old_firmware_dir}")
        self.log_info(f"🔢 新版本: {self.new_version} (动态检测，Web升级)")
        self.log_info(f"📁 新版本路径: {os.path.basename(self.new_firmware_path)}")
        self.log_info(f"⚠️  注意: 串口保持持久连接，持续记录日志")
        self.log_info(f"🚀 两台设备将并行测试，且分工协作，避免重复！\n")

        # ====== 固件分片分配逻辑 ======
        total_firmwares = len(self.old_firmware_list)
        mid_point = total_firmwares // 2

        # 设备1：测试前半部分固件
        firmware_slice1 = self.old_firmware_list[:mid_point]
        slice1_info = f"1-{mid_point}" if mid_point > 0 else "无"

        # 设备2：测试后半部分固件
        firmware_slice2 = self.old_firmware_list[mid_point:]
        slice2_start = mid_point + 1
        slice2_info = f"{slice2_start}-{total_firmwares}" if mid_point < total_firmwares else "无"

        self.log_info(f"📦 固件分片分配：")
        self.log_info(f"  设备1 ({self.device1_com_port}): 测试第 {slice1_info} 个固件 (共 {len(firmware_slice1)} 个)")
        self.log_info(f"  设备2 ({self.device2_com_port}): 测试第 {slice2_info} 个固件 (共 {len(firmware_slice2)} 个)")
        self.log_info(f"  ⚡ 优化效果: 两台设备分工协作，避免重复测试，效率提升100%！\n")

        # 保存分片信息到统计字典（用于后续报告显示）
        self.device1_stats["slice_info"] = slice1_info
        self.device1_stats["slice_count"] = len(firmware_slice1)
        self.device2_stats["slice_info"] = slice2_info
        self.device2_stats["slice_count"] = len(firmware_slice2)

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

        # 创建线程1：测试设备1（前半部分固件）
        thread1 = threading.Thread(
            target=self._test_device,
            args=(
                "设备1",
                self.device1_serial,
                self.device1_web,
                self.device1_bridge_ip,
                self.device1_stats,
                firmware_slice1,  # 🆕 传入前半部分固件
                slice1_info       # 🆕 传入分片信息
            ),
            name="Device1-Thread"
        )

        # 创建线程2：测试设备2（后半部分固件）
        thread2 = threading.Thread(
            target=self._test_device,
            args=(
                "设备2",
                self.device2_serial,
                self.device2_web,
                self.device2_bridge_ip,
                self.device2_stats,
                firmware_slice2,  # 🆕 传入后半部分固件
                slice2_info       # 🆕 传入分片信息
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

    def _get_all_firmware_files(self, directory: str) -> list:
        """
        扫描目录获取所有固件文件列表

        Args:
            directory: 固件目录路径

        Returns:
            list: 固件文件路径列表（按版本号排序）
        """
        if not os.path.exists(directory):
            return []

        extensions = ['*.bin', '*.img', '*.tar', '*.tar.gz', '*.zip', '*.ext2']
        firmware_files = []

        for ext in extensions:
            pattern = os.path.join(directory, ext)
            files = glob.glob(pattern)
            firmware_files.extend(files)

        # 按文件名排序（版本号排序）
        firmware_files.sort()

        return firmware_files

    def _extract_version_from_filename(self, filename: str) -> str:
        """
        从固件文件名中提取版本号

        支持的文件名格式：
        - 32.3.0.9.bin
        - 32.3.0.10.ext2
        - UR35-32.3.0.9.bin
        - firmware_32.3.0.9.img

        Args:
            filename: 固件文件名

        Returns:
            str: 提取的版本号（如："32.3.0.9"），失败返回None
        """
        import re

        # 移除文件扩展名
        name_without_ext = filename
        for ext in ['.bin', '.img', '.tar', '.tar.gz', '.zip', '.ext2']:
            if filename.endswith(ext):
                name_without_ext = filename[:-len(ext)]
                break

        # 匹配版本号模式：主版本.次版本.修订版.构建号
        # 支持格式：X.X.X.X 或 XX.X.X.X
        version_pattern = r'(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d{1,3})'
        match = re.search(version_pattern, name_without_ext)

        if match:
            return match.group(1)

        # 如果上面的模式不匹配，尝试简化模式（可能没有构建号）
        # 格式：X.X.X
        simple_pattern = r'(\d{1,2}\.\d{1,2}\.\d{1,2})'
        match = re.search(simple_pattern, name_without_ext)

        if match:
            return match.group(1)

        return None

    def _test_device(self, device_name: str, serial_client: SerialClient,
                     web_client: RouterClient, bridge_ip: str, stats: dict,
                     firmware_slice: list, slice_info: str):
        """测试单个设备的升级循环（遍历分配的固件列表）

        Args:
            device_name: 设备名称
            serial_client: 串口客户端
            web_client: Web客户端
            bridge_ip: Bridge IP地址
            stats: 统计信息字典
            firmware_slice: 分配给该设备的固件列表（分片）
            slice_info: 分片信息描述（如："1-5"）
        """
        # 获取分屏控制台管理器
        console_mgr = get_console_manager()

        # 确定是设备1还是设备2
        is_device1 = (device_name == "设备1")
        log_func = console_mgr.log_device1 if is_device1 else console_mgr.log_device2

        log_func(f"{'='*60}")
        log_func(f"{device_name} 开始遍历旧版本升级测试")
        log_func(f"{'='*60}")
        log_func(f"串口: {serial_client.port}")
        log_func(f"Web IP: {web_client.router_ip}")
        log_func(f"Bridge IP: {bridge_ip}")
        log_func(f"🎯 分配固件范围: 第 {slice_info} 个固件")
        log_func(f"📦 本设备测试数量: {len(firmware_slice)} 个")
        log_func(f"📊 总固件数量: {len(self.old_firmware_list)} 个")
        log_func(f"新版本: {self.new_version}")
        log_func(f"⚠️  串口持久连接，日志持续记录")
        log_func("")

        start_time = time.time()
        last_cycle_time = start_time  # 记录上一次循环的时间

        # 遍历分配的固件列表（分片）
        total_firmwares = len(firmware_slice)
        for firmware_index, old_firmware_path in enumerate(firmware_slice, 1):
            old_firmware_name = os.path.basename(old_firmware_path)
            # 从文件名提取版本号（假设格式为: 32.3.0.7.ext2）
            old_version = old_firmware_name.replace('.ext2', '').replace('.bin', '').replace('.img', '')

            log_func(f"{'='*60}")
            log_func(f"测试固件 {firmware_index}/{total_firmwares}: {old_firmware_name}")
            log_func(f"{'='*60}")

            try:
                # === 步骤1: 检查串口登录状态 ===
                log_func(f"步骤1: 检查串口登录状态...")
                if not self._ensure_serial_login(serial_client, log_func):
                    raise Exception("串口登录失败")
                log_func(f"✅ 串口已登录")
                log_func("")

                # === 步骤2: 串口烧录旧版本 ===
                log_func(f"步骤2: 串口烧录旧版本 {old_version}...")

                # ⚠️ 关键：在烧录前设置正确的固件文件名
                log_func(f"  设置TFTP固件文件名: {old_firmware_name}")
                serial_client.set_firmware_name(old_firmware_name)

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

                if not web_client.check_firmware_version(old_version):
                    raise Exception(f"版本号验证失败，不是 {old_version}")

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
                log_func(f"✅ 第{firmware_index}个固件测试成功！")
                log_func("")

                # 更新统计
                stats["success"] += 1
                stats["total"] = firmware_index

            except AssertionError as ae:
                # AssertionError表示固件升级失败，需要立即停止测试
                log_func(f"")
                log_func(f"{'='*60}")
                log_func(f"❌❌❌ 致命错误：固件升级失败 ❌❌❌")
                log_func(f"{'='*60}")
                log_func(f"固件: {firmware_index}/{total_firmwares} ({old_firmware_name})")
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
                stats["failed_cycles"].append(firmware_index)
                stats["total"] = firmware_index

                # 重新抛出，停止测试
                raise

            except Exception as e:
                log_func(f"❌ 固件 {firmware_index} ({old_firmware_name}) 失败: {e}")
                stats["failed"] += 1
                stats["failed_cycles"].append(firmware_index)
                stats["total"] = firmware_index

                # ⚠️ 不关闭串口！保持持久连接
                # 只关闭Web浏览器
                try:
                    if web_client.driver:
                        web_client.driver.quit()
                        web_client.driver = None
                except:
                    pass

                continue

            # 输出详细进度统计
            current_time = time.time()
            firmware_time = current_time - last_cycle_time  # 本次固件耗时
            last_cycle_time = current_time

            elapsed = current_time - start_time  # 总耗时
            avg_firmware_time = elapsed / firmware_index  # 平均每个固件耗时
            remaining_firmwares = total_firmwares - firmware_index
            eta_seconds = avg_firmware_time * remaining_firmwares  # 预计剩余时间

            # 计算实时成功率
            success_rate = (stats['success'] / firmware_index * 100) if firmware_index > 0 else 0

            log_func(f"")
            log_func(f"{'─'*60}")
            log_func(f"📊 进度统计 (固件 {firmware_index}/{total_firmwares})")
            log_func(f"{'─'*60}")
            log_func(f"  ✅ 成功: {stats['success']} 个")
            log_func(f"  ❌ 失败: {stats['failed']} 个")
            log_func(f"  📈 成功率: {success_rate:.1f}%")
            log_func(f"  ⏱️  本次耗时: {firmware_time/60:.1f} 分钟")
            log_func(f"  ⏱️  平均耗时: {avg_firmware_time/60:.1f} 分钟/个")
            log_func(f"  ⏳ 总耗时: {elapsed/60:.1f} 分钟 ({elapsed/3600:.1f} 小时)")
            log_func(f"  🔮 预计剩余: {eta_seconds/60:.1f} 分钟 ({eta_seconds/3600:.1f} 小时)")
            log_func(f"  🎯 预计完成: {(elapsed + eta_seconds)/3600:.1f} 小时后")
            log_func(f"{'─'*60}")
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
        """输出详细的统计信息"""
        self.log_info(f"\n{'='*70}")
        self.log_info(f"📊 最终测试统计报告")
        self.log_info(f"{'='*70}\n")

        # 设备1统计
        device1_success_rate = 0
        if self.device1_stats['total'] > 0:
            device1_success_rate = (self.device1_stats['success'] / self.device1_stats['total']) * 100

        self.log_info(f"【设备1】 {self.device1_com_port} → {self.device1_web_ip}")
        self.log_info(f"{'─'*70}")
        self.log_info(f"  🎯 分配固件范围: 第 {self.device1_stats.get('slice_info', '未知')} 个")
        self.log_info(f"  📦 分配固件数量: {self.device1_stats.get('slice_count', 0)} 个")
        self.log_info(f"  📈 实际测试次数: {self.device1_stats['total']} 次")
        self.log_info(f"  ✅ 成功次数: {self.device1_stats['success']}")
        self.log_info(f"  ❌ 失败次数: {self.device1_stats['failed']}")
        self.log_info(f"  📊 成功率: {device1_success_rate:.2f}%")
        if self.device1_stats['failed_cycles']:
            self.log_info(f"  ⚠️  失败的循环: {self.device1_stats['failed_cycles']}")
        self.log_info("")

        # 设备2统计
        device2_success_rate = 0
        if self.device2_stats['total'] > 0:
            device2_success_rate = (self.device2_stats['success'] / self.device2_stats['total']) * 100

        self.log_info(f"【设备2】 {self.device2_com_port} → {self.device2_web_ip}")
        self.log_info(f"{'─'*70}")
        self.log_info(f"  🎯 分配固件范围: 第 {self.device2_stats.get('slice_info', '未知')} 个")
        self.log_info(f"  📦 分配固件数量: {self.device2_stats.get('slice_count', 0)} 个")
        self.log_info(f"  📈 实际测试次数: {self.device2_stats['total']} 次")
        self.log_info(f"  ✅ 成功次数: {self.device2_stats['success']}")
        self.log_info(f"  ❌ 失败次数: {self.device2_stats['failed']}")
        self.log_info(f"  📊 成功率: {device2_success_rate:.2f}%")
        if self.device2_stats['failed_cycles']:
            self.log_info(f"  ⚠️  失败的循环: {self.device2_stats['failed_cycles']}")
        self.log_info("")

        # 汇总
        total_cycles = self.device1_stats['total'] + self.device2_stats['total']
        total_success = self.device1_stats['success'] + self.device2_stats['success']
        total_failed = self.device1_stats['failed'] + self.device2_stats['failed']
        overall_success_rate = 0
        if total_cycles > 0:
            overall_success_rate = (total_success / total_cycles) * 100

        self.log_info(f"【总体统计】")
        self.log_info(f"{'─'*70}")
        self.log_info(f"  🔄 旧版本固件总数: {len(self.old_firmware_list)} 个")
        self.log_info(f"  🎯 总测试次数: {total_success + total_failed} 次")
        self.log_info(f"  ✅ 成功测试: {total_success} 次")
        self.log_info(f"  ❌ 失败测试: {total_failed} 次")
        self.log_info(f"  📊 总体成功率: {overall_success_rate:.2f}%")
        self.log_info("")

        # 效率分析
        if total_cycles > 0:
            self.log_info(f"【效率分析】")
            self.log_info(f"{'─'*70}")
            self.log_info(f"  ⚡ 固件分片优化: 避免重复测试，每个固件只测试1次")
            self.log_info(f"  💪 设备利用率: 100% (两台设备并行工作，分工协作)")
            self.log_info(f"  🚀 效率提升: 相比旧版本（重复测试）节省50%时间")
            self.log_info(f"  🔥 测试覆盖: {len(self.old_firmware_list)} 个固件完整测试")

        self.log_info(f"\n{'='*70}\n")

    def _verify_results(self):
        """验证测试结果（支持固件分片）"""
        # 检查是否有失败
        if self.device1_stats['failed'] > 0 or self.device2_stats['failed'] > 0:
            total_failed = self.device1_stats['failed'] + self.device2_stats['failed']
            raise AssertionError(f"稳定性测试失败: 共有 {total_failed} 个固件测试失败")

        # 检查是否完成了分配的固件测试（固件分片模式）
        device1_expected = self.device1_stats.get('slice_count', 0)
        device2_expected = self.device2_stats.get('slice_count', 0)

        if self.device1_stats['total'] < device1_expected:
            raise AssertionError(
                f"设备1未完成分配的固件测试: "
                f"{self.device1_stats['total']}/{device1_expected} "
                f"(范围: {self.device1_stats.get('slice_info', '未知')})"
            )

        if self.device2_stats['total'] < device2_expected:
            raise AssertionError(
                f"设备2未完成分配的固件测试: "
                f"{self.device2_stats['total']}/{device2_expected} "
                f"(范围: {self.device2_stats.get('slice_info', '未知')})"
            )

        # 验证总测试次数
        total_tested = self.device1_stats['total'] + self.device2_stats['total']
        total_firmwares = len(self.old_firmware_list)
        if total_tested < total_firmwares:
            raise AssertionError(
                f"总测试次数不足: {total_tested}/{total_firmwares} "
                f"(设备1: {self.device1_stats['total']}, 设备2: {self.device2_stats['total']})"
            )

        self.log_info("✅ 稳定性测试通过：所有旧版本固件均成功升级（固件分片优化模式）")


# 测试入口
if __name__ == "__main__":
    from models.test_config import TestConfig, TestMode

    test_config = TestConfig(
        router_config=None,
        test_mode=TestMode.SPECIFIC,
        timeout=300,
        restore_default=False
    )

    test = AllVersionsFirmwareUpgradeStabilityTest(test_config)

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
