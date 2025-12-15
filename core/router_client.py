import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import time
from models.test_config import RouterConfig


class RouterClient:
    def __init__(self, router_config: RouterConfig = None, router_ip: str = None, username: str = None,
                 password: str = None, model: str = None, module_type: str = "auto", incognito_mode: bool = True):
        # 支持两种初始化方式：RouterConfig对象 或 独立参数
        if router_config is not None:
            # 使用RouterConfig对象初始化
            self.router_config = router_config
            self.router_ip = router_config.router_ip
            self.username = router_config.username
            self.password = router_config.password
            self.model = router_config.model
            self.module_type = router_config.module_type if hasattr(router_config, 'module_type') else "auto"
            self.incognito_mode = router_config.incognito_mode if hasattr(router_config, 'incognito_mode') else True
        else:
            # 使用独立参数初始化
            self.router_ip = router_ip
            self.username = username
            self.password = password
            self.model = model
            self.module_type = module_type
            self.incognito_mode = incognito_mode
            # 创建RouterConfig对象用于兼容性
            self.router_config = RouterConfig(
                router_ip=router_ip,
                username=username,
                password=password,
                model=model,
                module_type=module_type,
                incognito_mode=incognito_mode
            )

        self.driver = None
        self.wait = None
        self.session = requests.Session()
        self.session.verify = False
        urllib3.disable_warnings(InsecureRequestWarning)

        mode_str = "无痕模式" if self.incognito_mode else "普通模式"
        print(f"RouterClient初始化完成 - IP: {self.router_ip}, 型号: {self.model}, 模组类型: {self.module_type}, 浏览器: {mode_str}")

    def __del__(self):
        """析构方法 - 确保浏览器被关闭"""
        try:
            if self.driver:
                print(f"RouterClient析构：关闭浏览器（IP: {self.router_ip}）")
                self.driver.quit()
                self.driver = None
        except Exception as e:
            # 析构函数中不应抛出异常
            print(f"RouterClient析构时关闭浏览器失败: {e}")

    # 以下保持您提供的所有方法不变
    def login_web(self, max_retries=3):
        """通过Web界面登录路由器，带重试机制"""
        if not self.driver:
            options = webdriver.ChromeOptions()
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')

            # 根据配置决定是否使用无痕模式
            if self.incognito_mode:
                options.add_argument('--incognito')
                print("正在初始化 Chrome 浏览器驱动（无痕模式）...")
            else:
                print("正在初始化 Chrome 浏览器驱动（普通模式）...")

            # 调试时确保浏览器可见
            # options.add_argument('--headless')  # 注释掉这行

            # 使用 webdriver_manager 自动管理 ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 15)  # 增加等待时间
            print("✅ Chrome 浏览器驱动初始化成功")

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
                # ⚠️ 等待按钮真正可点击
                login_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="login"]'))
                )

                # 滚动到按钮位置，确保可见
                self.driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
                time.sleep(0.5)

                # 尝试两种点击方式：优先使用JavaScript click（更可靠）
                try:
                    self.driver.execute_script("arguments[0].click();", login_button)
                    print("已点击登录按钮（JavaScript方式）")
                except:
                    login_button.click()
                    print("已点击登录按钮（普通方式）")

                # 等待登录完成
                print("等待登录完成...")
                # ⚠️ 增加等待时间，避免过早刷新导致登录中断
                time.sleep(6)  # 增加到6秒，确保登录请求完成

                # ⚠️ 等待URL变化（登录成功后会跳转）
                print("检查URL是否已跳转...")
                max_wait = 10  # 最多等10秒
                start_time = time.time()
                while time.time() - start_time < max_wait:
                    current_url = self.driver.current_url.lower()
                    if "login" not in current_url:
                        print(f"✅ 已跳转离开登录页: {current_url}")
                        break
                    time.sleep(1)
                else:
                    print(f"⚠️ 仍在登录页面: {self.driver.current_url}")

                time.sleep(2)  # 额外等待页面稳定

                # 验证登录成功的多种方法
                if self._verify_login_success():
                    print("登录验证成功")

                    # 检查并处理修改密码弹窗
                    # 如果检测到修改密码弹窗，会自动修改并重新登录
                    # 返回True表示有弹窗且重新登录成功，False表示无弹窗（正常）
                    popup_result = self._handle_change_password_popup()

                    # 如果有修改密码弹窗
                    if popup_result:
                        print("✅ 修改密码弹窗处理完成，已重新登录")
                        # 再次验证登录状态
                        if self._verify_login_success():
                            print("✅ 最终登录状态验证成功")
                            return True
                        else:
                            print("❌ 修改密码后重新登录验证失败，需要重试")
                            if attempt < max_retries:
                                time.sleep(2)
                                continue
                            else:
                                return False
                    else:
                        # 没有修改密码弹窗，正常登录成功
                        print("✅ 登录成功（无修改密码弹窗）")
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

    def login_web_force(self, max_retries=3):
        """强制重新登录（不检查已登录状态），用于升级后重新登录"""
        print(f"\n{'='*50}")
        print(f"强制重新登录模式（跳过已登录检查）")
        print(f"{'='*50}")

        if not self.driver:
            options = webdriver.ChromeOptions()
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')

            # 根据配置决定是否使用无痕模式
            if self.incognito_mode:
                options.add_argument('--incognito')
                print("正在初始化 Chrome 浏览器驱动（无痕模式）...")
            else:
                print("正在初始化 Chrome 浏览器驱动（普通模式）...")

            # 使用 webdriver_manager 自动管理 ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 15)
            print("✅ Chrome 浏览器驱动初始化成功")

        login_url = f"http://{self.router_ip}"

        for attempt in range(1, max_retries + 1):
            print(f"\n{'='*50}")
            print(f"强制登录尝试 {attempt}/{max_retries}")
            print(f"{'='*50}")

            try:
                print(f"正在访问: {login_url}")
                self.driver.get(login_url)
                self.driver.maximize_window()
                time.sleep(2)

                # 等待页面加载
                time.sleep(3)

                print("开始强制登录过程（不检查已登录状态）...")

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
                # ⚠️ 等待按钮真正可点击
                login_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="login"]'))
                )

                # 滚动到按钮位置，确保可见
                self.driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
                time.sleep(0.5)

                # 尝试两种点击方式：优先使用JavaScript click（更可靠）
                try:
                    self.driver.execute_script("arguments[0].click();", login_button)
                    print("已点击登录按钮（JavaScript方式）")
                except:
                    login_button.click()
                    print("已点击登录按钮（普通方式）")

                # 等待登录完成
                print("等待登录完成...")
                # ⚠️ 增加等待时间，避免过早刷新导致登录中断
                time.sleep(6)  # 增加到6秒，确保登录请求完成

                # ⚠️ 等待URL变化（登录成功后会跳转）
                print("检查URL是否已跳转...")
                max_wait = 10  # 最多等10秒
                start_time = time.time()
                while time.time() - start_time < max_wait:
                    current_url = self.driver.current_url.lower()
                    if "login" not in current_url:
                        print(f"✅ 已跳转离开登录页: {current_url}")
                        break
                    time.sleep(1)
                else:
                    print(f"⚠️ 仍在登录页面: {self.driver.current_url}")

                time.sleep(2)  # 额外等待页面稳定

                # 验证登录成功的多种方法
                if self._verify_login_success():
                    print("强制登录验证成功")

                    # ⚠️ 关键：检查并处理修改密码弹窗
                    # 如果检测到修改密码弹窗，会自动修改并重新登录
                    # 返回True表示有弹窗且重新登录成功，False表示无弹窗（正常）
                    popup_result = self._handle_change_password_popup()

                    # 如果有修改密码弹窗
                    if popup_result:
                        print("✅ 修改密码弹窗处理完成，已重新登录")
                        # 再次验证登录状态
                        if self._verify_login_success():
                            print("✅ 最终登录状态验证成功")
                            return True
                        else:
                            print("❌ 修改密码后重新登录验证失败，需要重试")
                            if attempt < max_retries:
                                time.sleep(2)
                                continue
                            else:
                                return False
                    else:
                        # 没有修改密码弹窗，正常登录成功
                        print("✅ 登录成功（无修改密码弹窗）")
                        return True
                else:
                    print(f"强制登录验证失败，尝试 {attempt}/{max_retries}")
                    if attempt < max_retries:
                        time.sleep(2)
                        continue

            except Exception as e:
                print(f"强制登录过程中发生错误: {str(e)}")
                import traceback
                print(f"错误堆栈: {traceback.format_exc()}")
                if attempt < max_retries:
                    print(f"将进行第 {attempt + 1} 次重试...")
                    time.sleep(2)
                    continue

        print(f"强制登录失败，已重试 {max_retries} 次")
        return False

    def _enter_field_with_retry(self, xpath, value, field_name, max_attempts=3):
        """输入字段值并验证，带重试机制

        如果第一次找不到元素，会先强制F5刷新页面再重试
        """
        page_refreshed = False  # 标记是否已经刷新过页面
        actual_attempt = 0  # 实际尝试次数（不包括刷新后的额外尝试）

        while actual_attempt < max_attempts:
            actual_attempt += 1
            try:
                print(f"查找{field_name}输入框... (尝试 {actual_attempt}/{max_attempts})")
                field = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )

                # 确保元素可交互
                self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))

                # ⚠️ 强力清空输入框（三种方式确保清空）
                # 方式1: 使用clear()
                field.clear()
                time.sleep(0.3)

                # 方式2: 使用JavaScript清空
                self.driver.execute_script("arguments[0].value = '';", field)
                time.sleep(0.3)

                # 方式3: 选中全部内容并删除
                field.click()
                field.send_keys(Keys.CONTROL + "a")
                field.send_keys(Keys.DELETE)
                time.sleep(0.3)

                # 验证是否清空成功
                current_value = field.get_attribute('value')
                if current_value:
                    print(f"  ⚠️ 清空后仍有残留值: '{current_value}'，再次清空...")
                    self.driver.execute_script("arguments[0].value = '';", field)
                    time.sleep(0.3)

                # 输入新值
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
                    if actual_attempt < max_attempts:
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

                # 如果是第一次尝试且未刷新过页面，先强制F5刷新
                if actual_attempt == 1 and not page_refreshed:
                    print(f"  ⚠️ 未找到{field_name}输入框，尝试强制刷新页面（F5）...")
                    try:
                        self.driver.refresh()
                        print("  ✅ 页面已刷新，等待页面加载...")
                        time.sleep(3)  # 等待页面重新加载
                        page_refreshed = True

                        # 刷新后重新尝试，但不增加actual_attempt计数
                        print(f"  刷新后重新查找{field_name}输入框...")
                        actual_attempt -= 1  # 回退计数，这次不算
                        continue
                    except Exception as refresh_error:
                        print(f"  ⚠️ 页面刷新失败: {str(refresh_error)}")
                        # 刷新失败，继续正常的重试逻辑

                # 如果不是第一次或已经刷新过，继续正常的重试逻辑
                if actual_attempt < max_attempts:
                    print(f"  等待1秒后重试...")
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
                    print(f"[OK] 通过URL判断已登录: {current_url}")
                    return True

            return False
        except:
            return False

    def _verify_login_success(self):
        """验证登录是否成功"""
        print("开始验证登录状态...")

        # 等待页面稳定
        time.sleep(3)

        # ⚠️ 关键修复：优先检查URL是否还在登录页
        current_url = self.driver.current_url.lower()
        print(f"当前URL: {current_url}")

        # 如果URL包含login.html，明确判定为登录失败
        if "login.html" in current_url or "/login" in current_url:
            print("[FAILED] URL仍在登录页面，登录失败")
            return False

        # 如果URL不包含登录相关关键词，可能已经登录成功
        login_indicators = ["login", "auth", "signin"]
        if not any(indicator in current_url for indicator in login_indicators):
            print("[OK] 通过URL判断登录成功（不包含登录关键词）")
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
                    print(f"[OK] 找到登录成功元素: {xpath}")
                    return True
            except Exception as e:
                continue

        # 方法3: 检查页面标题
        page_title = self.driver.title.lower()
        print(f"页面标题: {page_title}")
        if page_title and "login" not in page_title and "sign in" not in page_title:
            print("[OK] 通过页面标题判断登录成功")
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
                    print(f"[ERROR] 找到错误消息: {error_text}")
                    return False
            except:
                continue

        print("[WARN] 登录状态不确定，但没有发现明显错误，假设登录成功")
        return True  # 如果没有发现错误，假设登录成功

    def _find_login_success_element(self):
        """查找登录成功元素"""
        try:
            element = self.driver.find_element(By.XPATH, '//*[@id="qwert_model"]')
            return element.is_displayed()
        except:
            return False

    def _handle_change_password_popup(self):
        """检查并处理修改密码弹窗（修改密码为admin1）"""
        try:
            print("\n检查是否有修改密码弹窗...")
            time.sleep(2)  # 等待弹窗出现

            # 尝试查找旧密码输入框
            try:
                old_password_field = self.driver.find_element(By.XPATH, '//*[@id="old_password"]')

                if old_password_field.is_displayed():
                    print("✅ 检测到修改密码弹窗，开始填写新密码...")
                    print(f"  当前密码: {self.password}")

                    # 步骤1: 填写旧密码
                    print(f"  步骤1: 填写旧密码 '{self.password}'...")
                    old_password_field.clear()
                    old_password_field.send_keys(self.password)  # 使用当前密码
                    time.sleep(0.5)

                    # 步骤2: 填写新密码
                    print("  步骤2: 填写新密码 'admin1'...")
                    new_password_field = self.driver.find_element(By.XPATH, '//*[@id="new_password"]')
                    new_password_field.clear()
                    new_password_field.send_keys("admin1")
                    time.sleep(0.5)

                    # 步骤3: 填写确认新密码
                    print("  步骤3: 填写确认新密码 'admin1'...")
                    confirm_password_field = self.driver.find_element(By.XPATH, '//*[@id="confirm_password"]')
                    confirm_password_field.clear()
                    confirm_password_field.send_keys("admin1")
                    time.sleep(0.5)

                    # 步骤4: 点击保存按钮
                    print("  步骤4: 点击保存按钮...")
                    save_button = self.driver.find_element(By.XPATH, '//*[@id="changepsw_btn"]')
                    save_button.click()
                    print("✅ 已点击保存按钮，密码修改中...")
                    time.sleep(2)  # 等待2秒，看是否有错误提示

                    # 检查是否有错误提示
                    try:
                        # 查找可能的错误消息
                        error_msg = self.driver.find_element(By.XPATH, '//*[contains(@class, "error") or contains(@class, "alert")]')
                        if error_msg.is_displayed():
                            error_text = error_msg.text
                            print(f"  ❌ 修改密码失败，错误提示: {error_text}")
                            print(f"  ⚠️ 密码修改操作未成功，保持原密码: {self.password}")
                            return False
                    except:
                        # 没有错误消息，继续
                        pass

                    # 步骤5: 等待跳转到登录页面和密码生效
                    print("  步骤5: 等待跳转到登录页面和密码生效...")
                    time.sleep(3)  # 先等待3秒

                    # 检查是否已跳转到登录页
                    max_wait = 10
                    start_time = time.time()
                    while time.time() - start_time < max_wait:
                        current_url = self.driver.current_url.lower()
                        if "login" in current_url:
                            print(f"  ✅ 已跳转到登录页: {current_url}")
                            break
                        time.sleep(1)
                    else:
                        print(f"  ⚠️ 未跳转到登录页，当前URL: {self.driver.current_url}")

                    # 额外等待，确保密码修改生效
                    time.sleep(3)
                    print(f"  ℹ️ 已等待密码生效（总共约{int(time.time() - start_time) + 3}秒）")

                    # 步骤6: 更新密码并重新登录
                    print("  步骤6: 使用新密码重新登录...")
                    old_password = self.password
                    self.password = "admin1"  # 更新为新密码
                    print(f"  密码已更新: {old_password} → admin1")
                    print(f"  ⚠️ 即将使用密码 'admin1' 重新登录")

                    # 执行登录操作
                    print("\n开始登录过程...")

                    # 输入用户名
                    username_entered = self._enter_field_with_retry(
                        '//*[@id="username"]',
                        self.username,
                        "用户名"
                    )
                    if not username_entered:
                        print(f"用户名输入失败")
                        return False

                    # 输入新密码
                    print(f"  ⚠️ 准备输入密码: '{self.password}'")

                    # 先禁用浏览器自动填充，避免干扰
                    try:
                        password_field = self.driver.find_element(By.XPATH, '//*[@id="password"]')
                        self.driver.execute_script("arguments[0].setAttribute('autocomplete', 'off');", password_field)
                        self.driver.execute_script("arguments[0].setAttribute('readonly', 'readonly');", password_field)
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].removeAttribute('readonly');", password_field)
                    except:
                        pass

                    password_entered = self._enter_field_with_retry(
                        '//*[@id="password"]',
                        self.password,  # 使用新密码
                        "密码"
                    )
                    if not password_entered:
                        print(f"❌ 密码输入失败")
                        return False

                    # 再次验证密码输入是否正确
                    try:
                        password_field = self.driver.find_element(By.XPATH, '//*[@id="password"]')
                        actual_password = password_field.get_attribute('value')
                        print(f"  ✅ 密码输入验证: 期望'{self.password}', 实际'{actual_password}', 匹配={actual_password == self.password}")
                        if actual_password != self.password:
                            print(f"  ⚠️ 密码输入值不匹配，重新强制设置...")
                            self.driver.execute_script(f"arguments[0].value = '{self.password}';", password_field)
                            time.sleep(0.5)
                            actual_password = password_field.get_attribute('value')
                            print(f"  重新验证: '{actual_password}'")
                    except Exception as e:
                        print(f"  ⚠️ 密码验证出错: {e}")

                    # 点击登录按钮
                    print("查找登录按钮...")
                    # ⚠️ 等待按钮真正可点击
                    login_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="login"]'))
                    )

                    # 滚动到按钮位置，确保可见
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
                    time.sleep(0.5)

                    # 尝试两种点击方式：优先使用JavaScript click（更可靠）
                    try:
                        self.driver.execute_script("arguments[0].click();", login_button)
                        print("已点击登录按钮（JavaScript方式）")
                    except:
                        login_button.click()
                        print("已点击登录按钮（普通方式）")

                    # 等待登录完成
                    print("等待登录完成...")
                    # ⚠️ 增加等待时间，避免过早刷新导致登录中断
                    time.sleep(6)  # 增加到6秒，确保登录请求完成

                    # ⚠️ 等待URL变化（登录成功后会跳转）
                    print("检查URL是否已跳转...")
                    max_wait = 10  # 最多等10秒
                    start_time = time.time()
                    while time.time() - start_time < max_wait:
                        current_url = self.driver.current_url.lower()
                        if "login" not in current_url:
                            print(f"✅ 已跳转离开登录页: {current_url}")
                            break
                        time.sleep(1)
                    else:
                        print(f"⚠️ 仍在登录页面: {self.driver.current_url}")

                    time.sleep(2)  # 额外等待页面稳定

                    # 验证登录成功
                    if self._verify_login_success():
                        print("✅ 使用新密码登录成功")
                        return True
                    else:
                        print("❌ 使用新密码登录失败")
                        return False

            except Exception as e:
                # 未找到修改密码弹窗
                print("ℹ️  未检测到修改密码弹窗（正常情况）")
                return False

        except Exception as e:
            print(f"⚠️ 处理修改密码弹窗时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def check_firmware_version(self, expected_version: str, skip_navigation: bool = False) -> tuple:
        """
        检查首页的固件版本号

        Args:
            expected_version: 期望的版本号（如 "32.3.0.7"）
            skip_navigation: 是否跳过导航到首页（默认False，会自动跳转到 #status/summary）

        Returns:
            tuple: (bool, dict) - (是否匹配, 详细信息)
                详细信息包含:
                - success: bool - 是否成功获取版本号
                - actual_version: str - 实际版本号
                - expected_version: str - 期望版本号
                - match: bool - 版本号是否匹配
                - error: str - 错误信息（如果有）
                - current_url: str - 当前URL
        """
        result = {
            "success": False,
            "actual_version": None,
            "expected_version": expected_version,
            "match": False,
            "error": None,
            "current_url": None
        }

        try:
            print(f"\n{'='*60}")
            print(f"检查固件版本号...")
            print(f"{'='*60}")

            # ⚠️ 关键：先跳转到首页（status/summary），确保版本号元素可见
            if not skip_navigation:
                print(f"步骤1: 导航到首页 #status/summary")
                status_url = f"http://{self.router_ip}/#status/summary"
                self.driver.get(status_url)
                time.sleep(2)
                self.driver.refresh()
                time.sleep(3)
                print(f"  ✅ 已跳转到首页")
                print(f"  当前URL: {self.driver.current_url}")
            else:
                print(f"  ℹ️  跳过导航，使用当前页面")
                print(f"  当前URL: {self.driver.current_url}")

            result["current_url"] = self.driver.current_url

            # 步骤2: 查找版本号元素
            version_xpath = '//*[@id="qwert_firmware_ver"]'
            print(f"\n步骤2: 查找版本号元素: {version_xpath}")

            version_element = self.wait.until(
                EC.presence_of_element_located((By.XPATH, version_xpath))
            )

            # 步骤3: 获取版本号文本
            actual_version = version_element.text.strip()
            result["success"] = True
            result["actual_version"] = actual_version

            print(f"\n步骤3: 对比版本号")
            print(f"  期望版本: {expected_version}")
            print(f"  实际版本: {actual_version}")
            print(f"  版本号长度: 期望={len(expected_version)}, 实际={len(actual_version)}")

            # 步骤4: 对比版本号（支持后缀匹配）
            # 精确匹配或前缀匹配（实际版本以期望版本开头）
            # 例如: 35.3.0.11-a1 可以匹配 35.3.0.11
            if actual_version == expected_version or actual_version.startswith(expected_version + "-"):
                print(f"\n✅ 版本号匹配: {actual_version}")
                if actual_version != expected_version:
                    print(f"   （前缀匹配成功，期望: {expected_version}, 实际: {actual_version}）")
                result["match"] = True
                return True, result
            else:
                print(f"\n❌ 版本号不匹配！")
                print(f"   期望: '{expected_version}'")
                print(f"   实际: '{actual_version}'")

                # 详细对比（逐字符）
                print(f"\n详细对比（逐字符）:")
                max_len = max(len(expected_version), len(actual_version))
                for i in range(max_len):
                    expected_char = expected_version[i] if i < len(expected_version) else '(无)'
                    actual_char = actual_version[i] if i < len(actual_version) else '(无)'
                    match = '✓' if expected_char == actual_char else '✗'
                    print(f"   位置 {i}: 期望='{expected_char}' 实际='{actual_char}' {match}")

                result["match"] = False
                return False, result

        except Exception as e:
            error_msg = str(e)
            result["error"] = error_msg
            result["current_url"] = self.driver.current_url if self.driver else None

            print(f"\n❌ 检查版本号失败: {e}")
            print(f"   当前URL: {result['current_url']}")
            import traceback
            traceback.print_exc()
            return False, result

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
            print("[OK] 已选择PPPoE拨号模式")
            time.sleep(1)

            # 2. 填写用户名
            print("填写PPPoE用户名...")
            pppoe_username_field = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[contains(@id, "_user")]'))
            )
            pppoe_username_field.clear()
            pppoe_username_field.send_keys(pppoe_config["username"])
            print("[OK] 已输入PPPoE用户名")

            # 3. 填写密码
            print("填写PPPoE密码...")
            pppoe_password_field = self.driver.find_element(
                By.XPATH, '//input[contains(@id, "_password")]'
            )
            pppoe_password_field.clear()
            pppoe_password_field.send_keys(pppoe_config["password"])
            print("[OK] 已输入PPPoE密码")

            # 4. 保存配置
            print("保存配置...")
            save_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
            )
            save_button.click()
            print("[OK] 已点击保存按钮")

            # 等待保存完成
            time.sleep(5)
            print("[OK] PPPoE配置完成")
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
            print("[OK] 已选择静态ip模式")
            time.sleep(1)

            # 2. 填写用户名
            print("填写ipv4地址...")
            pppoe_username_field = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[contains(@id, "_ip_address")]'))
            )
            pppoe_username_field.clear()
            pppoe_username_field.send_keys(static_config["ipv4"])
            print("[OK] 已输入ipv4地址")

            # 3. 填写子网掩码
            print("填写子网掩码...")
            pppoe_password_field = self.driver.find_element(
                By.XPATH, '//input[contains(@id, "_netmask")]'
            )
            pppoe_password_field.clear()
            pppoe_password_field.send_keys(static_config["netmask"])
            print("[OK] 已输入子网掩码")

            # 4. 保存配置
            print("保存配置...")
            save_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
            )
            save_button.click()
            print("[OK] 已点击保存按钮")

            # 等待保存完成
            time.sleep(5)
            print("[OK] 静态ip配置完成")
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
                    print("[OK] WAN口连接状态: 成功")
                elif any(word in status_text for word in ["离线", "offline", "disconnected", "down"]):
                    result["connection_status"] = "失败"
                    print("[ERROR] WAN口连接状态: 失败")
                else:
                    print(f"[WARN] 未知的WAN状态: {status_text}")
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
            print("[OK] 已点击Stop按钮")

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
                print("[OK] Ping测试成功 - 丢包率: 0%")
                ping_success = True
            else:
                print(f"[ERROR] Ping测试失败 - 丢包率: {packet_loss}%")
                ping_success = False

        except Exception as e:
            print(f"[ERROR] Ping测试过程中发生错误: {str(e)}")
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
                    print("[OK] 已再次点击Stop按钮确保停止")
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
                print("[WARN] 未找到包含'packet loss'的行")
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
            print("[WARN] 无法从行中解析出具体的丢包率数值")
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
                            print(f"[OK] 找到可用的网络类型选择框: {selector}")
                            found_selectors.append(selector)
                            break

                    if connection_type_select:
                        break
                except Exception as e:
                    print(f"[ERROR] 无法找到元素 {selector}: {str(e)}")
                    continue

            if not connection_type_select:
                print("[ERROR] 无法找到网络类型选择框")
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
                    print(f"[OK] 当前已经是 {networktype} 模式，无需更改")
                    return True
            except Exception as e:
                print(f"获取当前选中值失败: {str(e)}")

            # 如果当前模式不是目标模式，则进行配置
            print(f"当前模式不是 {networktype}，开始配置...")

            # 使用 Select 类选择选项
            mode_dropdown = Select(connection_type_select)
            mode_dropdown.select_by_value(select_value)
            print(f"[OK] 已选择 {networktype} 模式")
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
                    print(f"[OK] 找到保存按钮: {selector}")
                    break
                except Exception as e:
                    print(f"[ERROR] 无法找到保存按钮 {selector}: {str(e)}")
                    continue

            if not save_button:
                print("[ERROR] 无法找到保存按钮")
                return False

            save_button.click()
            print("[OK] 已点击保存按钮")
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
                    print(f"[OK] 找到应用按钮: {selector}")

                    # 检查按钮是否可点击
                    if apply_button.is_enabled():
                        print("应用按钮可点击，准备点击...")
                        apply_button.click()
                        print("[OK] 已点击应用按钮")
                        time.sleep(5)  # 等待应用完成
                    else:
                        print("[WARN] 应用按钮不可点击，跳过")

                    break
                except Exception as e:
                    print(f"[ERROR] 无法找到或点击应用按钮 {selector}: {str(e)}")
                    continue

            # 配置下发完成，返回成功
            print(f"[OK] {networktype}模式配置下发完成")
            return True

        except Exception as e:
            print(f"[ERROR] 配置蜂窝网络标准时发生错误: {str(e)}")
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
                print("[ERROR] 错误：短信中心号码不能为空")
                return False

            center_number = str(center_number).strip()
            if not center_number:
                print("[ERROR] 错误：短信中心号码不能为空字符串")
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
                            print(f"[OK] 找到可用的短信中心输入框: {selector}")
                            break

                    if sms_center_input:
                        break
                except Exception as e:
                    print(f"[ERROR] 无法找到元素 {selector}: {str(e)}")
                    continue

            if not sms_center_input:
                print("[ERROR] 无法找到短信中心号码输入框")
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
                print("[WARN] 检测到当前值与目标值相同，启动容错机制")
                print("第一步：先设置临时值以触发应用按钮")

                # 临时号码（故意使用一个不同的值）
                temp_number = "+8600000000000"

                try:
                    # 清空并输入临时号码
                    sms_center_input.clear()
                    time.sleep(0.5)
                    sms_center_input.send_keys(temp_number)
                    print(f"[OK] 已输入临时号码: {temp_number}")
                    time.sleep(1)

                    # 保存临时配置
                    print("保存临时配置...")
                    save_success = self._click_save_button()
                    if not save_success:
                        print("[ERROR] 保存临时配置失败")
                        return False

                    # 应用临时配置
                    print("应用临时配置...")
                    apply_success = self._click_apply_button()
                    if not apply_success:
                        print("[WARN] 应用临时配置失败，但继续执行")

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
                                    print(f"[OK] 重新找到短信中心输入框: {selector}")
                                    break
                            if sms_center_input:
                                break
                        except:
                            continue

                    if not sms_center_input:
                        print("[ERROR] 刷新后无法重新定位输入框")
                        return False

                except Exception as e:
                    print(f"[ERROR] 设置临时值失败: {str(e)}")
                    return False

                print("第二步：设置目标值")

            # 清空并输入目标短信中心号码
            try:
                print("清空并输入目标短信中心号码...")
                sms_center_input.clear()
                time.sleep(0.5)  # 等待清空完成
                sms_center_input.send_keys(center_number)
                print(f"[OK] 已输入短信中心号码: {center_number}")

                # 验证输入的值
                new_value = sms_center_input.get_attribute("value")
                if new_value != center_number:
                    print(f"[WARN] 输入的值与预期不符，预期: {center_number}, 实际: {new_value}")
                    # 尝试重新输入
                    sms_center_input.clear()
                    time.sleep(0.5)
                    sms_center_input.send_keys(center_number)
                    print("[OK] 已重新输入短信中心号码")
            except Exception as e:
                print(f"[ERROR] 输入短信中心号码时发生错误: {str(e)}")
                return False

            # 保存配置
            print("保存目标配置...")
            save_success = self._click_save_button()
            if not save_success:
                print("[ERROR] 保存配置失败")
                return False

            # 应用配置
            print("应用目标配置...")
            apply_success = self._click_apply_button()
            if not apply_success:
                print("[WARN] 应用配置失败或应用按钮不可用，但保存成功")

            print("[OK] 短信中心号码配置完成")
            return True

        except Exception as e:
            print(f"[ERROR] 配置短信中心号码时发生错误: {str(e)}")
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
                print("[ERROR] 错误：短信中心号码不能为空")
                return False

            center_number = str(center_number).strip()
            if not center_number:
                print("[ERROR] 错误：短信中心号码不能为空字符串")
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
                            print(f"[OK] 找到可用的SIM2短信中心输入框: {selector}")
                            break

                    if sms_center_input:
                        break
                except Exception as e:
                    print(f"[ERROR] 无法找到元素 {selector}: {str(e)}")
                    continue

            if not sms_center_input:
                print("[ERROR] 无法找到SIM2短信中心号码输入框")
                return False

            # 清空并输入目标短信中心号码
            try:
                print("清空并输入SIM2目标短信中心号码...")
                sms_center_input.clear()
                time.sleep(0.5)
                sms_center_input.send_keys(center_number)
                print(f"[OK] 已输入SIM2短信中心号码: {center_number}")

                # 验证输入的值
                new_value = sms_center_input.get_attribute("value")
                if new_value != center_number:
                    print(f"[WARN] 输入的值与预期不符，预期: {center_number}, 实际: {new_value}")
                    sms_center_input.clear()
                    time.sleep(0.5)
                    sms_center_input.send_keys(center_number)
                    print("[OK] 已重新输入SIM2短信中心号码")
            except Exception as e:
                print(f"[ERROR] 输入SIM2短信中心号码时发生错误: {str(e)}")
                return False

            # 保存配置
            print("保存SIM2目标配置...")
            save_success = self._click_save_button()
            if not save_success:
                print("[ERROR] 保存配置失败")
                return False

            # 应用配置
            print("应用SIM2目标配置...")
            apply_success = self._click_apply_button()
            if not apply_success:
                print("[WARN] 应用配置失败或应用按钮不可用，但保存成功")

            print("[OK] SIM2短信中心号码配置完成")
            return True

        except Exception as e:
            print(f"[ERROR] 配置SIM2短信中心号码时发生错误: {str(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            return False

    def navigate_to_page(self, hash_path, sub_tab_selector=None):
        """
        导航到指定的页面（通过 URL hash）

        Args:
            hash_path: URL hash路径（如 #network/firewall/portmapping）
            sub_tab_selector: 可选的子页面标签选择器（如 'network/firewall/security'）
                            某些页面需要点击子标签才能正确加载内容
                            ⚠️ 重要: 跳转URL后先刷新，然后再点击子标签，不要在点击后刷新

        Returns:
            bool: 导航成功返回True，失败返回False
        """
        try:
            # 确保 hash_path 以 # 开头
            if not hash_path.startswith('#'):
                hash_path = '#' + hash_path

            url = f"http://{self.router_ip}/{hash_path}"
            print(f"  导航到页面: {url}")
            self.driver.get(url)
            time.sleep(2)

            # ⚠️ 关键: 先刷新页面，再点击子标签（参照用户的实现）
            self.driver.refresh()
            time.sleep(2)

            # 如果提供了子标签选择器，点击子标签
            if sub_tab_selector:
                try:
                    print(f"  点击子页面标签: {sub_tab_selector}")
                    # 定位子标签元素（使用 data-target 属性）
                    sub_tab_xpath = f'//a[@data-target="{sub_tab_selector}"]'
                    sub_tab = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, sub_tab_xpath))
                    )
                    sub_tab.click()
                    time.sleep(3)  # 等待子页面内容加载
                    print(f"  ✅ 子页面标签点击成功，内容已加载")
                    # ⚠️ 不要在这里再次刷新！
                except Exception as sub_e:
                    print(f"  ⚠️  子页面标签点击失败: {sub_e}")
                    # 子标签点击失败不算致命错误，继续执行

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
                        print(f"[OK] 找到可用的保存按钮: {selector}")
                        save_button.click()
                        print("[OK] 已点击保存按钮")
                        time.sleep(3)  # 等待保存完成
                        return True
                except Exception as e:
                    print(f"[ERROR] 无法找到或点击保存按钮 {selector}: {str(e)}")
                    continue

            print("[ERROR] 无法找到任何可用的保存按钮")
            return False

        except Exception as e:
            print(f"[ERROR] 点击保存按钮时发生错误: {str(e)}")
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
                    print(f"[OK] 找到应用按钮: {selector}")
                    apply_found = True

                    # 检查按钮是否可点击
                    if apply_button.is_enabled():
                        print("应用按钮可点击，准备点击...")
                        apply_button.click()
                        print("[OK] 已点击应用按钮")
                        time.sleep(5)  # 等待应用完成
                        return True
                    else:
                        print("[WARN] 应用按钮不可点击，跳过")
                        return False  # 找到按钮但不可点击，返回False

                except Exception as e:
                    print(f"[ERROR] 无法找到应用按钮 {selector}: {str(e)}")
                    continue

            if not apply_found:
                print("[WARN] 未找到应用按钮，可能不需要应用操作")
                return True  # 没有应用按钮不一定表示失败

            return False

        except Exception as e:
            print(f"[ERROR] 点击应用按钮时发生错误: {str(e)}")
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
                    print(f"[OK] 通过AT命令配置 {networktype} 模式成功")
                    return True
                else:
                    print(f"[ERROR] AT命令配置 {networktype} 模式失败")
                    return False
            else:
                print(f"[ERROR] 不支持的配置: networktype={networktype}, module_type={module_type}")
                return False

        except Exception as e:
            print(f"[ERROR] AT命令配置过程中发生错误: {str(e)}")
            return False

    def check_cellular_summary_status(self, timeout: int = 30, skip_navigation: bool = False) -> dict:
        """检查 #status/summary 页面的蜂窝网络状态

        仅负责获取数据并返回，不做任何数据有效性判断

        Args:
            timeout: 超时时间(秒)，默认30秒
            skip_navigation: 是否跳过页面导航和刷新（适用于已在目标页面的情况），默认False

        Returns:
            dict: 包含状态信息的字典，字段名与页面显示一致:
            {
                'success': bool,  # 是否成功访问页面
                'Current Cellular Link': str,  # 当前链路
                'Status': str,  # 状态 (Ready, FDD LTE等)
                'IPv4': str,  # IPv4地址
                'IPv6': str,  # IPv6地址
                'Connection Duration': str,  # 连接时长
                'SIM Data Usage Monthly': str,  # SIM卡数据用量统计
                'error': str  # 错误信息(如果有)
            }
        """
        result = {
            'success': False,
            'Current Cellular Link': '',
            'Status': '',
            'IPv4': '',
            'IPv6': '',
            'Connection Duration': '',
            'SIM Data Usage Monthly': '',
            'error': ''
        }

        try:
            print(f"\n{'='*50}")
            print("检查 status/summary 页面蜂窝状态")
            print(f"{'='*50}")

            # 导航到状态概览页面（可选）
            if not skip_navigation:
                print(f"导航到 http://{self.router_ip}/#status/summary")
                self.driver.get(f"http://{self.router_ip}/#status/summary")
                self.driver.refresh()
                time.sleep(3)
            else:
                print("⚠️  跳过页面导航和刷新（使用当前页面状态）")
                time.sleep(1)  # 短暂等待确保页面稳定

            # 获取所有字段，获取到什么就返回什么
            # 注意: Summary页面中Cellular、WAN、LAN部分有重复的ID(如qwert_status, qwert_ip等)
            # 需要使用更精确的XPath来定位Cellular部分的字段

            # 1. 获取 Current Cellular Link
            try:
                # 查找 Cellular section 下带有绿色文字的 span (Link in use / 使用中的链路)
                # XPath: 查找颜色为 rgb(0, 204, 102) 的 span
                link_xpath = '//div[@id="summary_cellular_info"]//span[contains(@style, "rgb(0, 204, 102)")]'
                link_element = self.driver.find_element(By.XPATH, link_xpath)
                link_text = link_element.text.strip()

                # 如果找到了 span，使用 span 的文本；否则使用空字符串
                if link_text:
                    result['Current Cellular Link'] = link_text
                    print(f"Current Cellular Link: {result['Current Cellular Link']}")
                else:
                    # 如果 span 为空，尝试使用备用方法（兼容没有连接的情况）
                    result['Current Cellular Link'] = ''
                    print(f"Current Cellular Link: (空)")
            except Exception as e:
                # 如果找不到绿色的 span，说明可能没有连接
                print(f"[WARN] 未找到 Current Cellular Link (可能未连接): {e}")
                result['Current Cellular Link'] = ''

            # 2. 获取 Status (Ready, FDD LTE等)
            try:
                status_xpath = '//div[@id="summary_cellular_info"]//label[@id="qwert_status"]'
                status_element = self.driver.find_element(By.XPATH, status_xpath)
                result['Status'] = status_element.text.strip()
                print(f"Status: {result['Status']}")
            except Exception as e:
                print(f"[WARN] 获取Status失败: {e}")

            # 3. 获取 IPv4地址
            try:
                ipv4_xpath = '//div[@id="summary_cellular_info"]//label[@id="qwert_ip"]'
                ipv4_element = self.driver.find_element(By.XPATH, ipv4_xpath)
                result['IPv4'] = ipv4_element.text.strip()
                print(f"IPv4: {result['IPv4']}")
            except Exception as e:
                print(f"[WARN] 获取IPv4地址失败: {e}")

            # 4. 获取 IPv6地址
            try:
                ipv6_xpath = '//div[@id="summary_cellular_info"]//label[@id="qwert_ipv6"]'
                ipv6_element = self.driver.find_element(By.XPATH, ipv6_xpath)
                result['IPv6'] = ipv6_element.text.strip()
                print(f"IPv6: {result['IPv6']}")
            except Exception as e:
                print(f"[WARN] 获取IPv6地址失败: {e}")

            # 5. 获取 Connection Duration
            try:
                time_xpath = '//div[@id="summary_cellular_info"]//label[@id="qwert_time"]'
                time_element = self.driver.find_element(By.XPATH, time_xpath)
                result['Connection Duration'] = time_element.text.strip()
                print(f"Connection Duration: {result['Connection Duration']}")
            except Exception as e:
                print(f"[WARN] 获取Connection Duration失败: {e}")

            # 6. 获取 SIM Data Usage Monthly
            try:
                usage_xpath = '//div[@id="summary_cellular_info"]//label[@id="qwert_total"]'
                usage_element = self.driver.find_element(By.XPATH, usage_xpath)
                result['SIM Data Usage Monthly'] = usage_element.text.strip()
                print(f"SIM Data Usage Monthly: {result['SIM Data Usage Monthly']}")
            except Exception as e:
                print(f"[WARN] 获取SIM Data Usage Monthly失败: {e}")

            # 只要页面访问成功，就标记为成功
            result['success'] = True
            print(f"\n[OK] 页面访问成功，已获取所有可获取的字段")

        except Exception as e:
            result['error'] = f"页面导航失败: {str(e)}"
            print(f"[ERROR] {result['error']}")
            import traceback
            traceback.print_exc()

        return result

    def check_cellular_detail_status(self, timeout: int = 30, skip_navigation: bool = False) -> dict:
        """检查 #status/cellular 页面的详细蜂窝网络状态

        仅负责获取数据并返回，不做任何数据有效性判断

        Args:
            timeout: 超时时间(秒)，默认30秒
            skip_navigation: 是否跳过页面导航和刷新（适用于已在目标页面的情况），默认False

        Returns:
            dict: 包含详细状态信息的字典，字段名与页面显示一致
        """
        result = {
            'success': False,
            'error': '',
            # 蜂窝运行状态 (Cellular Running Status)
            'Model': '',  # 模块型号
            'Version': '',  # 版本
            'Current SIM': '',  # 当前SIM卡
            'Signal Level': '',  # 信号强度
            'Register Status': '',  # 注册状态
            'IMEI': '',  # IMEI
            'IMSI': '',  # IMSI
            'ICCID': '',  # ICCID
            'ISP': '',  # 运营商
            'Network Type': '',  # 网络类型
            'Cellular Frequency Band': '',  # 频段
            'PLMN ID': '',  # PLMN ID
            'LAC': '',  # 位置区码
            'Cell ID': '',  # Cell ID
            'RSRP': '',  # RSRP
            'RSRQ': '',  # RSRQ
            'SINR': '',  # SINR
            # 月度数据统计 (Data Monthly Statistics)
            'SIM-1 Monthly': '',  # SIM-1月度统计
            'SIM-2 Monthly': '',  # SIM-2月度统计
            # SIM卡APN信息 (SIM APN Profile)
            'SIM APN Profile': []  # [{'name': 'SIM1-APN1', 'Status': 'Connected', 'IPv4': '...', ...}, ...]
        }

        try:
            print(f"\n{'='*50}")
            print("检查 status/cellular 页面详细蜂窝状态")
            print(f"{'='*50}")

            # 导航到蜂窝状态页面（可选）
            if not skip_navigation:
                print(f"导航到 http://{self.router_ip}/#status/cellular")
                self.driver.get(f"http://{self.router_ip}/#status/cellular")
                self.driver.refresh()
                time.sleep(3)
            else:
                print("⚠️  跳过页面导航和刷新（使用当前页面状态）")
                time.sleep(1)  # 短暂等待确保页面稳定

            # === 蜂窝运行状态 (Cellular Running Status) ===
            print("\n--- Cellular Running Status ---")

            # Model (模块型号)
            try:
                element = self.driver.find_element(By.XPATH, '//*[@id="0_model"]')
                result['Model'] = element.text.strip()
                print(f"Model: {result['Model']}")
            except: pass

            # Version (版本)
            try:
                element = self.driver.find_element(By.XPATH, '//*[@id="0_version"]')
                result['Version'] = element.text.strip()
                print(f"Version: {result['Version']}")
            except: pass

            # Current SIM (当前SIM卡)
            try:
                element = self.driver.find_element(By.XPATH, '//*[@id="0_cur_sim"]')
                result['Current SIM'] = element.text.strip()
                print(f"Current SIM: {result['Current SIM']}")
            except: pass

            # Signal Level (信号强度)
            try:
                element = self.driver.find_element(By.XPATH, '//*[@id="0_signal"]')
                result['Signal Level'] = element.text.strip()
                print(f"Signal Level: {result['Signal Level']}")
            except: pass

            # Register Status (注册状态)
            try:
                element = self.driver.find_element(By.XPATH, '//*[@id="0_register"]')
                result['Register Status'] = element.text.strip()
                print(f"Register Status: {result['Register Status']}")
            except: pass

            # IMEI
            try:
                element = self.driver.find_element(By.XPATH, '//*[@id="0_imei"]')
                result['IMEI'] = element.text.strip()
                print(f"IMEI: {result['IMEI']}")
            except: pass

            # IMSI
            try:
                element = self.driver.find_element(By.XPATH, '//*[@id="0_imsi"]')
                result['IMSI'] = element.text.strip()
                print(f"IMSI: {result['IMSI']}")
            except: pass

            # ICCID
            try:
                element = self.driver.find_element(By.XPATH, '//*[@id="0_iccid"]')
                result['ICCID'] = element.text.strip()
                print(f"ICCID: {result['ICCID']}")
            except: pass

            # ISP (运营商)
            try:
                element = self.driver.find_element(By.XPATH, '//*[@id="0_net_provider"]')
                result['ISP'] = element.text.strip()
                print(f"ISP: {result['ISP']}")
            except: pass

            # Network Type (网络类型)
            try:
                element = self.driver.find_element(By.XPATH, '//*[@id="0_net_type"]')
                result['Network Type'] = element.text.strip()
                print(f"Network Type: {result['Network Type']}")
            except: pass

            # Cellular Frequency Band (频段) - 使用label查找方式(HTML中band字段与plmnid重复)
            try:
                # 查找"Cellular Frequency Band"标签的下一个div中的label
                band_xpath = '//div[contains(text(), "Cellular Frequency Band")]/following-sibling::div[1]/label'
                element = self.driver.find_element(By.XPATH, band_xpath)
                result['Cellular Frequency Band'] = element.text.strip()
                print(f"Cellular Frequency Band: {result['Cellular Frequency Band']}")
            except: pass

            # PLMN ID - 页面有两个id="0_plmnid"的label，需要精确定位到包含PLMN ID值的那个
            try:
                plmn_value = ''

                # 优先方法: 通过"PLMN ID"文本定位，获取其兄弟div中的label
                # 这个方法最准确，因为页面有两个id="0_plmnid"的元素
                try:
                    element = self.driver.find_element(By.XPATH, '//div[contains(text(), "PLMN ID")]/following-sibling::div[1]/label')
                    plmn_value = element.text.strip()
                except:
                    pass

                # 备用方法1: 尝试通过父元素定位
                if not plmn_value:
                    try:
                        element = self.driver.find_element(By.XPATH, '//div[contains(text(), "PLMN ID")]/..//label[not(contains(text(), "PLMN"))]')
                        plmn_value = element.text.strip()
                    except:
                        pass

                # 备用方法2: 使用索引获取第二个id="0_plmnid"的元素
                if not plmn_value:
                    try:
                        elements = self.driver.find_elements(By.XPATH, '//*[@id="0_plmnid"]')
                        # 如果有多个，取最后一个（通常是PLMN ID的值）
                        if len(elements) >= 2:
                            plmn_value = elements[-1].text.strip()
                        elif len(elements) == 1:
                            plmn_value = elements[0].text.strip()
                    except:
                        pass

                # 备用方法3: 尝试value属性
                if not plmn_value:
                    try:
                        element = self.driver.find_element(By.XPATH, '//div[contains(text(), "PLMN ID")]/following-sibling::div[1]/label')
                        plmn_value = element.get_attribute('value') or ''
                    except:
                        pass

                result['PLMN ID'] = plmn_value
                print(f"PLMN ID: {result['PLMN ID']}")
            except Exception as e:
                print(f"获取PLMN ID失败: {e}")

            # LAC (位置区码)
            try:
                element = self.driver.find_element(By.XPATH, '//*[@id="0_lac"]')
                result['LAC'] = element.text.strip()
                print(f"LAC: {result['LAC']}")
            except: pass

            # Cell ID
            try:
                element = self.driver.find_element(By.XPATH, '//*[@id="0_cellid"]')
                result['Cell ID'] = element.text.strip()
                print(f"Cell ID: {result['Cell ID']}")
            except: pass

            # RSRP - 使用label查找方式(HTML中ID错误标记为cellid)
            try:
                rsrp_xpath = '//div[contains(text(), "RSRP")]/following-sibling::div[1]/label'
                element = self.driver.find_element(By.XPATH, rsrp_xpath)
                result['RSRP'] = element.text.strip()
                print(f"RSRP: {result['RSRP']}")
            except: pass

            # RSRQ - 使用label查找方式(HTML中ID错误标记为cellid)
            try:
                rsrq_xpath = '//div[contains(text(), "RSRQ")]/following-sibling::div[1]/label'
                element = self.driver.find_element(By.XPATH, rsrq_xpath)
                result['RSRQ'] = element.text.strip()
                print(f"RSRQ: {result['RSRQ']}")
            except: pass

            # SINR - 使用label查找方式(HTML中ID错误标记为cellid)
            try:
                sinr_xpath = '//div[contains(text(), "SINR")]/following-sibling::div[1]/label'
                element = self.driver.find_element(By.XPATH, sinr_xpath)
                result['SINR'] = element.text.strip()
                print(f"SINR: {result['SINR']}")
            except: pass

            # === 月度数据统计 (Data Monthly Statistics) ===
            print("\n--- Data Monthly Statistics ---")
            try:
                # SIM-1统计
                sim1_element = self.driver.find_element(By.XPATH, '//*[@id="1_sim1"]')
                result['SIM-1 Monthly'] = sim1_element.text.strip()
                print(f"SIM-1 Monthly: {result['SIM-1 Monthly']}")
            except: pass

            try:
                # SIM-2统计
                sim2_element = self.driver.find_element(By.XPATH, '//*[@id="1_sim2"]')
                result['SIM-2 Monthly'] = sim2_element.text.strip()
                print(f"SIM-2 Monthly: {result['SIM-2 Monthly']}")
            except: pass

            # === SIM卡APN信息 (SIM APN Profile) ===
            print("\n--- SIM APN Profile ---")
            # 获取所有APN配置（通常有3个：SIM1-APN1, SIM1-APN2, SIM1-APN3）
            for apn_idx in range(3):  # 0, 1, 2 对应 SIM1-APN1, APN2, APN3
                try:
                    apn_info = {}
                    apn_info['Name'] = f"SIM1-APN{apn_idx+1}"

                    # Status (状态)
                    try:
                        element = self.driver.find_element(By.XPATH, f'//*[@id="{apn_idx}_status"]')
                        apn_info['Status'] = element.text.strip()
                    except: apn_info['Status'] = ''

                    # IPv4 (IPv4地址)
                    try:
                        element = self.driver.find_element(By.XPATH, f'//*[@id="{apn_idx}_ip"]')
                        apn_info['IPv4'] = element.text.strip()
                    except: apn_info['IPv4'] = ''

                    # IPv4 Gateway (IPv4网关)
                    try:
                        element = self.driver.find_element(By.XPATH, f'//*[@id="{apn_idx}_gate"]')
                        apn_info['IPv4 Gateway'] = element.text.strip()
                    except: apn_info['IPv4 Gateway'] = ''

                    # IPv4 DNS
                    try:
                        element = self.driver.find_element(By.XPATH, f'//*[@id="{apn_idx}_dns"]')
                        apn_info['IPv4 DNS'] = element.text.strip()
                    except: apn_info['IPv4 DNS'] = ''

                    # IPv6 (IPv6地址)
                    try:
                        element = self.driver.find_element(By.XPATH, f'//*[@id="{apn_idx}_ipv6"]')
                        apn_info['IPv6'] = element.text.strip()
                    except: apn_info['IPv6'] = ''

                    # IPv6 Gateway (IPv6网关)
                    try:
                        element = self.driver.find_element(By.XPATH, f'//*[@id="{apn_idx}_gatev6"]')
                        apn_info['IPv6 Gateway'] = element.text.strip()
                    except: apn_info['IPv6 Gateway'] = ''

                    # IPv6 DNS
                    try:
                        element = self.driver.find_element(By.XPATH, f'//*[@id="{apn_idx}_dnsv6"]')
                        apn_info['IPv6 DNS'] = element.text.strip()
                    except: apn_info['IPv6 DNS'] = ''

                    # Connection Duration (连接时长)
                    try:
                        element = self.driver.find_element(By.XPATH, f'//*[@id="{apn_idx}_time"]')
                        apn_info['Connection Duration'] = element.text.strip()
                    except: apn_info['Connection Duration'] = ''

                    # 无论是否有值都添加到列表
                    result['SIM APN Profile'].append(apn_info)
                    print(f"{apn_info['Name']}: Status={apn_info['Status']}, IPv4={apn_info['IPv4']}")
                except:
                    continue

            # 只要页面访问成功，就标记为成功
            result['success'] = True
            print(f"\n[OK] 页面访问成功，已获取所有可获取的字段")

        except Exception as e:
            result['error'] = f"页面导航失败: {str(e)}"
            print(f"[ERROR] {result['error']}")
            import traceback
            traceback.print_exc()

        return result

    def check_cellular_status(self) -> bool:
        """检查蜂窝网络状态（兼容性方法，保持向后兼容）

        调用新的 check_cellular_summary_status 和 check_cellular_detail_status
        只要页面访问成功就返回True，数据是否有效由调用者判断

        Returns:
            bool: 页面访问成功返回True，页面访问失败返回False
        """
        print(f"\n{'='*60}")
        print("蜂窝网络状态检查（兼容性方法）")
        print(f"{'='*60}")

        # 检查 summary 页面
        summary_result = self.check_cellular_summary_status(timeout=30)
        if not summary_result['success']:
            print(f"[ERROR] Summary页面访问失败: {summary_result['error']}")
            return False

        # 检查 cellular 页面
        detail_result = self.check_cellular_detail_status(timeout=30)
        if not detail_result['success']:
            print(f"[ERROR] Cellular页面访问失败: {detail_result['error']}")
            return False

        print("[OK] 两个页面均访问成功")
        return True

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
                    print(f"[OK] {field_name}: {value}")
                except Exception as e:
                    result[field_name] = None
                    print(f"[WARN] 无法读取 {field_name}: {str(e)}")

            print("[OK] 蜂窝状态页面信息读取完成")
            return result

        except Exception as e:
            print(f"[ERROR] 读取蜂窝状态页面信息失败: {str(e)}")
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
                print(f"[ERROR] 无法找到子网掩码输入框: {str(e)}")
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
                print("[WARN] 检测到当前值与目标值相同，启动容错机制")
                print("第一步：先设置临时值以触发应用按钮")

                # 临时掩码（故意使用一个不同的值）
                temp_netmask = "255.255.255.0"

                try:
                    # 清空并输入临时掩码
                    mask_input.clear()
                    time.sleep(0.5)
                    mask_input.send_keys(temp_netmask)
                    print(f"[OK] 已输入临时掩码: {temp_netmask}")
                    time.sleep(1)

                    # 保存临时配置
                    print("保存临时配置...")
                    save_success = self._click_save_button()
                    if not save_success:
                        print("[ERROR] 保存临时配置失败")
                        return False

                    # 应用临时配置
                    print("应用临时配置...")
                    apply_success = self._click_apply_button()
                    if not apply_success:
                        print("[WARN] 应用临时配置失败，但继续执行")

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
                    print(f"[ERROR] 设置临时值失败: {str(e)}")
                    return False

                print("第二步：设置目标值")

            # 清空并输入目标掩码
            try:
                print(f"清空并输入目标子网掩码: {netmask}")
                mask_input.clear()
                time.sleep(0.5)
                mask_input.send_keys(netmask)
                print(f"[OK] 已输入子网掩码: {netmask}")

                # 验证输入的值
                new_value = mask_input.get_attribute("value")
                if new_value != netmask:
                    print(f"[WARN] 输入的值与预期不符，预期: {netmask}, 实际: {new_value}")
                    # 尝试重新输入
                    mask_input.clear()
                    time.sleep(0.5)
                    mask_input.send_keys(netmask)
                    print("[OK] 已重新输入子网掩码")
            except Exception as e:
                print(f"[ERROR] 输入子网掩码时发生错误: {str(e)}")
                return False

            # 保存配置
            print("保存目标配置...")
            save_success = self._click_save_button()
            if not save_success:
                print("[ERROR] 保存配置失败")
                return False

            # 应用配置
            print("应用目标配置...")
            apply_success = self._click_apply_button()
            if not apply_success:
                print("[WARN] 应用配置失败或应用按钮不可用，但保存成功")

            print("[OK] 子网掩码配置完成")
            return True

        except Exception as e:
            print(f"[ERROR] 设置子网掩码失败: {str(e)}")
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
                print("[ERROR] 错误: AT命令参数不能为空")
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
            print(f"[OK] 已输入AT命令: {command}")

            # 查找并点击发送按钮
            print("查找发送按钮...")
            send_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_send"]'))
            )

            send_button.click()
            print("[OK] 已点击发送按钮")

            # 等待命令执行
            time.sleep(5)

            # 验证命令是否成功发送（可以检查是否有响应输出）
            # 这里我们假设只要成功点击发送按钮就算成功
            # 如果需要验证响应，可以添加额外的检查逻辑

            print("[OK] AT命令发送成功")
            return True

        except Exception as e:
            print(f"[ERROR] 执行AT命令时发生错误: {str(e)}")
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
            print(f"[ERROR] 获取AT命令响应时发生错误: {str(e)}")
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
                        print(f"  [OK] MQTT已连接（耗时 {elapsed} 秒，检查 {retry_count + 1} 次）")
                        return True

                    # 检查是否有连接失败的关键词
                    failed_keywords = ['失败', 'failed', 'error', '错误', 'disconnect', '断开']
                    if any(keyword in status_text_lower for keyword in failed_keywords):
                        print(f"  [ERROR] MQTT连接失败: {status_text}")
                        return False

                retry_count += 1

            except Exception as e:
                print(f"  检查MQTT状态时出错: {e}, 继续重试...")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(check_interval)

        # 超时
        elapsed = int(time.time() - start_time)
        print(f"  [ERROR] MQTT连接超时（已等待 {elapsed} 秒，检查 {retry_count} 次）")
        return False

    def upload_and_upgrade_firmware(self, firmware_path: str, timeout: int = 300, skip_relogin: bool = False) -> bool:
        """上传并升级固件

        Args:
            firmware_path: 固件文件的绝对路径
            timeout: 升级超时时间（秒），默认300秒
            skip_relogin: 是否跳过升级后的重新登录（默认False）
                         设置为True时，只上传固件并等待重启，不尝试重新登录
                         适用于升级后需要通过串口重新配置IP的场景

        Returns:
            bool: 升级是否成功
        """
        import os

        print(f"\n{'='*70}")
        print(f"开始固件升级流程")
        print(f"{'='*70}")
        print(f"固件路径: {firmware_path}")
        print(f"超时时间: {timeout}秒")

        # 检查固件文件是否存在
        if not os.path.exists(firmware_path):
            print(f"❌ 固件文件不存在: {firmware_path}")
            return False

        print(f"✅ 固件文件存在: {os.path.basename(firmware_path)}")

        # 🆕 步骤0: 检查登录状态（关键修复！）
        print("\n步骤0: 检查Web登录状态...")
        try:
            current_url = self.driver.current_url
            print(f"  📍 当前URL: {current_url}")

            # 检查是否在登录页面
            if 'login.html' in current_url or '/login' in current_url:
                print("  ⚠️  检测到未登录状态，正在重新登录...")
                if not self.login_web_force():
                    print("  ❌ 重新登录失败")
                    return False
                print("  ✅ 重新登录成功")
                time.sleep(2)  # 等待登录完成
            else:
                print(f"  ✅ 已登录状态")

            # 验证登录状态
            current_url_after = self.driver.current_url
            if 'login.html' in current_url_after or '/login' in current_url_after:
                print("  ❌ 登录验证失败，仍在登录页面")
                return False
            print(f"  ✅ 登录状态验证通过")

        except Exception as e:
            print(f"  ⚠️  登录状态检查异常: {e}")
            print("  尝试强制登录...")
            try:
                if not self.login_web_force():
                    print("  ❌ 强制登录失败")
                    return False
                print("  ✅ 强制登录成功")
            except Exception as e2:
                print(f"  ❌ 强制登录异常: {e2}")
                return False

        try:
            # 1. 跳转到升级页面
            print("\n步骤1: 跳转到固件升级页面...")
            upgrade_url = f"http://{self.router_ip}/#maintenance/upgrade/upgrade"
            self.driver.get(upgrade_url)
            print(f"  📍 目标URL: {upgrade_url}")
            time.sleep(5)  # 🆕 从3秒增加到5秒

            # 刷新页面确保加载完成
            print("  🔄 刷新页面确保加载完成...")
            self.driver.refresh()
            time.sleep(5)  # 🆕 从3秒增加到5秒

            # 🆕 输出页面信息
            print(f"  📍 当前URL: {self.driver.current_url}")
            print(f"  📄 页面标题: {self.driver.title}")
            print("✅ 已进入固件升级页面")

            # 2. 使用send_keys()方法直接上传文件（参考Python SDK安装用例）
            print("\n步骤2: 查找文件上传输入框...")

            # 等待页面稳定
            print("  ⏳ 等待页面元素加载...")
            time.sleep(2)  # 🆕 从1秒增加到2秒

            # 🆕 输出页面上所有的input元素信息（调试用）
            try:
                all_inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                print(f"  🔍 页面上共有 {len(all_inputs)} 个input元素")
                file_inputs = [inp for inp in all_inputs if inp.get_attribute('type') == 'file']
                print(f"  🔍 其中 {len(file_inputs)} 个type='file'的元素")
            except Exception as e:
                print(f"  ⚠️  无法获取input元素列表: {e}")

            # 查找文件上传输入框（type="file"）
            upload_input = None
            upload_input_locators = [
                ("ID: 1_file_url", By.XPATH, '//*[@id="1_file_url"]'),
                ("type=file", By.XPATH, '//input[@type="file"]'),
                ("name包含file", By.XPATH, '//input[contains(@name, "file") and @type="file"]'),
            ]

            print("  🔍 尝试使用多种定位器查找上传输入框...")
            for desc, by, xpath in upload_input_locators:
                try:
                    print(f"     尝试: {desc}")
                    elem = self.driver.find_element(by, xpath)
                    elem_type = elem.get_attribute('type')
                    elem_id = elem.get_attribute('id')
                    elem_name = elem.get_attribute('name')
                    print(f"     找到元素: type={elem_type}, id={elem_id}, name={elem_name}")
                    if elem_type == 'file':
                        print(f"  ✅ 找到文件上传输入框: {desc}")
                        # 滚动到元素位置
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                        time.sleep(0.5)
                        upload_input = elem
                        break
                except Exception as e:
                    print(f"     失败: {e}")
                    continue

            if not upload_input:
                print("\n  ❌ 无法找到文件上传输入框")
                # 🆕 失败时输出详细调试信息
                print("\n  🔍 调试信息：")
                print(f"     当前URL: {self.driver.current_url}")
                print(f"     页面标题: {self.driver.title}")
                # 🆕 保存失败截图
                try:
                    screenshot_path = f"logs/upload_fail_{int(time.time())}.png"
                    os.makedirs("logs", exist_ok=True)
                    self.driver.save_screenshot(screenshot_path)
                    print(f"     📸 失败截图已保存: {screenshot_path}")
                except Exception as e:
                    print(f"     ⚠️  无法保存截图: {e}")
                return False

            # 3. 使用send_keys()上传文件（与Python SDK安装用例相同的方法）
            print(f"\n步骤3: 上传固件文件...")
            print(f"  📁 固件路径: {firmware_path}")
            print(f"  📦 固件文件名: {os.path.basename(firmware_path)}")
            print(f"  📊 固件大小: {os.path.getsize(firmware_path) / (1024*1024):.2f} MB")
            try:
                upload_input.send_keys(firmware_path)
                print(f"  ✅ 文件已选择: {os.path.basename(firmware_path)}")
            except Exception as e:
                print(f"\n  ❌ 上传文件失败: {e}")
                # 🆕 保存失败截图
                try:
                    screenshot_path = f"logs/upload_select_fail_{int(time.time())}.png"
                    os.makedirs("logs", exist_ok=True)
                    self.driver.save_screenshot(screenshot_path)
                    print(f"  📸 失败截图已保存: {screenshot_path}")
                except:
                    pass
                return False

            # 等待文件路径显示在显示框中
            print(f"  等待文件路径显示...")
            time.sleep(2)

            # 验证文件路径已填充
            try:
                display_input_xpath = '//*[@id="1_file_url"]'
                display_input = self.driver.find_element(By.XPATH, display_input_xpath)
                file_value = display_input.get_attribute("value")
                if file_value and (firmware_path in file_value or os.path.basename(firmware_path) in file_value):
                    print(f"  ✅ 文件路径已显示: {file_value}")
                else:
                    print(f"  ⚠️ 文件路径未正确显示，当前值: {file_value}")
                    # 继续尝试
            except Exception as e:
                print(f"  ⚠️ 无法验证文件路径显示: {e}")
                # 继续尝试

            # 4. 等待升级按钮enabled（参考Python SDK安装用例）
            print("\n步骤4: 等待升级按钮enabled...")
            upgrade_btn_xpath = '//*[@id="1_file_import"]'
            print(f"  🔍 按钮XPath: {upgrade_btn_xpath}")

            max_wait = 10
            elapsed = 0
            upgrade_btn = None
            while elapsed < max_wait:
                try:
                    btn = self.driver.find_element(By.XPATH, upgrade_btn_xpath)
                    btn_class = btn.get_attribute('class') or ''
                    btn_text = btn.text
                    # 检查按钮是否disabled（根据Python SDK用例的逻辑）
                    if 'disable' not in btn_class.lower():
                        upgrade_btn = btn
                        print(f"  ✅ 按钮已enabled (等待{elapsed}秒)")
                        print(f"     按钮文本: {btn_text}")
                        print(f"     按钮class: {btn_class}")
                        break
                    else:
                        if elapsed % 2 == 0:  # 每2秒输出一次
                            print(f"  ⏳ 按钮仍disabled，继续等待... ({elapsed}秒)")
                except Exception as e:
                    if elapsed == 0:
                        print(f"  ⚠️  查找按钮失败: {e}")
                time.sleep(1)
                elapsed += 1

            if not upgrade_btn:
                print("\n  ❌ 等待按钮enabled超时")
                # 🆕 保存失败截图
                try:
                    screenshot_path = f"logs/button_disabled_{int(time.time())}.png"
                    os.makedirs("logs", exist_ok=True)
                    self.driver.save_screenshot(screenshot_path)
                    print(f"  📸 失败截图已保存: {screenshot_path}")
                except:
                    pass
                return False

            # 5. 点击升级按钮（使用JavaScript点击，避免元素被遮挡）
            print("\n步骤5: 点击升级按钮...")
            print("  🖱️  使用JavaScript点击（避免元素被遮挡）...")
            try:
                self.driver.execute_script("arguments[0].click();", upgrade_btn)
                print("  ✅ 已点击升级按钮")
                time.sleep(1)  # 等待点击生效
            except Exception as e:
                print(f"\n  ❌ 点击升级按钮失败: {e}")
                # 🆕 保存失败截图
                try:
                    screenshot_path = f"logs/button_click_fail_{int(time.time())}.png"
                    os.makedirs("logs", exist_ok=True)
                    self.driver.save_screenshot(screenshot_path)
                    print(f"  📸 失败截图已保存: {screenshot_path}")
                except:
                    pass
                return False

            # 6. 等待文件上传完成（约7分钟）
            print(f"\n步骤6: 等待文件上传到路由器...")
            print("  ⚠️ 文件上传需要约7分钟，请勿关闭浏览器！")
            upload_wait_time = 420  # 🆕 从300秒（5分钟）增加到420秒（7分钟）

            # 每10秒输出一次进度
            print(f"  📊 开始上传计时，总时长 {upload_wait_time//60} 分钟...")
            for i in range(0, upload_wait_time, 10):
                remaining = upload_wait_time - i
                minutes = remaining // 60
                seconds = remaining % 60
                elapsed_minutes = i // 60
                elapsed_seconds = i % 60
                if minutes > 0:
                    print(f"  ⏳ 上传中... 已等待 {elapsed_minutes}分{elapsed_seconds}秒 | 还需约 {minutes}分{seconds}秒")
                else:
                    print(f"  ⏳ 上传中... 已等待 {elapsed_minutes}分{elapsed_seconds}秒 | 还需约 {seconds} 秒")
                time.sleep(10)

            print("  ✅ 文件上传完成，路由器开始处理...")
            print(f"  📊 总上传等待时间: {upload_wait_time//60} 分钟")

            # 7. 确认升级对话框（如果有）
            print("\n步骤7: 处理确认对话框...")
            time.sleep(2)

            try:
                # 尝试查找确认按钮
                confirm_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), '确定') or contains(text(), 'OK') or contains(text(), 'Confirm')]")
                confirm_btn.click()
                print("  ✅ 已确认升级")
            except:
                print("  ℹ️ 无需确认或自动开始升级")

            # 8. 等待升级完成（路由器会重启）
            print(f"\n步骤8: 等待升级完成（最多{timeout}秒）...")
            print("  路由器正在升级并重启，请耐心等待...")

            # 关闭当前浏览器（路由器重启后连接会断开）
            self.driver.quit()
            self.driver = None

            # 等待路由器重启
            start_time = time.time()
            wait_time = 60  # 先等待60秒让路由器开始重启
            print(f"  等待{wait_time}秒让路由器开始重启...")
            time.sleep(wait_time)

            # 如果跳过重新登录，直接返回成功
            if skip_relogin:
                print(f"\n✅ 固件上传和重启等待完成")
                print(f"  ⚠️  注意：已跳过重新登录步骤")
                print(f"  ⚠️  请在外部通过串口配置IP后再尝试Web登录")
                return True

            # 9. 尝试重新连接
            print(f"\n步骤9: 尝试重新登录路由器...")
            print("  ⚠️ 升级后需要重新输入账号密码")
            retry_count = 0
            max_retries = (timeout - wait_time) // 10  # 每10秒重试一次

            while retry_count < max_retries:
                elapsed = int(time.time() - start_time)
                retry_count += 1

                print(f"\n  尝试第 {retry_count}/{max_retries} 次登录（已等待 {elapsed} 秒）...")

                try:
                    # ⚠️ 重要：强制重新登录，不检查已登录状态
                    # 因为升级后路由器重启，session已失效，必须重新输入账号密码
                    if self.login_web_force(max_retries=1):
                        elapsed = int(time.time() - start_time)
                        print(f"\n✅ 升级成功！路由器已重启并重新登录")
                        print(f"   总耗时: {elapsed} 秒")
                        return True
                except Exception as e:
                    print(f"   登录失败: {e}")

                # 等待后重试
                time.sleep(10)

            # 超时
            elapsed = int(time.time() - start_time)
            print(f"\n❌ 升级超时（已等待 {elapsed} 秒）")
            print("   路由器可能未成功重启或网络不可达")
            return False

        except Exception as e:
            print(f"\n❌ 升级过程中出错: {e}")
            import traceback
            print("\n🔍 详细错误堆栈:")
            print(traceback.format_exc())
            # 🆕 保存异常时的截图
            try:
                if self.driver:
                    screenshot_path = f"logs/exception_{int(time.time())}.png"
                    os.makedirs("logs", exist_ok=True)
                    self.driver.save_screenshot(screenshot_path)
                    print(f"📸 异常截图已保存: {screenshot_path}")
            except:
                pass
            return False

    def add_port_mapping(self, src: str, dst_ip: str, dst_port: str, external_port: str, click_add: bool = True) -> bool:
        """
        添加端口映射规则

        Args:
            src: 源地址 (例如: "192.168.1.100/24")
            dst_ip: 目标IP (例如: "10.10.10.10")
            dst_port: 目标端口 (例如: "222")
            external_port: 外部端口/源端口 (要测试的端口号)
            click_add: 是否点击添加按钮 (首次为True，后续为False)

        Returns:
            bool: 添加成功返回True，失败返回False
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # 点击添加按钮（仅首次）
            if click_add:
                add_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="mapping_operate"]'))
                )
                add_button.click()
                time.sleep(1)

            # 填写源地址 - 使用动态XPath（匹配包含指定ID部分的元素）
            src_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[contains(@id, "_src")]'))
            )
            src_input.clear()
            src_input.send_keys(src)

            # 填写目标IP
            dst_ip_input = self.driver.find_element(By.XPATH, '//input[contains(@id, "_to_dst")]')
            dst_ip_input.clear()
            dst_ip_input.send_keys(dst_ip)

            # 填写目标端口
            dst_port_input = self.driver.find_element(By.XPATH, '//input[contains(@id, "_to_dport")]')
            dst_port_input.clear()
            dst_port_input.send_keys(dst_port)

            # 填写源端口（外部端口/测试端口）
            external_port_input = self.driver.find_element(By.XPATH, '//input[contains(@id, "_dport") and not(contains(@id, "_to_dport"))]')
            external_port_input.clear()
            external_port_input.send_keys(external_port)

            return True

        except Exception as e:
            print(f"添加端口映射失败: {e}")
            return False

    def save_and_check_popup(self) -> bool:
        """
        点击保存按钮并检查是否有弹窗

        Returns:
            bool: True=有弹窗（端口冲突），False=无弹窗（端口可用）
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            # 点击保存按钮
            save_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
            )
            save_button.click()
            time.sleep(1)

            # 检查是否有弹窗（等待2秒）
            try:
                # 尝试定位弹窗的OK按钮
                # 常见的弹窗OK按钮xpath（根据实际情况调整）
                ok_button = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "OK") or contains(text(), "确定")]'))
                )

                # 有弹窗，点击OK关闭
                ok_button.click()
                time.sleep(0.5)
                return True

            except TimeoutException:
                # 没有弹窗
                return False

        except Exception as e:
            print(f"保存并检查弹窗失败: {e}")
            return False

    def configure_firewall_Security_ports(self, ports: list) -> dict:
        """
        配置防火墙安全端口 (HTTP, HTTPS, TELNET, SSH, FTP) - 端口冲突检测测试

        ⚠️ 重要变化: 与 port_check.py 不同，本测试要求所有端口都必须弹出冲突提示！
        - 有弹窗 = ✅ 测试通过（端口冲突检测生效）
        - 无弹窗 = ❌ 测试失败（端口冲突检测失效）

        Args:
            ports: 端口号列表，将依次测试每个端口在所有5个字段上

        Returns:
            dict: 测试结果统计
                {
                    "success": bool,           # 整体是否成功
                    "total": int,              # 总测试次数
                    "passed": int,             # 通过次数（有弹窗）
                    "failed": int,             # 失败次数（无弹窗）
                    "failed_details": list     # 失败的详细信息 [(field, port), ...]
                }
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            # 测试统计
            stats = {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": []
            }

            # 跳转到防火墙安全配置界面
            print("跳转到防火墙Security配置界面...")
            self.navigate_to_page(
                "#network/firewall/security",
                sub_tab_selector="network/firewall/security"
            )
            time.sleep(3)
            self.driver.refresh()
            print("页面已刷新，开始配置防火墙安全端口...")
            time.sleep(3)

            # 定义端口字段配置（按照参考文件顺序）
            port_fields = [
                {"name": "HTTP", "xpath": '//*[@id="1_http_port"]'},
                {"name": "HTTPS", "xpath": '//*[@id="1_https_port"]'},
                {"name": "TELNET", "xpath": '//*[@id="1_telnet_port"]'},
                {"name": "SSH", "xpath": '//*[@id="1_ssh_port"]'},
                {"name": "FTP", "xpath": '//*[@id="1_ftp_port"]'}
            ]

            print(f"\n📋 测试配置:")
            print(f"  端口数量: {len(ports)}")
            print(f"  测试字段: {len(port_fields)} (HTTP, HTTPS, TELNET, SSH, FTP)")
            print(f"  总测试次数: {len(ports) * len(port_fields)}")
            print(f"  ⚠️  预期行为: 所有端口都应该弹出冲突提示")
            print(f"      - 有弹窗 = ✅ 测试通过（端口冲突检测生效）")
            print(f"      - 无弹窗 = ❌ 测试失败（端口冲突检测失效）\n")

            # 遍历每个端口字段
            for field in port_fields:
                field_name = field["name"]
                field_xpath = field["xpath"]

                print(f"\n=== 开始测试 {field_name} 端口冲突检测 ===")

                try:
                    # 遍历所有端口号
                    for i, port in enumerate(ports, 1):
                        stats["total"] += 1
                        print(f"\n[{stats['total']}/{len(ports) * len(port_fields)}] 测试 {field_name} 端口: {port}")

                        try:
                            # 每次循环都重新查找元素，避免StaleElementReferenceException
                            port_field = self.wait.until(
                                EC.element_to_be_clickable((By.XPATH, field_xpath))
                            )
                            save_button = self.wait.until(
                                EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
                            )

                            # 清空端口输入框
                            port_field.clear()

                            # 输入端口号
                            port_field.send_keys(str(port))
                            print(f"  已输入端口号: {port}")

                            # 点击保存
                            save_button.click()
                            print(f"  已点击保存按钮")

                            # 等待页面响应（增加等待时间以确保路由器完成端口冲突检测）
                            time.sleep(2)

                            # ⚠️ 关键：检查是否有HTML模态对话框（必须有弹窗才算通过）
                            has_popup = False
                            try:
                                # 尝试检测HTML弹窗的OK按钮（等待3秒）
                                ok_button = WebDriverWait(self.driver, 3).until(
                                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                                )
                                has_popup = True
                                print(f"  ✅ 检测到冲突弹窗")

                                # 点击OK关闭弹窗
                                ok_button.click()
                                print(f"  已点击OK关闭弹窗")

                                # 等待弹窗关闭和页面稳定（增加等待时间）
                                time.sleep(2)

                            except TimeoutException:
                                # 没有弹窗 - 这是测试失败的情况！
                                has_popup = False
                                print(f"  ❌ 未检测到冲突弹窗（应该有弹窗）")
                            except Exception as e:
                                # 处理弹窗时出错（可能是弹窗已关闭等）
                                print(f"  ⚠️  处理弹窗时出错: {e}")
                                # 如果检测到了弹窗但点击失败，仍然算作有弹窗
                                if has_popup:
                                    print(f"  ℹ️  弹窗已检测到，继续测试")
                                time.sleep(1)

                            # 判断测试结果
                            if has_popup:
                                # 有弹窗 = 测试通过
                                stats["passed"] += 1
                                print(f"  ✅ [{field_name}] 端口 {port} 测试通过（冲突检测生效）")
                            else:
                                # 无弹窗 = 测试失败
                                stats["failed"] += 1
                                stats["failed_details"].append((field_name, port))
                                print(f"  ❌ [{field_name}] 端口 {port} 测试失败（冲突检测失效）")

                            # 等待页面完全稳定后再继续（增加等待）
                            time.sleep(0.5)

                        except Exception as e:
                            stats["failed"] += 1
                            stats["failed_details"].append((field_name, port))
                            print(f"  ❌ 配置 {field_name} 端口 {port} 时出错: {str(e)}")

                            # 如果出现元素状态异常，刷新页面并继续
                            if "stale element reference" in str(e).lower():
                                print("  检测到元素状态异常，刷新页面...")
                                self.driver.refresh()
                                time.sleep(3)
                                # 跳过当前端口，继续下一个
                                continue
                            else:
                                # 对于其他错误，也继续下一个端口
                                continue

                    print(f"\n{field_name} 字段测试完成:")
                    field_total = len(ports)
                    field_passed = sum(1 for f, p in [(field_name, port) for port in ports]
                                      if (f, p) not in stats["failed_details"])
                    field_failed = field_total - field_passed
                    print(f"  总计: {field_total} | 通过: {field_passed} | 失败: {field_failed}")

                except Exception as e:
                    print(f"测试 {field_name} 字段时出错: {str(e)}")
                    # 继续下一个字段
                    continue

            # 判断整体结果
            stats["success"] = (stats["failed"] == 0)

            # 输出测试总结
            print("\n" + "=" * 80)
            print("防火墙Security端口冲突检测测试总结")
            print("=" * 80)
            print(f"总测试次数: {stats['total']}")
            print(f"✅ 通过: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
            print(f"❌ 失败: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")

            if stats["failed"] > 0:
                print(f"\n失败的端口详情 (共{stats['failed']}个):")
                for field, port in stats["failed_details"]:
                    print(f"  - [{field}] 端口 {port} 未弹出冲突提示")

            if stats["success"]:
                print("\n✅ 测试结果: 通过")
                print("   所有端口都正确触发了冲突检测弹窗")
            else:
                print("\n❌ 测试结果: 失败")
                print(f"   有 {stats['failed']} 个端口未触发冲突检测弹窗")

            print("=" * 80)

            return stats

        except Exception as e:
            print(f"配置防火墙端口时发生未知错误: {str(e)}")
            return {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": [],
                "error": str(e)
            }

    def configure_Serial1_ports(self, ports: list) -> dict:
        """
        配置Serial1端口 - 端口冲突检测测试

        ⚠️ 测试逻辑: 所有保留端口都应该弹出冲突提示！
        - 有弹窗 = ✅ 测试通过（端口冲突检测生效）
        - 无弹窗 = ❌ 测试失败（端口冲突检测失效）

        Args:
            ports: 端口号列表

        Returns:
            dict: {
                "success": bool,
                "total": int,
                "passed": int,
                "failed": int,
                "failed_details": list  # [(protocol, port), ...]
            }
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import Select
            from selenium.common.exceptions import TimeoutException

            # 测试统计
            stats = {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": []
            }

            # 跳转到Serial1配置界面
            print("跳转到Serial1配置界面...")
            self.navigate_to_page("#industrial/serialport/serial1")
            time.sleep(3)
            print("页面已刷新，开始配置Serial1端口...")

            # 等待Serial1页面加载完成
            time.sleep(4)

            # 1. 启用Serial1
            print("查找并启用Serial1...")
            try:
                enable_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]'))
                )

                # 检查是否已启用
                is_enabled = False
                try:
                    # 方法1: 检查checked属性
                    if enable_btn.get_attribute("checked"):
                        is_enabled = True
                        print("启用按钮已经是勾选状态")
                except:
                    pass

                try:
                    # 方法2: 检查是否包含active或selected类
                    if not is_enabled and (
                            "active" in enable_btn.get_attribute("class") or "selected" in enable_btn.get_attribute(
                            "class")):
                        is_enabled = True
                        print("启用按钮已经是激活状态")
                except:
                    pass

                # 方法3: 检查元素类型和状态
                if not is_enabled:
                    if enable_btn.get_attribute("type") == "checkbox" and enable_btn.is_selected():
                        is_enabled = True
                        print("启用按钮已经是选中状态")

                # 如果未启用，则点击启用
                if not is_enabled:
                    print("点击启用Serial1...")
                    enable_btn.click()
                    print("已点击启用Serial1")
                    time.sleep(2)
                else:
                    print("Serial1已经是启用状态，跳过点击")

            except Exception as e:
                print(f"处理启用Serial1按钮时出错: {str(e)}")
                # 尝试使用JavaScript点击
                try:
                    print("尝试使用JavaScript点击启用按钮...")
                    self.driver.execute_script("document.getElementById('1_enable').click();")
                    print("已通过JavaScript点击启用按钮")
                    time.sleep(2)
                except Exception as js_e:
                    print(f"JavaScript点击也失败: {str(js_e)}")
                    return stats

            # 2. 选择DTU Mode
            print("选择DTU Mode...")
            try:
                mode_select = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_mode"]'))
                )
                mode_dropdown = Select(mode_select)
                mode_dropdown.select_by_value("1")  # DTU Mode
                print("已选择DTU Mode")
                time.sleep(1)
            except Exception as e:
                print(f"选择模式失败: {e}")
                return stats

            # 3. 定义协议与端口字段映射
            protocols = [
                {"name": "Modbus", "value": "2", "port_field": "1_local_port_1"},
                {"name": "TCP Server", "value": "3", "port_field": "1_local_port_2"},
                {"name": "UDP Server", "value": "4", "port_field": "1_local_port_2"}
            ]

            print(f"\n📋 测试配置:")
            print(f"  端口数量: {len(ports)}")
            print(f"  测试协议: {len(protocols)} (Modbus, TCP Server, UDP Server)")
            print(f"  总测试次数: {len(ports) * len(protocols)}")
            print(f"  ⚠️  预期行为: 所有端口都应该弹出冲突提示\n")

            # 4. 遍历每个协议
            for protocol in protocols:
                protocol_name = protocol["name"]
                protocol_value = protocol["value"]
                port_field_id = protocol["port_field"]

                print(f"\n=== 开始测试 {protocol_name} 协议 ===")

                try:
                    # 选择协议
                    protocol_select = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="1_protocol"]'))
                    )
                    protocol_dropdown = Select(protocol_select)
                    protocol_dropdown.select_by_value(protocol_value)
                    print(f"已选择 {protocol_name} 协议")
                    time.sleep(1)

                    # 遍历所有端口
                    for i, port in enumerate(ports, 1):
                        stats["total"] += 1
                        print(f"\n[{stats['total']}/{len(ports) * len(protocols)}] 测试 {protocol_name} 端口: {port}")

                        try:
                            # 定位端口输入框
                            port_field = self.wait.until(
                                EC.element_to_be_clickable((By.XPATH, f'//*[@id="{port_field_id}"]'))
                            )
                            save_button = self.wait.until(
                                EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
                            )

                            # 清空并输入端口号
                            port_field.clear()
                            port_field.send_keys(str(port))
                            print(f"  已输入端口号: {port}")

                            # 点击保存
                            save_button.click()
                            print(f"  已点击保存按钮")
                            time.sleep(2)  # 增加等待时间：1秒→2秒，确保路由器有足够时间检测端口冲突

                            # 检查弹窗
                            has_popup = False
                            try:
                                ok_button = WebDriverWait(self.driver, 3).until(
                                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                                )
                                has_popup = True
                                print(f"  ✅ 检测到冲突弹窗")
                                ok_button.click()
                                print(f"  已点击OK关闭弹窗")
                                time.sleep(2)
                            except TimeoutException:
                                has_popup = False
                                print(f"  ❌ 未检测到冲突弹窗（应该有弹窗）")
                            except Exception as e:
                                print(f"  ⚠️  处理弹窗时出错: {e}")
                                if has_popup:
                                    print(f"  ℹ️  弹窗已检测到，继续测试")
                                time.sleep(1)

                            # 判断结果
                            if has_popup:
                                stats["passed"] += 1
                                print(f"  ✅ [{protocol_name}] 端口 {port} 测试通过")
                            else:
                                stats["failed"] += 1
                                stats["failed_details"].append((protocol_name, port))
                                print(f"  ❌ [{protocol_name}] 端口 {port} 测试失败")

                            time.sleep(0.5)

                        except Exception as e:
                            stats["failed"] += 1
                            stats["failed_details"].append((protocol_name, port))
                            print(f"  ❌ 配置 {protocol_name} 端口 {port} 时出错: {e}")

                            # 元素状态异常时刷新页面
                            if "stale element reference" in str(e).lower():
                                print("  检测到元素状态异常，刷新页面...")
                                self.driver.refresh()
                                time.sleep(3)
                                continue
                            else:
                                continue

                    print(f"\n{protocol_name} 协议测试完成")

                except Exception as e:
                    print(f"测试 {protocol_name} 协议时出错: {e}")
                    continue

            # 判断整体结果
            stats["success"] = (stats["failed"] == 0)

            # 输出总结
            print("\n" + "=" * 80)
            print("Serial1端口冲突检测测试总结")
            print("=" * 80)
            print(f"总测试次数: {stats['total']}")
            print(f"✅ 通过: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
            print(f"❌ 失败: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")

            if stats["failed"] > 0:
                print(f"\n失败的端口详情 (共{stats['failed']}个):")
                for protocol, port in stats["failed_details"]:
                    print(f"  - [{protocol}] 端口 {port} 未弹出冲突提示")

            if stats["success"]:
                print("\n✅ 测试结果: 通过")
            else:
                print("\n❌ 测试结果: 失败")

            print("=" * 80)

            return stats

        except Exception as e:
            print(f"配置Serial1端口时发生未知错误: {str(e)}")
            return {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": [],
                "error": str(e)
            }

    def configure_Serial2_ports(self, ports: list) -> dict:
        """
        配置Serial2端口 - 端口冲突检测测试

        ⚠️ 测试逻辑: 所有保留端口都应该弹出冲突提示！
        - 有弹窗 = ✅ 测试通过（端口冲突检测生效）
        - 无弹窗 = ❌ 测试失败（端口冲突检测失效）

        Args:
            ports: 端口号列表

        Returns:
            dict: {
                "success": bool,
                "total": int,
                "passed": int,
                "failed": int,
                "failed_details": list  # [(protocol, port), ...]
            }
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import Select
            from selenium.common.exceptions import TimeoutException

            # 测试统计
            stats = {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": []
            }

            # 跳转到Serial2配置界面
            print("跳转到Serial2配置界面...")
            self.navigate_to_page("#industrial/serialport/serial2")
            time.sleep(3)
            print("页面已刷新，开始配置Serial2端口...")

            # 等待Serial2页面加载完成
            time.sleep(4)

            # 1. 启用Serial2
            print("查找并启用Serial2...")
            try:
                enable_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]'))
                )

                # 检查是否已启用
                is_enabled = False
                try:
                    # 方法1: 检查checked属性
                    if enable_btn.get_attribute("checked"):
                        is_enabled = True
                        print("启用按钮已经是勾选状态")
                except:
                    pass

                try:
                    # 方法2: 检查是否包含active或selected类
                    if not is_enabled and (
                            "active" in enable_btn.get_attribute("class") or "selected" in enable_btn.get_attribute(
                            "class")):
                        is_enabled = True
                        print("启用按钮已经是激活状态")
                except:
                    pass

                # 方法3: 检查元素类型和状态
                if not is_enabled:
                    if enable_btn.get_attribute("type") == "checkbox" and enable_btn.is_selected():
                        is_enabled = True
                        print("启用按钮已经是选中状态")

                # 如果未启用，则点击启用
                if not is_enabled:
                    print("点击启用Serial2...")
                    enable_btn.click()
                    print("已点击启用Serial2")
                    time.sleep(2)
                else:
                    print("Serial2已经是启用状态，跳过点击")

            except Exception as e:
                print(f"处理启用Serial2按钮时出错: {str(e)}")
                # 尝试使用JavaScript点击
                try:
                    print("尝试使用JavaScript点击启用按钮...")
                    self.driver.execute_script("document.getElementById('1_enable').click();")
                    print("已通过JavaScript点击启用按钮")
                    time.sleep(2)
                except Exception as js_e:
                    print(f"JavaScript点击也失败: {str(js_e)}")
                    return stats

            # 2. 选择DTU Mode
            print("选择DTU Mode...")
            try:
                mode_select = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_mode"]'))
                )
                mode_dropdown = Select(mode_select)
                mode_dropdown.select_by_value("1")  # DTU Mode
                print("已选择DTU Mode")
                time.sleep(1)
            except Exception as e:
                print(f"选择模式失败: {e}")
                return stats

            # 3. 定义协议与端口字段映射
            protocols = [
                {"name": "Modbus", "value": "2", "port_field": "1_local_port_1"},
                {"name": "TCP Server", "value": "3", "port_field": "1_local_port_2"},
                {"name": "UDP Server", "value": "4", "port_field": "1_local_port_2"}
            ]

            print(f"\n📋 测试配置:")
            print(f"  端口数量: {len(ports)}")
            print(f"  测试协议: {len(protocols)} (Modbus, TCP Server, UDP Server)")
            print(f"  总测试次数: {len(ports) * len(protocols)}")
            print(f"  ⚠️  预期行为: 所有端口都应该弹出冲突提示\n")

            # 4. 遍历每个协议
            for protocol in protocols:
                protocol_name = protocol["name"]
                protocol_value = protocol["value"]
                port_field_id = protocol["port_field"]

                print(f"\n=== 开始测试 {protocol_name} 协议 ===")

                try:
                    # 选择协议
                    protocol_select = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="1_protocol"]'))
                    )
                    protocol_dropdown = Select(protocol_select)
                    protocol_dropdown.select_by_value(protocol_value)
                    print(f"已选择 {protocol_name} 协议")
                    time.sleep(1)

                    # 遍历所有端口
                    for i, port in enumerate(ports, 1):
                        stats["total"] += 1
                        print(f"\n[{stats['total']}/{len(ports) * len(protocols)}] 测试 {protocol_name} 端口: {port}")

                        try:
                            # 定位端口输入框
                            port_field = self.wait.until(
                                EC.element_to_be_clickable((By.XPATH, f'//*[@id="{port_field_id}"]'))
                            )
                            save_button = self.wait.until(
                                EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
                            )

                            # 清空并输入端口号
                            port_field.clear()
                            port_field.send_keys(str(port))
                            print(f"  已输入端口号: {port}")

                            # 点击保存
                            save_button.click()
                            print(f"  已点击保存按钮")
                            time.sleep(2)  # 增加等待时间：1秒→2秒，确保路由器有足够时间检测端口冲突

                            # 检查弹窗
                            has_popup = False
                            try:
                                ok_button = WebDriverWait(self.driver, 3).until(
                                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                                )
                                has_popup = True
                                print(f"  ✅ 检测到冲突弹窗")
                                ok_button.click()
                                print(f"  已点击OK关闭弹窗")
                                time.sleep(2)
                            except TimeoutException:
                                has_popup = False
                                print(f"  ❌ 未检测到冲突弹窗（应该有弹窗）")
                            except Exception as e:
                                print(f"  ⚠️  处理弹窗时出错: {e}")
                                if has_popup:
                                    print(f"  ℹ️  弹窗已检测到，继续测试")
                                time.sleep(1)

                            # 判断结果
                            if has_popup:
                                stats["passed"] += 1
                                print(f"  ✅ [{protocol_name}] 端口 {port} 测试通过")
                            else:
                                stats["failed"] += 1
                                stats["failed_details"].append((protocol_name, port))
                                print(f"  ❌ [{protocol_name}] 端口 {port} 测试失败")

                            time.sleep(0.5)

                        except Exception as e:
                            stats["failed"] += 1
                            stats["failed_details"].append((protocol_name, port))
                            print(f"  ❌ 配置 {protocol_name} 端口 {port} 时出错: {e}")

                            # 元素状态异常时刷新页面
                            if "stale element reference" in str(e).lower():
                                print("  检测到元素状态异常，刷新页面...")
                                self.driver.refresh()
                                time.sleep(3)
                                continue
                            else:
                                continue

                    print(f"\n{protocol_name} 协议测试完成")

                except Exception as e:
                    print(f"测试 {protocol_name} 协议时出错: {e}")
                    continue

            # 判断整体结果
            stats["success"] = (stats["failed"] == 0)

            # 输出总结
            print("\n" + "=" * 80)
            print("Serial2端口冲突检测测试总结")
            print("=" * 80)
            print(f"总测试次数: {stats['total']}")
            print(f"✅ 通过: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
            print(f"❌ 失败: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")

            if stats["failed"] > 0:
                print(f"\n失败的端口详情 (共{stats['failed']}个):")
                for protocol, port in stats["failed_details"]:
                    print(f"  - [{protocol}] 端口 {port} 未弹出冲突提示")

            if stats["success"]:
                print("\n✅ 测试结果: 通过")
            else:
                print("\n❌ 测试结果: 失败")

            print("=" * 80)

            return stats

        except Exception as e:
            print(f"配置Serial2端口时发生未知错误: {str(e)}")
            return {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": [],
                "error": str(e)
            }

    def configure_Modbus_TCP_ports(self, ports: list) -> dict:
        """
        配置Modbus TCP端口 - 端口冲突检测测试

        ⚠️ 测试逻辑: 所有保留端口都应该弹出冲突提示！
        - 有弹窗 = ✅ 测试通过（端口冲突检测生效）
        - 无弹窗 = ❌ 测试失败（端口冲突检测失效）

        Args:
            ports: 端口号列表

        Returns:
            dict: {
                "success": bool,
                "total": int,
                "passed": int,
                "failed": int,
                "failed_details": list  # [port, ...]
            }
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            # 测试统计
            stats = {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": []
            }

            # 跳转到Modbus TCP配置界面
            print("跳转到Modbus TCP配置界面...")
            self.navigate_to_page("#industrial/modbus/modbustcp")
            time.sleep(3)
            print("页面已刷新，开始配置Modbus TCP端口...")
            time.sleep(3)

            # 1. 启用Modbus TCP
            print("查找并启用Modbus TCP...")
            try:
                enable_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]'))
                )

                # 检查是否已启用
                is_enabled = (enable_btn.get_attribute("checked") or
                             enable_btn.is_selected())

                if not is_enabled:
                    print("点击启用Modbus TCP...")
                    enable_btn.click()
                    time.sleep(2)
                else:
                    print("Modbus TCP已启用，跳过")
            except Exception as e:
                print(f"启用Modbus TCP失败: {e}")
                return stats

            print(f"\n📋 测试配置:")
            print(f"  保留端口: {ports}")
            print(f"  端口数量: {len(ports)}")
            print(f"  测试字段: Local Port (1个)")
            print(f"  总测试次数: {len(ports)}")
            print(f"  ⚠️  预期行为: 所有端口都应该弹出冲突提示\n")

            # 2. 遍历所有端口
            for i, port in enumerate(ports, 1):
                stats["total"] += 1
                print(f"\n[{stats['total']}/{len(ports)}] 测试端口: {port}")

                try:
                    # 定位端口输入框
                    port_field = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="1_local_port"]'))
                    )
                    save_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
                    )

                    # 清空并输入端口号
                    port_field.clear()
                    port_field.send_keys(str(port))
                    print(f"  已输入端口号: {port}")

                    # 点击保存
                    save_button.click()
                    print(f"  已点击保存按钮")
                    time.sleep(2)  # 增加等待时间：1秒→2秒，确保路由器有足够时间检测端口冲突

                    # 检查弹窗
                    has_popup = False
                    try:
                        ok_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                        )
                        has_popup = True
                        print(f"  ✅ 检测到冲突弹窗")
                        ok_button.click()
                        print(f"  已点击OK关闭弹窗")
                        time.sleep(2)
                    except TimeoutException:
                        has_popup = False
                        print(f"  ❌ 未检测到冲突弹窗（应该有弹窗）")
                    except Exception as e:
                        print(f"  ⚠️  处理弹窗时出错: {e}")
                        if has_popup:
                            print(f"  ℹ️  弹窗已检测到，继续测试")
                        time.sleep(1)

                    # 判断结果
                    if has_popup:
                        stats["passed"] += 1
                        print(f"  ✅ 端口 {port} 测试通过")
                    else:
                        stats["failed"] += 1
                        stats["failed_details"].append(port)
                        print(f"  ❌ 端口 {port} 测试失败")

                    time.sleep(0.5)

                except Exception as e:
                    stats["failed"] += 1
                    stats["failed_details"].append(port)
                    print(f"  ❌ 配置端口 {port} 时出错: {e}")

                    # 元素状态异常时刷新页面
                    if "stale element reference" in str(e).lower():
                        print("  检测到元素状态异常，刷新页面...")
                        self.driver.refresh()
                        time.sleep(3)
                        continue
                    else:
                        continue

            # 判断整体结果
            stats["success"] = (stats["failed"] == 0)

            # 输出总结
            print("\n" + "=" * 80)
            print("Modbus TCP端口冲突检测测试总结")
            print("=" * 80)
            print(f"总测试次数: {stats['total']}")
            print(f"✅ 通过: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
            print(f"❌ 失败: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")

            if stats["failed"] > 0:
                print(f"\n失败的端口详情 (共{stats['failed']}个):")
                for port in stats["failed_details"]:
                    print(f"  - 端口 {port} 未弹出冲突提示")

            if stats["success"]:
                print("\n✅ 测试结果: 通过")
            else:
                print("\n❌ 测试结果: 失败")

            print("=" * 80)

            return stats

        except Exception as e:
            print(f"配置Modbus TCP端口时发生未知错误: {str(e)}")
            return {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": [],
                "error": str(e)
            }

    def configure_snmp_ports(self, ports: list) -> dict:
        """
        配置SNMP端口 - 端口冲突检测测试

        ⚠️ 测试逻辑: 所有保留端口都应该弹出冲突提示！
        - 有弹窗 = ✅ 测试通过（端口冲突检测生效）
        - 无弹窗 = ❌ 测试失败（端口冲突检测失效）

        Args:
            ports: 端口号列表

        Returns:
            dict: {
                "success": bool,
                "total": int,
                "passed": int,
                "failed": int,
                "failed_details": list  # [port, ...]
            }
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            # 测试统计
            stats = {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": []
            }

            # 跳转到SNMP配置界面
            print("跳转到SNMP配置界面...")
            self.navigate_to_page("#industrial/snmp/snmp")
            time.sleep(3)
            print("页面已刷新，开始配置SNMP端口...")
            time.sleep(3)

            # 1. 启用SNMP
            print("查找并启用SNMP...")
            try:
                enable_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="0_enable"]'))
                )

                # 检查是否已启用
                is_enabled = (enable_btn.get_attribute("checked") or
                             enable_btn.is_selected())

                if not is_enabled:
                    print("点击启用SNMP...")
                    enable_btn.click()
                    time.sleep(2)
                else:
                    print("SNMP已启用，跳过")
            except Exception as e:
                print(f"启用SNMP失败: {e}")
                return stats

            # 2. 填写基本信息（location和contact）
            print("填写SNMP基本信息...")
            try:
                location_input = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="0_location"]'))
                )
                location_input.clear()
                location_input.send_keys("123")
                print("已填写Location")

                contact_input = self.driver.find_element(By.XPATH, '//*[@id="0_contact"]')
                contact_input.clear()
                contact_input.send_keys("admin")
                print("已填写Contact")
                time.sleep(1)
            except Exception as e:
                print(f"填写基本信息失败: {e}，继续测试端口...")

            print(f"\n📋 测试配置:")
            print(f"  保留端口: {ports}")
            print(f"  端口数量: {len(ports)}")
            print(f"  测试字段: Port (1个)")
            print(f"  总测试次数: {len(ports)}")
            print(f"  ⚠️  预期行为: 所有端口都应该弹出冲突提示\n")

            # 3. 遍历所有端口
            for i, port in enumerate(ports, 1):
                stats["total"] += 1
                print(f"\n[{stats['total']}/{len(ports)}] 测试端口: {port}")

                try:
                    # 定位端口输入框
                    # 注意：SNMP端口字段使用 0_port (不是1_port)
                    port_field = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="0_port"]'))
                    )
                    save_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
                    )

                    # 清空并输入端口号
                    port_field.clear()
                    port_field.send_keys(str(port))
                    print(f"  已输入端口号: {port}")

                    # 点击保存
                    save_button.click()
                    print(f"  已点击保存按钮")
                    time.sleep(2)  # 增加等待时间：1秒→2秒，确保路由器有足够时间检测端口冲突

                    # 检查弹窗
                    has_popup = False
                    try:
                        ok_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                        )
                        has_popup = True
                        print(f"  ✅ 检测到冲突弹窗")
                        ok_button.click()
                        print(f"  已点击OK关闭弹窗")
                        time.sleep(2)
                    except TimeoutException:
                        has_popup = False
                        print(f"  ❌ 未检测到冲突弹窗（应该有弹窗）")
                    except Exception as e:
                        print(f"  ⚠️  处理弹窗时出错: {e}")
                        if has_popup:
                            print(f"  ℹ️  弹窗已检测到，继续测试")
                        time.sleep(1)

                    # 判断结果
                    if has_popup:
                        stats["passed"] += 1
                        print(f"  ✅ 端口 {port} 测试通过")
                    else:
                        stats["failed"] += 1
                        stats["failed_details"].append(port)
                        print(f"  ❌ 端口 {port} 测试失败")

                    time.sleep(0.5)

                except Exception as e:
                    stats["failed"] += 1
                    stats["failed_details"].append(port)
                    print(f"  ❌ 配置端口 {port} 时出错: {e}")

                    # 元素状态异常时刷新页面
                    if "stale element reference" in str(e).lower():
                        print("  检测到元素状态异常，刷新页面...")
                        self.driver.refresh()
                        time.sleep(3)
                        continue
                    else:
                        continue

            # 判断整体结果
            stats["success"] = (stats["failed"] == 0)

            # 输出总结
            print("\n" + "=" * 80)
            print("SNMP端口冲突检测测试总结")
            print("=" * 80)
            print(f"总测试次数: {stats['total']}")
            print(f"✅ 通过: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
            print(f"❌ 失败: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")

            if stats["failed"] > 0:
                print(f"\n失败的端口详情 (共{stats['failed']}个):")
                for port in stats["failed_details"]:
                    print(f"  - 端口 {port} 未弹出冲突提示")

            if stats["success"]:
                print("\n✅ 测试结果: 通过")
            else:
                print("\n❌ 测试结果: 失败")

            print("=" * 80)

            return stats

        except Exception as e:
            print(f"配置SNMP端口时发生未知错误: {str(e)}")
            return {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": [],
                "error": str(e)
            }

    def configure_GPS_ports(self, ports: list) -> dict:
        """
        配置GPS IP Forwarding端口 - 端口冲突检测测试

        ⚠️ 测试逻辑: 所有保留端口都应该弹出冲突提示！
        - 有弹窗 = ✅ 测试通过（端口冲突检测生效）
        - 无弹窗 = ❌ 测试失败（端口冲突检测失效）

        测试流程:
        1. 跳转到GPS配置页面并启用GPS
        2. 跳转到IP Forwarding页面
        3. 启用IP Forwarding，类型选择server
        4. 遍历所有端口，测试本地端口字段的冲突检测

        Args:
            ports: 端口号列表

        Returns:
            dict: {
                "success": bool,
                "total": int,
                "passed": int,
                "failed": int,
                "failed_details": list  # [port, ...]
            }
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException
            from selenium.webdriver.support.ui import Select

            # 测试统计
            stats = {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": []
            }

            # === 步骤1: 跳转到GPS配置页面并启用GPS ===
            print("\n步骤1: 跳转到GPS配置页面...")
            self.navigate_to_page("#industrial/gps/gps")
            time.sleep(3)
            print("页面已加载")

            # 启用GPS
            print("查找并启用GPS...")
            try:
                enable_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]'))
                )

                # 检查是否已启用
                is_enabled = (enable_btn.get_attribute("checked") or
                             enable_btn.is_selected())

                if not is_enabled:
                    print("点击启用GPS...")
                    enable_btn.click()
                    time.sleep(1)
                else:
                    print("GPS已启用，跳过")

                # 点击保存
                save_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
                )
                save_button.click()
                print("已保存GPS配置")
                time.sleep(2)
            except Exception as e:
                print(f"启用GPS失败: {e}")
                return stats

            # === 步骤2: 跳转到IP Forwarding页面 ===
            print("\n步骤2: 跳转到IP Forwarding页面...")
            self.navigate_to_page("#industrial/gps/ipforwarding")
            time.sleep(3)
            print("页面已刷新，开始配置IP Forwarding...")
            time.sleep(3)

            # === 步骤3: 启用IP Forwarding，类型选择server ===
            print("\n步骤3: 启用IP Forwarding并配置为server模式...")
            try:
                # 启用IP Forwarding
                enable_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]'))
                )

                is_enabled = (enable_btn.get_attribute("checked") or
                             enable_btn.is_selected())

                if not is_enabled:
                    print("点击启用IP Forwarding...")
                    enable_btn.click()
                    time.sleep(1)
                else:
                    print("IP Forwarding已启用，跳过")

                # 选择类型为server
                print("设置类型为server...")
                type_select = Select(self.wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="1_type"]'))
                ))
                type_select.select_by_value("server")
                print("已选择server类型")
                time.sleep(1)

            except Exception as e:
                print(f"配置IP Forwarding失败: {e}")
                return stats

            print(f"\n📋 测试配置:")
            print(f"  保留端口: {ports}")
            print(f"  端口数量: {len(ports)}")
            print(f"  测试字段: Local Port (1个)")
            print(f"  总测试次数: {len(ports)}")
            print(f"  ⚠️  预期行为: 所有端口都应该弹出冲突提示\n")

            # === 步骤4: 遍历所有端口，测试端口冲突检测 ===
            for i, port in enumerate(ports, 1):
                stats["total"] += 1
                print(f"\n[{stats['total']}/{len(ports)}] 测试端口: {port}")

                try:
                    # 定位本地端口输入框
                    port_field = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="1_local_port"]'))
                    )
                    save_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
                    )

                    # 清空并输入端口号
                    port_field.clear()
                    port_field.send_keys(str(port))
                    print(f"  已输入端口号: {port}")

                    # 点击保存
                    save_button.click()
                    print(f"  已点击保存按钮")
                    time.sleep(2)  # 等待2秒，确保路由器有足够时间检测端口冲突

                    # 检查弹窗
                    has_popup = False
                    try:
                        ok_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                        )
                        has_popup = True
                        print(f"  ✅ 检测到冲突弹窗")
                        ok_button.click()
                        print(f"  已点击OK关闭弹窗")
                        time.sleep(2)
                    except TimeoutException:
                        has_popup = False
                        print(f"  ❌ 未检测到冲突弹窗（应该有弹窗）")
                    except Exception as e:
                        print(f"  ⚠️  处理弹窗时出错: {e}")
                        if has_popup:
                            print(f"  ℹ️  弹窗已检测到，继续测试")
                        time.sleep(1)

                    # 判断结果
                    if has_popup:
                        stats["passed"] += 1
                        print(f"  ✅ 端口 {port} 测试通过")
                    else:
                        stats["failed"] += 1
                        stats["failed_details"].append(port)
                        print(f"  ❌ 端口 {port} 测试失败")

                    time.sleep(0.5)

                except Exception as e:
                    stats["failed"] += 1
                    stats["failed_details"].append(port)
                    print(f"  ❌ 配置端口 {port} 时出错: {e}")

                    # 元素状态异常时刷新页面
                    if "stale element reference" in str(e).lower():
                        print("  检测到元素状态异常，刷新页面...")
                        self.driver.refresh()
                        time.sleep(3)
                        continue
                    else:
                        continue

            # 判断整体结果
            stats["success"] = (stats["failed"] == 0)

            # 输出总结
            print("\n" + "=" * 80)
            print("GPS IP Forwarding端口冲突检测测试总结")
            print("=" * 80)
            print(f"总测试次数: {stats['total']}")
            print(f"✅ 通过: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
            print(f"❌ 失败: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")

            if stats["failed"] > 0:
                print(f"\n失败的端口详情 (共{stats['failed']}个):")
                for port in stats["failed_details"]:
                    print(f"  - 端口 {port} 未弹出冲突提示")

            if stats["success"]:
                print("\n✅ 测试结果: 通过")
                print("   所有端口都正确触发了冲突检测弹窗")
            else:
                print("\n❌ 测试结果: 失败")
                print(f"   有 {stats['failed']} 个端口未触发冲突检测")

            print("=" * 80)

            return stats

        except Exception as e:
            print(f"配置GPS端口时发生未知错误: {str(e)}")
            return {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": [],
                "error": str(e)
            }

    def configure_OpenVPN_ports(self, ports: list) -> dict:
        """
        配置OpenVPN服务器端口 - 端口冲突检测测试

        ⚠️ 测试逻辑: 所有保留端口都应该弹出冲突提示！
        - 有弹窗 = ✅ 测试通过（端口冲突检测生效）
        - 无弹窗 = ❌ 测试失败（端口冲突检测失效）

        测试流程:
        1. 跳转到OpenVPN服务器配置页面
        2. 启用OpenVPN服务器
        3. 配置OpenVPN服务器必填字段
           - 服务器IP (Listen IP): 192.168.40.47
           - 本地虚拟IP (Local Virtual IP): 192.168.50.16
           - 远程虚拟IP (Remote Virtual IP): 192.168.50.47
        4. 遍历所有端口，测试端口字段的冲突检测

        Args:
            ports: 端口号列表

        Returns:
            dict: {
                "success": bool,
                "total": int,
                "passed": int,
                "failed": int,
                "failed_details": list  # [port, ...]
            }
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            # 测试统计
            stats = {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": []
            }

            # === 步骤1: 跳转到OpenVPN服务器配置页面 ===
            print("\n步骤1: 跳转到OpenVPN服务器配置页面...")
            self.navigate_to_page("#network/vpn/server")  # 修正路径：#network/vpn/server
            time.sleep(3)

            # 再次刷新页面（参考防火墙Security的实现）
            print("  刷新页面以确保元素加载...")
            self.driver.refresh()
            time.sleep(3)
            print("  ✅ 页面已完全加载")

            # === 步骤2: 启用OpenVPN服务器 ===
            print("\n步骤2: 启用OpenVPN服务器...")
            try:
                # 启用OpenVPN服务器
                enable_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]'))
                )

                # 检查是否已启用
                is_enabled = (enable_btn.get_attribute("checked") or
                             enable_btn.is_selected())

                if not is_enabled:
                    print("点击启用OpenVPN服务器...")
                    enable_btn.click()
                    time.sleep(1)
                else:
                    print("OpenVPN服务器已启用，跳过")

            except Exception as e:
                print(f"启用OpenVPN服务器失败: {e}")
                return stats

            # === 步骤3: 配置OpenVPN服务器必填字段 ===
            print("\n步骤3: 配置OpenVPN服务器必填字段...")
            try:
                # 服务器IP (Listen IP)
                print("  配置服务器IP...")
                listen_ip_field = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_listen_ip"]'))
                )
                listen_ip_field.clear()
                listen_ip_field.send_keys("192.168.40.47")
                print("  ✅ 已输入服务器IP: 192.168.40.47")

                # 本地虚拟IP (Local Virtual IP)
                print("  配置本地虚拟IP...")
                local_virtual_ip_field = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_local_virtual_ip"]'))
                )
                local_virtual_ip_field.clear()
                local_virtual_ip_field.send_keys("192.168.50.16")
                print("  ✅ 已输入本地虚拟IP: 192.168.50.16")

                # 远程虚拟IP (Remote Virtual IP)
                print("  配置远程虚拟IP...")
                remote_virtual_ip_field = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_remote_virtual_ip"]'))
                )
                remote_virtual_ip_field.clear()
                remote_virtual_ip_field.send_keys("192.168.50.47")
                print("  ✅ 已输入远程虚拟IP: 192.168.50.47")

            except Exception as e:
                print(f"配置OpenVPN服务器必填字段失败: {e}")
                return stats

            print(f"\n📋 测试配置:")
            print(f"  保留端口: {ports}")
            print(f"  端口数量: {len(ports)}")
            print(f"  测试字段: Port (1个)")
            print(f"  总测试次数: {len(ports)}")
            print(f"  ⚠️  预期行为: 所有端口都应该弹出冲突提示\n")

            # === 步骤4: 遍历所有端口，测试端口冲突检测 ===
            for i, port in enumerate(ports, 1):
                stats["total"] += 1
                print(f"\n[{stats['total']}/{len(ports)}] 测试端口: {port}")

                try:
                    # 定位端口输入框
                    port_field = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="1_port"]'))
                    )
                    save_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
                    )

                    # 清空并输入端口号
                    port_field.clear()
                    port_field.send_keys(str(port))
                    print(f"  已输入端口号: {port}")

                    # 点击保存
                    save_button.click()
                    print(f"  已点击保存按钮")
                    time.sleep(2)  # 等待2秒，确保路由器有足够时间检测端口冲突

                    # 检查弹窗
                    has_popup = False
                    try:
                        ok_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                        )
                        has_popup = True
                        print(f"  ✅ 检测到冲突弹窗")
                        ok_button.click()
                        print(f"  已点击OK关闭弹窗")
                        time.sleep(2)
                    except TimeoutException:
                        has_popup = False
                        print(f"  ❌ 未检测到冲突弹窗（应该有弹窗）")
                    except Exception as e:
                        print(f"  ⚠️  处理弹窗时出错: {e}")
                        if has_popup:
                            print(f"  ℹ️  弹窗已检测到，继续测试")
                        time.sleep(1)

                    # 判断结果
                    if has_popup:
                        stats["passed"] += 1
                        print(f"  ✅ 端口 {port} 测试通过")
                    else:
                        stats["failed"] += 1
                        stats["failed_details"].append(port)
                        print(f"  ❌ 端口 {port} 测试失败")

                    time.sleep(0.5)

                except Exception as e:
                    stats["failed"] += 1
                    stats["failed_details"].append(port)
                    print(f"  ❌ 配置端口 {port} 时出错: {e}")

                    # 元素状态异常时刷新页面
                    if "stale element reference" in str(e).lower():
                        print("  检测到元素状态异常，刷新页面...")
                        self.driver.refresh()
                        time.sleep(3)
                        continue
                    else:
                        continue

            # 判断整体结果
            stats["success"] = (stats["failed"] == 0)

            # 输出总结
            print("\n" + "=" * 80)
            print("OpenVPN服务器端口冲突检测测试总结")
            print("=" * 80)
            print(f"总测试次数: {stats['total']}")
            print(f"✅ 通过: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
            print(f"❌ 失败: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")

            if stats["failed"] > 0:
                print(f"\n失败的端口详情 (共{stats['failed']}个):")
                for port in stats["failed_details"]:
                    print(f"  - 端口 {port} 未弹出冲突提示")

            if stats["success"]:
                print("\n✅ 测试结果: 通过")
                print("   所有端口都正确触发了冲突检测弹窗")
            else:
                print("\n❌ 测试结果: 失败")
                print(f"   有 {stats['failed']} 个端口未触发冲突检测")

            print("=" * 80)

            return stats

        except Exception as e:
            print(f"配置OpenVPN端口时发生未知错误: {str(e)}")
            return {
                "success": False,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failed_details": [],
                "error": str(e)
            }

    def test_cross_page_port_conflict_openvpn_firewall(self, test_port: int = 1111) -> dict:
        """
        测试OpenVPN与防火墙FTP端口的跨页面端口冲突检测
        用例ID: 19
        测试点: OpenVPN Server与防火墙自定义端口冲突检测

        测试流程:
        1. 跳转到防火墙Security页面
        2. 配置FTP端口为指定端口号（默认1111）
        3. 启用FTP功能
        4. 保存并应用配置
        5. 跳转到OpenVPN服务器页面
        6. 尝试配置OpenVPN端口为相同端口号
        7. 检测是否弹出端口冲突提醒

        Args:
            test_port: 测试端口号，默认1111

        Returns:
            dict: {
                "success": bool,          # 是否检测到端口冲突弹窗
                "firewall_config": bool,  # 防火墙FTP配置是否成功
                "openvpn_conflict": bool, # OpenVPN是否检测到冲突
                "message": str            # 详细信息
            }
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            result = {
                "success": False,
                "firewall_config": False,
                "openvpn_conflict": False,
                "message": ""
            }

            print(f"\n{'='*80}")
            print(f"开始测试跨页面端口冲突检测（OpenVPN vs 防火墙FTP）")
            print(f"{'='*80}")
            print(f"测试端口: {test_port}\n")

            # ===== 步骤1-4: 在防火墙Security页面配置FTP端口 =====
            print("\n=== 阶段1: 配置防火墙FTP端口 ===")
            print(f"步骤1: 跳转到防火墙Security页面...")
            self.navigate_to_page(
                "#network/firewall/security",
                sub_tab_selector="network/firewall/security"
            )
            time.sleep(3)
            self.driver.refresh()
            time.sleep(3)
            print("  ✅ 页面已加载")

            print(f"\n步骤2: 配置FTP端口为 {test_port}...")
            try:
                # 定位FTP端口输入框
                ftp_port_field = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_ftp_port"]'))
                )

                # 清空并输入端口号
                ftp_port_field.clear()
                ftp_port_field.send_keys(str(test_port))
                print(f"  ✅ 已输入FTP端口: {test_port}")

            except Exception as e:
                result["message"] = f"配置FTP端口失败: {e}"
                print(f"  ❌ {result['message']}")
                return result

            print(f"\n步骤3: 启用FTP功能...")
            try:
                # 定位FTP启用复选框（正确的ID是1_ftp_local）
                ftp_enable_checkbox = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_ftp_local"]'))
                )

                # 检查是否已启用
                is_enabled = (ftp_enable_checkbox.get_attribute("checked") or
                             ftp_enable_checkbox.is_selected())

                if not is_enabled:
                    ftp_enable_checkbox.click()
                    time.sleep(1)
                    print("  ✅ 已启用FTP功能")
                else:
                    print("  ℹ️  FTP功能已启用，跳过")

            except Exception as e:
                result["message"] = f"启用FTP功能失败: {e}"
                print(f"  ❌ {result['message']}")
                return result

            print(f"\n步骤4: 保存并应用配置...")
            try:
                # 点击保存按钮
                save_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
                )
                save_button.click()
                print("  ✅ 已点击保存按钮")
                time.sleep(2)

                # 检查是否有弹窗（防火墙配置可能会有确认弹窗）
                try:
                    ok_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                    )
                    ok_button.click()
                    print("  ✅ 已关闭确认弹窗")
                    time.sleep(2)
                except TimeoutException:
                    print("  ℹ️  无确认弹窗，继续")

                # 点击应用按钮
                try:
                    apply_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="apply"]'))
                    )
                    apply_button.click()
                    print("  ✅ 已点击应用按钮")
                    time.sleep(3)  # 等待配置应用

                    # 等待应用完成的确认弹窗
                    try:
                        confirm_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                        )
                        confirm_button.click()
                        print("  ✅ 已关闭应用完成弹窗")
                        time.sleep(2)
                    except TimeoutException:
                        print("  ℹ️  无应用完成弹窗")

                except Exception as e:
                    print(f"  ⚠️  点击应用按钮失败: {e}")
                    print("  ℹ️  继续执行测试...")

                result["firewall_config"] = True
                print(f"\n✅ 防火墙FTP端口配置完成: {test_port}")

            except Exception as e:
                result["message"] = f"保存防火墙配置失败: {e}"
                print(f"  ❌ {result['message']}")
                return result

            # ===== 步骤5-7: 在OpenVPN页面测试端口冲突 =====
            print(f"\n{'='*80}")
            print("=== 阶段2: 测试OpenVPN端口冲突检测 ===")
            print(f"{'='*80}")

            print(f"\n步骤5: 跳转到OpenVPN服务器页面...")
            self.navigate_to_page("#network/vpn/server")
            time.sleep(3)
            self.driver.refresh()
            time.sleep(3)
            print("  ✅ 页面已加载")

            print(f"\n步骤6: 启用OpenVPN服务器...")
            try:
                # 启用OpenVPN服务器
                enable_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]'))
                )

                is_enabled = (enable_btn.get_attribute("checked") or
                             enable_btn.is_selected())

                if not is_enabled:
                    enable_btn.click()
                    time.sleep(1)
                    print("  ✅ 已启用OpenVPN服务器")
                else:
                    print("  ℹ️  OpenVPN服务器已启用，跳过")

            except Exception as e:
                result["message"] = f"启用OpenVPN服务器失败: {e}"
                print(f"  ❌ {result['message']}")
                return result

            print(f"\n步骤7: 配置OpenVPN端口为 {test_port} 并检测冲突...")
            try:
                # 定位端口输入框
                port_field = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_port"]'))
                )
                save_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
                )

                # 清空并输入端口号
                port_field.clear()
                port_field.send_keys(str(test_port))
                print(f"  ✅ 已输入OpenVPN端口: {test_port}")

                # 点击保存
                save_button.click()
                print(f"  ✅ 已点击保存按钮")
                time.sleep(2)  # 等待端口冲突检测

                # 检查是否弹出端口冲突提醒
                has_conflict_popup = False
                try:
                    ok_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                    )
                    has_conflict_popup = True

                    # 尝试获取弹窗文本内容
                    try:
                        popup_text = self.driver.find_element(By.XPATH, '/html/body/div[13]/div/div[2]').text
                        print(f"\n  ✅ 检测到端口冲突弹窗！")
                        print(f"  📋 弹窗内容: {popup_text}")
                    except:
                        print(f"\n  ✅ 检测到端口冲突弹窗！")

                    # 点击OK关闭弹窗
                    ok_button.click()
                    print(f"  ✅ 已点击OK关闭弹窗")
                    time.sleep(2)

                    result["openvpn_conflict"] = True
                    result["success"] = True
                    result["message"] = f"✅ 测试通过！OpenVPN成功检测到与防火墙FTP端口 {test_port} 的冲突"

                except TimeoutException:
                    has_conflict_popup = False
                    result["openvpn_conflict"] = False
                    result["success"] = False
                    result["message"] = f"❌ 测试失败！OpenVPN未检测到与防火墙FTP端口 {test_port} 的冲突（应该有弹窗但没有）"
                    print(f"\n  ❌ 未检测到端口冲突弹窗（应该有弹窗）")

            except Exception as e:
                result["message"] = f"配置OpenVPN端口时出错: {e}"
                print(f"  ❌ {result['message']}")
                return result

            # 输出测试结果
            print(f"\n{'='*80}")
            print("测试结果总结:")
            print(f"{'='*80}")
            print(f"防火墙FTP配置: {'✅ 成功' if result['firewall_config'] else '❌ 失败'}")
            print(f"OpenVPN冲突检测: {'✅ 检测到冲突' if result['openvpn_conflict'] else '❌ 未检测到冲突'}")
            print(f"测试结果: {'✅ 通过' if result['success'] else '❌ 失败'}")
            print(f"\n{result['message']}")
            print(f"{'='*80}\n")

            return result

        except Exception as e:
            error_msg = f"测试过程中发生未知错误: {str(e)}"
            print(f"\n❌ {error_msg}")
            return {
                "success": False,
                "firewall_config": False,
                "openvpn_conflict": False,
                "message": error_msg
            }

    def _configure_firewall_ftp_port(self, test_port: int = 1111) -> bool:
        """
        通用方法：配置防火墙FTP端口并启用
        用于ID20-24的跨页面端口冲突测试

        Args:
            test_port: FTP端口号，默认1111

        Returns:
            bool: 配置是否成功
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            print(f"\n=== 配置防火墙FTP端口 ===")
            print(f"步骤1: 跳转到防火墙Security页面...")
            self.navigate_to_page(
                "#network/firewall/security",
                sub_tab_selector="network/firewall/security"
            )
            time.sleep(3)
            self.driver.refresh()
            time.sleep(3)
            print("  ✅ 页面已加载")

            print(f"\n步骤2: 配置FTP端口为 {test_port}...")
            ftp_port_field = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_ftp_port"]'))
            )
            ftp_port_field.clear()
            ftp_port_field.send_keys(str(test_port))
            print(f"  ✅ 已输入FTP端口: {test_port}")

            print(f"\n步骤3: 启用FTP功能...")
            ftp_enable_checkbox = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_ftp_local"]'))
            )
            is_enabled = (ftp_enable_checkbox.get_attribute("checked") or
                         ftp_enable_checkbox.is_selected())
            if not is_enabled:
                ftp_enable_checkbox.click()
                time.sleep(1)
                print("  ✅ 已启用FTP功能")
            else:
                print("  ℹ️  FTP功能已启用，跳过")

            print(f"\n步骤4: 保存并应用配置...")
            save_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
            )
            save_button.click()
            print("  ✅ 已点击保存按钮")
            time.sleep(2)

            # 检查保存后的弹窗
            try:
                ok_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                )
                ok_button.click()
                print("  ✅ 已关闭确认弹窗")
                time.sleep(2)
            except TimeoutException:
                print("  ℹ️  无确认弹窗，继续")

            # 点击应用按钮
            try:
                apply_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="apply"]'))
                )
                apply_button.click()
                print("  ✅ 已点击应用按钮")
                time.sleep(3)

                # 等待应用完成的确认弹窗
                try:
                    confirm_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                    )
                    confirm_button.click()
                    print("  ✅ 已关闭应用完成弹窗")
                    time.sleep(2)
                except TimeoutException:
                    print("  ℹ️  无应用完成弹窗")
            except Exception as e:
                print(f"  ⚠️  点击应用按钮失败: {e}")
                print("  ℹ️  继续执行测试...")

            print(f"\n✅ 防火墙FTP端口配置完成: {test_port}")
            return True

        except Exception as e:
            print(f"❌ 配置防火墙FTP端口失败: {e}")
            return False

    def test_cross_page_port_conflict_portmapping_firewall(self, test_port: int = 1111) -> dict:
        """测试端口映射与防火墙FTP端口的跨页面端口冲突检测 - ID20"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            result = {"success": False, "firewall_config": False, "conflict_detected": False, "message": ""}

            print(f"\n{'='*80}\nID20: 端口映射与防火墙跨页面端口冲突检测\n{'='*80}")

            if not self._configure_firewall_ftp_port(test_port):
                result["message"] = "防火墙FTP配置失败"
                return result
            result["firewall_config"] = True

            print(f"\n{'='*80}\n=== 测试端口映射端口冲突检测 ===\n{'='*80}")
            print(f"\n步骤5: 跳转到端口映射页面...")
            self.navigate_to_page("#network/firewall/portmapping")
            time.sleep(3)
            self.driver.refresh()
            time.sleep(3)

            print(f"\n步骤6: 点击添加按钮...")
            add_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="add"]')))
            add_button.click()
            time.sleep(2)

            print(f"\n步骤7: 填写端口映射信息...")
            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="0_src"]'))).send_keys("192.168.1.100/24")
            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="0_dstip"]'))).send_keys("10.10.10.10")
            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="0_dstport"]'))).send_keys("222")
            external_port_input = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="0_externalport"]')))
            external_port_input.clear()
            external_port_input.send_keys(str(test_port))
            print(f"  ✅ 已输入端口映射信息（外部端口={test_port}）")

            print(f"\n步骤8: 保存配置并检测冲突...")
            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))).click()
            time.sleep(2)

            try:
                ok_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                )
                result["conflict_detected"] = True
                result["success"] = True
                result["message"] = f"✅ 测试通过！端口映射成功检测到与防火墙FTP端口 {test_port} 的冲突"
                print(f"\n  ✅ 检测到端口冲突弹窗！")
                ok_button.click()
                time.sleep(2)
            except TimeoutException:
                result["message"] = f"❌ 测试失败！端口映射未检测到与防火墙FTP端口 {test_port} 的冲突"

            return result
        except Exception as e:
            return {"success": False, "firewall_config": False, "conflict_detected": False, "message": f"测试异常: {e}"}

    def test_cross_page_port_conflict_serial_firewall(self, test_port: int = 1111) -> dict:
        """测试串口1/2与防火墙FTP端口的跨页面端口冲突检测 - ID21"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            result = {"success": False, "firewall_config": False, "serial1_conflict": False, "serial2_conflict": False, "message": ""}

            print(f"\n{'='*80}\nID21: 串口1/2与防火墙跨页面端口冲突检测\n{'='*80}")

            if not self._configure_firewall_ftp_port(test_port):
                result["message"] = "防火墙FTP配置失败"
                return result
            result["firewall_config"] = True

            # 测试Serial1
            print(f"\n{'='*80}\n=== 测试Serial1端口冲突检测 ===\n{'='*80}")
            self.navigate_to_page("#industrial/serialport/serial1")
            time.sleep(3)
            self.driver.refresh()
            time.sleep(3)

            # 使用Select类正确选择模式，触发change事件
            from selenium.webdriver.support.ui import Select
            mode_select_element = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_mode"]')))
            mode_select = Select(mode_select_element)
            mode_select.select_by_value('server')
            time.sleep(2)  # 等待页面响应change事件

            port_field = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_local_port"]')))
            port_field.clear()
            port_field.send_keys(str(test_port))
            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))).click()
            time.sleep(2)

            try:
                WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                ).click()
                result["serial1_conflict"] = True
                print(f"  ✅ Serial1检测到端口冲突")
                time.sleep(2)
            except TimeoutException:
                print(f"  ❌ Serial1未检测到端口冲突")

            # 测试Serial2
            print(f"\n{'='*80}\n=== 测试Serial2端口冲突检测 ===\n{'='*80}")
            self.navigate_to_page("#industrial/serialport/serial2")
            time.sleep(3)
            self.driver.refresh()
            time.sleep(3)

            # 使用Select类正确选择模式，触发change事件
            mode_select_element = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_mode"]')))
            mode_select = Select(mode_select_element)
            mode_select.select_by_value('server')
            time.sleep(2)  # 等待页面响应change事件

            port_field = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_local_port"]')))
            port_field.clear()
            port_field.send_keys(str(test_port))
            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))).click()
            time.sleep(2)

            try:
                WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                ).click()
                result["serial2_conflict"] = True
                print(f"  ✅ Serial2检测到端口冲突")
                time.sleep(2)
            except TimeoutException:
                print(f"  ❌ Serial2未检测到端口冲突")

            if result["serial1_conflict"] and result["serial2_conflict"]:
                result["success"] = True
                result["message"] = f"✅ 测试通过！Serial1和Serial2都检测到与防火墙FTP端口 {test_port} 的冲突"
            else:
                result["message"] = f"❌ 测试失败！Serial1冲突={result['serial1_conflict']}, Serial2冲突={result['serial2_conflict']}"

            return result
        except Exception as e:
            return {"success": False, "firewall_config": False, "serial1_conflict": False, "serial2_conflict": False, "message": f"测试异常: {e}"}

    def test_cross_page_port_conflict_modbus_firewall(self, test_port: int = 1111) -> dict:
        """测试Modbus TCP与防火墙FTP端口的跨页面端口冲突检测 - ID22"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            result = {"success": False, "firewall_config": False, "conflict_detected": False, "message": ""}

            print(f"\n{'='*80}\nID22: Modbus TCP与防火墙跨页面端口冲突检测\n{'='*80}")

            if not self._configure_firewall_ftp_port(test_port):
                result["message"] = "防火墙FTP配置失败"
                return result
            result["firewall_config"] = True

            print(f"\n{'='*80}\n=== 测试Modbus TCP端口冲突检测 ===\n{'='*80}")
            self.navigate_to_page("#industrial/modbus/modbustcp")
            time.sleep(3)
            self.driver.refresh()
            time.sleep(3)

            # 步骤1: 启用Modbus TCP
            print("步骤1: 启用Modbus TCP功能...")
            enable_checkbox = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]')))
            if not (enable_checkbox.get_attribute("checked") or enable_checkbox.is_selected()):
                enable_checkbox.click()
                print("  ✅ 已启用Modbus TCP")
                time.sleep(2)  # 等待端口字段加载
            else:
                print("  ℹ️  Modbus TCP已经启用")

            # 步骤2: 修改端口为测试端口
            print(f"步骤2: 修改Modbus TCP端口为 {test_port}...")
            port_field = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_local_port"]')))

            # 获取当前端口值
            current_port = port_field.get_attribute("value")
            print(f"  当前端口值: {current_port}")

            # 清空并输入新端口
            port_field.clear()
            time.sleep(0.5)
            port_field.send_keys(str(test_port))
            time.sleep(0.5)

            # 验证端口是否成功修改
            new_port = port_field.get_attribute("value")
            print(f"  修改后端口值: {new_port}")

            if new_port != str(test_port):
                result["message"] = f"❌ 端口修改失败！期望: {test_port}, 实际: {new_port}"
                return result

            print(f"  ✅ 端口已修改为 {test_port}")

            # 步骤3: 保存配置
            print("步骤3: 保存配置并检测端口冲突...")
            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))).click()
            time.sleep(2)

            # 步骤4: 检测端口冲突弹窗
            try:
                print("  等待端口冲突提示弹窗...")
                conflict_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                )
                print(f"  ✅ 检测到端口冲突弹窗！")
                conflict_button.click()
                time.sleep(1)

                result["conflict_detected"] = True
                result["success"] = True
                result["message"] = f"✅ 测试通过！Modbus TCP成功检测到与防火墙FTP端口 {test_port} 的冲突"
                print(f"\n{'='*80}")
                print(f"✅ ID22测试通过！")
                print(f"{'='*80}\n")
            except TimeoutException:
                print(f"  ❌ 未检测到端口冲突弹窗")
                result["message"] = f"❌ 测试失败！Modbus TCP配置端口 {test_port} 时未检测到与防火墙FTP的端口冲突"
                print(f"\n{'='*80}")
                print(f"❌ ID22测试失败！")
                print(f"{'='*80}\n")

            return result
        except Exception as e:
            return {"success": False, "firewall_config": False, "conflict_detected": False, "message": f"测试异常: {e}"}

    def test_cross_page_port_conflict_snmp_firewall(self, test_port: int = 1111) -> dict:
        """测试SNMP与防火墙FTP端口的跨页面端口冲突检测 - ID23"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            result = {"success": False, "firewall_config": False, "conflict_detected": False, "message": ""}

            print(f"\n{'='*80}\nID23: SNMP与防火墙跨页面端口冲突检测\n{'='*80}")

            if not self._configure_firewall_ftp_port(test_port):
                result["message"] = "防火墙FTP配置失败"
                return result
            result["firewall_config"] = True

            print(f"\n{'='*80}\n=== 测试SNMP端口冲突检测 ===\n{'='*80}")
            self.navigate_to_page("#management/snmp")
            time.sleep(3)
            self.driver.refresh()
            time.sleep(3)

            enable_checkbox = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]')))
            if not (enable_checkbox.get_attribute("checked") or enable_checkbox.is_selected()):
                enable_checkbox.click()
                time.sleep(1)

            port_field = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_port"]')))
            port_field.clear()
            port_field.send_keys(str(test_port))
            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))).click()
            time.sleep(2)

            try:
                WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                ).click()
                result["conflict_detected"] = True
                result["success"] = True
                result["message"] = f"✅ 测试通过！SNMP成功检测到与防火墙FTP端口 {test_port} 的冲突"
                print(f"  ✅ 检测到端口冲突")
                time.sleep(2)
            except TimeoutException:
                result["message"] = f"❌ 测试失败！SNMP未检测到端口冲突"

            return result
        except Exception as e:
            return {"success": False, "firewall_config": False, "conflict_detected": False, "message": f"测试异常: {e}"}

    def test_cross_page_port_conflict_gps_firewall(self, test_port: int = 1111) -> dict:
        """测试GPS与防火墙FTP端口的跨页面端口冲突检测 - ID24"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            result = {"success": False, "firewall_config": False, "conflict_detected": False, "message": ""}

            print(f"\n{'='*80}\nID24: GPS与防火墙跨页面端口冲突检测\n{'='*80}")

            # === 步骤1: 配置防火墙FTP端口 ===
            print(f"\n步骤1: 配置防火墙FTP端口为 {test_port}...")
            if not self._configure_firewall_ftp_port(test_port):
                result["message"] = "防火墙FTP配置失败"
                return result
            result["firewall_config"] = True
            print("  ✅ 防火墙FTP端口配置成功")

            print(f"\n{'='*80}\n=== 测试GPS端口冲突检测 ===\n{'='*80}")

            # === 步骤2: 启用GPS功能 ===
            print("\n步骤2: 启用GPS功能...")
            self.navigate_to_page("#industrial/gps/gps")
            print("  等待页面加载... (5秒)")
            time.sleep(5)

            print("  查找GPS启用按钮...")
            try:
                enable_checkbox = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]'))
                )
                print("  ✅ 找到GPS启用按钮")

                is_enabled = enable_checkbox.get_attribute("checked") or enable_checkbox.is_selected()
                if not is_enabled:
                    print("  点击启用GPS...")
                    enable_checkbox.click()
                    time.sleep(1)
                    print("  保存GPS配置...")
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
                    ).click()
                    time.sleep(3)
                    print("  ✅ GPS已启用")
                else:
                    print("  ℹ️  GPS已启用，跳过")
            except Exception as e:
                result["message"] = f"启用GPS失败: {e}"
                print(f"  ❌ {result['message']}")
                return result

            # === 步骤3: 跳转到IP Forwarding页面 ===
            print("\n步骤3: 跳转到GPS IP Forwarding页面...")
            self.navigate_to_page("#industrial/gps/ipforwarding")
            print("  等待页面加载... (3秒)")
            time.sleep(3)
            self.driver.refresh()
            time.sleep(3)

            # === 步骤4: 启用IP Forwarding ===
            print("\n步骤4: 启用IP Forwarding...")
            try:
                enable_checkbox = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]'))
                )
                print("  ✅ 找到IP Forwarding启用按钮")

                is_enabled = enable_checkbox.get_attribute("checked") or enable_checkbox.is_selected()
                if not is_enabled:
                    print("  点击启用IP Forwarding...")
                    enable_checkbox.click()
                    time.sleep(1)
                else:
                    print("  ℹ️  IP Forwarding已启用")
            except Exception as e:
                result["message"] = f"启用IP Forwarding失败: {e}"
                print(f"  ❌ {result['message']}")
                return result

            # === 步骤5: 设置类型为server ===
            print("\n步骤5: 设置类型为server...")
            try:
                from selenium.webdriver.support.ui import Select

                type_select_element = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_type"]'))
                )
                print("  ✅ 找到类型下拉框")

                # 使用Select类来正确选择选项，这会触发change事件
                type_select = Select(type_select_element)
                type_select.select_by_value('server')
                print("  ✅ 已选择server（触发了change事件）")

                # 等待页面响应change事件，端口输入框应该会显示出来
                time.sleep(2)
                print("  等待端口输入框显示...")
            except Exception as e:
                result["message"] = f"设置类型失败: {e}"
                print(f"  ❌ {result['message']}")
                return result

            # === 步骤6: 输入端口并保存 ===
            print(f"\n步骤6: 输入端口 {test_port} 并保存...")
            try:
                port_field = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="1_local_port"]'))
                )
                print("  ✅ 找到端口输入框")
                port_field.clear()
                time.sleep(0.5)
                port_field.send_keys(str(test_port))
                print(f"  ✅ 已输入端口: {test_port}")

                print("  点击保存按钮...")
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
                ).click()
                print("  ✅ 已点击保存")
                time.sleep(2)
            except Exception as e:
                result["message"] = f"输入端口或保存失败: {e}"
                print(f"  ❌ {result['message']}")
                return result

            # === 步骤7: 检测冲突弹窗 ===
            print("\n步骤7: 检测端口冲突弹窗...")
            print("  等待冲突弹窗出现... (最多5秒)")
            try:
                conflict_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                )
                print("  ✅ 检测到端口冲突弹窗！")
                conflict_button.click()
                print("  ✅ 已关闭弹窗")
                time.sleep(1)

                result["conflict_detected"] = True
                result["success"] = True
                result["message"] = f"✅ 测试通过！GPS成功检测到与防火墙FTP端口 {test_port} 的冲突"
            except TimeoutException:
                print("  ❌ 未检测到端口冲突弹窗")
                result["message"] = f"❌ 测试失败！GPS未检测到与防火墙FTP端口 {test_port} 的冲突\n" \
                                  f"   可能原因：路由器固件未实现跨页面端口冲突检测功能"

            return result
        except Exception as e:
            error_msg = f"测试异常: {type(e).__name__}: {str(e)}"
            print(f"\n❌ {error_msg}")
            return {"success": False, "firewall_config": False, "conflict_detected": False, "message": error_msg}

    # ========================================
    # 配置备份和恢复方法
    # ========================================

    def backup_firewall_security_config(self) -> dict:
        """
        备份防火墙Security页面配置

        ⚠️ 注意：只备份FTP端口，HTTP和HTTPS端口不备份不恢复
        原因：如果修改HTTP/HTTPS端口，会导致无法通过Web界面访问路由器进行恢复

        Returns:
            dict: 只包含FTP端口配置的字典
                {
                    'ftp_port': '21',
                    'ftp_enabled': False
                }
        """
        try:
            print("\n=== 备份防火墙Security配置（仅FTP端口）===")

            # 跳转到防火墙Security页面
            self.navigate_to_page("#network/firewall/security")
            time.sleep(3)

            # 刷新页面确保获取最新状态
            self.driver.refresh()
            time.sleep(3)

            config = {}

            # 只读取FTP配置（跨页面测试只会用到FTP端口）
            ftp_port = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="1_ftp_port"]')))
            config['ftp_port'] = ftp_port.get_attribute('value')
            ftp_enable = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="1_ftp_enable"]')))
            config['ftp_enabled'] = ftp_enable.is_selected() or ftp_enable.get_attribute('checked') is not None

            print(f"✅ 防火墙Security配置备份成功:")
            print(f"   FTP: {config['ftp_port']} (启用: {config['ftp_enabled']})")
            print(f"   ⚠️  注意：HTTP和HTTPS端口不备份（防止Web访问失效）")

            return config

        except Exception as e:
            print(f"❌ 备份防火墙Security配置失败: {e}")
            return None

    def restore_firewall_security_config(self, config: dict) -> bool:
        """
        恢复防火墙Security页面配置

        ⚠️ 注意：只恢复FTP端口，HTTP和HTTPS端口不恢复
        原因：如果修改HTTP/HTTPS端口，会导致无法通过Web界面访问路由器

        Args:
            config: 配置字典（由backup_firewall_security_config返回）

        Returns:
            bool: 恢复是否成功
        """
        try:
            if not config:
                print("⚠️  配置为空，跳过恢复")
                return False

            print("\n=== 恢复防火墙Security配置（仅FTP端口）===")

            # 跳转到防火墙Security页面
            self.navigate_to_page("#network/firewall/security")
            time.sleep(3)

            # 刷新页面
            self.driver.refresh()
            time.sleep(3)

            # 只恢复FTP配置
            if 'ftp_port' in config:
                ftp_port = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_ftp_port"]')))
                ftp_port.clear()
                ftp_port.send_keys(config['ftp_port'])

                ftp_enable = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_ftp_enable"]')))
                current_ftp_enabled = ftp_enable.is_selected() or ftp_enable.get_attribute('checked') is not None
                if current_ftp_enabled != config['ftp_enabled']:
                    ftp_enable.click()

                print(f"✅ 配置已恢复，准备保存...")
                print(f"   FTP: {config['ftp_port']} (启用: {config['ftp_enabled']})")
                print(f"   ⚠️  注意：HTTP和HTTPS端口不恢复（防止Web访问失效）")

                # 保存配置
                if not self._click_save_button():
                    print("❌ 保存配置失败")
                    return False

                # 应用配置
                if not self._click_apply_button():
                    print("⚠️  应用配置失败或不需要应用")

                print(f"✅ 防火墙Security配置恢复成功")
                return True
            else:
                print("⚠️  配置中没有FTP端口信息")
                return False

        except Exception as e:
            print(f"❌ 恢复防火墙Security配置失败: {e}")
            return False

    def ensure_ssh_enabled(self) -> bool:
        """
        确保SSH功能已启用

        新版本路由器固件默认关闭SSH，需要通过Web界面主动开启。
        此方法会检查SSH是否启用，如果未启用则自动启用并保存。

        Returns:
            bool: SSH启用成功返回True，失败返回False
        """
        try:
            print("\n=== 检查SSH启用状态 ===")

            # 检查driver是否可用
            if self.driver is None:
                print("⚠️  浏览器未初始化，尝试重新登录...")
                if not self.login_web():
                    print("❌ 重新登录失败")
                    return False
                print("✅ 重新登录成功")

            # 跳转到防火墙Security页面
            print("跳转到防火墙Security页面...")
            self.navigate_to_page("#network/firewall/security")
            time.sleep(2)

            # 刷新页面确保获取最新状态
            print("刷新页面...")
            self.driver.refresh()
            time.sleep(3)

            # 检查SSH是否启用
            ssh_checkbox_xpath = '//*[@id="1_ssh_local"]'
            ssh_checkbox = self.wait.until(
                EC.presence_of_element_located((By.XPATH, ssh_checkbox_xpath))
            )

            # 检查当前状态
            is_enabled = ssh_checkbox.is_selected() or ssh_checkbox.get_attribute('checked') is not None

            if is_enabled:
                print("✅ SSH已启用，无需操作")
                return True
            else:
                print("⚠️  SSH未启用，正在启用...")

                # 勾选SSH启用
                self.driver.execute_script("arguments[0].scrollIntoView(true);", ssh_checkbox)
                time.sleep(0.5)
                ssh_checkbox.click()
                time.sleep(1)

                print("保存配置...")
                # 点击保存按钮
                if not self._click_save_button():
                    print("❌ 保存SSH配置失败")
                    return False

                print("应用配置...")
                # 点击应用按钮
                if not self._click_apply_button():
                    print("⚠️  应用SSH配置失败或不需要应用")

                # 再次验证SSH是否已启用
                time.sleep(2)
                self.driver.refresh()
                time.sleep(3)

                ssh_checkbox = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, ssh_checkbox_xpath))
                )
                is_enabled = ssh_checkbox.is_selected() or ssh_checkbox.get_attribute('checked') is not None

                if is_enabled:
                    print("✅ SSH已成功启用")
                    return True
                else:
                    print("❌ SSH启用失败")
                    return False

        except Exception as e:
            print(f"❌ 检查/启用SSH失败: {e}")
            import traceback
            print(traceback.format_exc())
            return False

    def backup_serial_config(self, serial_num: int) -> dict:
        """
        备份Serial配置

        Args:
            serial_num: Serial编号 (1 or 2)

        Returns:
            dict: Serial配置字典
        """
        try:
            print(f"\n=== 备份Serial{serial_num}配置 ===")

            # 跳转到Serial配置页面
            page_path = f"#industrial/serialport/serial{serial_num}"
            self.navigate_to_page(page_path)
            time.sleep(3)

            config = {'serial_num': serial_num}

            # 读取启用状态
            enable_checkbox = self.driver.find_element(By.XPATH, f'//*[@id="{serial_num}_enable"]')
            config['enabled'] = enable_checkbox.is_selected() or enable_checkbox.get_attribute('checked') is not None
            print(f"  启用状态: {config['enabled']}")

            # 如果启用，读取其他配置
            if config['enabled']:
                # 读取工作模式
                mode_select = self.driver.find_element(By.XPATH, f'//*[@id="{serial_num}_mode"]')
                config['mode'] = mode_select.get_attribute('value')
                print(f"  工作模式: {config['mode']}")

                # 读取协议
                protocol_select = self.driver.find_element(By.XPATH, f'//*[@id="{serial_num}_protocol"]')
                config['protocol'] = protocol_select.get_attribute('value')
                print(f"  协议: {config['protocol']}")

                # 读取端口（根据协议不同，端口字段可能不同）
                try:
                    port_field_1 = self.driver.find_element(By.XPATH, f'//*[@id="{serial_num}_local_port_1"]')
                    config['local_port_1'] = port_field_1.get_attribute('value')
                    print(f"  本地端口1: {config['local_port_1']}")
                except:
                    config['local_port_1'] = None

                try:
                    port_field_2 = self.driver.find_element(By.XPATH, f'//*[@id="{serial_num}_local_port_2"]')
                    config['local_port_2'] = port_field_2.get_attribute('value')
                    print(f"  本地端口2: {config['local_port_2']}")
                except:
                    config['local_port_2'] = None

            print(f"✅ Serial{serial_num}配置备份成功")
            return config

        except Exception as e:
            print(f"❌ 备份Serial{serial_num}配置失败: {e}")
            return None

    def restore_serial_config(self, serial_num: int, config: dict) -> bool:
        """
        恢复Serial配置

        Args:
            serial_num: Serial编号 (1 or 2)
            config: 配置字典

        Returns:
            bool: 恢复是否成功
        """
        try:
            if not config:
                print("⚠️  配置为空，跳过恢复")
                return False

            print(f"\n=== 恢复Serial{serial_num}配置 ===")

            # 跳转到Serial配置页面
            page_path = f"#industrial/serialport/serial{serial_num}"
            self.navigate_to_page(page_path)
            time.sleep(3)

            # 恢复启用状态
            enable_checkbox = self.wait.until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="{serial_num}_enable"]')))
            current_enabled = enable_checkbox.is_selected() or enable_checkbox.get_attribute('checked') is not None
            if current_enabled != config['enabled']:
                enable_checkbox.click()
                time.sleep(1)

            # 如果需要启用，恢复其他配置
            if config['enabled']:
                # 恢复工作模式
                if 'mode' in config and config['mode']:
                    mode_select = self.driver.find_element(By.XPATH, f'//*[@id="{serial_num}_mode"]')
                    Select(mode_select).select_by_value(config['mode'])
                    time.sleep(1)

                # 恢复协议
                if 'protocol' in config and config['protocol']:
                    protocol_select = self.driver.find_element(By.XPATH, f'//*[@id="{serial_num}_protocol"]')
                    Select(protocol_select).select_by_value(config['protocol'])
                    time.sleep(1)

                # 恢复端口
                if 'local_port_1' in config and config['local_port_1']:
                    try:
                        port_field = self.driver.find_element(By.XPATH, f'//*[@id="{serial_num}_local_port_1"]')
                        port_field.clear()
                        port_field.send_keys(config['local_port_1'])
                    except:
                        pass

                if 'local_port_2' in config and config['local_port_2']:
                    try:
                        port_field = self.driver.find_element(By.XPATH, f'//*[@id="{serial_num}_local_port_2"]')
                        port_field.clear()
                        port_field.send_keys(config['local_port_2'])
                    except:
                        pass

            print(f"✅ 配置已恢复，准备保存...")

            # 保存并应用配置
            if not self._click_save_button():
                print("❌ 保存配置失败")
                return False

            if not self._click_apply_button():
                print("⚠️  应用配置失败或不需要应用")

            print(f"✅ Serial{serial_num}配置恢复成功")
            return True

        except Exception as e:
            print(f"❌ 恢复Serial{serial_num}配置失败: {e}")
            return False

    def backup_openvpn_config(self) -> dict:
        """
        备份OpenVPN服务器配置

        Returns:
            dict: OpenVPN配置字典
        """
        try:
            print("\n=== 备份OpenVPN配置 ===")

            # 跳转到OpenVPN服务器页面
            self.navigate_to_page("#vpn/openvpn/server")
            time.sleep(3)

            config = {}

            # 读取启用状态
            enable_checkbox = self.driver.find_element(By.XPATH, '//*[@id="1_enable"]')
            config['enabled'] = enable_checkbox.is_selected() or enable_checkbox.get_attribute('checked') is not None
            print(f"  启用状态: {config['enabled']}")

            if config['enabled']:
                # 读取端口
                port_field = self.driver.find_element(By.XPATH, '//*[@id="1_port"]')
                config['port'] = port_field.get_attribute('value')
                print(f"  端口: {config['port']}")

            print("✅ OpenVPN配置备份成功")
            return config

        except Exception as e:
            print(f"❌ 备份OpenVPN配置失败: {e}")
            return None

    def restore_openvpn_config(self, config: dict) -> bool:
        """
        恢复OpenVPN服务器配置

        Args:
            config: 配置字典

        Returns:
            bool: 恢复是否成功
        """
        try:
            if not config:
                print("⚠️  配置为空，跳过恢复")
                return False

            print("\n=== 恢复OpenVPN配置 ===")

            # 跳转到OpenVPN服务器页面
            self.navigate_to_page("#vpn/openvpn/server")
            time.sleep(3)

            # 恢复启用状态
            enable_checkbox = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]')))
            current_enabled = enable_checkbox.is_selected() or enable_checkbox.get_attribute('checked') is not None
            if current_enabled != config['enabled']:
                enable_checkbox.click()
                time.sleep(1)

            # 如果需要启用，恢复端口配置
            if config['enabled'] and 'port' in config:
                port_field = self.driver.find_element(By.XPATH, '//*[@id="1_port"]')
                port_field.clear()
                port_field.send_keys(config['port'])

            print("✅ 配置已恢复，准备保存...")

            # 保存并应用配置
            if not self._click_save_button():
                print("❌ 保存配置失败")
                return False

            if not self._click_apply_button():
                print("⚠️  应用配置失败或不需要应用")

            print("✅ OpenVPN配置恢复成功")
            return True

        except Exception as e:
            print(f"❌ 恢复OpenVPN配置失败: {e}")
            return False

    def backup_gps_config(self) -> dict:
        """
        备份GPS IP Forwarding配置

        Returns:
            dict: GPS配置字典
        """
        try:
            print("\n=== 备份GPS配置 ===")

            config = {}

            # 备份GPS主功能启用状态
            self.navigate_to_page("#industrial/gps/gps")
            time.sleep(3)
            gps_enable = self.driver.find_element(By.XPATH, '//*[@id="1_enable"]')
            config['gps_enabled'] = gps_enable.is_selected() or gps_enable.get_attribute('checked') is not None
            print(f"  GPS启用状态: {config['gps_enabled']}")

            # 备份IP Forwarding配置
            self.navigate_to_page("#industrial/gps/ipforwarding")
            time.sleep(3)
            ipfwd_enable = self.driver.find_element(By.XPATH, '//*[@id="1_enable"]')
            config['ipfwd_enabled'] = ipfwd_enable.is_selected() or ipfwd_enable.get_attribute('checked') is not None
            print(f"  IP Forwarding启用状态: {config['ipfwd_enabled']}")

            if config['ipfwd_enabled']:
                # 读取类型
                type_select = self.driver.find_element(By.XPATH, '//*[@id="1_type"]')
                config['type'] = type_select.get_attribute('value')
                print(f"  类型: {config['type']}")

                # 读取本地端口
                try:
                    port_field = self.driver.find_element(By.XPATH, '//*[@id="1_local_port"]')
                    config['local_port'] = port_field.get_attribute('value')
                    print(f"  本地端口: {config['local_port']}")
                except:
                    config['local_port'] = None

            print("✅ GPS配置备份成功")
            return config

        except Exception as e:
            print(f"❌ 备份GPS配置失败: {e}")
            return None

    def restore_gps_config(self, config: dict) -> bool:
        """
        恢复GPS IP Forwarding配置

        Args:
            config: 配置字典

        Returns:
            bool: 恢复是否成功
        """
        try:
            if not config:
                print("⚠️  配置为空，跳过恢复")
                return False

            print("\n=== 恢复GPS配置 ===")

            # 恢复GPS主功能
            self.navigate_to_page("#industrial/gps/gps")
            time.sleep(3)
            gps_enable = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]')))
            current_gps_enabled = gps_enable.is_selected() or gps_enable.get_attribute('checked') is not None
            if current_gps_enabled != config['gps_enabled']:
                gps_enable.click()
                time.sleep(1)
                self._click_save_button()
                time.sleep(2)

            # 恢复IP Forwarding配置
            self.navigate_to_page("#industrial/gps/ipforwarding")
            time.sleep(3)
            ipfwd_enable = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]')))
            current_ipfwd_enabled = ipfwd_enable.is_selected() or ipfwd_enable.get_attribute('checked') is not None
            if current_ipfwd_enabled != config['ipfwd_enabled']:
                ipfwd_enable.click()
                time.sleep(1)

            if config['ipfwd_enabled']:
                # 恢复类型
                if 'type' in config:
                    type_select = self.driver.find_element(By.XPATH, '//*[@id="1_type"]')
                    self.driver.execute_script(f"arguments[0].value = '{config['type']}';", type_select)
                    time.sleep(1)

                # 恢复端口
                if 'local_port' in config and config['local_port']:
                    port_field = self.driver.find_element(By.XPATH, '//*[@id="1_local_port"]')
                    port_field.clear()
                    port_field.send_keys(config['local_port'])

            print("✅ 配置已恢复，准备保存...")

            # 保存并应用配置
            if not self._click_save_button():
                print("❌ 保存配置失败")
                return False

            if not self._click_apply_button():
                print("⚠️  应用配置失败或不需要应用")

            print("✅ GPS配置恢复成功")
            return True

        except Exception as e:
            print(f"❌ 恢复GPS配置失败: {e}")
            return False

    def backup_modbus_config(self) -> dict:
        """
        备份Modbus TCP配置

        Returns:
            dict: Modbus TCP配置字典
        """
        try:
            print("\n=== 备份Modbus TCP配置 ===")

            # 跳转到Modbus TCP页面
            self.navigate_to_page("#industrial/modbus/modbustcp")
            time.sleep(3)

            config = {}

            # 读取启用状态
            enable_checkbox = self.driver.find_element(By.XPATH, '//*[@id="1_enable"]')
            config['enabled'] = enable_checkbox.is_selected() or enable_checkbox.get_attribute('checked') is not None
            print(f"  启用状态: {config['enabled']}")

            if config['enabled']:
                # 读取本地端口
                port_field = self.driver.find_element(By.XPATH, '//*[@id="1_local_port"]')
                config['local_port'] = port_field.get_attribute('value')
                print(f"  本地端口: {config['local_port']}")

            print("✅ Modbus TCP配置备份成功")
            return config

        except Exception as e:
            print(f"❌ 备份Modbus TCP配置失败: {e}")
            return None

    def restore_modbus_config(self, config: dict) -> bool:
        """
        恢复Modbus TCP配置

        Args:
            config: 配置字典

        Returns:
            bool: 恢复是否成功
        """
        try:
            if not config:
                print("⚠️  配置为空，跳过恢复")
                return False

            print("\n=== 恢复Modbus TCP配置 ===")

            # 跳转到Modbus TCP页面
            self.navigate_to_page("#industrial/modbus/modbustcp")
            time.sleep(3)

            # 恢复启用状态
            enable_checkbox = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]')))
            current_enabled = enable_checkbox.is_selected() or enable_checkbox.get_attribute('checked') is not None
            if current_enabled != config['enabled']:
                enable_checkbox.click()
                time.sleep(1)

            # 如果需要启用，恢复端口配置
            if config['enabled'] and 'local_port' in config:
                port_field = self.driver.find_element(By.XPATH, '//*[@id="1_local_port"]')
                port_field.clear()
                port_field.send_keys(config['local_port'])

            print("✅ 配置已恢复，准备保存...")

            # 保存并应用配置
            if not self._click_save_button():
                print("❌ 保存配置失败")
                return False

            if not self._click_apply_button():
                print("⚠️  应用配置失败或不需要应用")

            print("✅ Modbus TCP配置恢复成功")
            return True

        except Exception as e:
            print(f"❌ 恢复Modbus TCP配置失败: {e}")
            return False

    def backup_snmp_config(self) -> dict:
        """
        备份SNMP配置

        Returns:
            dict: SNMP配置字典
        """
        try:
            print("\n=== 备份SNMP配置 ===")

            # 跳转到SNMP页面
            self.navigate_to_page("#industrial/snmp/snmp")
            time.sleep(3)

            config = {}

            # 读取启用状态
            enable_checkbox = self.driver.find_element(By.XPATH, '//*[@id="0_enable"]')
            config['enabled'] = enable_checkbox.is_selected() or enable_checkbox.get_attribute('checked') is not None
            print(f"  启用状态: {config['enabled']}")

            if config['enabled']:
                # 读取Location
                try:
                    location_field = self.driver.find_element(By.XPATH, '//*[@id="0_location"]')
                    config['location'] = location_field.get_attribute('value')
                    print(f"  Location: {config['location']}")
                except:
                    config['location'] = None

                # 读取Contact
                try:
                    contact_field = self.driver.find_element(By.XPATH, '//*[@id="0_contact"]')
                    config['contact'] = contact_field.get_attribute('value')
                    print(f"  Contact: {config['contact']}")
                except:
                    config['contact'] = None

                # 读取端口
                # 注意：SNMP端口字段使用 0_port (不是1_port)
                try:
                    port_field = self.driver.find_element(By.XPATH, '//*[@id="0_port"]')
                    config['port'] = port_field.get_attribute('value')
                    print(f"  端口: {config['port']}")
                except:
                    config['port'] = None

            print("✅ SNMP配置备份成功")
            return config

        except Exception as e:
            print(f"❌ 备份SNMP配置失败: {e}")
            return None

    def restore_snmp_config(self, config: dict) -> bool:
        """
        恢复SNMP配置

        Args:
            config: 配置字典

        Returns:
            bool: 恢复是否成功
        """
        try:
            if not config:
                print("⚠️  配置为空，跳过恢复")
                return False

            print("\n=== 恢复SNMP配置 ===")

            # 跳转到SNMP页面
            self.navigate_to_page("#industrial/snmp/snmp")
            time.sleep(3)

            # 恢复启用状态
            enable_checkbox = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="0_enable"]')))
            current_enabled = enable_checkbox.is_selected() or enable_checkbox.get_attribute('checked') is not None
            if current_enabled != config['enabled']:
                enable_checkbox.click()
                time.sleep(1)

            # 如果需要启用，恢复配置
            if config['enabled']:
                # 恢复Location
                if 'location' in config and config['location']:
                    location_field = self.driver.find_element(By.XPATH, '//*[@id="0_location"]')
                    location_field.clear()
                    location_field.send_keys(config['location'])

                # 恢复Contact
                if 'contact' in config and config['contact']:
                    contact_field = self.driver.find_element(By.XPATH, '//*[@id="0_contact"]')
                    contact_field.clear()
                    contact_field.send_keys(config['contact'])

                # 恢复端口
                # 注意：SNMP端口字段使用 0_port (不是1_port)
                if 'port' in config and config['port']:
                    port_field = self.driver.find_element(By.XPATH, '//*[@id="0_port"]')
                    port_field.clear()
                    port_field.send_keys(config['port'])

            print("✅ 配置已恢复，准备保存...")

            # 保存并应用配置
            if not self._click_save_button():
                print("❌ 保存配置失败")
                return False

            if not self._click_apply_button():
                print("⚠️  应用配置失败或不需要应用")

            print("✅ SNMP配置恢复成功")
            return True

        except Exception as e:
            print(f"❌ 恢复SNMP配置失败: {e}")
            return False

    def close(self):
        """关闭浏览器"""
        if self.driver:
            print("关闭浏览器...")
            self.driver.quit()
            self.driver = None


