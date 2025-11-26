# -*- coding: utf-8 -*-
from test_cases.base_test import BaseTest
import time
import os
import paramiko
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PythonSDKLowMemoryInstallTest(BaseTest):
    """设备剩余内存低于28M时安装Python SDK测试

    测试项：功能用例/APP/python
    测试点：不同内存条件下Python SDK安装稳定性测试

    测试步骤：
    1. 内存~50M：安装卸载10次，统计成功/失败比例
    2. 内存~40M：安装卸载10次，统计成功/失败比例
    3. 内存~30M：安装卸载10次，统计成功/失败比例
    4. 内存<28M：安装1次，应该失败

    注意：测试过程中内存不足时，需要后台执行reboot重启，然后继续下一步测试

    预期：
    1. 内存充足时，安装成功率高
    2. 内存降低时，成功率逐渐下降
    3. 内存<28M时，安装应该失败
    """

    # 添加分类信息属性
    category = "功能用例/APP/python"
    is_regression = True  # 标记为回归测试用例

    # SDK文件路径
    SDK_FILE_PATH = r"E:\GIT\ROUTER_TEST\config\pysdk-ur3x-5.0.2-u1.tar.gz"

    # 内存测试场景（单位：KB）
    MEMORY_SCENARIOS = [
        {"name": "~50M", "target": 51200, "min": 48000, "max": 54000, "cycles": 10},
        {"name": "~40M", "target": 40960, "min": 38000, "max": 44000, "cycles": 10},
        {"name": "~30M", "target": 30720, "min": 28500, "max": 33000, "cycles": 10},
        {"name": "<28M", "target": 27000, "min": 20000, "max": 28000, "cycles": 1},
    ]

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "设备剩余内存低于28M时安装Python SDK"

    @property
    def description(self):
        """测试描述"""
        return "验证不同内存条件下SDK安装稳定性，统计成功/失败比例"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 获取路由器配置
        self.router_ip = self.config.router_config.router_ip
        self.ssh_conn = None

        # 测试结果统计
        self.test_results = []

    def setup(self):
        """测试前置条件"""
        print(f"\n{'='*70}")
        print(f"测试用例: {self.test_name}")
        print(f"测试分类: {self.category}")
        print(f"{'='*70}")
        print(f"路由器IP: {self.router_ip}")
        print(f"SDK文件: {self.SDK_FILE_PATH}")
        print(f"\n内存测试场景:")
        for scenario in self.MEMORY_SCENARIOS:
            print(f"  - {scenario['name']}: {scenario['min']//1024}-{scenario['max']//1024}MB, {scenario['cycles']}次")
        print(f"{'='*70}\n")

        # 检查SDK文件是否存在
        if not os.path.exists(self.SDK_FILE_PATH):
            raise FileNotFoundError(f"SDK文件不存在: {self.SDK_FILE_PATH}")
        print(f"✅ SDK文件存在\n")

        # 建立SSH连接
        print("建立SSH连接...")
        self._connect_ssh()
        print("✅ SSH连接成功\n")

        # 登录Web界面
        print("登录路由器Web界面...")
        if not self.router_client.login_web():
            raise Exception("Web登录失败")
        print("✅ Web登录成功\n")

    def execute(self):
        """执行测试"""
        try:
            print(f"\n{'='*70}")
            print(f"开始执行Python SDK内存梯度安装测试")
            print(f"{'='*70}\n")

            # 跳转到Python SDK状态页面
            print("跳转到Python SDK状态页面...")
            self._navigate_to_python_status()
            print("✅ 成功跳转到Python SDK状态页面\n")

            # 确保初始状态SDK未安装
            print("检查初始SDK状态...")
            self._ensure_sdk_uninstalled()
            print("✅ SDK初始状态检查完成\n")

            # 执行每个内存场景的测试
            for idx, scenario in enumerate(self.MEMORY_SCENARIOS, 1):
                print(f"\n{'='*70}")
                print(f"场景 {idx}/{len(self.MEMORY_SCENARIOS)}: 内存{scenario['name']} ({scenario['cycles']}次循环)")
                print(f"{'='*70}")

                result = self._test_memory_scenario(scenario)
                self.test_results.append(result)

                # 打印场景结果
                self._print_scenario_result(result)

                # 如果不是最后一个场景，等待一下
                if idx < len(self.MEMORY_SCENARIOS):
                    print("\n等待5秒后进入下一场景...")
                    time.sleep(5)

            # 打印总结
            self._print_final_summary()

            return True

        except Exception as e:
            print(f"\n测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise
        finally:
            # 清理临时文件
            self._cleanup_temp_files()

    def _test_memory_scenario(self, scenario):
        """测试单个内存场景"""
        result = {
            'scenario': scenario['name'],
            'target_mem_kb': scenario['target'],
            'target_mem_mb': scenario['target'] // 1024,
            'cycles': scenario['cycles'],
            'install_success': 0,
            'install_fail': 0,
            'uninstall_success': 0,
            'uninstall_fail': 0,
            'details': []
        }

        # 调整内存到目标范围
        print(f"\n步骤1: 调整内存到 {scenario['min']//1024}-{scenario['max']//1024}MB 范围...")
        if not self._adjust_memory_to_target(scenario['target'], scenario['min'], scenario['max']):
            print(f"  ⚠️ 无法调整内存，尝试重启设备...")
            self._reboot_device()
            # 重启后重新调整
            if not self._adjust_memory_to_target(scenario['target'], scenario['min'], scenario['max']):
                print(f"  ❌ 重启后仍无法调整内存，跳过此场景")
                result['details'].append({'error': '无法调整内存'})
                return result

        # 执行多次安装卸载循环
        for cycle in range(1, scenario['cycles'] + 1):
            print(f"\n--- 循环 {cycle}/{scenario['cycles']} ---")

            cycle_result = {'cycle': cycle}

            # 检查内存是否仍在范围内
            current_mem = self._get_free_memory()
            if not (scenario['min'] <= current_mem <= scenario['max']):
                print(f"  ⚠️ 内存偏离目标范围 (当前: {current_mem}KB)，重新调整...")
                if not self._adjust_memory_to_target(scenario['target'], scenario['min'], scenario['max']):
                    print(f"  ❌ 无法调整内存，尝试重启...")
                    self._reboot_device()
                    continue

            # 刷新页面
            self.router_client.driver.refresh()
            time.sleep(2)

            # 安装SDK
            print(f"  安装SDK (第{cycle}次)...")
            install_success = self._install_sdk(timeout=300)

            if install_success:
                result['install_success'] += 1
                cycle_result['install'] = 'success'
                print(f"  ✅ 安装成功")

                # 如果安装成功，尝试卸载
                print(f"  卸载SDK (第{cycle}次)...")
                time.sleep(2)
                uninstall_success = self._uninstall_sdk_via_web()

                if uninstall_success:
                    result['uninstall_success'] += 1
                    cycle_result['uninstall'] = 'success'
                    print(f"  ✅ 卸载成功")
                else:
                    result['uninstall_fail'] += 1
                    cycle_result['uninstall'] = 'fail'
                    print(f"  ❌ 卸载失败")
                    # 卸载失败，尝试重启
                    print(f"  卸载失败，重启设备...")
                    self._reboot_device()

            else:
                result['install_fail'] += 1
                cycle_result['install'] = 'fail'
                print(f"  ❌ 安装失败")

                # 对于<28M场景，安装失败是预期的
                if scenario['name'] == '<28M':
                    print(f"  ✅ 预期行为：内存不足时安装应该失败")

            result['details'].append(cycle_result)

            # 每次循环后短暂等待
            time.sleep(3)

        return result

    def _print_scenario_result(self, result):
        """打印场景结果"""
        print(f"\n{'='*70}")
        print(f"场景 {result['scenario']} 测试结果")
        print(f"{'='*70}")
        print(f"目标内存: ~{result['target_mem_mb']}MB ({result['target_mem_kb']}KB)")
        print(f"循环次数: {result['cycles']}")
        print(f"安装成功: {result['install_success']}/{result['cycles']} ({result['install_success']/result['cycles']*100:.1f}%)")
        print(f"安装失败: {result['install_fail']}/{result['cycles']} ({result['install_fail']/result['cycles']*100:.1f}%)")
        if result['install_success'] > 0:
            total_uninstall = result['uninstall_success'] + result['uninstall_fail']
            if total_uninstall > 0:
                print(f"卸载成功: {result['uninstall_success']}/{total_uninstall} ({result['uninstall_success']/total_uninstall*100:.1f}%)")
                print(f"卸载失败: {result['uninstall_fail']}/{total_uninstall} ({result['uninstall_fail']/total_uninstall*100:.1f}%)")
        print(f"{'='*70}")

    def _print_final_summary(self):
        """打印最终总结"""
        print(f"\n\n{'='*70}")
        print("Python SDK 内存梯度测试 - 最终总结")
        print(f"{'='*70}\n")

        for result in self.test_results:
            install_rate = result['install_success'] / result['cycles'] * 100 if result['cycles'] > 0 else 0
            print(f"场景 {result['scenario']:>6} (~{result['target_mem_mb']:>3}MB): "
                  f"安装成功率 {install_rate:5.1f}% ({result['install_success']}/{result['cycles']})")

        print(f"\n{'='*70}")
        print("✅ 所有场景测试完成")
        print(f"{'='*70}\n")

    def _connect_ssh(self):
        """建立SSH连接"""
        try:
            self.ssh_conn = paramiko.SSHClient()
            self.ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_conn.connect(
                self.router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )
        except Exception as e:
            raise Exception(f"SSH连接失败: {str(e)}")

    def _reboot_device(self):
        """重启设备"""
        try:
            print("  [重启] 执行设备重启...")

            # 通过SSH执行reboot命令（后台执行）
            if self.ssh_conn:
                try:
                    self.ssh_conn.exec_command("reboot &")
                except:
                    pass  # reboot会断开连接，忽略异常

            print("  [重启] 等待设备重启 (90秒)...")
            time.sleep(90)

            # 重新建立SSH连接
            print("  [重启] 重新连接SSH...")
            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    self._connect_ssh()
                    print(f"  [重启] ✅ SSH重新连接成功 (尝试 {attempt+1}/{max_attempts})")
                    break
                except:
                    if attempt < max_attempts - 1:
                        print(f"  [重启] SSH连接失败，10秒后重试... ({attempt+1}/{max_attempts})")
                        time.sleep(10)
                    else:
                        raise Exception("重启后无法重新连接SSH")

            # 重新登录Web
            print("  [重启] 重新登录Web界面...")
            time.sleep(5)
            if not self.router_client.login_web():
                raise Exception("重启后Web登录失败")

            # 重新跳转到Python状态页面
            print("  [重启] 重新跳转到Python状态页面...")
            self._navigate_to_python_status()
            time.sleep(3)

            print("  [重启] ✅ 设备重启完成，已重新连接")

        except Exception as e:
            print(f"  [重启] ❌ 重启过程出错: {str(e)}")
            raise

    def _get_free_memory(self):
        """获取设备当前空闲内存（KB）"""
        try:
            stdin, stdout, stderr = self.ssh_conn.exec_command("free | grep 'Mem:' | awk '{print $4}'")
            output = stdout.read().decode('utf-8').strip()
            free_mem = int(output)
            print(f"  当前空闲内存: {free_mem} KB ({free_mem/1024:.1f} MB)")
            return free_mem
        except Exception as e:
            print(f"  ❌ 获取内存失败: {str(e)}")
            raise

    def _adjust_memory_to_target(self, target_mem, min_mem, max_mem, max_attempts=15):
        """调整内存到目标范围"""
        print(f"  目标内存范围: {min_mem//1024}-{max_mem//1024} MB ({min_mem}-{max_mem} KB)")

        for attempt in range(max_attempts):
            current_mem = self._get_free_memory()

            # 检查是否已在目标范围内
            if min_mem <= current_mem <= max_mem:
                print(f"  ✅ 内存已在目标范围内: {current_mem} KB ({current_mem//1024} MB)")
                return True

            # 内存太高，需要占用一些内存
            if current_mem > max_mem:
                needed_reduction = current_mem - target_mem
                file_size_mb = max(1, (needed_reduction // 1024) + 1)
                print(f"  内存过高({current_mem//1024}MB)，创建{file_size_mb}MB临时文件...")

                try:
                    temp_file = f"/tmp/mem_filler_{attempt}.tmp"
                    cmd = f"dd if=/dev/zero of={temp_file} bs=1M count={file_size_mb} 2>/dev/null"
                    self.ssh_conn.exec_command(cmd)
                    time.sleep(2)
                except Exception as e:
                    print(f"  ⚠️ 创建临时文件失败: {str(e)}")

            # 内存太低，需要释放一些内存
            elif current_mem < min_mem:
                print(f"  内存过低({current_mem//1024}MB)，删除临时文件释放内存...")
                try:
                    self.ssh_conn.exec_command("rm -f /tmp/mem_filler_*.tmp 2>/dev/null")
                    time.sleep(2)
                except Exception as e:
                    print(f"  ⚠️ 删除临时文件失败: {str(e)}")

            time.sleep(1)

        # 最后检查一次
        current_mem = self._get_free_memory()
        if min_mem <= current_mem <= max_mem:
            print(f"  ✅ 内存调整成功: {current_mem} KB ({current_mem//1024} MB)")
            return True
        else:
            print(f"  ❌ 无法将内存调整到目标范围，当前: {current_mem} KB ({current_mem//1024} MB)")
            return False

    def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            print("  清理临时文件...")
            if self.ssh_conn:
                self.ssh_conn.exec_command("rm -f /tmp/mem_filler_*.tmp 2>/dev/null")
            print("  ✅ 临时文件已清理")
        except:
            pass

    def _navigate_to_python_status(self):
        """跳转到Python SDK状态页面"""
        try:
            driver = self.router_client.driver
            url_with_hash = f"http://{self.router_ip}/#app/python/status"
            driver.get(url_with_hash)
            time.sleep(1)
            driver.refresh()
            time.sleep(2)
        except Exception as e:
            raise Exception(f"跳转到Python状态页面失败: {str(e)}")

    def _ensure_sdk_uninstalled(self):
        """确保SDK处于未安装状态"""
        try:
            driver = self.router_client.driver
            time.sleep(2)

            status_elem1_xpath = '//*[@id="status_python"]/div[2]/div[3]/div[2]'
            status_elem2_xpath = '//*[@id="status_python"]/div[2]/div[4]/div[2]'

            try:
                elem1 = driver.find_element(By.XPATH, status_elem1_xpath)
                elem2 = driver.find_element(By.XPATH, status_elem2_xpath)

                if elem1.text.strip() or elem2.text.strip():
                    print("  检测到SDK已安装，开始卸载...")
                    success = self._uninstall_sdk_via_web()
                    if success:
                        print("  ✅ 初始SDK已卸载")
                    else:
                        print("  ⚠️ 初始卸载失败，尝试重启...")
                        self._reboot_device()
                else:
                    print("  ✅ SDK未安装")
            except:
                print("  ✅ SDK未安装")

        except Exception as e:
            print(f"  ⚠️ 检查SDK状态时出错: {str(e)}")

    def _install_sdk(self, timeout=300):
        """安装SDK，返回是否成功"""
        try:
            driver = self.router_client.driver
            wait = WebDriverWait(driver, 10)

            # 查找文件上传输入框
            upload_input = None
            locators = [
                (By.XPATH, '//*[@id="0_sdkfile_url"]'),
                (By.XPATH, '//input[@type="file"]'),
            ]

            for by, xpath in locators:
                try:
                    elem = driver.find_element(by, xpath)
                    if elem.get_attribute('type') == 'file':
                        upload_input = elem
                        break
                except:
                    continue

            if not upload_input:
                print("  ❌ 无法找到文件上传输入框")
                return False

            # 上传文件
            upload_input.send_keys(self.SDK_FILE_PATH)
            time.sleep(2)

            # 等待并点击安装按钮
            install_btn = None
            for _ in range(10):
                try:
                    btn = driver.find_element(By.XPATH, '//*[@id="0_sdkfile_import"]')
                    btn_class = btn.get_attribute('class') or ''
                    if 'ys-upload-disable' not in btn_class:
                        install_btn = btn
                        break
                except:
                    pass
                time.sleep(1)

            if not install_btn:
                print("  ❌ 安装按钮未就绪")
                return False

            driver.execute_script("arguments[0].click();", install_btn)

            # 等待安装完成
            status_elem1_xpath = '//*[@id="status_python"]/div[2]/div[3]/div[2]'
            status_elem2_xpath = '//*[@id="status_python"]/div[2]/div[4]/div[2]'

            elapsed = 0
            while elapsed < timeout:
                try:
                    elem1 = driver.find_element(By.XPATH, status_elem1_xpath)
                    elem2 = driver.find_element(By.XPATH, status_elem2_xpath)

                    if elem1.text.strip() and elem2.text.strip():
                        return True

                except:
                    pass

                time.sleep(1)
                elapsed += 1

            return False

        except Exception as e:
            print(f"  ❌ 安装异常: {str(e)}")
            return False

    def _uninstall_sdk_via_web(self):
        """通过Web界面卸载SDK"""
        try:
            driver = self.router_client.driver

            uninstall_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="uninstall_btn"]'))
            )
            uninstall_btn.click()
            time.sleep(1)

            # 处理确认弹窗
            try:
                confirm_btns = driver.find_elements(By.XPATH,
                    "//button[contains(text(), '确定') or contains(text(), 'OK') or contains(text(), 'ok')]")
                if confirm_btns:
                    confirm_btns[0].click()
                    time.sleep(1)
            except:
                pass

            # 等待卸载完成
            status_elem1_xpath = '//*[@id="status_python"]/div[2]/div[3]/div[2]'
            status_elem2_xpath = '//*[@id="status_python"]/div[2]/div[4]/div[2]'

            max_wait = 60
            elapsed = 0
            while elapsed < max_wait:
                try:
                    elem1 = driver.find_element(By.XPATH, status_elem1_xpath)
                    elem2 = driver.find_element(By.XPATH, status_elem2_xpath)

                    if not elem1.text.strip() and not elem2.text.strip():
                        return True
                except:
                    return True

                time.sleep(1)
                elapsed += 1

            return False

        except Exception as e:
            print(f"  ❌ 卸载异常: {str(e)}")
            return False

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        # 清理临时文件
        self._cleanup_temp_files()

        # 关闭SSH连接
        if self.ssh_conn:
            try:
                self.ssh_conn.close()
                print("✅ SSH连接已关闭")
            except:
                pass

        print("测试清理完成")
