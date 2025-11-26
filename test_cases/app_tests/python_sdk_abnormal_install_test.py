from test_cases.base_test import BaseTest
import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PythonSDKAbnormalInstallTest(BaseTest):
    """Python3.0 SDK异常安装测试

    测试项：功能用例/APP/python
    测试点：python3.0 SDK异常安装

    测试步骤：
    1. 登录设备web并跳转到#app/python/status
    2. 判断SDK是否已安装，如已安装则先卸载
    3. 上传非法SDK文件并尝试安装
    4. 验证显示错误提示

    预期：
    1. 显示错误提示 "非法文件" 或 "Illegal file"
    2. SDK状态元素保持为空（未安装状态）
    """

    # 添加分类信息属性
    category = "功能用例/APP/python"
    is_regression = True  # 标记为回归测试用例

    # 非法SDK文件路径
    ILLEGAL_SDK_FILE_PATH = r"E:\GIT\ROUTER_TEST\config\非法PythonSDK测试文件.ta.gz"

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "python3.0 SDK异常安装"

    @property
    def description(self):
        """测试描述"""
        return "验证上传非法SDK文件时系统能正确拒绝并提示错误信息"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 获取路由器配置
        self.router_ip = self.config.router_config.router_ip

    def setup(self):
        """测试前置条件"""
        print(f"\n{'='*70}")
        print(f"测试用例: {self.test_name}")
        print(f"测试分类: {self.category}")
        print(f"{'='*70}")
        print(f"路由器IP: {self.router_ip}")
        print(f"非法SDK文件: {self.ILLEGAL_SDK_FILE_PATH}")
        print(f"{'='*70}\n")

        # 检查非法SDK文件是否存在
        if not os.path.exists(self.ILLEGAL_SDK_FILE_PATH):
            raise FileNotFoundError(f"非法SDK测试文件不存在: {self.ILLEGAL_SDK_FILE_PATH}")
        print(f"✅ 非法SDK测试文件存在: {self.ILLEGAL_SDK_FILE_PATH}\n")

        # 登录Web界面
        print("登录路由器Web界面...")
        if not self.router_client.login_web():
            raise Exception("Web登录失败")
        print("✅ Web登录成功\n")

    def execute(self):
        """执行测试"""
        try:
            print(f"\n{'='*70}")
            print(f"开始执行Python SDK异常安装测试")
            print(f"{'='*70}\n")

            # 步骤1：跳转到Python SDK状态页面
            print("步骤1: 跳转到Python SDK状态页面...")
            self._navigate_to_python_status()
            print("✅ 成功跳转到Python SDK状态页面\n")

            # 步骤2: 检查并清理初始状态
            print("步骤2: 检查SDK状态...")
            self._ensure_sdk_uninstalled()
            print("✅ SDK状态检查完成\n")

            # 步骤3: 尝试安装非法SDK文件
            print("步骤3: 尝试安装非法SDK文件...")
            self._upload_illegal_sdk()
            print("✅ 非法文件上传完成\n")

            # 步骤4: 验证错误提示
            print("步骤4: 验证错误提示...")
            if not self._verify_error_message():
                raise AssertionError("未检测到预期的错误提示信息")
            print("✅ 错误提示验证通过\n")

            # 步骤5: 验证SDK仍未安装
            print("步骤5: 验证SDK仍未安装...")
            if not self._verify_sdk_not_installed():
                raise AssertionError("SDK状态异常，应保持未安装状态")
            print("✅ SDK状态正常（未安装）\n")

            print(f"\n{'='*70}")
            print("✅ Python SDK异常安装测试通过")
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

    def _upload_illegal_sdk(self):
        """上传非法SDK文件"""
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
                raise Exception("无法找到文件上传输入框")

            # 上传非法文件
            print(f"  上传非法SDK文件...")
            upload_input.send_keys(self.ILLEGAL_SDK_FILE_PATH)
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
                raise Exception("等待按钮enabled超时")

            # 使用JavaScript点击，避免元素被遮挡
            driver.execute_script("arguments[0].click();", install_btn)
            print("  ✅ 已点击安装按钮")
            time.sleep(2)  # 等待错误提示出现

        except Exception as e:
            raise Exception(f"上传非法SDK文件失败: {str(e)}")

    def _verify_error_message(self):
        """验证是否显示错误提示信息"""
        try:
            driver = self.router_client.driver

            # 等待错误提示出现
            time.sleep(2)

            # 查找错误提示元素
            print("  查找错误提示元素...")

            # 方法1: 查找包含 "ys-upload-error" class 的 span 元素
            try:
                error_span = driver.find_element(By.XPATH, "//span[@class='ys-upload-error']")
                error_text = error_span.text.strip()
                print(f"  找到错误提示元素（ys-upload-error）: {error_text}")

                if "非法文件" in error_text or "Illegal file" in error_text.lower():
                    print(f"  ✅ 错误提示正确: {error_text}")
                    return True
                else:
                    print(f"  ⚠️ 错误提示内容不匹配: {error_text}")
            except:
                print("  未找到 ys-upload-error 元素")

            # 方法2: 在页面源码中搜索错误提示文本
            page_source = driver.page_source
            if "非法文件" in page_source or "Illegal file" in page_source:
                print(f"  ✅ 页面中包含错误提示文本")
                return True

            # 方法3: 检查所有包含 "error" 的元素
            error_elements = driver.find_elements(By.XPATH,
                "//*[contains(@class, 'error') or contains(text(), '非法') or contains(text(), 'Illegal')]")

            if error_elements:
                for elem in error_elements:
                    elem_text = elem.text.strip()
                    if elem_text and ("非法" in elem_text or "Illegal" in elem_text.lower()):
                        print(f"  ✅ 找到错误提示: {elem_text}")
                        return True

            print("  ❌ 未找到预期的错误提示信息")
            return False

        except Exception as e:
            print(f"  ❌ 验证错误提示失败: {str(e)}")
            return False

    def _verify_sdk_not_installed(self):
        """验证SDK仍处于未安装状态"""
        try:
            driver = self.router_client.driver

            status_elem1_xpath = '//*[@id="status_python"]/div[2]/div[3]/div[2]'
            status_elem2_xpath = '//*[@id="status_python"]/div[2]/div[4]/div[2]'

            time.sleep(1)

            try:
                elem1 = driver.find_element(By.XPATH, status_elem1_xpath)
                elem2 = driver.find_element(By.XPATH, status_elem2_xpath)

                elem1_text = elem1.text.strip()
                elem2_text = elem2.text.strip()

                if not elem1_text and not elem2_text:
                    print("  ✅ SDK状态为空（未安装）")
                    return True
                else:
                    print(f"  ❌ SDK状态异常: elem1='{elem1_text}', elem2='{elem2_text}'")
                    return False

            except:
                # 元素不存在也认为是未安装状态
                print("  ✅ SDK状态元素不存在（未安装）")
                return True

        except Exception as e:
            print(f"  ❌ 验证SDK状态失败: {str(e)}")
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

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        # 确保SDK未安装（清理可能的异常状态）
        try:
            driver = self.router_client.driver
            # 刷新页面
            driver.refresh()
            time.sleep(2)
        except:
            pass

        print("测试清理完成")
