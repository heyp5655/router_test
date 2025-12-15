"""
Web固定两版本循环升级稳定性测试

测试ID: 41
测试项: 稳定性
测试点: web固定两版本循环升级稳定性验证

测试流程:
1. 登录路由器（HTTPS响应较慢，增加超时时间）
2. 检查当前固件版本
3. Web上传并升级另一个版本的固件
4. 检测上传过程中是否出现失败提示
5. 验证升级后的版本号
6. 重复步骤3-5，在两个版本之间循环切换100次

关键检测点:
- 上传失败检测: <span class="ys-upload-error"> 包含 "Failed to upload. Please try again"
- 记录每次上传的成功/失败状态
- 统计失败次数和失败率

测试配置:
- 循环次数: 100次
- 版本A: 35.3.0.10 (docs/upload/GD_uploade/A)
- 版本B: 35.3.0.11 (docs/upload/GD_uploade/B)
- 上传超时: 600秒（10分钟）
- 升级后等待时间: 120秒
"""

import os
import time
import glob
from typing import Tuple, Dict, Optional
from test_cases.base_test import BaseTest
from models.test_config import TestConfig, RouterConfig
from core.router_client import RouterClient
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class WebTwoVersionsFirmwareUpgradeStabilityTest(BaseTest):
    """Web固定两版本循环升级稳定性测试"""

    @property
    def test_name(self) -> str:
        return "Web固定两版本循环升级稳定性测试"

    @property
    def description(self) -> str:
        return "在两个固件版本之间通过Web反复升级，检测上传失败情况（100次）"

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
                    model="UR35",
                    incognito_mode=False  # 使用普通模式
                ),
                test_mode=TestMode.SPECIFIC
            )

        self.config = config
        self.router_client = None

        # 状态管理标志
        self._state_saved = False
        self._auto_restore = True

        # 固件配置
        self.version_a = "35.3.0.10"  # 版本A
        self.version_b = "35.3.0.11"  # 版本B
        self.firmware_dir_a = r"E:\GIT\ROUTER_TEST\docs\upload\GD_uploade\A"  # 版本A固件目录
        self.firmware_dir_b = r"E:\GIT\ROUTER_TEST\docs\upload\GD_uploade\B"  # 版本B固件目录

        # 固件文件路径（在setup中初始化）
        self.firmware_path_a = None
        self.firmware_path_b = None

        # 测试配置
        self.upgrade_cycles = 100  # 升级循环次数
        self.upload_timeout = 600  # 上传超时时间（秒）
        self.upgrade_wait_time = 240  # 升级后等待时间（秒）- 路由器完全重启需要更长时间
        self.https_timeout = 30  # HTTPS响应超时（秒）

        # 统计信息
        self.stats = {
            "total": 0,
            "success": 0,
            "upload_failed": 0,  # 上传失败次数
            "upgrade_failed": 0,  # 升级失败次数（版本号未更新）
            "failed_cycles": [],  # 失败的循环编号
            "upload_failure_details": []  # 上传失败详情
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

        # 1. 检查版本A固件文件
        self.log_info(f"步骤1: 检查版本A固件文件 ({self.version_a})...")
        firmware_a = self._get_firmware_file(self.firmware_dir_a, self.version_a)
        if not firmware_a:
            raise Exception(f"版本A固件文件不存在: {self.firmware_dir_a} ({self.version_a})")
        self.firmware_path_a = firmware_a
        self.log_info(f"  ✅ 找到版本A固件: {os.path.basename(firmware_a)}\n")

        # 2. 检查版本B固件文件
        self.log_info(f"步骤2: 检查版本B固件文件 ({self.version_b})...")
        firmware_b = self._get_firmware_file(self.firmware_dir_b, self.version_b)
        if not firmware_b:
            raise Exception(f"版本B固件文件不存在: {self.firmware_dir_b} ({self.version_b})")
        self.firmware_path_b = firmware_b
        self.log_info(f"  ✅ 找到版本B固件: {os.path.basename(firmware_b)}\n")

        # 3. 创建路由器客户端（增加HTTPS超时）
        self.log_info("步骤3: 创建路由器客户端...")
        self.router_client = RouterClient(self.config.router_config)
        # 增加页面加载超时时间，因为HTTPS响应慢
        self.router_client.timeout = self.https_timeout
        self.log_info(f"  ✅ 路由器客户端创建完成（超时: {self.https_timeout}秒）\n")

        # 4. 登录路由器
        self.log_info("步骤4: 登录路由器...")
        self.log_info(f"  ℹ️  HTTPS响应较慢，请耐心等待...")
        if not self.router_client.login_web():
            raise Exception("路由器登录失败")
        self.log_info("  ✅ 路由器登录成功\n")

        # 5. 检查当前版本
        self.log_info("步骤5: 检查当前固件版本...")

        # 尝试检查版本A
        match_a, version_info_a = self.router_client.check_firmware_version(self.version_a)
        if match_a:
            current_version = version_info_a['actual_version']
            self.log_info(f"  ✅ 当前版本: {current_version}")
            self.log_info(f"  ℹ️  当前版本是版本A，将先升级到版本B")
            self.initial_target = "B"
        else:
            # 尝试检查版本B
            match_b, version_info_b = self.router_client.check_firmware_version(self.version_b)
            if match_b:
                current_version = version_info_b['actual_version']
                self.log_info(f"  ✅ 当前版本: {current_version}")
                self.log_info(f"  ℹ️  当前版本是版本B，将先升级到版本A")
                self.initial_target = "A"
            else:
                # 都不匹配，获取实际版本号
                current_version = version_info_a['actual_version'] if version_info_a['actual_version'] else "未知"
                self.log_warning(f"  ⚠️  当前版本 {current_version} 不是预期的版本A或版本B")
                self.log_info(f"     将先升级到版本A")
                self.initial_target = "A"

        self.log_info("")

        self.log_info("="*70)
        self.log_info("测试前置条件检查完成")
        self.log_info("="*70 + "\n")

    def execute(self):
        """执行测试"""
        self.log_info(f"\n{'='*70}")
        self.log_info(f"开始执行稳定性测试")
        self.log_info(f"{'='*70}")
        self.log_info(f"升级模式: 版本A ⇄ 版本B 循环切换")
        self.log_info(f"路由器IP: {self.router_client.router_ip}")
        self.log_info(f"升级循环次数: {self.upgrade_cycles}")
        self.log_info(f"版本A: {self.version_a}")
        self.log_info(f"版本B: {self.version_b}")
        self.log_info(f"⚠️  每次上传都会检测失败提示信息")
        self.log_info(f"🚀 测试开始...\n")

        # 记录开始时间
        start_time = time.time()
        last_cycle_time = start_time

        # 确定初始目标版本
        current_target = self.initial_target

        for cycle in range(1, self.upgrade_cycles + 1):
            self.log_info(f"{'='*70}")
            self.log_info(f"升级循环 {cycle}/{self.upgrade_cycles}")
            self.log_info(f"{'='*70}")

            # 确定目标版本和固件路径
            if current_target == "A":
                target_version = self.version_a
                firmware_path = self.firmware_path_a
                self.log_info(f"目标版本: A ({self.version_a})")
            else:
                target_version = self.version_b
                firmware_path = self.firmware_path_b
                self.log_info(f"目标版本: B ({self.version_b})")

            try:
                # === 步骤1: Web上传并升级固件 ===
                self.log_info(f"\n步骤1: Web上传并升级固件 {target_version}...")
                self.log_info(f"  固件文件: {os.path.basename(firmware_path)}")
                self.log_info(f"  🔄 开始固件上传流程...")
                self.log_info(f"     1) 跳转到升级页面")
                self.log_info(f"     2) 选择固件文件")
                self.log_info(f"     3) 检测上传失败提示")
                self.log_info(f"     4) 等待文件上传完成")
                self.log_info(f"     5) 确认升级对话框")
                self.log_info(f"     6) 等待路由器重启")
                self.log_info(f"  ⏳ 预计总耗时: 约10-15分钟，请耐心等待...")
                self.log_info("")

                # 使用改进的上传方法，带上传失败检测
                upload_success, upload_failed = self._upload_and_upgrade_with_check(
                    firmware_path,
                    target_version
                )

                if upload_failed:
                    # 上传失败
                    self.log_error(f"❌ 循环 {cycle}: 固件上传失败")
                    self.stats["upload_failed"] += 1
                    self.stats["failed_cycles"].append(cycle)
                    self.stats["total"] = cycle

                    # 记录失败详情
                    self.stats["upload_failure_details"].append({
                        "cycle": cycle,
                        "target_version": target_version,
                        "reason": "上传失败: Failed to upload. Please try again"
                    })

                    # 上传失败，不切换目标版本，下次重试相同版本
                    self.log_warning(f"  ⚠️  下次循环将重试升级到相同版本")
                    continue

                if not upload_success:
                    # 上传过程出错
                    self.log_error(f"❌ 循环 {cycle}: 固件上传过程出错")
                    self.stats["upgrade_failed"] += 1
                    self.stats["failed_cycles"].append(cycle)
                    self.stats["total"] = cycle

                    # 关闭浏览器，重新登录
                    self._relogin()
                    continue

                self.log_info(f"✅ 固件上传完成，路由器已开始重启")
                self.log_info("")

                # === 步骤2: 等待路由器重启并重新登录 ===
                self.log_info(f"步骤2: 等待路由器重启...")
                self.log_info(f"  ⏳ 等待 {self.upgrade_wait_time} 秒...")
                time.sleep(self.upgrade_wait_time)

                self.log_info(f"\n步骤3: 重新登录路由器...")
                if not self._relogin():
                    raise Exception("升级后重新登录失败")
                self.log_info(f"✅ 重新登录成功")
                self.log_info("")

                # === 步骤3: 验证版本号 ===
                self.log_info(f"步骤4: 验证固件版本...")
                match, version_info = self.router_client.check_firmware_version(target_version)

                self.log_info(f"  期望版本: {version_info['expected_version']}")
                self.log_info(f"  实际版本: {version_info['actual_version']}")

                if not match:
                    self.log_error(f"❌ 版本号验证失败！")
                    self.log_error(f"   期望: {target_version}, 实际: {version_info['actual_version']}")
                    self.stats["upgrade_failed"] += 1
                    self.stats["failed_cycles"].append(cycle)
                    self.stats["total"] = cycle

                    # 记录失败详情
                    self.stats["upload_failure_details"].append({
                        "cycle": cycle,
                        "target_version": target_version,
                        "reason": f"版本验证失败: 期望 {target_version}, 实际 {version_info['actual_version']}"
                    })

                    continue

                self.log_info(f"✅ 版本验证成功")
                self.log_info(f"✅ 第{cycle}次升级成功！")
                self.log_info("")

                # 更新统计
                self.stats["success"] += 1
                self.stats["total"] = cycle

                # 切换目标版本
                current_target = "A" if current_target == "B" else "B"

            except Exception as e:
                self.log_error(f"❌ 循环 {cycle} 失败: {e}")
                self.stats["upgrade_failed"] += 1
                self.stats["failed_cycles"].append(cycle)
                self.stats["total"] = cycle

                # 记录失败详情
                self.stats["upload_failure_details"].append({
                    "cycle": cycle,
                    "target_version": target_version,
                    "reason": str(e)
                })

                # 尝试重新登录
                try:
                    self._relogin()
                except:
                    pass

                continue

            # 输出详细进度统计
            current_time = time.time()
            cycle_time = current_time - last_cycle_time
            last_cycle_time = current_time

            elapsed = current_time - start_time
            avg_cycle_time = elapsed / cycle
            remaining_cycles = self.upgrade_cycles - cycle
            eta_seconds = avg_cycle_time * remaining_cycles

            # 计算实时成功率
            success_rate = (self.stats['success'] / cycle * 100) if cycle > 0 else 0

            self.log_info(f"")
            self.log_info(f"{'─'*70}")
            self.log_info(f"📊 进度统计 (循环 {cycle}/{self.upgrade_cycles})")
            self.log_info(f"{'─'*70}")
            self.log_info(f"  ✅ 成功: {self.stats['success']} 次")
            self.log_info(f"  ❌ 上传失败: {self.stats['upload_failed']} 次")
            self.log_info(f"  ❌ 升级失败: {self.stats['upgrade_failed']} 次")
            self.log_info(f"  ❌ 总失败: {self.stats['upload_failed'] + self.stats['upgrade_failed']} 次")
            self.log_info(f"  📈 成功率: {success_rate:.1f}%")
            self.log_info(f"  ⏱️  本次耗时: {cycle_time/60:.1f} 分钟")
            self.log_info(f"  ⏱️  平均耗时: {avg_cycle_time/60:.1f} 分钟/次")
            self.log_info(f"  ⏳ 总耗时: {elapsed/60:.1f} 分钟 ({elapsed/3600:.1f} 小时)")
            self.log_info(f"  🔮 预计剩余: {eta_seconds/60:.1f} 分钟 ({eta_seconds/3600:.1f} 小时)")
            self.log_info(f"  🎯 预计完成: {(elapsed + eta_seconds)/3600:.1f} 小时后")
            self.log_info(f"{'─'*70}")
            self.log_info("")

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

        # 关闭路由器客户端
        if self.router_client:
            try:
                self.router_client.close()
            except:
                pass

        self.log_info(f"\n✅ {self.test_name} 清理完成\n")

    def _get_firmware_file(self, directory: str, version: str = None) -> Optional[str]:
        """
        从目录中获取固件文件

        Args:
            directory: 固件目录路径
            version: 固件版本号（可选，用于匹配文件名）

        Returns:
            固件文件路径，如果未找到返回None
        """
        extensions = ['*.bin', '*.img', '*.tar', '*.tar.gz', '*.zip', '*.ext2']

        for ext in extensions:
            pattern = os.path.join(directory, ext)
            files = glob.glob(pattern)

            # 如果指定了版本号，优先查找包含版本号的文件
            if version and files:
                for file in files:
                    if version in os.path.basename(file):
                        return file

            # 如果没有指定版本号，或者没找到匹配版本的文件，返回第一个
            if files:
                return files[0]

        return None

    def _upload_and_upgrade_with_check(self, firmware_path: str, expected_version: str) -> Tuple[bool, bool]:
        """
        Web上传固件并检测上传失败提示

        Args:
            firmware_path: 固件文件路径
            expected_version: 期望的版本号

        Returns:
            Tuple[bool, bool]: (上传成功, 上传失败标志)
                - (True, False): 上传成功
                - (False, True): 上传失败（检测到失败提示）
                - (False, False): 上传过程出错
        """
        try:
            driver = self.router_client.driver

            # 1. 跳转到升级页面
            self.log_info("  跳转到升级页面...")
            upgrade_url = f"https://{self.router_client.router_ip}/#maintenance/upgrade/upgrade"
            driver.get(upgrade_url)
            time.sleep(2)

            # 强制刷新页面，避免页面空白
            self.log_info("  强制刷新页面（F5）...")
            driver.refresh()
            time.sleep(3)

            # 2. 选择固件文件
            self.log_info(f"  选择固件文件: {os.path.basename(firmware_path)}")
            try:
                file_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                )
                file_input.send_keys(firmware_path)
                time.sleep(2)
            except TimeoutException:
                self.log_error("  ❌ 未找到文件上传输入框")
                return False, False

            # 3. 点击升级按钮
            self.log_info("  点击升级按钮...")
            try:
                upgrade_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Upgrade') or contains(text(), '升级')]"))
                )
                upgrade_button.click()
                time.sleep(2)
            except TimeoutException:
                self.log_error("  ❌ 未找到升级按钮")
                return False, False

            # 4. 等待文件上传并开始升级
            self.log_info("  等待文件上传...")
            self.log_info("  ⚠️  固件上传后路由器会自动重启")

            # 点击升级后，等待页面响应或超时
            upload_timeout = 600  # 最多等待10分钟
            check_interval = 10  # 每10秒检查一次
            upload_start_time = time.time()

            page_changed = False  # 页面是否已变化（路由器重启标志）

            for i in range(0, upload_timeout, check_interval):
                elapsed = int(time.time() - upload_start_time)
                remaining = upload_timeout - elapsed
                minutes = remaining // 60
                seconds = remaining % 60
                elapsed_minutes = elapsed // 60
                elapsed_seconds = elapsed % 60

                # 输出进度
                if minutes > 0:
                    self.log_info(f"  ⏳ 等待中... 已等待 {elapsed_minutes}分{elapsed_seconds}秒 | 最多还等 {minutes}分{seconds}秒")
                else:
                    self.log_info(f"  ⏳ 等待中... 已等待 {elapsed_minutes}分{elapsed_seconds}秒 | 最多还等 {seconds}秒")

                # 检查上传失败提示
                try:
                    error_span = driver.find_element(By.CSS_SELECTOR, "span.ys-upload-error")
                    error_text = error_span.text

                    if "Failed to upload. Please try again" in error_text:
                        self.log_error("  ❌ 检测到上传失败提示: Failed to upload. Please try again")
                        return False, True
                except:
                    pass

                # 检测页面是否还能访问（如果路由器重启，页面会断开）
                try:
                    # 尝试获取页面title，如果路由器重启，这个操作会失败
                    _ = driver.title
                    # 检查URL是否发生变化
                    current_url = driver.current_url
                    if "login" in current_url or current_url == "data:,":
                        self.log_info("  ✅ 检测到路由器重启（页面已断开）")
                        page_changed = True
                        break
                except:
                    # 页面无法访问，说明路由器已重启
                    self.log_info("  ✅ 检测到路由器重启（页面无法访问）")
                    page_changed = True
                    break

                time.sleep(check_interval)

            if not page_changed:
                self.log_warning(f"  ⚠️  等待{upload_timeout}秒未检测到路由器重启，继续尝试...")

            self.log_info("  ✅ 固件上传完成，路由器已开始重启")

            return True, False

        except Exception as e:
            self.log_error(f"  ❌ 上传过程出错: {e}")
            return False, False

    def _relogin(self) -> bool:
        """
        重新登录路由器

        Returns:
            bool: 登录成功返回True，失败返回False
        """
        try:
            # 关闭浏览器
            if self.router_client.driver:
                try:
                    self.router_client.driver.quit()
                except:
                    pass
                self.router_client.driver = None

            # 等待一段时间
            time.sleep(5)

            # 重新登录
            return self.router_client.login_web()

        except Exception as e:
            self.log_error(f"  ❌ 重新登录失败: {e}")
            return False

    def _print_statistics(self):
        """输出详细的统计信息"""
        self.log_info(f"\n{'='*70}")
        self.log_info(f"📊 最终测试统计报告")
        self.log_info(f"{'='*70}\n")

        # 计算成功率
        success_rate = 0
        if self.stats['total'] > 0:
            success_rate = (self.stats['success'] / self.stats['total']) * 100

        # 计算失败率
        total_failed = self.stats['upload_failed'] + self.stats['upgrade_failed']
        fail_rate = 0
        if self.stats['total'] > 0:
            fail_rate = (total_failed / self.stats['total']) * 100

        self.log_info(f"【总体统计】")
        self.log_info(f"{'─'*70}")
        self.log_info(f"  🔄 总循环次数: {self.stats['total']}")
        self.log_info(f"  ✅ 成功次数: {self.stats['success']}")
        self.log_info(f"  ❌ 上传失败: {self.stats['upload_failed']}")
        self.log_info(f"  ❌ 升级失败: {self.stats['upgrade_failed']}")
        self.log_info(f"  ❌ 总失败次数: {total_failed}")
        self.log_info(f"  📊 成功率: {success_rate:.2f}%")
        self.log_info(f"  📊 失败率: {fail_rate:.2f}%")
        self.log_info("")

        # 输出失败的循环
        if self.stats['failed_cycles']:
            self.log_info(f"【失败的循环】")
            self.log_info(f"{'─'*70}")
            self.log_info(f"  ⚠️  失败循环编号: {self.stats['failed_cycles']}")
            self.log_info("")

        # 输出失败详情
        if self.stats['upload_failure_details']:
            self.log_info(f"【失败详情】")
            self.log_info(f"{'─'*70}")
            for detail in self.stats['upload_failure_details']:
                self.log_info(f"  循环 {detail['cycle']}: {detail['reason']}")
            self.log_info("")

        self.log_info(f"{'='*70}\n")

    def _verify_results(self):
        """验证测试结果"""
        total_failed = self.stats['upload_failed'] + self.stats['upgrade_failed']

        # 检查是否有失败
        if total_failed > 0:
            fail_rate = (total_failed / self.stats['total']) * 100
            raise AssertionError(
                f"稳定性测试失败: 共有 {total_failed} 次失败 "
                f"(上传失败: {self.stats['upload_failed']}, 升级失败: {self.stats['upgrade_failed']}, "
                f"失败率: {fail_rate:.2f}%)"
            )

        # 检查是否完成了所有循环
        if self.stats['total'] < self.upgrade_cycles:
            raise AssertionError(f"未完成所有循环: {self.stats['total']}/{self.upgrade_cycles}")

        self.log_info("✅ 稳定性测试通过：所有升级循环均成功完成，无上传失败")


# 测试入口
if __name__ == "__main__":
    from models.test_config import TestConfig, TestMode

    test_config = TestConfig(
        router_config=RouterConfig(
            router_ip="192.168.50.17",
            username="admin",
            password="password",
            model="UR35",
            incognito_mode=False  # 使用普通模式
        ),
        test_mode=TestMode.SPECIFIC,
        timeout=300,
        restore_default=False
    )

    test = WebTwoVersionsFirmwareUpgradeStabilityTest(test_config)

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
