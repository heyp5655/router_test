from test_cases.base_test import BaseTest
import time
import paramiko
import re


class CellularNetmaskCancelTest(BaseTest):
    """SIM1 取消自定义掩码测试

    测试项：功能用例/网络/接口/蜂窝网络
    测试点：SIM1 取消自定义掩码

    前置条件：
    1. 设备SIM1已插卡
    2. 蜂窝SIM1的子网掩码已设置为255.0.0.0

    测试步骤：
    1. 设置蜂窝SIM1的IPv4子网掩码为255.0.0.0，保存并应用
       预期：蜂窝reload，重新驻网拨号上，并且获取到ip
    2. 清空蜂窝SIM1的子网掩码，保存并应用
       预期：蜂窝reload，重新驻网拨号上，并且获取到ip
    3. 进入设备后台，查看蜂窝日志：/etc/urlog/cellular.log
       预期：日志中有发送AT指令：AT+QCFG="netmasket",0
    4. 进入设备后台，执行ifconfig
       预期：蜂窝接口cellular0的掩码为模块计算的掩码，不是255.0.0.0
    """

    # 添加分类信息属性
    category = "功能用例/网络/接口/蜂窝网络"
    is_regression = True  # 标记为回归测试用例

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "SIM1 取消自定义掩码"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 从config中获取router_client
        self.router_client = self.create_router_client(config.router_config)

        # 测试参数
        self.custom_netmask = "255.0.0.0"  # 自定义掩码
        self.expected_cancel_at_command = 'AT+QCFG="netmasket",0'  # 取消掩码的AT指令

        # 从config获取超时时间
        self.timeout = config.timeout if hasattr(config, 'timeout') else 300
        print(f"测试超时设置: {self.timeout}秒")

        # 存储各步骤验证结果
        self.step_results = []

    def create_router_client(self, router_config):
        """创建路由器客户端"""
        try:
            from core.router_client import RouterClient
            print(f"✅ 成功从 core.router_client 导入 RouterClient")
            return RouterClient(router_config)
        except ImportError as e:
            print(f"❌ 无法从 core.router_client 导入: {e}")
            raise

    def setup(self):
        """测试前置条件"""
        print(f"INFO - {self.__class__.__name__}: 前置条件检查")

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

        print("✅ 前置条件：设备SIM1已插卡（假设已满足）")
        print("✅ 前置条件：蜂窝SIM1的子网掩码将在步骤1设置为255.0.0.0")

    def execute(self):
        """执行测试"""
        try:
            print(f"INFO - {self.__class__.__name__}: 开始执行测试")
            print(f"\n{'='*70}")
            print(f"测试用例：{self.test_name}")
            print(f"超时设置：{self.timeout}秒")
            print(f"{'='*70}\n")

            all_passed = True

            # 步骤1：设置蜂窝SIM1的IPv4子网掩码为255.0.0.0，保存并应用
            step1_result = self._step1_set_custom_netmask()
            self.step_results.append(("步骤1：设置自定义掩码255.0.0.0", step1_result))
            if not step1_result:
                all_passed = False
                print("❌ 步骤1失败，终止测试")
                return False

            # 等待蜂窝重新注网并获取IP（使用用户设置的超时时间）
            wait_time = min(self.timeout, 120)
            print(f"\n等待{wait_time}秒，让蜂窝重新注网并获取IP...")
            time.sleep(wait_time)

            # 验证步骤1后是否获取到IP
            print("\n步骤1后置验证：验证设备是否获取到IP...")
            if self._verify_device_has_ip():
                print("✅ 预期1：蜂窝reload，重新驻网拨号上，并且获取到ip - 验证通过")
            else:
                print("❌ 预期1：设备未能获取到IP")
                all_passed = False

            # 步骤2：清空蜂窝SIM1的子网掩码，保存并应用
            step2_result = self._step2_cancel_netmask()
            self.step_results.append(("步骤2：清空子网掩码恢复默认", step2_result))
            if not step2_result:
                all_passed = False
                print("❌ 步骤2失败，终止测试")
                return False

            # 等待蜂窝重新注网并获取IP
            print(f"\n等待{wait_time}秒，让蜂窝重新注网并获取IP...")
            time.sleep(wait_time)

            # 验证步骤2后是否获取到IP
            print("\n步骤2后置验证：验证设备是否获取到IP...")
            if self._verify_device_has_ip():
                print("✅ 预期2：蜂窝reload，重新驻网拨号上，并且获取到ip - 验证通过")
            else:
                print("❌ 预期2：设备未能获取到IP")
                all_passed = False

            # 步骤3：查看蜂窝日志，验证AT指令
            step3_result = self._step3_verify_cancel_at_command()
            self.step_results.append(("步骤3：验证日志中取消掩码AT指令", step3_result))
            if not step3_result:
                all_passed = False

            # 步骤4：执行ifconfig，验证掩码不是255.0.0.0
            step4_result = self._step4_verify_default_netmask()
            self.step_results.append(("步骤4：验证ifconfig掩码已恢复默认", step4_result))
            if not step4_result:
                all_passed = False

            # 打印汇总结果
            self._print_summary()

            return all_passed

        except Exception as e:
            print(f"ERROR - {self.__class__.__name__}: ❌ 测试执行失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise

    def _step1_set_custom_netmask(self):
        """步骤1：设置蜂窝SIM1的IPv4子网掩码为255.0.0.0，保存并应用"""
        print(f"\n{'='*70}")
        print("步骤1：设置蜂窝SIM1的IPv4子网掩码为255.0.0.0，保存并应用")
        print(f"{'='*70}")
        print(f"预期1：蜂窝reload，重新驻网拨号上，并且获取到ip")

        try:
            # 调用RouterClient的方法设置子网掩码
            result = self.router_client.set_cellular_netmask(self.custom_netmask)

            if result:
                print(f"✅ 自定义子网掩码{self.custom_netmask}设置并应用成功")
                return True
            else:
                print(f"❌ 自定义子网掩码设置失败")
                return False

        except Exception as e:
            print(f"❌ 步骤1执行失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _step2_cancel_netmask(self):
        """步骤2：清空蜂窝SIM1的子网掩码，保存并应用"""
        print(f"\n{'='*70}")
        print("步骤2：清空蜂窝SIM1的子网掩码，保存并应用")
        print(f"{'='*70}")
        print(f"预期2：蜂窝reload，重新驻网拨号上，并且获取到ip")

        try:
            # 清空子网掩码（设置为空字符串）
            print("清空子网掩码，恢复为默认...")
            result = self.router_client.set_cellular_netmask("")

            if result:
                print(f"✅ 子网掩码已清空并应用成功")
                return True
            else:
                print(f"❌ 清空子网掩码失败")
                return False

        except Exception as e:
            print(f"❌ 步骤2执行失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _verify_device_has_ip(self):
        """验证设备是否获取到IP地址"""
        try:
            router_ip = self.router_client.router_ip

            # 设置重试参数
            max_retry_time = 60  # 最多重试60秒
            retry_interval = 10
            start_time = time.time()
            attempt = 0

            while time.time() - start_time < max_retry_time:
                attempt += 1
                elapsed_time = int(time.time() - start_time)
                print(f"第{attempt}次验证设备IP (已等待{elapsed_time}秒)...")

                # SSH连接
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    ssh.connect(router_ip, username=self.SSH_ROOT_USERNAME, password=self.SSH_ROOT_PASSWORD, timeout=10)

                    # 执行ifconfig命令
                    stdin, stdout, stderr = ssh.exec_command("ifconfig cellular0")
                    ifconfig_output = stdout.read().decode('utf-8')

                    ssh.close()

                    # 检查是否有IP地址
                    ip_match = re.search(r'inet addr:(\d+\.\d+\.\d+\.\d+)', ifconfig_output)

                    if ip_match:
                        ip_address = ip_match.group(1)
                        print(f"✅ 设备已获取IP地址: {ip_address}")
                        return True
                    else:
                        print(f"⚠️ 第{attempt}次验证：设备尚未获取到IP地址，{retry_interval}秒后重试...")
                        time.sleep(retry_interval)
                        continue

                except Exception as e:
                    print(f"❌ SSH连接失败: {str(e)}，{retry_interval}秒后重试...")
                    try:
                        ssh.close()
                    except:
                        pass
                    time.sleep(retry_interval)
                    continue

            print(f"❌ 在{max_retry_time}秒内设备未能获取到IP")
            return False

        except Exception as e:
            print(f"验证设备IP失败: {str(e)}")
            return False

    def _step3_verify_cancel_at_command(self):
        """步骤3：查看蜂窝日志，验证取消掩码AT指令"""
        print(f"\n{'='*70}")
        print("步骤3：进入设备后台，查看蜂窝日志：/etc/urlog/cellular.log")
        print(f"{'='*70}")
        print(f'预期3：日志中有发送AT指令：{self.expected_cancel_at_command}')

        try:
            router_ip = self.router_client.router_ip
            search_pattern = self.expected_cancel_at_command.lower()

            # 设置重试参数
            max_retry_time = min(self.timeout // 2, 60)
            retry_interval = 5
            start_time = time.time()
            attempt = 0

            while time.time() - start_time < max_retry_time:
                attempt += 1
                elapsed_time = int(time.time() - start_time)
                print(f"第{attempt}次尝试查找AT指令 (已等待{elapsed_time}秒)...")

                # SSH连接
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    ssh.connect(router_ip, username=self.SSH_ROOT_USERNAME, password=self.SSH_ROOT_PASSWORD, timeout=10)

                    # 获取cellular.log日志
                    stdin, stdout, stderr = ssh.exec_command("cat /etc/urlog/cellular.log")
                    log_content = stdout.read().decode('utf-8')
                    error = stderr.read().decode('utf-8')

                    if error:
                        print(f"SSH命令执行错误: {error}")
                        ssh.close()
                        time.sleep(retry_interval)
                        continue

                    # 查找AT命令（支持模糊匹配，因为AT指令格式可能有变化）
                    # 匹配 AT+QCFG="netmasket",0 或 netmaskset
                    if 'netmasket",0' in log_content.lower() or 'netmaskset",0' in log_content.lower():
                        print(f"✅ 预期3：成功在日志中找到取消掩码AT指令")
                        # 打印相关日志行
                        for line in log_content.split('\n'):
                            if 'netmasket",0' in line.lower() or 'netmaskset",0' in line.lower():
                                print(f"  找到日志: {line}")
                                break
                        ssh.close()
                        return True
                    else:
                        print(f"❌ 第{attempt}次尝试未找到AT指令，{retry_interval}秒后重试...")

                except Exception as e:
                    print(f"SSH连接失败: {str(e)}")
                finally:
                    try:
                        ssh.close()
                    except:
                        pass

                time.sleep(retry_interval)

            # 超时未找到
            print(f"❌ 预期3：在{max_retry_time}秒内未找到AT指令")
            return False

        except Exception as e:
            print(f"❌ 步骤3执行失败: {str(e)}")
            return False

    def _step4_verify_default_netmask(self):
        """步骤4：执行ifconfig，验证掩码不是255.0.0.0"""
        print(f"\n{'='*70}")
        print("步骤4：进入设备后台，执行ifconfig")
        print(f"{'='*70}")
        print(f"预期4：蜂窝接口cellular0的掩码为模块计算的掩码，不是255.0.0.0")

        try:
            router_ip = self.router_client.router_ip

            # 设置重试参数（等待设备获取IP地址）
            max_retry_time = min(self.timeout, 180)
            retry_interval = 10
            start_time = time.time()
            attempt = 0

            while time.time() - start_time < max_retry_time:
                attempt += 1
                elapsed_time = int(time.time() - start_time)
                print(f"第{attempt}次尝试验证ifconfig掩码 (已等待{elapsed_time}秒)...")

                # SSH连接
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    ssh.connect(router_ip, username=self.SSH_ROOT_USERNAME, password=self.SSH_ROOT_PASSWORD, timeout=10)

                    # 执行ifconfig命令
                    stdin, stdout, stderr = ssh.exec_command("ifconfig cellular0")
                    ifconfig_output = stdout.read().decode('utf-8')
                    error = stderr.read().decode('utf-8')

                    ssh.close()

                    if error:
                        print(f"⚠️ ifconfig执行警告: {error}")

                    print(f"ifconfig cellular0 输出:\n{ifconfig_output}")

                    # 首先检查是否有IP地址（验证设备已获取IP）
                    ip_match = re.search(r'inet addr:(\d+\.\d+\.\d+\.\d+)', ifconfig_output)

                    if not ip_match:
                        print(f"⚠️ 第{attempt}次尝试：设备尚未获取到IP地址，{retry_interval}秒后重试...")
                        time.sleep(retry_interval)
                        continue

                    ip_address = ip_match.group(1)
                    print(f"✅ 设备已获取IP地址: {ip_address}")

                    # 解析掩码
                    mask_match = re.search(r'Mask:(\d+\.\d+\.\d+\.\d+)', ifconfig_output)

                    if mask_match:
                        actual_mask = mask_match.group(1)
                        print(f"实际掩码: {actual_mask}")

                        # 验证掩码不是255.0.0.0
                        if actual_mask != self.custom_netmask:
                            print(f"✅ 预期4：cellular0的掩码已恢复为模块计算的掩码({actual_mask})，不是{self.custom_netmask} - 验证通过")
                            return True
                        else:
                            print(f"❌ 预期4：掩码仍然是{self.custom_netmask}，未恢复默认")
                            return False
                    else:
                        print(f"⚠️ 第{attempt}次尝试：无法从ifconfig输出中解析掩码，{retry_interval}秒后重试...")
                        time.sleep(retry_interval)
                        continue

                except Exception as e:
                    print(f"❌ SSH连接失败: {str(e)}，{retry_interval}秒后重试...")
                    try:
                        ssh.close()
                    except:
                        pass
                    time.sleep(retry_interval)
                    continue

            # 超时未成功
            print(f"❌ 预期4：在{max_retry_time}秒内未能验证掩码")
            return False

        except Exception as e:
            print(f"❌ 步骤4执行失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _print_summary(self):
        """打印测试结果汇总"""
        print(f"\n{'='*70}")
        print("测试结果汇总")
        print(f"{'='*70}")

        passed_count = 0
        failed_count = 0
        skipped_count = 0

        for step_name, result in self.step_results:
            if result is None:
                status = "⚠️ 跳过"
                skipped_count += 1
            elif result:
                status = "✅ 通过"
                passed_count += 1
            else:
                status = "❌ 失败"
                failed_count += 1

            print(f"{status} - {step_name}")

        print(f"\n总计: {len(self.step_results)} 个步骤")
        print(f"通过: {passed_count} 个")
        print(f"失败: {failed_count} 个")
        print(f"跳过: {skipped_count} 个")
        print(f"{'='*70}\n")

    def cleanup(self):
        """测试后清理"""
        print(f"INFO - {self.__class__.__name__}: 取消自定义掩码测试完成")

        # 关闭浏览器
        if hasattr(self.router_client, 'close'):
            self.router_client.close()
