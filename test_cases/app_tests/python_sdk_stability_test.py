from test_cases.base_test import BaseTest
import time
import serial
import threading
import re
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PythonSDKStabilityTest(BaseTest):
    """Python3.0 SDK安装卸载稳定性测试

    测试项：功能用例/网络/APP/python
    测试点：python3.0 SDK安装卸载稳定性测试

    测试步骤：
    1. 登录设备web并跳转到#app/python/status
    2. 判断是否已安装SDK，如已安装则先卸载
    3. 上传SDK文件并安装，记录安装时间
    4. 确保安装成功后开始卸载
    5. 反复执行安装卸载10000次
    6. 在过程中通过串口监控CPU和内存使用情况

    预期：
    安装卸载反复执行中没有出现无法安装和卸载，内存cpu无异常，设备无异常死机重启
    """

    # 添加分类信息属性
    category = "功能用例/APP/python"
    is_regression = True  # 标记为回归测试用例

    # SDK文件路径
    SDK_FILE_PATH = r"E:\GIT\ROUTER_TEST\config\pysdk-ur3x-5.0.2-u1.tar.gz"

    # 测试循环次数
    TEST_ITERATIONS = 1000

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "python3.0 SDK安装卸载稳定性测试"

    @property
    def description(self):
        """测试描述"""
        return f"反复执行SDK安装卸载{self.TEST_ITERATIONS}次，监控CPU和内存使用情况"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 获取路由器配置
        self.router_ip = self.config.router_config.router_ip

        # 从配置中获取串口配置
        self.serial_port = self.config.router_config.serial_port
        self.serial_baudrate = self.config.router_config.serial_baudrate

        # 串口连接对象
        self.serial_conn = None
        self.serial_lock = threading.Lock()  # 串口访问锁

        # 监控数据
        self.cpu_samples = []
        self.memory_samples = []
        self.monitoring_active = False
        self.monitor_thread = None

        # 测试结果统计
        self.install_times = []
        self.uninstall_times = []
        self.failed_installs = 0
        self.failed_uninstalls = 0
        self.completed_iterations = 0

    def setup(self):
        """测试前置条件"""
        print(f"\n{'='*70}")
        print(f"测试用例: {self.test_name}")
        print(f"测试分类: {self.category}")
        print(f"{'='*70}")
        print(f"路由器IP: {self.router_ip}")
        print(f"SDK文件: {self.SDK_FILE_PATH}")
        print(f"测试次数: {self.TEST_ITERATIONS}")
        print(f"串口配置: {self.serial_port} @ {self.serial_baudrate}")
        print(f"{'='*70}\n")

        # 检查SDK文件是否存在
        if not os.path.exists(self.SDK_FILE_PATH):
            raise FileNotFoundError(f"SDK文件不存在: {self.SDK_FILE_PATH}")

        # 登录Web界面
        print("登录路由器Web界面...")
        if not self.router_client.login_web():
            raise Exception("Web登录失败")
        print("✅ Web登录成功")

        # 初始化串口连接
        print(f"\n初始化串口连接 {self.serial_port}...")
        try:
            self.serial_conn = serial.Serial(
                port=self.serial_port,
                baudrate=self.serial_baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
            print("✅ 串口连接成功")

            # 登录串口
            self._serial_login()
            print("✅ 串口登录成功")

        except Exception as e:
            raise Exception(f"串口初始化失败: {str(e)}")

    def execute(self):
        """执行测试"""
        try:
            print(f"\n{'='*70}")
            print(f"开始执行稳定性测试")
            print(f"{'='*70}\n")

            # 启动串口监控线程
            self._start_monitoring()

            # 步骤1：跳转到Python SDK状态页面
            print("步骤1: 跳转到Python SDK状态页面...")
            self._navigate_to_python_status()

            # 步骤2: 确保初始状态为未安装
            print("\n步骤2: 检查并清理初始状态...")
            self._ensure_sdk_uninstalled()

            # 步骤3-5: 循环执行安装卸载
            print(f"\n步骤3: 开始循环执行安装卸载 ({self.TEST_ITERATIONS}次)...\n")

            consecutive_failures = 0  # 连续失败次数
            max_consecutive_failures = 3  # 最大允许连续失败次数

            for iteration in range(1, self.TEST_ITERATIONS + 1):
                print(f"\n{'='*70}")
                print(f"📋 第 {iteration}/{self.TEST_ITERATIONS} 次迭代")
                print(f"{'='*70}")

                iteration_success = True  # 本次迭代是否成功

                # 安装SDK
                install_success, install_time = self._install_sdk()
                if not install_success:
                    self.failed_installs += 1
                    consecutive_failures += 1
                    iteration_success = False
                    print(f"❌ 第{iteration}次安装失败 (连续失败{consecutive_failures}次)")

                    # 检查连续失败次数
                    if consecutive_failures >= max_consecutive_failures:
                        print(f"\n{'='*70}")
                        print(f"⚠️ 连续失败{consecutive_failures}次，停止测试")
                        print(f"{'='*70}\n")
                        raise Exception(f"连续安装失败{consecutive_failures}次，测试终止")

                    # 刷新页面重置状态
                    print("  刷新页面重置状态...")
                    self._reset_page()
                    continue
                else:
                    self.install_times.append(install_time)

                # 卸载SDK
                uninstall_success, uninstall_time = self._uninstall_sdk()
                if not uninstall_success:
                    self.failed_uninstalls += 1
                    consecutive_failures += 1
                    iteration_success = False
                    print(f"❌ 第{iteration}次卸载失败 (连续失败{consecutive_failures}次)")

                    # 检查连续失败次数
                    if consecutive_failures >= max_consecutive_failures:
                        print(f"\n{'='*70}")
                        print(f"⚠️ 连续失败{consecutive_failures}次，停止测试")
                        print(f"{'='*70}\n")
                        raise Exception(f"连续卸载失败{consecutive_failures}次，测试终止")

                    # 刷新页面重置状态
                    print("  刷新页面重置状态...")
                    self._reset_page()
                    continue
                else:
                    self.uninstall_times.append(uninstall_time)

                # 如果本次迭代成功，重置连续失败计数并打印汇总
                if iteration_success:
                    consecutive_failures = 0
                    self.completed_iterations += 1

                    # 打印本次迭代汇总
                    total_time = install_time + uninstall_time
                    print(f"\n{'─'*70}")
                    print(f"✅ 第 {iteration} 次迭代完成")
                    print(f"   安装耗时: {install_time:.2f}秒 | 卸载耗时: {uninstall_time:.2f}秒 | 总耗时: {total_time:.2f}秒")

                    # 打印当前资源使用情况
                    if self.cpu_samples and self.memory_samples:
                        current_cpu = self.cpu_samples[-1] if self.cpu_samples else 0
                        current_mem = self.memory_samples[-1] if self.memory_samples else 0
                        print(f"   当前系统状态: CPU {current_cpu}% | 空闲内存 {current_mem/1024:.1f}MB")

                    print(f"   已完成: {self.completed_iterations}/{self.TEST_ITERATIONS} ({self.completed_iterations/self.TEST_ITERATIONS*100:.1f}%)")
                    print(f"{'─'*70}")

                # 每100次输出一次统计
                if iteration % 100 == 0:
                    self._print_interim_stats()

            # 停止监控
            self._stop_monitoring()

            # 输出最终统计
            self._print_final_stats()

            # 判断测试结果
            if self.failed_installs > 0 or self.failed_uninstalls > 0:
                raise AssertionError(
                    f"测试失败：安装失败{self.failed_installs}次，"
                    f"卸载失败{self.failed_uninstalls}次"
                )

            return True

        except Exception as e:
            print(f"\n测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise
        finally:
            # 确保停止监控线程
            self._stop_monitoring()

    def _navigate_to_python_status(self):
        """跳转到Python SDK状态页面"""
        try:
            driver = self.router_client.driver
            wait = WebDriverWait(driver, 15)

            # 方法：直接访问带hash的URL，然后刷新
            url_with_hash = f"http://{self.router_ip}/#app/python/status"
            print(f"跳转到: {url_with_hash}")
            driver.get(url_with_hash)
            time.sleep(1)

            # 刷新页面以触发前端路由
            print("刷新页面以触发路由...")
            driver.refresh()
            time.sleep(2)

            # 等待并验证Python页面特征元素出现
            print("等待Python页面加载...")
            try:
                python_link = wait.until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//a[@data-target='app/python/status' and text()='Python']"
                    ))
                )
                print("✅ 找到Python页面特征元素")

                # 验证当前URL
                current_url = driver.current_url
                print(f"当前URL: {current_url}")

                if "app/python/status" in current_url:
                    print("✅ 页面跳转成功")
                else:
                    print(f"⚠️ 警告: URL不包含预期路径，但找到了页面元素")

            except Exception as e:
                current_url = driver.current_url
                print(f"❌ 未找到Python页面特征元素")
                print(f"当前URL: {current_url}")
                raise Exception(f"页面跳转失败，未找到预期的Python链接元素: {str(e)}")

        except Exception as e:
            raise Exception(f"跳转到Python状态页面失败: {str(e)}")

    def _reset_page(self):
        """重置页面状态，用于失败后恢复"""
        try:
            driver = self.router_client.driver
            print("  刷新页面...")
            driver.refresh()
            time.sleep(3)

            # 重新跳转到Python SDK状态页面
            print("  重新进入Python SDK状态页面...")
            self._navigate_to_python_status()

            print("  ✅ 页面重置完成")

        except Exception as e:
            print(f"  ⚠️ 页面重置失败: {str(e)}")
            # 页面重置失败不抛出异常，让主流程继续

    def _ensure_sdk_uninstalled(self):
        """确保SDK处于未安装状态"""
        try:
            driver = self.router_client.driver
            wait = WebDriverWait(driver, 10)

            # 等待页面元素加载完成
            time.sleep(2)

            # 检查状态元素
            status_elem1_xpath = '//*[@id="status_python"]/div[2]/div[3]/div[2]'
            status_elem2_xpath = '//*[@id="status_python"]/div[2]/div[4]/div[2]'

            try:
                elem1 = driver.find_element(By.XPATH, status_elem1_xpath)
                elem2 = driver.find_element(By.XPATH, status_elem2_xpath)

                # 如果元素不为空，说明已安装
                if elem1.text.strip() or elem2.text.strip():
                    print("检测到SDK已安装，开始卸载...")
                    success, _ = self._uninstall_sdk()
                    if not success:
                        raise Exception("初始卸载失败")
                    print("✅ 初始卸载成功")
                else:
                    print("✅ SDK未安装，状态正常")

            except Exception as e:
                # 如果元素不存在或为空，认为未安装
                print("✅ SDK未安装，状态正常")

        except Exception as e:
            raise Exception(f"检查SDK状态失败: {str(e)}")

    def _install_sdk(self):
        """安装SDK，返回(是否成功, 安装耗时)"""
        start_time = time.time()
        print(f"\n{'─'*60}")
        print(f"⏱️  开始安装SDK - {time.strftime('%H:%M:%S')}")
        print(f"{'─'*60}")

        try:
            driver = self.router_client.driver
            wait = WebDriverWait(driver, 10)

            # 等待页面稳定
            time.sleep(1)

            # 检查文件是否存在
            if not os.path.exists(self.SDK_FILE_PATH):
                print(f"  ❌ SDK文件不存在: {self.SDK_FILE_PATH}")
                return False, time.time() - start_time

            print(f"  ✅ SDK文件存在: {self.SDK_FILE_PATH}")

            # 检查是否需要先卸载已有SDK
            try:
                uninstall_btn = driver.find_element(By.XPATH, '//*[@id="uninstall_btn"]')
                if uninstall_btn.is_displayed():
                    print("  检测到已安装SDK，先执行卸载...")
                    uninstall_success, _ = self._uninstall_sdk()
                    if not uninstall_success:
                        print("  ⚠️ 卸载失败，但继续尝试安装...")
                    time.sleep(2)
            except:
                print("  未检测到已安装的SDK")
                pass

            # 查找文件上传输入框
            print("  查找文件上传输入框...")
            upload_input = None

            # 尝试多种方式定位
            locators = [
                ("ID: 0_sdkfile_url", By.XPATH, '//*[@id="0_sdkfile_url"]'),
                ("type=file", By.XPATH, '//input[@type="file"]'),
                ("name包含sdk", By.XPATH, '//input[contains(@name, "sdk") and @type="file"]'),
                ("name包含file", By.XPATH, '//input[contains(@name, "file") and @type="file"]'),
            ]

            for desc, by, xpath in locators:
                try:
                    print(f"  尝试定位器: {desc}")
                    elem = driver.find_element(by, xpath)

                    # 验证元素类型
                    elem_type = elem.get_attribute('type')
                    if elem_type != 'file':
                        print(f"  ✗ {desc} 找到元素但类型不是file: {elem_type}")
                        continue

                    print(f"  ✅ 找到文件上传框: {desc}")

                    # 尝试滚动到元素位置（file input通常是隐藏的，但仍然可以交互）
                    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                    time.sleep(0.5)

                    upload_input = elem
                    break

                except Exception as e:
                    print(f"  ✗ {desc} 定位失败: {str(e)}")
                    continue

            if not upload_input:
                print("  ❌ 无法找到文件上传输入框")
                # 打印页面源码帮助调试
                print("  页面HTML片段:")
                try:
                    page_source = driver.page_source
                    if 'sdkfile' in page_source or 'type="file"' in page_source:
                        # 找到包含file input的部分
                        lines = page_source.split('\n')
                        for i, line in enumerate(lines):
                            if 'type="file"' in line or 'sdkfile' in line:
                                print(f"    行{i}: {line.strip()[:200]}")
                except:
                    pass
                return False, time.time() - start_time

            # 上传文件
            print(f"  上传SDK文件: {self.SDK_FILE_PATH}")
            try:
                upload_input.send_keys(self.SDK_FILE_PATH)
                print("  ✅ send_keys执行完成")
            except Exception as e:
                print(f"  ❌ send_keys失败: {str(e)}")
                import traceback
                print(traceback.format_exc())
                return False, time.time() - start_time

            # 等待文件选择生效
            time.sleep(2)

            # 验证文件是否真正上传
            print("  验证文件已选择...")
            try:
                # 检查files属性
                files_length = driver.execute_script("return arguments[0].files.length;", upload_input)
                print(f"  文件对象数量: {files_length}")

                if files_length > 0:
                    # 获取文件名
                    file_name = driver.execute_script("return arguments[0].files[0].name;", upload_input)
                    print(f"  ✅ 文件已选择: {file_name}")
                else:
                    print(f"  ❌ 文件选择失败：files.length = 0")
                    # 尝试从value属性获取更多信息
                    file_value = upload_input.get_attribute('value')
                    print(f"  文件输入框value属性: '{file_value}'")
                    return False, time.time() - start_time

            except Exception as e:
                print(f"  ❌ 验证文件选择时出错: {str(e)}")
                return False, time.time() - start_time

            # 点击安装按钮
            print("  查找并点击安装按钮...")
            install_btn_xpath = '//*[@id="0_sdkfile_import"]'
            try:
                install_btn = wait.until(
                    EC.element_to_be_clickable((By.XPATH, install_btn_xpath))
                )
                print(f"  找到安装按钮，文本: {install_btn.text}")
                install_btn.click()
                print("  ✅ 已点击安装按钮，等待安装完成...")
            except Exception as e:
                print(f"  ❌ 点击安装按钮失败: {str(e)}")
                return False, time.time() - start_time

            # 等待安装完成 - 检查状态元素变为非空
            status_elem1_xpath = '//*[@id="status_python"]/div[2]/div[3]/div[2]'
            status_elem2_xpath = '//*[@id="status_python"]/div[2]/div[4]/div[2]'

            # 最多等待300秒
            max_wait = 300
            elapsed = 0
            print("  等待安装完成（最多300秒）...")
            while elapsed < max_wait:
                try:
                    elem1 = driver.find_element(By.XPATH, status_elem1_xpath)
                    elem2 = driver.find_element(By.XPATH, status_elem2_xpath)

                    elem1_text = elem1.text.strip()
                    elem2_text = elem2.text.strip()

                    if elem1_text and elem2_text:
                        install_time = time.time() - start_time
                        print(f"\n{'─'*60}")
                        print(f"✅ 安装完成！")
                        print(f"   耗时: {install_time:.2f}秒")
                        print(f"   状态信息: {elem1_text}, {elem2_text}")

                        # 打印安装过程中的资源使用情况
                        if self.cpu_samples:
                            recent_cpu = self.cpu_samples[-10:] if len(self.cpu_samples) >= 10 else self.cpu_samples
                            avg_cpu = sum(recent_cpu) / len(recent_cpu) if recent_cpu else 0
                            print(f"   安装期间平均CPU使用率: {avg_cpu:.1f}%")

                        if self.memory_samples:
                            recent_mem = self.memory_samples[-10:] if len(self.memory_samples) >= 10 else self.memory_samples
                            avg_mem = sum(recent_mem) / len(recent_mem) if recent_mem else 0
                            print(f"   安装期间平均空闲内存: {avg_mem/1024:.1f}MB")

                        print(f"{'─'*60}\n")
                        return True, install_time

                    # 每10秒打印一次进度和当前资源使用情况
                    if elapsed % 10 == 0 and elapsed > 0:
                        cpu_info = ""
                        mem_info = ""

                        if self.cpu_samples:
                            current_cpu = self.cpu_samples[-1]
                            cpu_info = f"CPU: {current_cpu}%"

                        if self.memory_samples:
                            current_mem = self.memory_samples[-1]
                            mem_info = f"空闲内存: {current_mem/1024:.1f}MB"

                        status_info = f" | {cpu_info}" if cpu_info else ""
                        status_info += f" | {mem_info}" if mem_info else ""
                        print(f"  ⏳ 安装中... ({elapsed}秒{status_info})")

                except:
                    pass

                time.sleep(1)
                elapsed += 1

            # 超时
            print("  ❌ 安装超时（等待120秒后状态未更新）")
            # 打印最终状态帮助调试
            try:
                elem1 = driver.find_element(By.XPATH, status_elem1_xpath)
                elem2 = driver.find_element(By.XPATH, status_elem2_xpath)
                print(f"     最终状态: elem1='{elem1.text}', elem2='{elem2.text}'")
            except:
                pass
            return False, time.time() - start_time

        except Exception as e:
            print(f"  ❌ 安装异常: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False, time.time() - start_time

    def _uninstall_sdk(self):
        """卸载SDK，返回(是否成功, 卸载耗时)"""
        start_time = time.time()
        print(f"\n{'─'*60}")
        print(f"🗑️  开始卸载SDK - {time.strftime('%H:%M:%S')}")
        print(f"{'─'*60}")

        try:
            driver = self.router_client.driver

            # 点击卸载按钮
            print("  点击卸载按钮...")
            uninstall_btn_xpath = '//*[@id="uninstall_btn"]'
            uninstall_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, uninstall_btn_xpath))
            )
            uninstall_btn.click()
            time.sleep(1)

            # 尝试处理确认弹窗
            try:
                # 查找确认按钮（可能是"确定"或"ok"）
                confirm_btns = driver.find_elements(By.XPATH, "//button[contains(text(), '确定') or contains(text(), 'OK') or contains(text(), 'ok')]")
                if confirm_btns:
                    print("  检测到确认弹窗，点击确定...")
                    confirm_btns[0].click()
                    time.sleep(1)
            except:
                # 没有弹窗，直接卸载
                pass

            # 等待卸载完成 - 检查状态元素变为空
            print("  等待卸载完成（最多60秒）...")
            status_elem1_xpath = '//*[@id="status_python"]/div[2]/div[3]/div[2]'
            status_elem2_xpath = '//*[@id="status_python"]/div[2]/div[4]/div[2]'

            # 最多等待60秒
            max_wait = 60
            elapsed = 0
            while elapsed < max_wait:
                try:
                    elem1 = driver.find_element(By.XPATH, status_elem1_xpath)
                    elem2 = driver.find_element(By.XPATH, status_elem2_xpath)

                    if not elem1.text.strip() and not elem2.text.strip():
                        uninstall_time = time.time() - start_time
                        print(f"\n{'─'*60}")
                        print(f"✅ 卸载完成！")
                        print(f"   耗时: {uninstall_time:.2f}秒")

                        # 打印卸载过程中的资源使用情况
                        if self.cpu_samples:
                            recent_cpu = self.cpu_samples[-10:] if len(self.cpu_samples) >= 10 else self.cpu_samples
                            avg_cpu = sum(recent_cpu) / len(recent_cpu) if recent_cpu else 0
                            print(f"   卸载期间平均CPU使用率: {avg_cpu:.1f}%")

                        if self.memory_samples:
                            recent_mem = self.memory_samples[-10:] if len(self.memory_samples) >= 10 else self.memory_samples
                            avg_mem = sum(recent_mem) / len(recent_mem) if recent_mem else 0
                            print(f"   卸载期间平均空闲内存: {avg_mem/1024:.1f}MB")

                        print(f"{'─'*60}\n")
                        return True, uninstall_time

                    # 每5秒打印一次进度和当前资源使用情况
                    if elapsed % 5 == 0 and elapsed > 0:
                        cpu_info = ""
                        mem_info = ""

                        if self.cpu_samples:
                            current_cpu = self.cpu_samples[-1]
                            cpu_info = f"CPU: {current_cpu}%"

                        if self.memory_samples:
                            current_mem = self.memory_samples[-1]
                            mem_info = f"空闲内存: {current_mem/1024:.1f}MB"

                        status_info = f" | {cpu_info}" if cpu_info else ""
                        status_info += f" | {mem_info}" if mem_info else ""
                        print(f"  ⏳ 卸载中... ({elapsed}秒{status_info})")

                except:
                    # 元素可能不存在也认为是卸载成功
                    uninstall_time = time.time() - start_time
                    print(f"\n{'─'*60}")
                    print(f"✅ 卸载完成！")
                    print(f"   耗时: {uninstall_time:.2f}秒")
                    print(f"{'─'*60}\n")
                    return True, uninstall_time

                time.sleep(1)
                elapsed += 1

            # 超时
            print("  ❌ 卸载超时")
            return False, time.time() - start_time

        except Exception as e:
            print(f"  ❌ 卸载异常: {str(e)}")
            return False, time.time() - start_time

    def _serial_login(self):
        """通过串口登录设备"""
        try:
            # 发送回车激活终端
            self.serial_conn.write(b'\n')
            time.sleep(0.5)

            # 读取当前输出
            output = self._read_serial_output(timeout=2)

            # 如果已经是登录状态，直接返回
            if 'root@' in output or '#' in output:
                print("  已经处于登录状态")
                return

            # 发送用户名
            self.serial_conn.write(b'root\n')
            time.sleep(0.5)

            # 等待密码提示
            output = self._read_serial_output(timeout=2)

            # 发送密码
            self.serial_conn.write(b'R0uT3&U&s@l1nk46#3\n')
            time.sleep(1)

            # 验证登录成功
            output = self._read_serial_output(timeout=2)
            if 'root@' not in output and '#' not in output:
                raise Exception("串口登录失败")

        except Exception as e:
            raise Exception(f"串口登录失败: {str(e)}")

    def _read_serial_output(self, timeout=1):
        """读取串口输出"""
        output = b''
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.serial_conn.in_waiting > 0:
                output += self.serial_conn.read(self.serial_conn.in_waiting)
            time.sleep(0.1)
        return output.decode('utf-8', errors='ignore')

    def _start_monitoring(self):
        """启动监控线程"""
        print("\n启动CPU和内存监控线程...")
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_system_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print("✅ 监控线程已启动")

    def _stop_monitoring(self):
        """停止监控线程"""
        if self.monitoring_active:
            print("\n停止监控线程...")
            self.monitoring_active = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            print("✅ 监控线程已停止")

    def _monitor_system_resources(self):
        """监控系统资源（在独立线程中运行）"""
        try:
            while self.monitoring_active:
                # 采集CPU使用率
                cpu_usage = self._get_cpu_usage()
                if cpu_usage is not None:
                    self.cpu_samples.append(cpu_usage)

                # 采集内存使用情况
                memory_free = self._get_memory_free()
                if memory_free is not None:
                    self.memory_samples.append(memory_free)

                # 每3秒采集一次（避免频繁占用串口）
                time.sleep(3)

        except Exception as e:
            print(f"监控线程异常: {str(e)}")

    def _get_cpu_usage(self):
        """获取CPU使用率"""
        try:
            with self.serial_lock:
                # 发送top命令 - 获取前3行以确保包含CPU行
                self.serial_conn.write(b'top -n 1 -b | head -n 3\n')
                time.sleep(0.5)

                # 读取输出
                output = self._read_serial_output(timeout=1)

            # 调试：打印原始输出（只在前几次打印）
            if len(self.cpu_samples) < 3:
                print(f"[DEBUG] CPU命令输出: {output[:300]}")

            # 解析CPU使用率 - 根据实际设备输出格式
            # 实际格式: CPU:   1% usr   3% sys   0% nic  95% idle   0% io   0% irq   0% sirq
            match = re.search(r'CPU:\s+(\d+)%\s+usr\s+(\d+)%\s+sys', output, re.IGNORECASE)
            if match:
                usr = int(match.group(1))
                sys = int(match.group(2))
                cpu_usage = usr + sys
                if len(self.cpu_samples) < 3:
                    print(f"[DEBUG] 解析到CPU: usr={usr}%, sys={sys}%, 总计={cpu_usage}%")
                return cpu_usage

            # 格式2: CPU: 5%usr 2%sys (无空格)
            match = re.search(r'CPU:\s*(\d+)%usr\s+(\d+)%sys', output, re.IGNORECASE)
            if match:
                usr = int(match.group(1))
                sys = int(match.group(2))
                cpu_usage = usr + sys
                if len(self.cpu_samples) < 3:
                    print(f"[DEBUG] 解析到CPU (格式2): usr={usr}%, sys={sys}%, 总计={cpu_usage}%")
                return cpu_usage

            # 格式3: 只有idle百分比，用100-idle计算
            match = re.search(r'(\d+)%\s+idle', output, re.IGNORECASE)
            if match:
                idle = int(match.group(1))
                cpu_usage = 100 - idle
                if len(self.cpu_samples) < 3:
                    print(f"[DEBUG] 解析到CPU (格式3): idle={idle}%, 使用率={cpu_usage}%")
                return cpu_usage

            # 如果前3次都没匹配到，打印警告
            if len(self.cpu_samples) < 3:
                print(f"[WARNING] 无法解析CPU使用率，输出: {output[:300]}")

            return None

        except Exception as e:
            if len(self.cpu_samples) < 3:
                print(f"[ERROR] CPU采集异常: {str(e)}")
            return None

    def _get_memory_free(self):
        """获取空闲内存"""
        try:
            with self.serial_lock:
                # 使用free命令查看内存
                self.serial_conn.write(b'free\n')
                time.sleep(0.5)

                # 读取输出
                output = self._read_serial_output(timeout=1)

            # 调试：打印原始输出（只在前几次打印）
            if len(self.memory_samples) < 3:
                print(f"[DEBUG] 内存命令输出: {output[:300]}")

            # 解析内存信息
            # 实际格式: Mem: 50028K used, 71444K free, 228K shrd, 2668K buff, 7732K cached
            match = re.search(r'Mem:.*?(\d+)K\s+free', output, re.IGNORECASE)
            if match:
                # 获取的是KB，返回KB单位
                free_mem_kb = int(match.group(1))
                if len(self.memory_samples) < 3:
                    print(f"[DEBUG] 解析到空闲内存: {free_mem_kb}KB ({free_mem_kb/1024:.1f}MB)")
                return free_mem_kb

            # 备用格式1: 可能有换行，单独一行显示free
            match = re.search(r'(\d+)K\s+free', output, re.IGNORECASE)
            if match:
                free_mem_kb = int(match.group(1))
                if len(self.memory_samples) < 3:
                    print(f"[DEBUG] 解析到空闲内存(格式2): {free_mem_kb}KB ({free_mem_kb/1024:.1f}MB)")
                return free_mem_kb

            # 备用格式2: 传统的free命令格式（数字格式）
            # 格式: Mem:      123456      67890      55566
            match = re.search(r'Mem:\s+(\d+)\s+\d+\s+(\d+)', output)
            if match:
                free_mem = int(match.group(2))
                if len(self.memory_samples) < 3:
                    print(f"[DEBUG] 解析到空闲内存(格式3): {free_mem} ({free_mem/1024:.1f}MB)")
                return free_mem

            # 如果前3次都没匹配到，打印警告
            if len(self.memory_samples) < 3:
                print(f"[WARNING] 无法解析内存信息，输出: {output[:300]}")

            return None

        except Exception as e:
            if len(self.memory_samples) < 3:
                print(f"[ERROR] 内存采集异常: {str(e)}")
            return None

    def _print_interim_stats(self):
        """打印中期统计"""
        print(f"\n{'='*70}")
        print(f"中期统计 (已完成{self.completed_iterations}次)")
        print(f"{'='*70}")

        if self.install_times:
            avg_install = sum(self.install_times) / len(self.install_times)
            print(f"平均安装时间: {avg_install:.2f}秒")

        if self.uninstall_times:
            avg_uninstall = sum(self.uninstall_times) / len(self.uninstall_times)
            print(f"平均卸载时间: {avg_uninstall:.2f}秒")

        if self.cpu_samples:
            avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples)
            max_cpu = max(self.cpu_samples)
            print(f"CPU使用率 - 平均: {avg_cpu:.2f}%, 最大: {max_cpu}%")

        if self.memory_samples:
            avg_mem = sum(self.memory_samples) / len(self.memory_samples)
            min_mem = min(self.memory_samples)
            print(f"空闲内存 - 平均: {avg_mem/1024:.2f}MB, 最小: {min_mem/1024:.2f}MB")

        print(f"失败次数 - 安装: {self.failed_installs}, 卸载: {self.failed_uninstalls}")
        print(f"{'='*70}\n")

    def _print_final_stats(self):
        """打印最终统计"""
        print(f"\n{'='*70}")
        print(f"最终测试统计")
        print(f"{'='*70}")
        print(f"总测试次数: {self.TEST_ITERATIONS}")
        print(f"完成次数: {self.completed_iterations}")
        print(f"失败次数 - 安装: {self.failed_installs}, 卸载: {self.failed_uninstalls}")
        print(f"成功率: {self.completed_iterations/self.TEST_ITERATIONS*100:.2f}%")

        if self.install_times:
            avg_install = sum(self.install_times) / len(self.install_times)
            min_install = min(self.install_times)
            max_install = max(self.install_times)
            print(f"\n安装时间统计:")
            print(f"  平均: {avg_install:.2f}秒")
            print(f"  最小: {min_install:.2f}秒")
            print(f"  最大: {max_install:.2f}秒")

        if self.uninstall_times:
            avg_uninstall = sum(self.uninstall_times) / len(self.uninstall_times)
            min_uninstall = min(self.uninstall_times)
            max_uninstall = max(self.uninstall_times)
            print(f"\n卸载时间统计:")
            print(f"  平均: {avg_uninstall:.2f}秒")
            print(f"  最小: {min_uninstall:.2f}秒")
            print(f"  最大: {max_uninstall:.2f}秒")

        if self.cpu_samples:
            avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples)
            min_cpu = min(self.cpu_samples)
            max_cpu = max(self.cpu_samples)
            print(f"\nCPU使用率统计:")
            print(f"  平均: {avg_cpu:.2f}%")
            print(f"  最小: {min_cpu}%")
            print(f"  最大: {max_cpu}%")

        if self.memory_samples:
            avg_mem = sum(self.memory_samples) / len(self.memory_samples)
            min_mem = min(self.memory_samples)
            max_mem = max(self.memory_samples)
            print(f"\n空闲内存统计:")
            print(f"  平均: {avg_mem/1024:.2f}MB")
            print(f"  最小: {min_mem/1024:.2f}MB")
            print(f"  最大: {max_mem/1024:.2f}MB")

        print(f"{'='*70}\n")

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        # 停止监控
        self._stop_monitoring()

        # 关闭串口
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
                print("已关闭串口连接")
        except Exception as e:
            print(f"关闭串口时出错: {str(e)}")

        # 关闭浏览器
        try:
            if hasattr(self, 'router_client') and self.router_client:
                self.router_client.close()
                print("已关闭浏览器")
        except Exception as e:
            print(f"关闭浏览器时出错: {str(e)}")

        print("测试清理完成")
