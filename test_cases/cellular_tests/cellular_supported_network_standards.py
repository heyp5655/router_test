from test_cases.base_test import BaseTest
from utils.network_utils import network_utils
import time
import subprocess
import paramiko
import sys
import os


class CellularSupportedNetworkStandardsTest(BaseTest):
    """蜂窝支持的网络制式测试
    1，路由器lan侧地址：192.168.1.x
    2，测试电脑有线连接路由器并配置静态：192.168.1.100  255.255.255.0 114.114.114.114 8.8.8.8
    """

    # 添加分类信息属性
    category = "功能用例/网络/接口/蜂窝网络"
    is_regression = True  # 标记为回归测试用例

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "蜂窝支持的网络制式测试"

    def __init__(self, config):
        """修改初始化方法，直接使用基类的 router_client"""
        super().__init__(config)

        # 使用基类已经创建的 router_client，不再重复创建
        # self.router_client 已经在 BaseTest 中创建

        self.test_steps = [
            {
                'mode': '4G_ONLY',
                'description': '4G ONLY模式测试',
                'quectel_at_command': 'AT+QCFG="NWSCANMODE",3',  # 移远
                'meig_at_command': 'AT^SYSCFGEX="03"',  # 美格
                'need_connectivity_check': True,  # 需要检查网络连通性
                'need_page_check': False  # 不需要页面状态检查
            },
            {
                'mode': 'AUTO',
                'description': 'AUTO模式测试',
                'quectel_at_command': 'AT+QCFG="NWSCANMODE",0',  # 移远
                'meig_at_command': 'AT^SYSCFGEX="00"',  # 美格
                'need_connectivity_check': True,  # 需要检查网络连通性
                'need_page_check': False  # 不需要页面状态检查
            },
            {
                'mode': '3G_ONLY',
                'description': '3G ONLY模式测试',
                'quectel_at_command': 'AT+QCFG="NWSCANMODE",2',  # 移远
                'meig_at_command': 'AT^SYSCFGEX="02"',  # 美格
                'need_connectivity_check': False,  # 不需要检查网络连通性
                'need_page_check': False  # 不需要页面状态检查
            },
            {
                'mode': '2G_ONLY',
                'description': '2G ONLY模式测试',
                'quectel_at_command': 'AT+QCFG="NWSCANMODE",1',  # 移远
                'meig_at_command': 'AT^SYSCFGEX="01"',  # 美格
                'need_connectivity_check': False,  # 不需要检查网络连通性
                'need_page_check': False  # 不需要页面状态检查
            }
        ]
        self.network_interface = "TEST"  # 电脑网卡名称

    def setup(self):
        """测试前置条件"""
        print(f"INFO - {self.__class__.__name__}: 前置条件：蜂窝作为主链路")

        # 检查 router_client 是否可用
        if self.router_client is None:
            raise Exception("RouterClient 不可用，无法执行测试")

        # 确保已登录
        if not hasattr(self.router_client, 'logged_in') or not self.router_client.logged_in:
            login_success = self.router_client.login_web()
            if not login_success:
                raise Exception("登录失败")

        # 检查并启用SSH（新版本固件默认关闭SSH）
        print("前置条件: 检查SSH启用状态...")
        if not self.router_client.ensure_ssh_enabled():
            raise Exception("SSH未启用且自动启用失败，无法继续测试")
        print("✅ SSH已就绪")

    def execute(self):
        """执行测试"""
        try:
            # 执行每个测试步骤，按照新顺序：4G_ONLY → AUTO → 3G_ONLY → 2G_ONLY
            for step in self.test_steps:
                self._execute_single_step(step)
                # 每个步骤完成后等待一段时间
                time.sleep(10)

        except Exception as e:
            raise
        finally:
            # 测试完成后恢复默认设置
            self._restore_default_settings()

    def _execute_single_step(self, step):
        """执行单个测试步骤"""
        mode = step['mode']
        description = step['description']
        need_connectivity_check = step['need_connectivity_check']
        need_page_check = step['need_page_check']

        print(f"INFO - {self.__class__.__name__}: 开始执行步骤: {mode}模式测试")
        print(f"INFO - {self.__class__.__name__}: 步骤描述: {description}")

        try:
            # 记录设置前的时间戳
            start_timestamp = int(time.time())
            print(f"INFO - {self.__class__.__name__}: 设置前时间戳: {start_timestamp}")

            # 1. 配置Network Type
            print(f"INFO - {self.__class__.__name__}: 1. 配置Network Type为{mode}")
            config_success = self.router_client.cellular_supported_network_standards(mode)
            if not config_success:
                raise Exception(f"{mode}模式配置失败")

            # 2. 等待网络连接建立，先检查蜂窝状态，如果成功则跳过等待
            print(f"INFO - {self.__class__.__name__}: 等待蜂窝网络连接建立...")

            # 对于AUTO和4G_ONLY模式，先检查蜂窝状态
            if mode in ['AUTO', '4G_ONLY']:
                # 先等待一段时间让网络开始建立
                time.sleep(10)

                # 检查蜂窝状态，如果成功则直接继续
                cellular_status = self._check_cellular_status_with_timeout(max_wait_time=600)
                if cellular_status:
                    print(f"✅ {mode}模式蜂窝连接已建立，跳过等待")
                else:
                    print(f"❌ {mode}模式蜂窝连接未在200秒内建立")
                    # 对于AUTO和4G_ONLY模式，连接失败是严重问题
                    if mode in ['AUTO', '4G_ONLY']:
                        raise Exception(f"{mode}模式蜂窝连接未在200秒内建立")
                    else:
                        # 对于3G/2G模式，连接失败是预期的
                        print(f"⚠️ {mode}模式连接失败（预期，当前环境无信号）")
            else:
                # 对于3G/2G ONLY模式，等待较短时间
                wait_time = 60
                print(f"INFO - {self.__class__.__name__}: 等待{wait_time}秒...")
                time.sleep(wait_time)

            # 3. 验证后台AT指令配置
            print(f"INFO - {self.__class__.__name__}: 2. 验证后台AT指令配置")
            at_verified = self._verify_at_command_in_log(step, start_timestamp)
            if not at_verified:
                raise Exception(f"{mode}模式AT指令验证失败")

            # 4. 对于AUTO和4G_ONLY模式，进行网络连通性检查
            if need_connectivity_check:
                print(f"INFO - {self.__class__.__name__}: 3. 检查网络连通性")
                connectivity_verified = self._check_network_connectivity()
                if not connectivity_verified:
                    raise Exception(f"{mode}模式网络连通性检查失败")

            print(f"INFO - {self.__class__.__name__}: ✅ {mode}模式测试通过")
            return True

        except Exception as e:
            print(f"ERROR - {self.__class__.__name__}: ❌ {mode}模式测试执行失败: {str(e)}")
            raise

    def _check_cellular_status_with_timeout(self, max_wait_time=200):
        """检查蜂窝状态，带有超时机制"""
        start_time = time.time()
        check_interval = 10  # 每10秒检查一次

        while time.time() - start_time < max_wait_time:
            print(f"检查蜂窝状态... (已等待{int(time.time() - start_time)}秒)")

            # 使用router_client的check_cellular_status方法检查状态
            cellular_status = self.router_client.check_cellular_status()

            if cellular_status:
                print("✅ 蜂窝状态检查通过")
                return True
            else:
                # 计算剩余等待时间
                remaining_time = max_wait_time - (time.time() - start_time)
                if remaining_time > check_interval:
                    print(f"蜂窝状态未就绪，{check_interval}秒后重试...")
                    time.sleep(check_interval)
                else:
                    # 最后一次检查
                    print(f"最后一次检查蜂窝状态...")
                    time.sleep(remaining_time)
                    cellular_status = self.router_client.check_cellular_status()
                    return cellular_status

        print(f"❌ 蜂窝状态检查超时（{max_wait_time}秒）")
        return False

    def _verify_at_command_in_log(self, step, start_timestamp):
        """通过SSH登录并检查cellular.log中的AT命令，带有重试机制"""
        try:
            router_ip = self.router_client.router_ip
            mode = step['mode']

            # 使用页面填写的模组类型来判断
            module_type = getattr(self.router_client, 'module_type', 'quectel')  # 默认为移远

            if module_type == "quectel":
                expected_at_command = step['quectel_at_command']
                print(f"检测到移远模组，期望AT命令: {expected_at_command}")
            elif module_type == "meig":
                expected_at_command = step['meig_at_command']
                print(f"检测到美格模组，期望AT命令: {expected_at_command}")
            else:
                # 默认使用移远模组
                expected_at_command = step['quectel_at_command']
                print(f"未知模组类型 '{module_type}'，默认使用移远模组，期望AT命令: {expected_at_command}")

            # 创建大小写不敏感的搜索模式
            search_pattern = expected_at_command.lower()

            # 设置重试参数
            max_retry_time = 200  # 最大重试时间200秒
            retry_interval = 3  # 重试间隔3秒
            start_time = time.time()
            attempt = 0

            print(f"开始查找AT命令，最多重试{max_retry_time}秒，间隔{retry_interval}秒...")

            while time.time() - start_time < max_retry_time:
                attempt += 1
                elapsed_time = int(time.time() - start_time)
                print(f"第{attempt}次尝试查找AT命令 (已等待{elapsed_time}秒)...")

                # 使用paramiko建立SSH连接
                ssh = paramiko.SSHClient()
                # 自动添加主机密钥
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    # 连接路由器
                    ssh.connect(router_ip, username=self.SSH_ROOT_USERNAME, password=self.SSH_ROOT_PASSWORD, timeout=10)

                    # 执行命令获取日志
                    stdin, stdout, stderr = ssh.exec_command("cat /etc/urlog/cellular.log")
                    log_content = stdout.read().decode('utf-8')
                    error = stderr.read().decode('utf-8')

                    if error:
                        print(f"SSH命令执行错误: {error}")
                        # 关闭SSH连接后继续重试
                        ssh.close()
                        time.sleep(retry_interval)
                        continue

                    # 在日志中查找AT命令 - 使用大小写不敏感的搜索
                    lines = log_content.split('\n')
                    at_command_found = False
                    found_line = None

                    for line in lines:
                        # 将行也转换为小写进行大小写不敏感的搜索
                        if search_pattern in line.lower():
                            at_command_found = True
                            found_line = line
                            break

                    if at_command_found:
                        print(f"✅ 成功在日志中找到AT命令: {found_line}")
                        ssh.close()
                        return True
                    else:
                        print(f"❌ 第{attempt}次尝试未找到AT命令，{retry_interval}秒后重试...")
                        # 打印前几行日志用于调试
                        if attempt == 1:  # 只在第一次尝试时打印日志前几行
                            print(f"日志前几行: {lines[:3]}")

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
            print(f"❌ 在{max_retry_time}秒内未找到AT命令: {expected_at_command}")
            return False

        except Exception as e:
            print(f"❌ 检查AT命令日志时发生异常: {str(e)}")
            return False

    def _check_network_connectivity(self):
        """检查网络连通性 - 使用固定IP 192.168.1.100作为源地址ping百度"""
        try:
            from utils.network_utils import network_utils

            # 使用 network_utils 的静态IP方法检查外网连通性
            return network_utils.check_pc_internet_via_static_ip(
                adapter_name=self.network_interface,
                static_ip="192.168.1.100",
                subnet="255.255.255.0",
                timeout=30
            )

        except Exception as e:
            print(f"❌ 网络连通性检查异常: {str(e)}")
            return False

    def _restore_default_settings(self):
        """恢复默认AUTO设置"""
        print(f"INFO - {self.__class__.__name__}: 恢复默认AUTO设置")
        try:
            self.router_client.cellular_supported_network_standards("AUTO")
            time.sleep(20)  # 等待恢复完成
        except Exception as e:
            print(f"WARNING - {self.__class__.__name__}: 恢复默认设置失败: {str(e)}")

    def cleanup(self):
        """测试后清理 - 将teardown重命名为cleanup以符合BaseTest约定"""
        print(f"INFO - {self.__class__.__name__}: 蜂窝网络制式测试完成")

        # 恢复网卡配置
        try:
            from utils.network_utils import network_utils
            print("\n恢复网卡配置...")
            network_utils.restore_adapter_auto_config(adapter_name=self.network_interface)
        except Exception as e:
            print(f"⚠️  恢复网卡配置时出错: {str(e)}")