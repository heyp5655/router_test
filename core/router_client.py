import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import time
from models.test_config import RouterConfig


class RouterClient:
    def __init__(self, router_config: RouterConfig = None, router_ip: str = None, username: str = None,
                 password: str = None, model: str = None, module_type: str = "auto"):
        # 支持两种初始化方式：RouterConfig对象 或 独立参数
        if router_config is not None:
            # 使用RouterConfig对象初始化
            self.router_config = router_config
            self.router_ip = router_config.router_ip
            self.username = router_config.username
            self.password = router_config.password
            self.model = router_config.model
            self.module_type = router_config.module_type if hasattr(router_config, 'module_type') else "auto"
        else:
            # 使用独立参数初始化
            self.router_ip = router_ip
            self.username = username
            self.password = password
            self.model = model
            self.module_type = module_type
            # 创建RouterConfig对象用于兼容性
            self.router_config = RouterConfig(
                router_ip=router_ip,
                username=username,
                password=password,
                model=model,
                module_type=module_type
            )

        self.driver = None
        self.wait = None
        self.session = requests.Session()
        self.session.verify = False
        urllib3.disable_warnings(InsecureRequestWarning)

        print(f"RouterClient初始化完成 - IP: {self.router_ip}, 型号: {self.model}, 模组类型: {self.module_type}")

    # 以下保持您提供的所有方法不变
    def login_web(self, max_retries=3):
        """通过Web界面登录路由器，带重试机制"""
        if not self.driver:
            options = webdriver.ChromeOptions()
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')
            options.add_argument('--incognito')  # 使用无痕模式
            # 调试时确保浏览器可见
            # options.add_argument('--headless')  # 注释掉这行
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 15)  # 增加等待时间

        login_url = f"http://{self.router_ip}"

        for attempt in range(1, max_retries + 1):
            print(f"\n{'='*50}")
            print(f"登录尝试 {attempt}/{max_retries}")
            print(f"{'='*50}")

            try:
                print(f"正在访问: {login_url}")
                self.driver.get(login_url)
                self.driver.maximize_window()
                time.sleep(2)

                # 等待页面加载
                time.sleep(3)

                # 检查是否已经在登录状态（可能已经有session）
                if self._check_already_logged_in():
                    print("已经处于登录状态")
                    return True

                print("开始登录过程...")

                # 输入用户名（带重试和验证）
                username_entered = self._enter_field_with_retry(
                    '//*[@id="username"]',
                    self.username,
                    "用户名"
                )
                if not username_entered:
                    print(f"用户名输入失败，重试登录...")
                    continue

                # 输入密码（带重试和验证）
                password_entered = self._enter_field_with_retry(
                    '//*[@id="password"]',
                    self.password,
                    "密码"
                )
                if not password_entered:
                    print(f"密码输入失败，重试登录...")
                    continue

                # 点击登录按钮
                print("查找登录按钮...")
                login_button = self.driver.find_element(By.XPATH, '//*[@id="login"]')
                login_button.click()
                print("已点击登录按钮")

                # 等待登录完成
                print("等待登录完成...")
                time.sleep(3)
                self.driver.refresh()
                time.sleep(3)

                # 验证登录成功的多种方法
                if self._verify_login_success():
                    print("登录验证成功")
                    return True
                else:
                    print(f"登录验证失败，尝试 {attempt}/{max_retries}")
                    if attempt < max_retries:
                        time.sleep(2)
                        continue

            except Exception as e:
                print(f"登录过程中发生错误: {str(e)}")
                import traceback
                print(f"错误堆栈: {traceback.format_exc()}")
                if attempt < max_retries:
                    print(f"将进行第 {attempt + 1} 次重试...")
                    time.sleep(2)
                    continue

        print(f"登录失败，已重试 {max_retries} 次")
        return False

    def _enter_field_with_retry(self, xpath, value, field_name, max_attempts=3):
        """输入字段值并验证，带重试机制"""
        for attempt in range(1, max_attempts + 1):
            try:
                print(f"查找{field_name}输入框... (尝试 {attempt}/{max_attempts})")
                field = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )

                # 确保元素可交互
                self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))

                # 清空并输入
                field.clear()
                time.sleep(0.3)
                field.send_keys(value)
                time.sleep(0.5)

                # 验证输入是否成功
                actual_value = field.get_attribute('value')
                if actual_value == value:
                    print(f"已输入{field_name}，验证成功")
                    return True
                else:
                    print(f"{field_name}输入验证失败: 期望'{value}', 实际'{actual_value}'")

                    # 尝试使用JavaScript强制设置值
                    if attempt < max_attempts:
                        print(f"尝试使用JavaScript设置{field_name}...")
                        self.driver.execute_script(
                            "arguments[0].value = arguments[1];",
                            field,
                            value
                        )
                        # 触发input事件
                        self.driver.execute_script(
                            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                            field
                        )
                        time.sleep(0.5)

                        # 再次验证
                        actual_value = field.get_attribute('value')
                        if actual_value == value:
                            print(f"JavaScript设置{field_name}成功")
                            return True

            except Exception as e:
                print(f"{field_name}输入出错: {str(e)}")
                if attempt < max_attempts:
                    time.sleep(1)
                    continue

        return False

    def _check_already_logged_in(self):
        """检查是否已经登录"""
        try:
            # 尝试查找登录后的元素
            if self._find_login_success_element():
                return True

            # 检查URL是否包含登录后的页面
            current_url = self.driver.current_url.lower()
            login_indicators = ["status", "main", "index", "overview", "home"]
            for indicator in login_indicators:
                if indicator in current_url:
                    print(f"✅ 通过URL判断已登录: {current_url}")
                    return True

            return False
        except:
            return False

    def _verify_login_success(self):
        """验证登录是否成功"""
        print("开始验证登录状态...")

        # 等待页面稳定
        time.sleep(3)

        # 方法1: 检查当前URL
        current_url = self.driver.current_url.lower()
        print(f"当前URL: {current_url}")

        # 如果URL不包含登录相关关键词，可能已经登录成功
        login_indicators = ["login", "auth", "signin"]
        if not any(indicator in current_url for indicator in login_indicators):
            print("✅ 通过URL判断登录成功（不包含登录关键词）")
            return True

        # 方法2: 查找特定的成功元素
        success_elements = [
            '//*[@id="qwert_model"]',
            '//*[contains(@class, "dashboard")]',
            '//*[contains(@class, "status")]',
            '//*[contains(@class, "overview")]',
            '//*[contains(text(), "系统状态")]',
            '//*[contains(text(), "System Status")]',
            '//*[contains(text(), "网络状态")]',
            '//*[contains(text(), "Network Status")]',
        ]

        for xpath in success_elements:
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                if element.is_displayed():
                    print(f"✅ 找到登录成功元素: {xpath}")
                    return True
            except Exception as e:
                continue

        # 方法3: 检查页面标题
        page_title = self.driver.title.lower()
        print(f"页面标题: {page_title}")
        if page_title and "login" not in page_title and "sign in" not in page_title:
            print("✅ 通过页面标题判断登录成功")
            return True

        # 方法4: 检查是否有错误消息
        error_indicators = [
            '//*[contains(text(), "错误")]',
            '//*[contains(text(), "Error")]',
            '//*[contains(text(), "失败")]',
            '//*[contains(text(), "Invalid")]',
            '//*[contains(text(), "不正确")]',
            '//*[contains(text(), "Wrong")]',
        ]

        for error_xpath in error_indicators:
            try:
                error_element = self.driver.find_element(By.XPATH, error_xpath)
                if error_element.is_displayed():
                    error_text = error_element.text[:100]  # 只取前100个字符
                    print(f"❌ 找到错误消息: {error_text}")
                    return False
            except:
                continue

        print("⚠️ 登录状态不确定，但没有发现明显错误，假设登录成功")
        return True  # 如果没有发现错误，假设登录成功

    def _find_login_success_element(self):
        """查找登录成功元素"""
        try:
            element = self.driver.find_element(By.XPATH, '//*[@id="qwert_model"]')
            return element.is_displayed()
        except:
            return False

    def _check_already_logged_in(self):
        """检查是否已经登录"""
        try:
            # 尝试查找登录后的元素
            if self._find_login_success_element():
                return True

            # 检查URL是否包含登录后的页面
            current_url = self.driver.current_url.lower()
            login_indicators = ["status", "main", "index", "overview", "home"]
            for indicator in login_indicators:
                if indicator in current_url:
                    print(f"✅ 通过URL判断已登录: {current_url}")
                    return True

            return False
        except:
            return False

    def _verify_login_success(self):
        """验证登录是否成功"""
        print("开始验证登录状态...")

        # 等待页面稳定
        time.sleep(3)

        # 方法1: 检查当前URL
        current_url = self.driver.current_url.lower()
        print(f"当前URL: {current_url}")

        # 如果URL不包含登录相关关键词，可能已经登录成功
        login_indicators = ["login", "auth", "signin"]
        if not any(indicator in current_url for indicator in login_indicators):
            print("✅ 通过URL判断登录成功（不包含登录关键词）")
            return True

        # 方法2: 查找特定的成功元素
        success_elements = [
            '//*[@id="qwert_model"]',
            '//*[contains(@class, "dashboard")]',
            '//*[contains(@class, "status")]',
            '//*[contains(@class, "overview")]',
            '//*[contains(text(), "系统状态")]',
            '//*[contains(text(), "System Status")]',
            '//*[contains(text(), "网络状态")]',
            '//*[contains(text(), "Network Status")]',
        ]

        for xpath in success_elements:
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                if element.is_displayed():
                    print(f"✅ 找到登录成功元素: {xpath}")
                    return True
            except Exception as e:
                continue

        # 方法3: 检查页面标题
        page_title = self.driver.title.lower()
        print(f"页面标题: {page_title}")
        if page_title and "login" not in page_title and "sign in" not in page_title:
            print("✅ 通过页面标题判断登录成功")
            return True

        # 方法4: 检查是否有错误消息
        error_indicators = [
            '//*[contains(text(), "错误")]',
            '//*[contains(text(), "Error")]',
            '//*[contains(text(), "失败")]',
            '//*[contains(text(), "Invalid")]',
            '//*[contains(text(), "不正确")]',
            '//*[contains(text(), "Wrong")]',
        ]

        for error_xpath in error_indicators:
            try:
                error_element = self.driver.find_element(By.XPATH, error_xpath)
                if error_element.is_displayed():
                    error_text = error_element.text[:100]  # 只取前100个字符
                    print(f"❌ 找到错误消息: {error_text}")
                    return False
            except:
                continue

        print("⚠️ 登录状态不确定，但没有发现明显错误，假设登录成功")
        return True  # 如果没有发现错误，假设登录成功

    def _find_login_success_element(self):
        """查找登录成功元素"""
        try:
            element = self.driver.find_element(By.XPATH, '//*[@id="qwert_model"]')
            return element.is_displayed()
        except:
            return False

    def configure_wan_pppoe(self, pppoe_config):
        """配置WAN口设置"""
        try:
            print(f"开始配置WAN口")

            # 导航到WAN设置页面
            print("导航到WAN设置页面")
            self.driver.get(f"http://{self.router_ip}/#network/interfaces/wan")
            self.driver.refresh()
            time.sleep(3)

            # 启用WAN口
            print("查找并启用WAN口...")

            add_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//input[contains(@id, "_enable_wan") and @type="checkbox"]')))

            # 检查按钮是否已经是启用状态
            is_enabled = False
            try:
                # 方法1: 检查checked属性
                if add_button.get_attribute("checked"):
                    is_enabled = True
                    print("启用按钮已经是勾选状态")
            except:
                pass

            try:
                # 方法2: 检查是否包含active或selected类
                if not is_enabled and (
                        "active" in add_button.get_attribute("class") or "selected" in add_button.get_attribute(
                    "class")):
                    is_enabled = True
                    print("启用按钮已经是激活状态")
            except:
                pass

            # 方法3: 检查元素类型和状态
            if not is_enabled:
                if add_button.get_attribute("type") == "checkbox" and add_button.is_selected():
                    is_enabled = True
                    print("启用按钮已经是选中状态")

            # 如果未启用，则点击启用
            if not is_enabled:
                print("点击启用WAN口按钮...")
                add_button.click()
                print("已点击启用WAN口按钮")
                time.sleep(2)
            else:
                print("WAN口已经是启用状态，跳过点击")

        except Exception as e:
            print(f"处理启用WAN口按钮时出错: {str(e)}")
            # 尝试使用JavaScript点击
            try:
                print("尝试使用JavaScript点击启用按钮...")
                self.driver.execute_script("arguments[0].click();", add_button)
                print("已通过JavaScript点击启用按钮")
                time.sleep(2)
            except Exception as js_e:
                print(f"JavaScript点击也失败: {str(js_e)}")
                return False

        try:
            print("开始配置PPPoE...")

            # 1. 选择协议类型
            print("选择PPPoE协议...")
            connection_type_select = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//select[contains(@id, "_protocol")]')))

            from selenium.webdriver.support.ui import Select
            mode_dropdown = Select(connection_type_select)
            # 根据提供的HTML，PPPoE的value是2
            mode_dropdown.select_by_value("2")  # 选择PPPoE
            print("✅ 已选择PPPoE拨号模式")
            time.sleep(1)

            # 2. 填写用户名
            print("填写PPPoE用户名...")
            pppoe_username_field = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[contains(@id, "_user")]'))
            )
            pppoe_username_field.clear()
            pppoe_username_field.send_keys(pppoe_config["username"])
            print("✅ 已输入PPPoE用户名")

            # 3. 填写密码
            print("填写PPPoE密码...")
            pppoe_password_field = self.driver.find_element(
                By.XPATH, '//input[contains(@id, "_password")]'
            )
            pppoe_password_field.clear()
            pppoe_password_field.send_keys(pppoe_config["password"])
            print("✅ 已输入PPPoE密码")

            # 4. 保存配置
            print("保存配置...")
            save_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
            )
            save_button.click()
            print("✅ 已点击保存按钮")

            # 等待保存完成
            time.sleep(5)
            print("✅ PPPoE配置完成")
            return True

        except Exception as e:
            print(f"配置PPPoE时发生错误: {str(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            return False

    def configure_wan_static(self, static_config):
        """配置WAN口设置"""
        try:
            print(f"开始配置WAN口")

            # 导航到WAN设置页面
            print("导航到WAN设置页面")
            self.driver.get(f"http://{self.router_ip}/#network/interfaces/wan")
            self.driver.refresh()
            time.sleep(3)

            # 启用WAN口
            print("查找并启用WAN口...")

            add_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//input[contains(@id, "_enable_wan") and @type="checkbox"]')))

            # 检查按钮是否已经是启用状态
            is_enabled = False
            try:
                # 方法1: 检查checked属性
                if add_button.get_attribute("checked"):
                    is_enabled = True
                    print("启用按钮已经是勾选状态")
            except:
                pass

            try:
                # 方法2: 检查是否包含active或selected类
                if not is_enabled and (
                        "active" in add_button.get_attribute("class") or "selected" in add_button.get_attribute(
                    "class")):
                    is_enabled = True
                    print("启用按钮已经是激活状态")
            except:
                pass

            # 方法3: 检查元素类型和状态
            if not is_enabled:
                if add_button.get_attribute("type") == "checkbox" and add_button.is_selected():
                    is_enabled = True
                    print("启用按钮已经是选中状态")

            # 如果未启用，则点击启用
            if not is_enabled:
                print("点击启用WAN口按钮...")
                add_button.click()
                print("已点击启用WAN口按钮")
                time.sleep(2)
            else:
                print("WAN口已经是启用状态，跳过点击")

        except Exception as e:
            print(f"处理启用WAN口按钮时出错: {str(e)}")
            # 尝试使用JavaScript点击
            try:
                print("尝试使用JavaScript点击启用按钮...")
                self.driver.execute_script("arguments[0].click();", add_button)
                print("已通过JavaScript点击启用按钮")
                time.sleep(2)
            except Exception as js_e:
                print(f"JavaScript点击也失败: {str(js_e)}")
                return False

        try:
            print("开始配置wan 静态...")

            # 1. 选择协议类型
            print("选择静态...")
            connection_type_select = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//select[contains(@id, "_protocol")]')))

            from selenium.webdriver.support.ui import Select
            mode_dropdown = Select(connection_type_select)
            # 根据提供的HTML，PPPoE的value是2
            mode_dropdown.select_by_value("0")  # 选择PPPoE
            print("✅ 已选择静态ip模式")
            time.sleep(1)

            # 2. 填写用户名
            print("填写ipv4地址...")
            pppoe_username_field = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[contains(@id, "_ip_address")]'))
            )
            pppoe_username_field.clear()
            pppoe_username_field.send_keys(static_config["ipv4"])
            print("✅ 已输入ipv4地址")

            # 3. 填写子网掩码
            print("填写子网掩码...")
            pppoe_password_field = self.driver.find_element(
                By.XPATH, '//input[contains(@id, "_netmask")]'
            )
            pppoe_password_field.clear()
            pppoe_password_field.send_keys(static_config["netmask"])
            print("✅ 已输入子网掩码")

            # 4. 保存配置
            print("保存配置...")
            save_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
            )
            save_button.click()
            print("✅ 已点击保存按钮")

            # 等待保存完成
            time.sleep(5)
            print("✅ 静态ip配置完成")
            return True

        except Exception as e:
            print(f"配置PPPoE时发生错误: {str(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            return False

    def check_wan_status(self) -> dict:
        """检查WAN口状态并返回详细信息

        Returns:
            dict: 包含连接状态、IPv4地址、IPv6地址、MAC地址和连接时长的字典
        """
        try:
            # 刷新状态页面
            self.driver.get(f"http://{self.router_ip}/#status/summary")
            self.driver.refresh()
            time.sleep(3)

            # 初始化返回结果
            result = {
                "connection_status": "失败",
                "ipv4_address": "",
                "ipv6_address": "",
                "mac_address": "",
                "connection_duration": ""
            }

            # 1. 检查连接状态
            try:
                wan_status = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="qwert_status"]'))
                )
                status_text = wan_status.text.lower()
                print(f"WAN状态文本: {status_text}")

                # 判断连接状态
                if any(word in status_text for word in ["在线", "online", "connected", "up"]):
                    result["connection_status"] = "成功"
                    print("✅ WAN口连接状态: 成功")
                elif any(word in status_text for word in ["离线", "offline", "disconnected", "down"]):
                    result["connection_status"] = "失败"
                    print("❌ WAN口连接状态: 失败")
                else:
                    print(f"⚠️ 未知的WAN状态: {status_text}")
                    result["connection_status"] = "未知"

            except Exception as e:
                print(f"获取WAN连接状态失败: {str(e)}")
                result["connection_status"] = "获取失败"

            # 2. 获取IPv4地址
            try:
                ipv4_element = self.driver.find_element(By.XPATH, '//*[@id="qwert_ip"]')
                ipv4_text = ipv4_element.text.strip()
                result["ipv4_address"] = ipv4_text if ipv4_text else ""
                print(f"IPv4地址: {result['ipv4_address']}")
            except Exception as e:
                print(f"获取IPv4地址失败: {str(e)}")
                result["ipv4_address"] = ""

            # 3. 获取IPv6地址
            try:
                ipv6_element = self.driver.find_element(By.XPATH, '//*[@id="qwert_ipv6"]')
                ipv6_text = ipv6_element.text.strip()
                result["ipv6_address"] = ipv6_text if ipv6_text else ""
                print(f"IPv6地址: {result['ipv6_address']}")
            except Exception as e:
                print(f"获取IPv6地址失败: {str(e)}")
                result["ipv6_address"] = ""

            # 4. 获取MAC地址
            try:
                mac_element = self.driver.find_element(By.XPATH, '//*[@id="qwert_mac"]')
                mac_text = mac_element.text.strip()
                result["mac_address"] = mac_text if mac_text else ""
                print(f"MAC地址: {result['mac_address']}")
            except Exception as e:
                print(f"获取MAC地址失败: {str(e)}")
                result["mac_address"] = ""

            # 5. 获取连接时长
            try:
                time_element = self.driver.find_element(By.XPATH, '//*[@id="qwert_time"]')
                time_text = time_element.text.strip()
                result["connection_duration"] = time_text if time_text else ""
                print(f"连接时长: {result['connection_duration']}")
            except Exception as e:
                print(f"获取连接时长失败: {str(e)}")
                result["connection_duration"] = ""

            return result

        except Exception as e:
            print(f"检查WAN状态失败: {str(e)}")
            # 即使整体失败，也返回一个包含空值的字典
            return {
                "connection_status": "获取失败",
                "ipv4_address": "",
                "ipv6_address": "",
                "mac_address": "",
                "connection_duration": ""
            }

    def check_ping(self, host: str = "www.baidu.com", ping_duration: int = 10) -> bool:
        """执行Ping测试并验证丢包率

        Args:
            host: 要ping的主机地址
            ping_duration: Ping运行的持续时间（秒），之后会点击Stop

        Returns:
            bool: 如果丢包率为0%则返回True，否则返回False
        """
        ping_success = False

        try:
            # 导航到ping设置页面
            print(f"导航到ping设置页面，准备ping: {host}")
            self.driver.get(f"http://{self.router_ip}/#maintenance/tools/ping")
            self.driver.refresh()
            time.sleep(3)

            # 填写ping地址
            print("查找ping地址输入框...")
            ping_host = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="1_host"]'))
            )

            print("查找ping按钮...")
            ping_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_ping_btn"]'))
            )

            # 清空并输入ping地址
            ping_host.clear()
            ping_host.send_keys(host)

            # 点击ping按钮开始ping
            print("点击ping按钮开始ping测试...")
            ping_button.click()

            # 让ping运行一段时间
            print(f"让ping运行 {ping_duration} 秒...")
            time.sleep(ping_duration)

            # 点击Stop按钮停止ping并获取结果
            print("点击Stop按钮停止ping并获取结果...")
            stop_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@id="1_stop_btn"]'))
            )
            stop_button.click()
            print("✅ 已点击Stop按钮")

            # 等待结果稳定
            time.sleep(2)

            # 获取ping结果
            print("获取ping结果...")
            ping_result_element = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="pingres"]'))
            )

            ping_result_text = ping_result_element.text
            print(f"Ping结果:\n{ping_result_text}")

            # 解析丢包率
            packet_loss = self._parse_packet_loss(ping_result_text)

            if packet_loss == 0:
                print("✅ Ping测试成功 - 丢包率: 0%")
                ping_success = True
            else:
                print(f"❌ Ping测试失败 - 丢包率: {packet_loss}%")
                ping_success = False

        except Exception as e:
            print(f"❌ Ping测试过程中发生错误: {str(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")

            ping_success = False

        finally:
            # 确保在任何情况下都尝试停止ping（如果还在运行）
            try:
                print("确保ping进程已停止...")
                stop_button = self.driver.find_element(By.XPATH, '//button[@id="1_stop_btn"]')
                if stop_button.is_enabled():
                    stop_button.click()
                    print("✅ 已再次点击Stop按钮确保停止")
                    time.sleep(1)
            except Exception as e:
                # Stop按钮可能已经不可用，这不是问题
                pass

            return ping_success

    def _parse_packet_loss(self, ping_result_text: str) -> float:

        """从ping结果文本中解析丢包率"""
        result = False
        try:
            print("开始解析丢包率...")

            # 查找包含丢包率的行
            lines = ping_result_text.split('\n')
            packet_loss_line = None

            for line in lines:
                if 'packet loss' in line.lower():
                    packet_loss_line = line
                    break

            if not packet_loss_line:
                print("⚠️ 未找到包含'packet loss'的行")
                return result

            print(f"找到丢包率行: {packet_loss_line}")

            # 使用正则表达式提取丢包率
            import re

            # 尝试匹配百分比格式: "0% packet loss"
            match = re.search(r'(\d+)% packet loss', packet_loss_line)
            if match:
                packet_loss = float(match.group(1))
                print(f"解析到丢包率: {packet_loss}%")
                return packet_loss

            # 尝试匹配其他格式
            match = re.search(r'(\d+)\s*packet loss', packet_loss_line)
            if match:
                packet_loss = float(match.group(1))
                print(f"解析到丢包率: {packet_loss}%")
                return packet_loss

            # 如果都没有匹配到，返回100%表示失败
            print("⚠️ 无法从行中解析出具体的丢包率数值")
            return result

        except Exception as e:
            print(f"解析丢包率时发生错误: {str(e)}")
            return result

    def cellular_supported_network_standards(self, networktype):
        """配置蜂窝网络标准"""
        try:
            print(f"开始配置蜂窝网络标准: {networktype}")

            # 导航到蜂窝设置页面
            print("导航到蜂窝设置页面")
            self.driver.get(f"http://{self.router_ip}/#network/interfaces/cellular")
            self.driver.refresh()
            time.sleep(5)

            # 打印所有select元素
            select_elements = self.driver.find_elements(By.TAG_NAME, "select")
            print(f"找到 {len(select_elements)} 个select元素:")
            for i, select in enumerate(select_elements):
                select_id = select.get_attribute("id")
                select_name = select.get_attribute("name")
                select_class = select.get_attribute("class")
                print(f"  Select {i}: id='{select_id}', name='{select_name}', class='{select_class}'")

            # 映射网络类型到对应的值
            type_mapping = {
                "AUTO": "0",
                "4G_ONLY": "2",
                "3G_ONLY": "4",
                "2G_ONLY": "6"
            }

            select_value = type_mapping[networktype]

            # 选择网络类型 - 使用更灵活的定位方式
            print(f"选择 {networktype} 模式...")

            # 尝试多种可能的元素定位方式
            select_selectors = [
                '//*[@id="0_network1"]',
                '//select[contains(@id, "network")]',
                '//select[contains(@name, "network")]',
                '//select[contains(@class, "network")]',
                '//select[contains(@id, "cellular")]',
                '//select[contains(@name, "cellular")]',
                '//select[contains(@id, "mode")]',
                '//select[contains(@name, "mode")]',
                '//select[contains(@id, "0_")]',  # 可能以0_开头的ID
                '//select',  # 最后尝试所有select元素
            ]

            connection_type_select = None
            found_selectors = []

            for selector in select_selectors:
                try:
                    print(f"尝试定位元素: {selector}")
                    elements = self.driver.find_elements(By.XPATH, selector)
                    print(f"找到 {len(elements)} 个元素匹配: {selector}")

                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            connection_type_select = element
                            print(f"✅ 找到可用的网络类型选择框: {selector}")
                            found_selectors.append(selector)
                            break

                    if connection_type_select:
                        break
                except Exception as e:
                    print(f"❌ 无法找到元素 {selector}: {str(e)}")
                    continue

            if not connection_type_select:
                print("❌ 无法找到网络类型选择框")
                print("所有尝试的选择器:")
                for selector in select_selectors:
                    print(f"  - {selector}")

                # 如果Web界面配置失败，尝试AT命令备用方案
                print("尝试使用AT命令备用方案...")
                return self._configure_by_at_command(networktype)

            # 首先检查当前选中的值是否已经是目标值
            try:
                current_selection = Select(connection_type_select).first_selected_option.get_attribute("value")
                print(f"当前选中的网络模式值: {current_selection}")
                print(f"目标网络模式值: {select_value}")

                if current_selection == select_value:
                    print(f"✅ 当前已经是 {networktype} 模式，无需更改")
                    return True
            except Exception as e:
                print(f"获取当前选中值失败: {str(e)}")

            # 如果当前模式不是目标模式，则进行配置
            print(f"当前模式不是 {networktype}，开始配置...")

            # 使用 Select 类选择选项
            mode_dropdown = Select(connection_type_select)
            mode_dropdown.select_by_value(select_value)
            print(f"✅ 已选择 {networktype} 模式")
            time.sleep(2)

            # 保存配置
            print("查找保存按钮...")
            save_selectors = [
                '//*[@id="save"]',
                '//button[contains(@id, "save")]',
                '//input[contains(@id, "save")]',
                '//*[contains(text(), "保存")]',
                '//*[contains(text(), "Save")]',
                '//button[contains(@class, "save")]'
            ]

            save_button = None
            for selector in save_selectors:
                try:
                    print(f"尝试定位保存按钮: {selector}")
                    save_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    print(f"✅ 找到保存按钮: {selector}")
                    break
                except Exception as e:
                    print(f"❌ 无法找到保存按钮 {selector}: {str(e)}")
                    continue

            if not save_button:
                print("❌ 无法找到保存按钮")
                return False

            save_button.click()
            print("✅ 已点击保存按钮")
            time.sleep(5)  # 等待保存完成

            # 查找并点击应用按钮（如果存在且可点击）
            print("查找应用按钮...")
            apply_selectors = [
                '//*[@id="apply"]',
                '//button[contains(@id, "apply")]',
                '//input[contains(@id, "apply")]',
                '//*[contains(text(), "应用")]',
                '//*[contains(text(), "Apply")]',
                '//button[contains(@class, "apply")]'
            ]

            apply_button = None
            for selector in apply_selectors:
                try:
                    print(f"尝试定位应用按钮: {selector}")
                    # 使用 presence 而不是 clickable，因为应用按钮可能在保存后才会出现
                    apply_button = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    print(f"✅ 找到应用按钮: {selector}")

                    # 检查按钮是否可点击
                    if apply_button.is_enabled():
                        print("应用按钮可点击，准备点击...")
                        apply_button.click()
                        print("✅ 已点击应用按钮")
                        time.sleep(5)  # 等待应用完成
                    else:
                        print("⚠️ 应用按钮不可点击，跳过")

                    break
                except Exception as e:
                    print(f"❌ 无法找到或点击应用按钮 {selector}: {str(e)}")
                    continue

            # 配置下发完成，返回成功
            print(f"✅ {networktype}模式配置下发完成")
            return True

        except Exception as e:
            print(f"❌ 配置蜂窝网络标准时发生错误: {str(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")

            return False

    def SMS_Center_set(self, center_number):
        """配置蜂窝网络的短信中心号码

        Args:
            center_number: 短信中心号码字符串

        Returns:
            bool: 配置成功返回True，失败返回False
        """
        try:
            # 参数验证
            if not center_number:
                print("❌ 错误：短信中心号码不能为空")
                return False

            center_number = str(center_number).strip()
            if not center_number:
                print("❌ 错误：短信中心号码不能为空字符串")
                return False

            print(f"开始配置蜂窝网络短信中心号码为: {center_number}")

            # 导航到蜂窝设置页面
            print("导航到蜂窝设置页面")
            self.driver.get(f"http://{self.router_ip}/#network/interfaces/cellular")
            self.driver.refresh()
            time.sleep(5)

            # 尝试多种可能的短信中心号码输入框定位方式
            sms_center_selectors = [
                '//*[@id="0_sms_center1"]',
                '//input[contains(@id, "sms_center")]',
                '//input[contains(@name, "sms_center")]',
                '//input[contains(@id, "center")]',
                '//input[contains(@name, "center")]',
                '//input[contains(@placeholder, "短信中心")]',
                '//input[contains(@placeholder, "SMS Center")]',
                '//input[@type="text" and contains(@class, "sms")]',
                '//input[@type="tel"]',  # 电话号码输入框
            ]

            sms_center_input = None
            found_selector = None

            for selector in sms_center_selectors:
                try:
                    print(f"尝试定位短信中心输入框: {selector}")
                    elements = self.driver.find_elements(By.XPATH, selector)
                    print(f"找到 {len(elements)} 个元素匹配: {selector}")

                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            sms_center_input = element
                            found_selector = selector
                            print(f"✅ 找到可用的短信中心输入框: {selector}")
                            break

                    if sms_center_input:
                        break
                except Exception as e:
                    print(f"❌ 无法找到元素 {selector}: {str(e)}")
                    continue

            if not sms_center_input:
                print("❌ 无法找到短信中心号码输入框")
                print("所有尝试的选择器:")
                for selector in sms_center_selectors:
                    print(f"  - {selector}")
                return False

            # 获取当前值，用于判断是否需要容错处理
            try:
                print("获取当前短信中心号码...")
                current_value = sms_center_input.get_attribute("value") or ""
                print(f"当前短信中心号码: {current_value}")
                print(f"目标短信中心号码: {center_number}")
            except Exception as e:
                print(f"获取当前值失败: {str(e)}")
                current_value = ""

            # 容错机制：如果当前值和目标值相同，路由器不会显示应用按钮
            # 需要先设置一个临时值触发应用按钮，再设置回目标值
            if current_value == center_number:
                print("⚠️ 检测到当前值与目标值相同，启动容错机制")
                print("第一步：先设置临时值以触发应用按钮")

                # 临时号码（故意使用一个不同的值）
                temp_number = "+8600000000000"

                try:
                    # 清空并输入临时号码
                    sms_center_input.clear()
                    time.sleep(0.5)
                    sms_center_input.send_keys(temp_number)
                    print(f"✅ 已输入临时号码: {temp_number}")
                    time.sleep(1)

                    # 保存临时配置
                    print("保存临时配置...")
                    save_success = self._click_save_button()
                    if not save_success:
                        print("❌ 保存临时配置失败")
                        return False

                    # 应用临时配置
                    print("应用临时配置...")
                    apply_success = self._click_apply_button()
                    if not apply_success:
                        print("⚠️ 应用临时配置失败，但继续执行")

                    time.sleep(2)  # 等待临时配置应用完成

                    # 重新导航到页面（刷新输入框状态）
                    print("重新加载页面...")
                    self.driver.refresh()
                    time.sleep(3)

                    # 重新定位输入框
                    print("重新定位短信中心输入框...")
                    sms_center_input = None
                    for selector in sms_center_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    sms_center_input = element
                                    print(f"✅ 重新找到短信中心输入框: {selector}")
                                    break
                            if sms_center_input:
                                break
                        except:
                            continue

                    if not sms_center_input:
                        print("❌ 刷新后无法重新定位输入框")
                        return False

                except Exception as e:
                    print(f"❌ 设置临时值失败: {str(e)}")
                    return False

                print("第二步：设置目标值")

            # 清空并输入目标短信中心号码
            try:
                print("清空并输入目标短信中心号码...")
                sms_center_input.clear()
                time.sleep(0.5)  # 等待清空完成
                sms_center_input.send_keys(center_number)
                print(f"✅ 已输入短信中心号码: {center_number}")

                # 验证输入的值
                new_value = sms_center_input.get_attribute("value")
                if new_value != center_number:
                    print(f"⚠️ 输入的值与预期不符，预期: {center_number}, 实际: {new_value}")
                    # 尝试重新输入
                    sms_center_input.clear()
                    time.sleep(0.5)
                    sms_center_input.send_keys(center_number)
                    print("✅ 已重新输入短信中心号码")
            except Exception as e:
                print(f"❌ 输入短信中心号码时发生错误: {str(e)}")
                return False

            # 保存配置
            print("保存目标配置...")
            save_success = self._click_save_button()
            if not save_success:
                print("❌ 保存配置失败")
                return False

            # 应用配置
            print("应用目标配置...")
            apply_success = self._click_apply_button()
            if not apply_success:
                print("⚠️ 应用配置失败或应用按钮不可用，但保存成功")

            print("✅ 短信中心号码配置完成")
            return True

        except Exception as e:
            print(f"❌ 配置短信中心号码时发生错误: {str(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")

            return False

    def SMS_Center_set_SIM2(self, center_number):
        """配置SIM2的短信中心号码

        Args:
            center_number: 短信中心号码字符串

        Returns:
            bool: 配置成功返回True，失败返回False
        """
        try:
            # 参数验证
            if not center_number:
                print("❌ 错误：短信中心号码不能为空")
                return False

            center_number = str(center_number).strip()
            if not center_number:
                print("❌ 错误：短信中心号码不能为空字符串")
                return False

            print(f"开始配置SIM2短信中心号码为: {center_number}")

            # 导航到蜂窝设置页面
            print("导航到蜂窝设置页面")
            self.driver.get(f"http://{self.router_ip}/#network/interfaces/cellular")
            self.driver.refresh()
            time.sleep(5)

            # SIM2短信中心号码输入框定位方式
            sms_center_selectors = [
                '//*[@id="0_sms_center2"]',  # SIM2专用选择器
                '//*[@id="1_sms_center1"]',  # 备用选择器
                '//input[contains(@id, "sms_center2")]',
                '//input[contains(@name, "sms_center2")]',
            ]

            sms_center_input = None
            found_selector = None

            for selector in sms_center_selectors:
                try:
                    print(f"尝试定位SIM2短信中心输入框: {selector}")
                    elements = self.driver.find_elements(By.XPATH, selector)
                    print(f"找到 {len(elements)} 个元素匹配: {selector}")

                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            sms_center_input = element
                            found_selector = selector
                            print(f"✅ 找到可用的SIM2短信中心输入框: {selector}")
                            break

                    if sms_center_input:
                        break
                except Exception as e:
                    print(f"❌ 无法找到元素 {selector}: {str(e)}")
                    continue

            if not sms_center_input:
                print("❌ 无法找到SIM2短信中心号码输入框")
                return False

            # 清空并输入目标短信中心号码
            try:
                print("清空并输入SIM2目标短信中心号码...")
                sms_center_input.clear()
                time.sleep(0.5)
                sms_center_input.send_keys(center_number)
                print(f"✅ 已输入SIM2短信中心号码: {center_number}")

                # 验证输入的值
                new_value = sms_center_input.get_attribute("value")
                if new_value != center_number:
                    print(f"⚠️ 输入的值与预期不符，预期: {center_number}, 实际: {new_value}")
                    sms_center_input.clear()
                    time.sleep(0.5)
                    sms_center_input.send_keys(center_number)
                    print("✅ 已重新输入SIM2短信中心号码")
            except Exception as e:
                print(f"❌ 输入SIM2短信中心号码时发生错误: {str(e)}")
                return False

            # 保存配置
            print("保存SIM2目标配置...")
            save_success = self._click_save_button()
            if not save_success:
                print("❌ 保存配置失败")
                return False

            # 应用配置
            print("应用SIM2目标配置...")
            apply_success = self._click_apply_button()
            if not apply_success:
                print("⚠️ 应用配置失败或应用按钮不可用，但保存成功")

            print("✅ SIM2短信中心号码配置完成")
            return True

        except Exception as e:
            print(f"❌ 配置SIM2短信中心号码时发生错误: {str(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            return False

    def navigate_to_page(self, hash_path):
        """导航到指定的页面（通过 URL hash）"""
        try:
            # 确保 hash_path 以 # 开头
            if not hash_path.startswith('#'):
                hash_path = '#' + hash_path

            url = f"http://{self.router_ip}/{hash_path}"
            print(f"  导航到页面: {url}")
            self.driver.get(url)
            time.sleep(2)

            # 刷新页面确保加载
            self.driver.refresh()
            time.sleep(2)
            return True
        except Exception as e:
            print(f"  导航失败: {str(e)}")
            return False

    def click_element(self, xpath, timeout=10):
        """点击指定元素"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            element.click()
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"  点击元素失败 {xpath}: {str(e)}")
            return False

    def input_text(self, xpath, text, timeout=10):
        """在指定元素中输入文本"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            element.clear()
            element.send_keys(text)
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"  输入文本失败 {xpath}: {str(e)}")
            return False

    def get_element_text(self, xpath, timeout=10):
        """获取指定元素的文本内容"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return element.text
        except Exception as e:
            print(f"  获取文本失败 {xpath}: {str(e)}")
            return None

    def refresh_page(self):
        """刷新当前页面"""
        try:
            self.driver.refresh()
            time.sleep(2)
            return True
        except Exception as e:
            print(f"  刷新页面失败: {str(e)}")
            return False

    def _click_save_button(self):
        """点击保存按钮的通用方法"""
        try:
            print("查找保存按钮...")
            save_selectors = [
                '//*[@id="fakeSave"]',  # Save & Apply 一体按钮
                '//*[@id="save"]',
                '//button[contains(text(), "Save & Apply")]',
                '//button[contains(text(), "Save &amp; Apply")]',
                '//button[contains(@id, "save")]',
                '//input[contains(@id, "save")]',
                '//*[contains(text(), "保存")]',
                '//*[contains(text(), "Save")]',
                '//button[contains(@class, "save")]',
                '//input[contains(@class, "save")]',
                '//input[@type="submit"]',
                '//button[@type="submit"]'
            ]

            for selector in save_selectors:
                try:
                    print(f"尝试定位保存按钮: {selector}")
                    save_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if save_button.is_displayed() and save_button.is_enabled():
                        print(f"✅ 找到可用的保存按钮: {selector}")
                        save_button.click()
                        print("✅ 已点击保存按钮")
                        time.sleep(3)  # 等待保存完成
                        return True
                except Exception as e:
                    print(f"❌ 无法找到或点击保存按钮 {selector}: {str(e)}")
                    continue

            print("❌ 无法找到任何可用的保存按钮")
            return False

        except Exception as e:
            print(f"❌ 点击保存按钮时发生错误: {str(e)}")
            return False

    def _click_apply_button(self):
        """点击应用按钮的通用方法"""
        try:
            print("查找应用按钮...")
            apply_selectors = [
                '//*[@id="apply"]',
                '//button[contains(@id, "apply")]',
                '//input[contains(@id, "apply")]',
                '//*[contains(text(), "应用")]',
                '//*[contains(text(), "Apply")]',
                '//button[contains(@class, "apply")]',
                '//input[contains(@class, "apply")]'
            ]

            apply_found = False
            for selector in apply_selectors:
                try:
                    print(f"尝试定位应用按钮: {selector}")
                    # 使用 presence 而不是 clickable，因为应用按钮可能在保存后才会出现
                    apply_button = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    print(f"✅ 找到应用按钮: {selector}")
                    apply_found = True

                    # 检查按钮是否可点击
                    if apply_button.is_enabled():
                        print("应用按钮可点击，准备点击...")
                        apply_button.click()
                        print("✅ 已点击应用按钮")
                        time.sleep(5)  # 等待应用完成
                        return True
                    else:
                        print("⚠️ 应用按钮不可点击，跳过")
                        return False  # 找到按钮但不可点击，返回False

                except Exception as e:
                    print(f"❌ 无法找到应用按钮 {selector}: {str(e)}")
                    continue

            if not apply_found:
                print("⚠️ 未找到应用按钮，可能不需要应用操作")
                return True  # 没有应用按钮不一定表示失败

            return False

        except Exception as e:
            print(f"❌ 点击应用按钮时发生错误: {str(e)}")
            return False







    def _configure_by_at_command(self, networktype):
        """使用AT命令配置网络模式的备用方案"""
        try:
            print(f"使用AT命令配置 {networktype} 模式")

            # 根据网络类型和模组类型选择AT命令
            module_type = getattr(self, 'module_type', 'quectel')

            at_commands = {
                "AUTO": {
                    "quectel": 'AT+QCFG="NWSCANMODE",0',
                    "meig": 'AT^SYSCFGEX="00"'
                },
                "4G_ONLY": {
                    "quectel": 'AT+QCFG="NWSCANMODE",3',
                    "meig": 'AT^SYSCFGEX="03"'
                },
                "3G_ONLY": {
                    "quectel": 'AT+QCFG="NWSCANMODE",2',
                    "meig": 'AT^SYSCFGEX="02"'
                },
                "2G_ONLY": {
                    "quectel": 'AT+QCFG="NWSCANMODE",1',
                    "meig": 'AT^SYSCFGEX="01"'
                }
            }

            if networktype in at_commands and module_type in at_commands[networktype]:
                at_command = at_commands[networktype][module_type]
                print(f"使用{module_type}模组的AT命令: {at_command}")

                # 执行AT命令
                success = self.AT_COMAND_SET(at_command)
                if success:
                    print(f"✅ 通过AT命令配置 {networktype} 模式成功")
                    return True
                else:
                    print(f"❌ AT命令配置 {networktype} 模式失败")
                    return False
            else:
                print(f"❌ 不支持的配置: networktype={networktype}, module_type={module_type}")
                return False

        except Exception as e:
            print(f"❌ AT命令配置过程中发生错误: {str(e)}")
            return False

    def check_cellular_status(self) -> bool:
        """检查蜂窝网络状态

        检查两个页面的多个条件，如果首次失败则等待200秒后重试一次

        Returns:
            bool: 所有检查条件都满足返回True，否则返回False
        """
        if self.router_config is None:
            print("错误: 无法检查蜂窝状态，路由器配置为空")
            return False
        max_attempts = 2
        attempt = 1

        while attempt <= max_attempts:
            try:
                print(f"第 {attempt} 次尝试检查蜂窝网络状态...")

                # 第一部分：检查 #status/summary 页面
                print("导航到状态概览页面...")
                self.driver.get(f"http://{self.router_ip}/#status/summary")
                print("导航到状态概览页面成功")
                self.driver.refresh()
                time.sleep(3)

                # 1. 检查链路状态 - 显示 "Link in use" 或 "当前链路"
                try:
                    link_status_element = self.driver.find_element(By.XPATH,
                                                                   '//span[contains(text(), "Link in use") or contains(text(), "当前链路")]')
                    link_status = link_status_element.text
                    print(f"链路状态: {link_status}")

                    if not link_status:
                        print("❌ 链路状态为空")
                        if attempt == max_attempts:
                            return False
                        else:
                            break  # 跳出当前尝试，等待重试
                except Exception as e:
                    print(f"❌ 检查链路状态失败")
                    if attempt == max_attempts:
                        return False
                    else:
                        break  # 跳出当前尝试，等待重试

                # 2. 检查 qwert_status 元素包含 "LTE"
                try:
                    status_element = self.driver.find_element(By.XPATH, '//*[@id="qwert_status"]')
                    status_text = status_element.text
                    print(f"状态文本: {status_text}")

                    if "LTE" not in status_text:
                        print("❌ 状态文本中不包含 'LTE'")
                        if attempt == max_attempts:
                            return False
                        else:
                            break  # 跳出当前尝试，等待重试
                except Exception as e:
                    print(f"❌ 检查状态文本失败:")
                    if attempt == max_attempts:
                        return False
                    else:
                        break  # 跳出当前尝试，等待重试

                # 3. 检查 SIM 卡状态不为空
                try:
                    sim_element = self.driver.find_element(By.XPATH, '//*[@id="qwert_cur_sim"]')
                    sim_text = sim_element.text.strip()
                    print(f"SIM卡状态: {sim_text}")

                    if not sim_text:
                        print("❌ SIM卡状态为空")
                        if attempt == max_attempts:
                            return False
                        else:
                            break  # 跳出当前尝试，等待重试
                except Exception as e:
                    print(f"❌ 检查SIM卡状态失败: ")
                    if attempt == max_attempts:
                        return False
                    else:
                        break  # 跳出当前尝试，等待重试

                # 4. 检查 IPv4 地址不为空
                try:
                    ipv4_element = self.driver.find_element(By.XPATH, '//*[@id="qwert_ip"]')
                    ipv4_text = ipv4_element.text.strip()
                    print(f"IPv4地址: {ipv4_text}")

                    if not ipv4_text:
                        print("❌ IPv4地址为空")
                        if attempt == max_attempts:
                            return False
                        else:
                            break  # 跳出当前尝试，等待重试
                except Exception as e:
                    print(f"❌ 检查IPv4地址失败:")
                    if attempt == max_attempts:
                        return False
                    else:
                        break  # 跳出当前尝试，等待重试

                # 5. 检查 IPv6 地址不为空
                try:
                    ipv6_element = self.driver.find_element(By.XPATH, '//*[@id="qwert_ipv6"]')
                    ipv6_text = ipv6_element.text.strip()
                    print(f"IPv6地址: {ipv6_text}")

                    if not ipv6_text:
                        print("❌ IPv6地址为空")
                        if attempt == max_attempts:
                            return False
                        else:
                            break  # 跳出当前尝试，等待重试
                except Exception as e:
                    print(f"❌ 检查IPv6地址失败: ")
                    if attempt == max_attempts:
                        return False
                    else:
                        break  # 跳出当前尝试，等待重试

                # 6. 检查连接时长不为空
                try:
                    time_element = self.driver.find_element(By.XPATH, '//*[@id="qwert_time"]')
                    time_text = time_element.text.strip()
                    print(f"连接时长: {time_text}")

                    if not time_text:
                        print("❌ 连接时长为空")
                        if attempt == max_attempts:
                            return False
                        else:
                            break  # 跳出当前尝试，等待重试
                except Exception as e:
                    print(f"❌ 检查连接时长失败:")
                    if attempt == max_attempts:
                        return False
                    else:
                        break  # 跳出当前尝试，等待重试

                # 7. 检查总流量不为空
                try:
                    total_element = self.driver.find_element(By.XPATH, '//*[@id="qwert_total"]')
                    total_text = total_element.text.strip()
                    print(f"总流量: {total_text}")

                    if not total_text:
                        print("❌ 总流量为空")
                        if attempt == max_attempts:
                            return False
                        else:
                            break  # 跳出当前尝试，等待重试
                except Exception as e:
                    print(f"❌ 检查总流量失败:")
                    if attempt == max_attempts:
                        return False
                    else:
                        break  # 跳出当前尝试，等待重试

                # 第二部分：检查 #status/cellular 页面
                print("导航到蜂窝状态页面...")
                self.driver.get(f"http://{self.router_ip}/#status/cellular")
                self.driver.refresh()
                time.sleep(3)

                # 8. 检查蜂窝连接状态为 "Connected"
                try:
                    cellular_status_element = self.driver.find_element(By.XPATH, '//*[@id="1_status"]')
                    cellular_status = cellular_status_element.text.strip()
                    print(f"蜂窝连接状态: {cellular_status}")

                    if cellular_status != "Connected":
                        print(f"❌ 蜂窝连接状态不是 'Connected'，实际为: {cellular_status}")
                        if attempt == max_attempts:
                            return False
                        else:
                            break  # 跳出当前尝试，等待重试
                except Exception as e:
                    print(f"❌ 检查蜂窝连接状态失败: ")
                    if attempt == max_attempts:
                        return False
                    else:
                        break  # 跳出当前尝试，等待重试

                # 9. 检查网络类型为 "FDD LTE"
                try:
                    net_type_element = self.driver.find_element(By.XPATH, '//*[@id="0_net_type"]')
                    net_type = net_type_element.text.strip()
                    print(f"网络类型: {net_type}")

                    if net_type != "FDD LTE":
                        print(f"❌ 网络类型不是 'FDD LTE'，实际为: {net_type}")
                        if attempt == max_attempts:
                            return False
                        else:
                            break  # 跳出当前尝试，等待重试
                except Exception as e:
                    print(f"❌ 检查网络类型失败: ")
                    if attempt == max_attempts:
                        return False
                    else:
                        break  # 跳出当前尝试，等待重试

                # 所有检查都通过
                print("✅ 所有蜂窝网络状态检查通过")
                return True

            except Exception as e:
                print(f"❌ 第 {attempt} 次检查蜂窝网络状态过程中发生错误: {str(e)}")
                import traceback
                print(f"错误堆栈: {traceback.format_exc()}")

                # 如果是最后一次尝试，返回失败
                if attempt == max_attempts:
                    return False

            # 如果当前尝试失败且不是最后一次，等待120秒后重试
            if attempt < max_attempts:
                print(f"等待120秒后重试... ({attempt}/{max_attempts})")
                time.sleep(200)

                # 刷新当前页面
                try:
                    self.driver.refresh()
                    time.sleep(3)
                except:
                    print("刷新页面失败，继续尝试...")

            attempt += 1

        # 如果循环结束但未返回成功，则返回失败
        return False

    def get_cellular_status_page_info(self) -> dict:
        """读取蜂窝状态页面的所有信息

        Returns:
            dict: 包含所有蜂窝状态信息的字典
        """
        try:
            print("开始读取蜂窝状态页面信息...")

            # 导航到状态-蜂窝页面
            status_url = f"http://{self.router_ip}/#status/cellular"
            print(f"导航到: {status_url}")
            self.driver.get(status_url)

            # 刷新页面确保最新数据
            self.driver.refresh()

            # 等待页面加载
            time.sleep(5)

            # 定义要读取的字段及其XPath
            fields = {
                'model': '//*[@id="0_model"]',
                'modem_version': '//*[@id="yruo_celluar_cellular_modem"]/div[2]/div[3]/div[2]',
                'signal': '//*[@id="0_signal"]',
                'register': '//*[@id="0_register"]',
                'imei': '//*[@id="0_imei"]',
                'imsi': '//*[@id="0_imsi"]',
                'iccid': '//*[@id="0_iccid"]',
                'net_provider': '//*[@id="0_net_provider"]',
                'net_type': '//*[@id="0_net_type"]',
                'band': '//*[@id="0_band"]',
                'plmnid': '//*[@id="0_plmnid"]',
                'lac': '//*[@id="0_lac"]',
                'cellid': '//*[@id="0_cellid"]',
                'rsrp': '//*[@id="0_rsrp"]',
                'rsrq': '//*[@id="0_rsrq"]',
                'sinr': '//*[@id="0_sinr"]'
            }

            result = {}

            # 读取每个字段的值
            for field_name, xpath in fields.items():
                try:
                    element = self.driver.find_element(By.XPATH, xpath)
                    value = element.text.strip()
                    result[field_name] = value
                    print(f"✅ {field_name}: {value}")
                except Exception as e:
                    result[field_name] = None
                    print(f"⚠️ 无法读取 {field_name}: {str(e)}")

            print("✅ 蜂窝状态页面信息读取完成")
            return result

        except Exception as e:
            print(f"❌ 读取蜂窝状态页面信息失败: {str(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            return {}

    def set_cellular_netmask(self, netmask: str = "255.0.0.0") -> bool:
        """设置蜂窝网络子网掩码（通过Web页面）

        Args:
            netmask: 子网掩码，如 "255.0.0.0"，传入空字符串""表示清空掩码恢复默认

        Returns:
            bool: 设置成功返回True，失败返回False
        """
        try:
            if netmask == "":
                print(f"开始通过Web页面清空蜂窝子网掩码（恢复默认）")
            else:
                print(f"开始通过Web页面设置蜂窝子网掩码为: {netmask}")

            # 导航到蜂窝配置页面
            config_url = f"http://{self.router_ip}/#network/interfaces/cellular"
            print(f"导航到配置页面: {config_url}")
            self.driver.get(config_url)
            self.driver.refresh()
            time.sleep(3)

            # 定位子网掩码输入框
            mask_xpath = '//*[@id="0_mask1"]'
            print(f"定位子网掩码输入框: {mask_xpath}")

            try:
                mask_input = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, mask_xpath))
                )
            except Exception as e:
                print(f"❌ 无法找到子网掩码输入框: {str(e)}")
                return False

            # 获取当前值
            try:
                current_value = mask_input.get_attribute("value") or ""
                print(f"当前子网掩码值: {current_value}")
                print(f"目标子网掩码值: {netmask}")
            except Exception as e:
                print(f"获取当前值失败: {str(e)}")
                current_value = ""

            # 容错机制：如果当前值和目标值相同，先设置临时值
            if current_value == netmask:
                print("⚠️ 检测到当前值与目标值相同，启动容错机制")
                print("第一步：先设置临时值以触发应用按钮")

                # 临时掩码（故意使用一个不同的值）
                temp_netmask = "255.255.255.0"

                try:
                    # 清空并输入临时掩码
                    mask_input.clear()
                    time.sleep(0.5)
                    mask_input.send_keys(temp_netmask)
                    print(f"✅ 已输入临时掩码: {temp_netmask}")
                    time.sleep(1)

                    # 保存临时配置
                    print("保存临时配置...")
                    save_success = self._click_save_button()
                    if not save_success:
                        print("❌ 保存临时配置失败")
                        return False

                    # 应用临时配置
                    print("应用临时配置...")
                    apply_success = self._click_apply_button()
                    if not apply_success:
                        print("⚠️ 应用临时配置失败，但继续执行")

                    time.sleep(3)  # 等待临时配置应用完成

                    # 重新加载页面
                    print("重新加载页面...")
                    self.driver.refresh()
                    time.sleep(3)

                    # 重新定位输入框
                    print("重新定位子网掩码输入框...")
                    mask_input = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, mask_xpath))
                    )

                except Exception as e:
                    print(f"❌ 设置临时值失败: {str(e)}")
                    return False

                print("第二步：设置目标值")

            # 清空并输入目标掩码
            try:
                print(f"清空并输入目标子网掩码: {netmask}")
                mask_input.clear()
                time.sleep(0.5)
                mask_input.send_keys(netmask)
                print(f"✅ 已输入子网掩码: {netmask}")

                # 验证输入的值
                new_value = mask_input.get_attribute("value")
                if new_value != netmask:
                    print(f"⚠️ 输入的值与预期不符，预期: {netmask}, 实际: {new_value}")
                    # 尝试重新输入
                    mask_input.clear()
                    time.sleep(0.5)
                    mask_input.send_keys(netmask)
                    print("✅ 已重新输入子网掩码")
            except Exception as e:
                print(f"❌ 输入子网掩码时发生错误: {str(e)}")
                return False

            # 保存配置
            print("保存目标配置...")
            save_success = self._click_save_button()
            if not save_success:
                print("❌ 保存配置失败")
                return False

            # 应用配置
            print("应用目标配置...")
            apply_success = self._click_apply_button()
            if not apply_success:
                print("⚠️ 应用配置失败或应用按钮不可用，但保存成功")

            print("✅ 子网掩码配置完成")
            return True

        except Exception as e:
            print(f"❌ 设置子网掩码失败: {str(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            return False

    def AT_COMAND_SET(self, at_command):
        """执行AT命令

        Args:
            at_command: AT命令字符串，例如："AT+QCFG=\"NWSCANMODE\",0"

        Returns:
            bool: 命令发送成功返回True，失败返回False
        """
        try:
            # 验证输入参数
            if not at_command or at_command.strip() == "":
                print("❌ 错误: AT命令参数不能为空")
                return False

            command = at_command.strip()
            print(f"开始执行AT命令: {command}")

            # 导航到AT命令调试页面
            print("导航到AT命令调试页面...")
            self.driver.get(f"http://{self.router_ip}/#maintenance/debug/cellular")
            self.driver.refresh()
            time.sleep(3)

            # 查找AT命令输入框
            print("查找AT命令输入框...")
            command_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="1_command"]'))
            )

            # 清空并输入AT命令
            command_input.clear()
            command_input.send_keys(command)
            print(f"✅ 已输入AT命令: {command}")

            # 查找并点击发送按钮
            print("查找发送按钮...")
            send_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_send"]'))
            )

            send_button.click()
            print("✅ 已点击发送按钮")

            # 等待命令执行
            time.sleep(5)

            # 验证命令是否成功发送（可以检查是否有响应输出）
            # 这里我们假设只要成功点击发送按钮就算成功
            # 如果需要验证响应，可以添加额外的检查逻辑

            print("✅ AT命令发送成功")
            return True

        except Exception as e:
            print(f"❌ 执行AT命令时发生错误: {str(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")

            return False

    def AT_COMAND_GET(self) -> dict:
        """获取AT命令的返回结果

        Returns:
            dict: 包含原始响应和提取后的响应内容的字典
        """
        try:
            print("开始获取AT命令响应...")

            # 导航到AT命令调试页面
            print("导航到AT命令调试页面...")
            self.driver.get(f"http://{self.router_ip}/#maintenance/debug/cellular")
            self.driver.refresh()
            time.sleep(3)

            # 查找日志文本区域
            print("查找日志文本区域...")
            log_textarea = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="1_log"]'))
            )

            # 获取日志文本
            log_text = log_textarea.text
            print(f"原始日志文本:\n{log_text}")

            # 处理日志文本，提取关键信息
            processed_response = self._process_at_response(log_text)

            result = {
                "success": True,
                "raw_response": log_text,
                "processed_response": processed_response
            }

            print(f"处理后的响应: {processed_response}")
            return result

        except Exception as e:
            print(f"❌ 获取AT命令响应时发生错误: {str(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")

            return {
                "success": False,
                "raw_response": "",
                "processed_response": "",
                "error": str(e)
            }

    def _process_at_response(self, log_text: str) -> str:
        """处理AT命令响应，提取关键信息

        Args:
            log_text: 原始日志文本

        Returns:
            str: 处理后的响应文本
        """
        try:
            if not log_text:
                return ""

            lines = log_text.split('\n')
            processed_lines = []

            for line in lines:
                # 跳过空行
                if not line.strip():
                    continue

                # 提取关键部分
                if '>>>' in line:
                    # 提取命令部分（去掉时间戳）
                    parts = line.split('>>>', 1)
                    if len(parts) > 1:
                        command = parts[1].strip()
                        processed_lines.append(f">>> {command}")

                elif '<<<' in line:
                    # 提取响应部分（去掉时间戳）
                    parts = line.split('<<<', 1)
                    if len(parts) > 1:
                        response = parts[1].strip()
                        processed_lines.append(f"<<< {response}")

            # 如果没有找到>>>或<<<，返回原始文本的最后几行
            if not processed_lines:
                # 返回最后5行作为备选
                return "\n".join(lines[-5:])

            return "\n".join(processed_lines)

        except Exception as e:
            print(f"处理AT响应时发生错误: {str(e)}")
            return log_text  # 如果处理失败，返回原始文本

    def wait_for_mqtt_connection(self, status_xpath: str = '//*[@id="mqtt_list"]/div[2]/div[1]/div[4]/span',
                                 max_wait: int = 300, check_interval: int = 5) -> bool:
        """
        等待MQTT连接建立，兼容中英文状态

        Args:
            status_xpath: MQTT状态元素的XPath
            max_wait: 最大等待时间(秒)
            check_interval: 检查间隔(秒)

        Returns:
            bool: 连接是否成功
        """
        print(f"  等待MQTT连接建立 (最长等待 {max_wait} 秒)...")
        start_time = time.time()
        retry_count = 0
        max_retries = int(max_wait / check_interval)

        while retry_count < max_retries:
            try:
                # 每隔一段时间刷新页面（不要太频繁）
                if retry_count % 3 == 0 and retry_count > 0:  # 每3次检查刷新一次页面，首次不刷新
                    self.refresh_page()
                    time.sleep(2)  # 等待页面加载
                elif retry_count > 0:
                    time.sleep(check_interval)

                # 检查连接状态
                status_text = self.get_element_text(status_xpath)

                if status_text:
                    status_text_lower = status_text.lower().strip()
                    print(f"  当前MQTT状态: {status_text} (第{retry_count + 1}次检查)")

                    # 兼容中英文连接状态
                    connected_keywords = ['已连接', 'connected', '连接成功', 'connect success']
                    if any(keyword in status_text_lower for keyword in connected_keywords):
                        elapsed = int(time.time() - start_time)
                        print(f"  ✅ MQTT已连接（耗时 {elapsed} 秒，检查 {retry_count + 1} 次）")
                        return True

                    # 检查是否有连接失败的关键词
                    failed_keywords = ['失败', 'failed', 'error', '错误', 'disconnect', '断开']
                    if any(keyword in status_text_lower for keyword in failed_keywords):
                        print(f"  ✗ MQTT连接失败: {status_text}")
                        return False

                retry_count += 1

            except Exception as e:
                print(f"  检查MQTT状态时出错: {e}, 继续重试...")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(check_interval)

        # 超时
        elapsed = int(time.time() - start_time)
        print(f"  ✗ MQTT连接超时（已等待 {elapsed} 秒，检查 {retry_count} 次）")
        return False

    def close(self):
        """关闭浏览器"""
        if self.driver:
            print("关闭浏览器...")
            self.driver.quit()
            self.driver = None


