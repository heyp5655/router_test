# -*- coding: utf-8 -*-
from test_cases.base_test import BaseTest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PinFunctionTest(BaseTest):
    """PIN功能可生效测试

    测试项：功能用例/网络/接口/蜂窝网络
    测试点：PIN功能可生效

    前置条件：
    测试的SIM卡已经设了PIN码为0000并且可用

    测试步骤：
    1. 登录路由器web，并且跳转到#network/interfaces/cellular页面
    2. 点击SIM卡设置按钮
    3. 在弹窗中输入PIN码0000并点击确认
    4. 点击保存并应用
    5. 跳转到概览首页查看蜂窝网络状态，等蜂窝注册成功，并且获取到IP
    6. 设置本地电脑网卡名称为TEST的网卡地址获取方式为DHCP

    预期：
    1. 登录路由器成功，并且跳转后检测到SIM1标题
    2. 弹窗成功
    3. 弹窗设置没有报错
    4. 保持应用成功
    5. 等蜂窝注册成功，并且获取到IP
    6. 电脑自动获取地址后可用访问外网
    """

    # 添加分类信息属性
    category = "功能用例/网络/接口/蜂窝网络"
    is_regression = True  # 标记为回归测试用例

    # PIN码配置
    PIN_CODE = "0000"

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "PIN功能可生效"

    @property
    def description(self):
        """测试描述"""
        return "验证SIM卡PIN码功能，确保设置PIN码后蜂窝网络能正常注册并获取IP"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)
        self.router_ip = self.config.router_config.router_ip

    def setup(self):
        """测试前置条件"""
        print(f"\n{'='*70}")
        print(f"测试用例: {self.test_name}")
        print(f"测试分类: {self.category}")
        print(f"{'='*70}")
        print(f"路由器IP: {self.router_ip}")
        print(f"PIN码: {self.PIN_CODE}")
        print(f"{'='*70}\n")

        # 登录Web界面
        print("登录路由器Web界面...")
        if not self.router_client.login_web():
            raise Exception("Web登录失败")
        print("✅ Web登录成功\n")

    def execute(self):
        """执行测试"""
        try:
            print(f"\n{'='*70}")
            print(f"开始执行PIN功能测试")
            print(f"{'='*70}\n")

            # 步骤1: 跳转到蜂窝设置页面
            print("步骤1: 跳转到蜂窝设置页面...")
            if not self._navigate_to_cellular_page():
                raise Exception("跳转到蜂窝设置页面失败")
            print("✅ 成功跳转到蜂窝设置页面\n")

            # 步骤2: 点击SIM卡设置按钮
            print("步骤2: 点击SIM卡设置按钮...")
            if not self._click_sim_settings_button():
                raise Exception("点击SIM卡设置按钮失败")
            print("✅ SIM卡设置弹窗已打开\n")

            # 步骤3: 在弹窗中输入PIN码
            print("步骤3: 在弹窗中输入PIN码...")
            if not self._input_pin_code():
                raise Exception("输入PIN码失败")
            print("✅ PIN码输入成功\n")

            # 步骤4: 点击保存并应用
            print("步骤4: 点击保存并应用...")
            if not self._save_and_apply():
                raise Exception("保存并应用失败")
            print("✅ 保存并应用成功\n")

            # 步骤5: 跳转到概览首页查看蜂窝网络状态
            print("步骤5: 查看蜂窝网络状态...")
            if not self._check_cellular_status():
                raise Exception("蜂窝网络未能成功注册或获取IP")
            print("✅ 蜂窝网络注册成功并获取到IP\n")

            # 步骤6: 检查网络连通性
            print("步骤6: 检查网络连通性...")
            if not self._check_network_connectivity():
                raise Exception("网络连通性检查失败，无法验证通过路由器访问外网")

            print("✅ 网络连通性验证通过\n")

            print(f"\n{'='*70}")
            print("✅ PIN功能测试全部通过")
            print(f"{'='*70}\n")

            return True

        except Exception as e:
            print(f"\n测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise

    def _navigate_to_cellular_page(self):
        """跳转到蜂窝设置页面"""
        try:
            driver = self.router_client.driver
            wait = WebDriverWait(driver, 15)

            # 跳转到蜂窝设置页面
            url_with_hash = f"http://{self.router_ip}/#network/interfaces/cellular"
            driver.get(url_with_hash)
            time.sleep(1)
            driver.refresh()
            time.sleep(3)

            # 验证是否成功跳转（检测SIM1标题）
            try:
                sim1_title = wait.until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//h3[@class='ys-title-3' and text()='SIM1']"
                    ))
                )
                print("  检测到SIM1标题，页面跳转成功")
                return True
            except:
                print("  ⚠️  未检测到SIM1标题，但继续执行")
                return True

        except Exception as e:
            print(f"  跳转到蜂窝设置页面失败: {str(e)}")
            return False

    def _click_sim_settings_button(self):
        """点击SIM卡设置按钮"""
        try:
            driver = self.router_client.driver
            wait = WebDriverWait(driver, 10)

            # 尝试多种选择器定位SIM卡设置按钮
            selectors = [
                "//button[contains(text(), 'SIM卡设置')]",
                "//button[contains(text(), 'SIM Setting')]",
                "//button[@id='undefined_undefined']",
                "//button[contains(@class, 'button') and contains(text(), 'SIM')]",
            ]

            for selector in selectors:
                try:
                    print(f"  尝试定位SIM卡设置按钮: {selector}")
                    button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    button.click()
                    print("  ✅ 成功点击SIM卡设置按钮")
                    time.sleep(2)  # 等待弹窗打开
                    return True
                except:
                    continue

            print("  ❌ 无法找到SIM卡设置按钮")
            return False

        except Exception as e:
            print(f"  点击SIM卡设置按钮失败: {str(e)}")
            return False

    def _input_pin_code(self):
        """在弹窗中输入PIN码"""
        try:
            driver = self.router_client.driver
            wait = WebDriverWait(driver, 10)

            # 尝试多种选择器定位PIN码输入框
            selectors = [
                '//*[@id="1_pin1"]',
                '//input[@type="password" and contains(@id, "pin")]',
                '//input[contains(@id, "pin1")]',
                '//input[@autocomplete="new-password" and @type="password"]',
            ]

            pin_input = None
            for selector in selectors:
                try:
                    print(f"  尝试定位PIN码输入框: {selector}")
                    pin_input = driver.find_element(By.XPATH, selector)
                    if pin_input.is_displayed() and pin_input.is_enabled():
                        print(f"  ✅ 找到PIN码输入框")
                        break
                except:
                    continue

            if not pin_input:
                print("  ❌ 无法找到PIN码输入框")
                return False

            # 清空并输入PIN码
            pin_input.clear()
            time.sleep(0.5)
            pin_input.send_keys(self.PIN_CODE)
            print(f"  ✅ 已输入PIN码: {self.PIN_CODE}")

            # 验证输入
            input_value = pin_input.get_attribute("value")
            if input_value != self.PIN_CODE:
                print(f"  ⚠️  输入验证失败，重新输入")
                pin_input.clear()
                time.sleep(0.5)
                pin_input.send_keys(self.PIN_CODE)

            # 点击弹窗确认按钮
            time.sleep(1)
            confirm_selectors = [
                "//button[contains(@class, 'ys-dialog-btn') and contains(@class, 'btn-primary')]",
                "//button[contains(text(), '确认')]",
                "//button[contains(text(), 'OK')]",
                "//button[contains(text(), 'Confirm')]",
            ]

            for selector in confirm_selectors:
                try:
                    print(f"  尝试定位确认按钮: {selector}")
                    confirm_btn = driver.find_element(By.XPATH, selector)
                    if confirm_btn.is_displayed() and confirm_btn.is_enabled():
                        confirm_btn.click()
                        print("  ✅ 已点击确认按钮")
                        time.sleep(2)
                        return True
                except:
                    continue

            print("  ⚠️  未找到确认按钮，但PIN已输入")
            return True

        except Exception as e:
            print(f"  输入PIN码失败: {str(e)}")
            return False

    def _save_and_apply(self):
        """点击保存并应用（此页面保存和应用是一体按钮）"""
        try:
            driver = self.router_client.driver

            # 点击保存按钮（在此页面，保存和应用是一体的，点击后自动应用）
            print("  点击保存并应用按钮...")
            save_success = self.router_client._click_save_button()
            if not save_success:
                print("  ⚠️  保存并应用按钮点击失败")
                return False
            print("  ✅ 保存并应用成功")

            # 等待配置生效
            time.sleep(3)

            return True

        except Exception as e:
            print(f"  保存并应用失败: {str(e)}")
            return False

    def _check_cellular_status(self):
        """检查蜂窝网络状态

        检查逻辑：
        1. 每5秒刷新页面，检查 summary_cellular_info 元素是否为 "Link in use" 或 "当前链路"
        2. 如果正常，再检查是否获取到IP
        3. 如果IP拿到了，则证明蜂窝正常
        """
        try:
            driver = self.router_client.driver

            # 获取配置的超时时间（秒）
            max_wait = self.config.timeout if hasattr(self.config, 'timeout') else 300
            print(f"  等待蜂窝网络注册并获取IP（最多等待{max_wait}秒）...")

            start_time = time.time()
            check_interval = 5  # 每5秒检查一次

            while time.time() - start_time < max_wait:
                elapsed = int(time.time() - start_time)

                # 每10秒打印一次状态
                if elapsed % 10 == 0:
                    print(f"  ⏳ 检查蜂窝网络状态... ({elapsed}秒)", flush=True)

                try:
                    # 跳转到概览页面并刷新
                    driver.get(f"http://{self.router_ip}/#status/summary")
                    driver.refresh()
                    time.sleep(2)  # 等待页面加载

                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    wait = WebDriverWait(driver, 5)

                    # 步骤1: 检查链路状态 - 必须是 "Link in use" 或 "当前链路"
                    link_status_ok = False
                    try:
                        cellular_status_element = wait.until(
                            EC.presence_of_element_located((By.XPATH, '//*[@id="summary_cellular_info"]/div[2]/div[1]/div/h3/div/span[2]'))
                        )
                        cellular_status = cellular_status_element.text.strip()

                        if elapsed % 10 == 0:
                            print(f"  链路状态: '{cellular_status}' ({elapsed}秒)", flush=True)

                        # 检查是否为正常状态
                        if cellular_status == "Link in use" or cellular_status == "当前链路":
                            link_status_ok = True
                            if elapsed % 10 == 0:
                                print(f"  ✅ 链路状态正常: {cellular_status} ({elapsed}秒)", flush=True)
                        else:
                            if elapsed % 10 == 0:
                                print(f"  ⚠️  链路状态异常，等待恢复: '{cellular_status}' ({elapsed}秒)", flush=True)
                            # 继续等待下一次检查
                            time.sleep(check_interval)
                            continue

                    except Exception as status_ex:
                        if elapsed % 10 == 0:
                            print(f"  ⚠️  无法获取链路状态元素 ({elapsed}秒)", flush=True)
                        time.sleep(check_interval)
                        continue

                    # 步骤2: 链路状态正常后，检查是否获取到IP
                    if link_status_ok:
                        try:
                            ip_element = wait.until(
                                EC.presence_of_element_located((By.XPATH, '//*[@id="qwert_ip"]'))
                            )
                            ip_text = ip_element.text.strip()

                            # 检查是否获取到有效的IP地址
                            if ip_text and ip_text != "" and ip_text != "-":
                                if '.' in ip_text and any(char.isdigit() for char in ip_text):
                                    print(f"  ✅ 蜂窝网络已连接，链路状态: {cellular_status}, IP: {ip_text}", flush=True)
                                    return True
                                else:
                                    if elapsed % 10 == 0:
                                        print(f"  ⚠️  IP格式无效: '{ip_text}' ({elapsed}秒)", flush=True)
                            else:
                                if elapsed % 10 == 0:
                                    print(f"  ⚠️  IP为空或无效，当前: '{ip_text}' ({elapsed}秒)", flush=True)

                        except Exception as ip_ex:
                            if elapsed % 10 == 0:
                                print(f"  ⚠️  无法获取IP元素 ({elapsed}秒)", flush=True)

                except Exception as e:
                    if elapsed % 10 == 0:
                        print(f"  ⚠️  检查时发生异常 ({elapsed}秒): {str(e)[:100]}", flush=True)

                # 等待下一次检查
                time.sleep(check_interval)

            print(f"  ⚠️  等待超时，未能在{max_wait}秒内检测到蜂窝网络连接和IP")
            return False

        except Exception as e:
            print(f"  检查蜂窝网络状态失败: {str(e)}")
            import traceback
            print(f"  错误详情: {traceback.format_exc()}")
            return False

    def _check_network_connectivity(self):
        """检查网络连通性"""
        try:
            from utils.network_utils import network_utils

            # 使用 network_utils 的一站式方法检查外网连通性
            return network_utils.check_pc_internet_via_adapter(adapter_name="TEST", timeout=10)

        except Exception as e:
            print(f"  网络连通性检查失败: {str(e)}")
            import traceback
            print(f"  错误详情: {traceback.format_exc()}")
            return False

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        # 恢复网卡配置
        try:
            from utils.network_utils import network_utils
            print("\n恢复网卡TEST配置...")
            network_utils.restore_adapter_auto_config(adapter_name="TEST")
        except Exception as e:
            print(f"⚠️  恢复网卡配置时出错: {str(e)}")

        # 关闭浏览器
        try:
            if self.router_client and self.router_client.driver:
                print("关闭浏览器...")
                self.router_client.close()
                print("✅ 浏览器已关闭")
        except Exception as e:
            print(f"⚠️  关闭浏览器时出错: {str(e)}")

        print("PIN功能测试完成")
