from test_cases.base_test import BaseTest
import time
import paramiko
import re


class SmsCenterConfigurationTest(BaseTest):
    """quagga（UR3X/UR41/UG6X/UG56）：SIM2配置短信中心号码

    适用机型：UR3X、UR41、UG6X、UG56

    测试步骤：
    1. 登录路由器
    2. 设置SIM2的短信中心号码为：+86123456789012
    3. 通过SSH登录路由器查看日志中是否有AT+CSCA="+86123456789012",145下发
    4. 通过Web页面下发AT+CSCA?命令
    5. 通过SSH查看日志中是否有+CSCA: "+86123456789012",145响应
    """

    # 添加分类信息属性
    category = "功能用例/网络/接口/蜂窝网络"
    is_regression = True  # 标记为回归测试用例

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "quagga（UR3X/UR41/UG6X/UG56）：SIM2配置短信中心号码"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 从config中获取router_client
        self.router_client = self.create_router_client(config.router_config)

        # 测试参数
        self.sms_center_number = "+86123456789012"
        self.expected_at_command = f'AT+CSCA="{self.sms_center_number}",145'
        self.expected_response = f'+CSCA: "{self.sms_center_number}",145'

    def create_router_client(self, router_config):
        """创建路由器客户端"""
        try:
            # 从 core.router_client 导入 RouterClient
            from core.router_client import RouterClient
            print(f"✅ 成功从 core.router_client 导入 RouterClient")
            return RouterClient(router_config)
        except ImportError as e:
            print(f"❌ 无法从 core.router_client 导入: {e}")

            # 备用方案：尝试其他可能的路径
            try:
                # 尝试从 utils.router_client 导入
                from utils.router_client import RouterClient
                print(f"✅ 成功从 utils.router_client 导入 RouterClient")
                return RouterClient(router_config)
            except ImportError:
                # 最后使用模拟客户端
                class MockRouterClient:
                    def __init__(self, config):
                        self.router_ip = config.router_ip
                        self.username = config.username
                        self.password = config.password
                        self.model = config.model
                        self.logged_in = False

                    def login_web(self):
                        print(f"模拟登录路由器 {self.router_ip}")
                        self.logged_in = True
                        return True

                    def SMS_Center_set(self, center_number):
                        print(f"模拟配置短信中心号码为 {center_number}")
                        return True

                    def AT_COMAND_SET(self, at_command):
                        print(f"模拟执行AT命令: {at_command}")
                        return True

                print("⚠️ 使用模拟 RouterClient")
                return MockRouterClient(router_config)

    def setup(self):
        """测试前置条件"""
        print(f"INFO - {self.__class__.__name__}: 前置条件：登录路由器")

        # 确保已登录
        if not hasattr(self.router_client, 'logged_in') or not self.router_client.logged_in:
            login_success = self.router_client.login_web()
            if not login_success:
                raise Exception("登录失败")

        print("✅ 路由器登录成功")

        # 检查并启用SSH（新版本固件默认关闭SSH）
        print("前置条件: 检查SSH启用状态...")
        if not self.router_client.ensure_ssh_enabled():
            raise Exception("SSH未启用且自动启用失败，无法继续测试")
        print("✅ SSH已就绪")

    def execute(self):
        """执行测试"""
        try:
            # 记录开始时间
            start_timestamp = int(time.time())
            print(f"INFO - {self.__class__.__name__}: 测试开始时间戳: {start_timestamp}")

            # 步骤1: 配置SIM2短信中心号码
            print(f"INFO - {self.__class__.__name__}: 1. 配置SIM2短信中心号码为: {self.sms_center_number}")
            config_success = self.router_client.SMS_Center_set_SIM2(self.sms_center_number)
            if not config_success:
                raise Exception("短信中心号码配置失败")

            print("✅ SIM2短信中心号码配置成功")
            time.sleep(5)  # 等待配置生效

            # 步骤2: 通过SSH检查日志中的AT命令
            print(f"INFO - {self.__class__.__name__}: 2. 检查日志中的AT命令下发")
            at_command_verified = self._verify_at_command_in_log(start_timestamp)
            if not at_command_verified:
                raise Exception("AT命令验证失败")

            print("✅ AT命令验证成功")

            # 步骤3: 通过Web页面下发AT+CSCA?命令
            print(f"INFO - {self.__class__.__name__}: 3. 通过Web页面下发AT+CSCA?命令")
            at_send_success = self.router_client.AT_COMAND_SET("AT+CSCA?")
            if not at_send_success:
                raise Exception("AT+CSCA?命令下发失败")

            print("✅ AT+CSCA?命令下发成功")
            time.sleep(5)  # 等待命令执行

            # 步骤4: 通过SSH检查日志中的AT命令响应
            print(f"INFO - {self.__class__.__name__}: 4. 检查日志中的AT命令响应")
            at_response_verified = self._verify_at_response_in_log()
            if not at_response_verified:
                raise Exception("AT命令响应验证失败")

            print("✅ AT命令响应验证成功")

            # 所有步骤通过
            print(f"INFO - {self.__class__.__name__}: ✅ SIM2短信中心号码配置测试全部通过")
            return True

        except Exception as e:
            print(f"ERROR - {self.__class__.__name__}: ❌ 测试执行失败: {str(e)}")
            raise

    def _verify_at_command_in_log(self, start_timestamp):
        """通过SSH登录并检查日志中的AT+CSCA命令"""
        try:
            router_ip = self.router_client.router_ip

            # 创建搜索模式
            search_pattern = self.expected_at_command.lower()

            # 设置重试参数
            max_retry_time = 60  # 最大重试时间60秒
            retry_interval = 3  # 重试间隔3秒
            start_time = time.time()
            attempt = 0

            print(f"开始查找AT命令: {self.expected_at_command}")
            print(f"最多重试{max_retry_time}秒，间隔{retry_interval}秒...")

            while time.time() - start_time < max_retry_time:
                attempt += 1
                elapsed_time = int(time.time() - start_time)
                print(f"第{attempt}次尝试查找AT命令 (已等待{elapsed_time}秒)...")

                # 使用paramiko建立SSH连接
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    # 连接路由器
                    ssh.connect(router_ip, username=self.SSH_ROOT_USERNAME, password=self.SSH_ROOT_PASSWORD, timeout=10)

                    # 执行命令获取cellular.log日志
                    stdin, stdout, stderr = ssh.exec_command("cat /etc/urlog/cellular.log")
                    log_content = stdout.read().decode('utf-8')
                    error = stderr.read().decode('utf-8')

                    if error:
                        print(f"SSH命令执行错误: {error}")
                        ssh.close()
                        time.sleep(retry_interval)
                        continue

                    # 在日志中查找AT命令 - 使用大小写不敏感的搜索
                    lines = log_content.split('\n')
                    at_command_found = False
                    found_line = None
                    found_timestamp = None

                    for line in lines:
                        # 将行转换为小写进行大小写不敏感的搜索
                        if search_pattern in line.lower():
                            at_command_found = True
                            found_line = line

                            # 尝试提取时间戳
                            timestamp_match = re.search(r'(\d{10})', line)
                            if timestamp_match:
                                found_timestamp = int(timestamp_match.group(1))
                                print(f"找到AT命令时间戳: {found_timestamp}")

                            break

                    if at_command_found:
                        # 验证时间戳
                        if found_timestamp and found_timestamp >= start_timestamp:
                            print(f"✅ 成功在日志中找到AT命令 (时间戳验证通过): {found_line}")
                            ssh.close()
                            return True
                        else:
                            print(f"⚠️ 找到AT命令但时间戳不匹配或未找到时间戳: {found_line}")
                            # 继续查找更新的记录
                    else:
                        print(f"❌ 第{attempt}次尝试未找到AT命令，{retry_interval}秒后重试...")

                        # 第一次尝试时打印日志的最后几行用于调试
                        if attempt == 1:
                            print(f"日志最后5行: {lines[-5:]}")

                except Exception as e:
                    print(f"❌ 第{attempt}次SSH连接失败: {str(e)}")
                finally:
                    # 关闭SSH连接
                    try:
                        ssh.close()
                    except:
                        pass

                # 等待重试间隔
                time.sleep(retry_interval)

            # 如果超过最大重试时间仍未找到
            print(f"❌ 在{max_retry_time}秒内未找到AT命令: {self.expected_at_command}")
            return False

        except Exception as e:
            print(f"❌ 检查AT命令日志时发生异常: {str(e)}")
            return False

    def _verify_at_response_in_log(self):
        """通过SSH登录并检查日志中的AT+CSCA?命令响应"""
        try:
            router_ip = self.router_client.router_ip

            # 创建搜索模式
            search_pattern = self.expected_response.lower()

            # 设置重试参数
            max_retry_time = 30  # 最大重试时间30秒
            retry_interval = 3  # 重试间隔3秒
            start_time = time.time()
            attempt = 0

            print(f"开始查找AT命令响应: {self.expected_response}")
            print(f"最多重试{max_retry_time}秒，间隔{retry_interval}秒...")

            while time.time() - start_time < max_retry_time:
                attempt += 1
                elapsed_time = int(time.time() - start_time)
                print(f"第{attempt}次尝试查找AT命令响应 (已等待{elapsed_time}秒)...")

                # 使用paramiko建立SSH连接
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    # 连接路由器
                    ssh.connect(router_ip, username=self.SSH_ROOT_USERNAME, password=self.SSH_ROOT_PASSWORD, timeout=10)

                    # 执行命令获取cellular.log日志
                    stdin, stdout, stderr = ssh.exec_command("cat /etc/urlog/cellular.log")
                    log_content = stdout.read().decode('utf-8')
                    error = stderr.read().decode('utf-8')

                    if error:
                        print(f"SSH命令执行错误: {error}")
                        ssh.close()
                        time.sleep(retry_interval)
                        continue

                    # 在日志中查找AT命令响应 - 使用大小写不敏感的搜索
                    lines = log_content.split('\n')
                    response_found = False
                    found_line = None

                    for line in lines:
                        # 将行转换为小写进行大小写不敏感的搜索
                        if search_pattern in line.lower():
                            response_found = True
                            found_line = line
                            break

                    if response_found:
                        print(f"✅ 成功在日志中找到AT命令响应: {found_line}")
                        ssh.close()
                        return True
                    else:
                        print(f"❌ 第{attempt}次尝试未找到AT命令响应，{retry_interval}秒后重试...")

                        # 第一次尝试时打印日志的最后几行用于调试
                        if attempt == 1:
                            print(f"日志最后10行:")
                            for i, line in enumerate(lines[-10:]):
                                print(f"  {i + 1}: {line}")

                except Exception as e:
                    print(f"❌ 第{attempt}次SSH连接失败: {str(e)}")
                finally:
                    # 关闭SSH连接
                    try:
                        ssh.close()
                    except:
                        pass

                # 等待重试间隔
                time.sleep(retry_interval)

            # 如果超过最大重试时间仍未找到
            print(f"❌ 在{max_retry_time}秒内未找到AT命令响应: {self.expected_response}")

            # 打印更多调试信息
            print("尝试获取完整的日志文件内容用于调试...")
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(router_ip, username=self.SSH_ROOT_USERNAME, password=self.SSH_ROOT_PASSWORD, timeout=10)

                # 获取最后50行日志
                stdin, stdout, stderr = ssh.exec_command("tail -50 /etc/urlog/cellular.log")
                recent_logs = stdout.read().decode('utf-8')
                print(f"最近50行日志:\n{recent_logs}")

                ssh.close()
            except Exception as debug_e:
                print(f"获取调试日志失败: {str(debug_e)}")

            return False

        except Exception as e:
            print(f"❌ 检查AT命令响应日志时发生异常: {str(e)}")
            return False

    def cleanup(self):
        """测试后清理"""
        print(f"INFO - {self.__class__.__name__}: SIM2短信中心号码配置测试完成")

        # 如果需要恢复默认设置，可以在这里添加
        # 例如：self.router_client.SMS_Center_set("+8613800210500")  # 默认短信中心

        # 关闭浏览器（如果需要）
        if hasattr(self.router_client, 'close'):
            self.router_client.close()