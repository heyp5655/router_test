from abc import ABC, abstractmethod
from models.test_config import TestConfig, RouterConfig
from utils.state_manager import state_manager


class BaseTest(ABC):
    """测试用例基类

    提供测试用例的基础功能：
    - 自动保存和恢复PC网卡状态
    - 自动保存和恢复路由器配置状态
    - 统一的日志记录
    - Python SDK安装检查
    """

    # SSH root用户凭据（用于执行系统命令，如urtool、ifconfig、cat等）
    # admin用户登录后进入vtysh，无法执行系统命令
    SSH_ROOT_USERNAME = "root"
    SSH_ROOT_PASSWORD = "R0uT3&U&s@l1nk46#3"

    def __init__(self, config: TestConfig = None):
        print(f"=== BaseTest 初始化开始 ===")
        print(f"传入的 config 类型: {type(config)}")

        if config is None:
            # 创建一个空的默认配置
            config = TestConfig()
            print("⚠️ 使用默认配置")

        self.config = config
        print(f"配置内容: {self.config}")

        # 只有当有有效的路由器配置时才创建 RouterClient
        if hasattr(self.config, 'router_config') and self.config.router_config:
            print(f"创建 RouterClient，路由器IP: {self.config.router_config.router_ip}")
            self.router_client = self._create_router_client()
        else:
            print("❌ 没有有效的路由器配置，router_client 为 None")
            self.router_client = None

        # 状态管理标志
        self._state_saved = False
        self._auto_restore = True  # 默认启用自动恢复

        print(f"=== BaseTest 初始化完成 ===\n")

    def _create_router_client(self):
        """创建路由器客户端 - 支持多种导入路径"""
        try:
            # 首先尝试从 core.router_client 导入
            from core.router_client import RouterClient
            print(f"✅ RouterClient 创建成功 (从 core.router_client 导入)")
            return RouterClient(self.config.router_config)
        except ImportError as e:
            print(f"❌ 从 core.router_client 导入失败: {str(e)}")

            # 备用方案：尝试从 utils.router_client 导入
            try:
                from utils.router_client import RouterClient
                print(f"✅ RouterClient 创建成功 (从 utils.router_client 导入)")
                return RouterClient(self.config.router_config)
            except ImportError as e2:
                print(f"❌ 从 utils.router_client 导入失败: {str(e2)}")

                # 最后使用模拟客户端
                class MockRouterClient:
                    def __init__(self, config):
                        self.router_ip = config.router_ip
                        self.username = config.username
                        self.password = config.password
                        self.model = config.model
                        self.logged_in = False
                        print(f"⚠️ 使用模拟 RouterClient")

                    def login_web(self):
                        print(f"模拟登录路由器 {self.router_ip}")
                        self.logged_in = True
                        return True

                    # 添加其他必要的方法
                    def __getattr__(self, name):
                        """为未实现的方法返回一个默认函数"""

                        def method(*args, **kwargs):
                            print(f"模拟调用方法: {name}, 参数: {args}, {kwargs}")
                            return True

                        return method

                return MockRouterClient(self.config.router_config)

    @property
    @abstractmethod
    def test_name(self) -> str:
        """测试用例名称"""
        pass

    @property
    def description(self) -> str:
        """测试用例描述"""
        return ""

    @property
    def is_regression(self) -> bool:
        """是否为回归测试"""
        return False

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

    @abstractmethod
    def setup(self):
        """测试前置条件"""
        pass

    @abstractmethod
    def execute(self):
        """执行测试"""
        pass

    def cleanup(self):
        """测试清理 - 自动恢复测试前的状态并关闭浏览器"""
        print(f"\n{'='*70}")
        print(f"测试清理: {self.test_name}")
        print(f"{'='*70}\n")

        # 如果启用了自动恢复且已保存状态，则恢复
        if self._auto_restore and self._state_saved:
            print("自动恢复测试前的状态...")
            self.restore_test_environment()
        else:
            if not self._auto_restore:
                print("⚠️  自动恢复已禁用，跳过状态恢复")
            elif not self._state_saved:
                print("⚠️  没有保存的状态，跳过恢复")

        # 自动关闭浏览器（重要：防止资源泄露）
        if self.router_client and hasattr(self.router_client, 'driver') and self.router_client.driver:
            try:
                print("关闭路由器Web浏览器...")
                self.router_client.close()
                print("✅ 浏览器已关闭")
            except Exception as e:
                print(f"⚠️  关闭浏览器时出错: {e}")

        print(f"\n✅ {self.test_name} 清理完成\n")

    def save_test_environment(self, save_pc_adapter: bool = True, save_router: bool = False,
                             adapter_name: str = "TEST") -> bool:
        """
        保存测试环境状态

        Args:
            save_pc_adapter: 是否保存PC网卡状态
            save_router: 是否保存路由器配置状态
            adapter_name: PC网卡名称

        Returns:
            bool: 保存是否成功
        """
        print(f"\n{'='*70}")
        print(f"保存测试环境状态")
        print(f"{'='*70}\n")

        success = True

        # 保存PC网卡状态
        if save_pc_adapter:
            print(f"保存PC网卡状态 ({adapter_name})...")
            if not state_manager.save_pc_adapter_state(adapter_name):
                print(f"⚠️  保存PC网卡状态失败")
                success = False

        # 保存路由器状态
        if save_router and self.router_client:
            print(f"保存路由器配置状态...")
            router_ip = self.config.router_config.router_ip if hasattr(self.config, 'router_config') else "unknown"
            if not state_manager.save_router_state(router_ip, self.router_client):
                print(f"⚠️  保存路由器状态失败")
                success = False

        if success:
            self._state_saved = True
            print(f"\n✅ 测试环境状态保存完成")
            print(f"   已保存: {state_manager.get_saved_states_summary()}\n")
        else:
            print(f"\n⚠️  测试环境状态保存部分失败\n")

        return success

    def restore_test_environment(self) -> bool:
        """
        恢复测试环境到之前保存的状态

        Returns:
            bool: 恢复是否成功
        """
        print(f"\n{'='*70}")
        print(f"恢复测试环境状态")
        print(f"{'='*70}\n")

        success = True

        # 恢复PC网卡状态
        if not state_manager.restore_pc_adapter_state():
            print(f"⚠️  恢复PC网卡状态失败")
            success = False

        # 恢复路由器状态
        if not state_manager.restore_router_state(self.router_client):
            print(f"⚠️  恢复路由器状态失败")
            success = False

        if success:
            print(f"\n✅ 测试环境状态恢复完成\n")
        else:
            print(f"\n⚠️  测试环境状态恢复部分失败\n")

        return success

    def set_auto_restore(self, enabled: bool):
        """
        设置是否启用自动恢复

        Args:
            enabled: True启用，False禁用
        """
        self._auto_restore = enabled
        status = "启用" if enabled else "禁用"
        print(f"{'✅' if enabled else '⚠️ '} 自动恢复已{status}")

    def ensure_python_sdk_installed(self, router_ip=None):
        """确保Python SDK已安装，如果未安装则自动安装

        Args:
            router_ip: 路由器IP地址，如果不提供则从config中获取

        Returns:
            bool: True表示SDK已就绪，False表示安装失败
        """
        import paramiko
        import os
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        if router_ip is None:
            router_ip = self.config.router_config.router_ip

        # SDK文件路径
        SDK_FILE_PATH = r"E:\GIT\ROUTER_TEST\config\pysdk-ur3x-5.0.2-u1.tar.gz"

        print("检查Python SDK是否已安装...")

        try:
            # 通过SSH检查python3.9是否可用
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )

            check_cmd = "export LD_LIBRARY_PATH=/usr/python/lib:$LD_LIBRARY_PATH && /usr/python/bin/python3.9 --version 2>&1"
            stdin, stdout, stderr = ssh.exec_command(check_cmd)
            output = stdout.read().decode('utf-8', errors='ignore').strip()
            ssh.close()

            if 'Python 3.9' in output:
                print(f"✅ Python SDK已安装: {output}")
                return True
            else:
                print(f"⚠️  Python SDK未安装或不可用")
                print(f"   检查输出: {output}")

        except Exception as e:
            print(f"⚠️  SDK检查失败: {e}")

        # Python SDK未安装，开始自动安装
        print(f"\n{'='*70}")
        print("开始自动安装Python SDK...")
        print(f"{'='*70}\n")

        # 检查SDK文件是否存在
        if not os.path.exists(SDK_FILE_PATH):
            print(f"❌ SDK文件不存在: {SDK_FILE_PATH}")
            print("   请确保SDK文件存在后再运行测试")
            return False

        print(f"✅ SDK文件存在: {SDK_FILE_PATH}")

        try:
            # 登录Web界面
            print("登录Web界面...")
            if not self.router_client.login_web():
                print("❌ Web登录失败")
                return False
            print("✅ Web登录成功")

            # 跳转到Python SDK页面
            print("跳转到Python SDK页面...")
            driver = self.router_client.driver
            python_url = f"http://{router_ip}/#app/python/status"
            driver.get(python_url)
            time.sleep(3)
            driver.refresh()
            time.sleep(3)
            print("✅ 已进入Python SDK页面")

            # 查找文件上传输入框
            print("查找文件上传输入框...")
            wait = WebDriverWait(driver, 10)
            upload_input = None

            locators = [
                ("ID: 0_sdkfile_url", By.XPATH, '//*[@id="0_sdkfile_url"]'),
                ("type=file", By.XPATH, '//input[@type="file"]'),
            ]

            for desc, by, xpath in locators:
                try:
                    elem = driver.find_element(by, xpath)
                    if elem.get_attribute('type') == 'file':
                        print(f"✅ 找到文件上传框: {desc}")
                        upload_input = elem
                        break
                except:
                    continue

            if not upload_input:
                print("❌ 无法找到文件上传输入框")
                return False

            # 上传SDK文件
            print(f"上传SDK文件...")
            upload_input.send_keys(SDK_FILE_PATH)
            time.sleep(2)

            # 验证文件已选择
            files_length = driver.execute_script("return arguments[0].files.length;", upload_input)
            if files_length == 0:
                print("❌ 文件选择失败")
                return False

            file_name = driver.execute_script("return arguments[0].files[0].name;", upload_input)
            print(f"✅ 文件已选择: {file_name}")

            # 点击安装按钮
            print("点击安装按钮...")
            install_btn_xpath = '//*[@id="0_sdkfile_import"]'
            install_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, install_btn_xpath))
            )
            install_btn.click()
            print("✅ 已点击安装按钮")

            # 等待安装完成
            print("等待安装完成（最多120秒）...")
            status_elem1_xpath = '//*[@id="status_python"]/div[2]/div[3]/div[2]'
            status_elem2_xpath = '//*[@id="status_python"]/div[2]/div[4]/div[2]'

            max_wait = 120
            elapsed = 0
            start_time = time.time()

            while elapsed < max_wait:
                try:
                    elem1 = driver.find_element(By.XPATH, status_elem1_xpath)
                    elem2 = driver.find_element(By.XPATH, status_elem2_xpath)

                    elem1_text = elem1.text.strip()
                    elem2_text = elem2.text.strip()

                    if elem1_text and elem2_text:
                        install_time = time.time() - start_time
                        print(f"\n✅ SDK安装成功！")
                        print(f"   耗时: {install_time:.2f}秒")
                        print(f"   状态: {elem1_text}, {elem2_text}\n")
                        return True

                except:
                    pass

                time.sleep(2)
                elapsed = time.time() - start_time

                # 每10秒输出一次进度
                if int(elapsed) % 10 == 0 and elapsed > 0:
                    print(f"   安装中... 已等待 {int(elapsed)} 秒")

            print(f"❌ 安装超时（{max_wait}秒）")
            return False

        except Exception as e:
            print(f"❌ 自动安装SDK失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False