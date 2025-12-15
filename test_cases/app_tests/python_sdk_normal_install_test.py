from test_cases.base_test import BaseTest
import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PythonSDKNormalInstallTest(BaseTest):
    """Python3.0 SDK正常安装测试

    测试项：功能用例/APP/python
    测试点：python3.0 SDK正常安装

    测试步骤：
    1. 登录设备web并跳转到#app/python/status
    2. 判断SDK是否已安装，如已安装则先卸载
    3. 上传SDK文件并安装
    4. 验证安装成功

    预期：
    SDK正常安装成功，状态元素显示版本信息
    """

    # 添加分类信息属性
    category = "功能用例/APP/python"
    is_regression = True  # 标记为回归测试用例

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "python3.0 SDK正常安装"

    @property
    def description(self):
        """测试描述"""
        return "验证Python SDK可以正常安装，检查安装后状态正常显示"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 动态获取SDK文件路径
        self.SDK_FILE_PATH = self.get_sdk_file_path()

        # 获取路由器配置
        self.router_ip = self.config.router_config.router_ip

    def setup(self):
        """测试前置条件"""
        print(f"\n{'='*70}")
        print(f"测试用例: {self.test_name}")
        print(f"测试分类: {self.category}")
        print(f"{'='*70}")
        print(f"路由器IP: {self.router_ip}")
        print(f"SDK文件: {self.SDK_FILE_PATH}")
        print(f"{'='*70}\n")

        # 检查SDK文件是否存在
        if not os.path.exists(self.SDK_FILE_PATH):
            raise FileNotFoundError(f"SDK文件不存在: {self.SDK_FILE_PATH}")
        print(f"✅ SDK文件存在: {self.SDK_FILE_PATH}\n")

        # 登录Web界面
        print("登录路由器Web界面...")
        if not self.router_client.login_web():
            raise Exception("Web登录失败")
        print("✅ Web登录成功\n")

    def execute(self):
        """执行测试"""
        try:
            print(f"\n{'='*70}")
            print(f"开始执行Python SDK正常安装测试")
            print(f"{'='*70}\n")

            # 步骤1：跳转到Python SDK状态页面
            print("步骤1: 跳转到Python SDK状态页面...")
            self._navigate_to_python_status()
            print("✅ 成功跳转到Python SDK状态页面\n")

            # 步骤2: 检查并清理初始状态
            print("步骤2: 检查SDK状态...")
            self._ensure_sdk_uninstalled()
            print("✅ SDK状态检查完成\n")

            # 步骤3: 安装SDK
            print("步骤3: 开始安装SDK...")
            install_success = self._install_sdk()
            if not install_success:
                raise Exception("SDK安装失败")
            print("✅ SDK安装成功\n")

            # 验证安装结果
            print("验证安装结果...")
            if not self._verify_sdk_installed():
                raise AssertionError("SDK安装后验证失败，状态元素未正确显示")

            print(f"\n{'='*70}")
            print("✅ Python SDK正常安装测试通过")
            print(f"{'='*70}\n")

            return True

        except Exception as e:
            print(f"\n测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise

    def _navigate_to_python_status(self):
        """跳转到Python SDK状态页面"""
        try:
            driver = self.router_client.driver
            wait = WebDriverWait(driver, 15)

            # 直接访问带hash的URL
            url_with_hash = f"http://{self.router_ip}/#app/python/status"
            print(f"跳转到: {url_with_hash}")
            driver.get(url_with_hash)
            time.sleep(1)

            # 刷新页面以触发前端路由
            driver.refresh()
            time.sleep(2)

            # 等待并验证Python页面特征元素
            try:
                python_link = wait.until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//a[@data-target='app/python/status' and text()='Python']"
                    ))
                )
                print("✅ 页面跳转成功")

            except Exception as e:
                raise Exception(f"页面跳转失败: {str(e)}")

        except Exception as e:
            raise Exception(f"跳转到Python状态页面失败: {str(e)}")

    def _ensure_sdk_uninstalled(self):
        """确保SDK处于未安装状态"""
        try:
            driver = self.router_client.driver

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
                    success = self._uninstall_sdk()
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
        """安装SDK，返回是否成功"""
        try:
            driver = self.router_client.driver
            wait = WebDriverWait(driver, 10)

            # 等待页面稳定
            time.sleep(1)

            # 查找文件上传输入框
            print("  查找文件上传输入框...")
            upload_input = None

            locators = [
                ("ID: 0_sdkfile_url", By.XPATH, '//*[@id="0_sdkfile_url"]'),
                ("type=file", By.XPATH, '//input[@type="file"]'),
                ("name包含sdk", By.XPATH, '//input[contains(@name, "sdk") and @type="file"]'),
            ]

            for desc, by, xpath in locators:
                try:
                    elem = driver.find_element(by, xpath)
                    elem_type = elem.get_attribute('type')
                    if elem_type == 'file':
                        print(f"  ✅ 找到文件上传框: {desc}")
                        driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                        time.sleep(0.5)
                        upload_input = elem
                        break
                except:
                    continue

            if not upload_input:
                print("  ❌ 无法找到文件上传输入框")
                return False

            # 上传文件
            print(f"  上传SDK文件...")
            upload_input.send_keys(self.SDK_FILE_PATH)
            print("  ✅ 文件已选择，等待按钮enabled...")

            # 等待安装按钮变为enabled（不包含disable class）
            max_wait = 10
            elapsed = 0
            install_btn = None
            while elapsed < max_wait:
                try:
                    btn = driver.find_element(By.XPATH, '//*[@id="0_sdkfile_import"]')
                    btn_class = btn.get_attribute('class') or ''
                    if 'ys-upload-disable' not in btn_class:
                        install_btn = btn
                        print(f"  ✅ 按钮已enabled (等待{elapsed}秒)")
                        break
                except:
                    pass
                time.sleep(1)
                elapsed += 1

            if not install_btn:
                print("  ❌ 等待按钮enabled超时")
                return False

            # 使用JavaScript点击，避免元素被遮挡
            driver.execute_script("arguments[0].click();", install_btn)
            print("  ✅ 已点击安装按钮，等待安装完成...")

            # 等待安装完成
            status_elem1_xpath = '//*[@id="status_python"]/div[2]/div[3]/div[2]'
            status_elem2_xpath = '//*[@id="status_python"]/div[2]/div[4]/div[2]'

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
                        print(f"  ✅ SDK安装完成!")
                        print(f"     版本信息: {elem1_text}, {elem2_text}")
                        return True

                    if elapsed % 10 == 0 and elapsed > 0:
                        print(f"  ⏳ 安装中... ({elapsed}秒)")

                except:
                    pass

                time.sleep(1)
                elapsed += 1

            # 超时
            print("  ❌ 安装超时")
            return False

        except Exception as e:
            print(f"  ❌ 安装异常: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _uninstall_sdk(self):
        """卸载SDK，返回是否成功"""
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
                confirm_btns = driver.find_elements(By.XPATH,
                    "//button[contains(text(), '确定') or contains(text(), 'OK') or contains(text(), 'ok')]")
                if confirm_btns:
                    print("  检测到确认弹窗，点击确定...")
                    confirm_btns[0].click()
                    time.sleep(1)
            except:
                pass

            # 等待卸载完成
            print("  等待卸载完成（最多60秒）...")
            status_elem1_xpath = '//*[@id="status_python"]/div[2]/div[3]/div[2]'
            status_elem2_xpath = '//*[@id="status_python"]/div[2]/div[4]/div[2]'

            max_wait = 60
            elapsed = 0
            while elapsed < max_wait:
                try:
                    elem1 = driver.find_element(By.XPATH, status_elem1_xpath)
                    elem2 = driver.find_element(By.XPATH, status_elem2_xpath)

                    if not elem1.text.strip() and not elem2.text.strip():
                        print(f"  ✅ 卸载完成")
                        return True

                except:
                    # 元素不存在也认为是卸载成功
                    print(f"  ✅ 卸载完成")
                    return True

                time.sleep(1)
                elapsed += 1

            # 超时
            print("  ❌ 卸载超时")
            return False

        except Exception as e:
            print(f"  ❌ 卸载异常: {str(e)}")
            return False

    def _verify_sdk_installed(self):
        """验证SDK已正确安装"""
        try:
            driver = self.router_client.driver

            status_elem1_xpath = '//*[@id="status_python"]/div[2]/div[3]/div[2]'
            status_elem2_xpath = '//*[@id="status_python"]/div[2]/div[4]/div[2]'

            elem1 = driver.find_element(By.XPATH, status_elem1_xpath)
            elem2 = driver.find_element(By.XPATH, status_elem2_xpath)

            elem1_text = elem1.text.strip()
            elem2_text = elem2.text.strip()

            if elem1_text and elem2_text:
                print(f"✅ SDK安装验证通过")
                print(f"   版本信息: {elem1_text}, {elem2_text}")
                return True
            else:
                print("❌ SDK安装验证失败：状态元素为空")
                return False

        except Exception as e:
            print(f"❌ SDK安装验证失败: {str(e)}")
            return False

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        # 保留SDK安装状态不卸载，因为这是正常安装测试
        print("保留SDK安装状态（正常安装测试不卸载）")
        print("测试清理完成")
