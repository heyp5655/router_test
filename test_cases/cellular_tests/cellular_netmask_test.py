from test_cases.base_test import BaseTest
import time
import paramiko
import re


class CellularNetmaskTest(BaseTest):
    """SIM1 IPv4子网掩码设置255.0.0.0测试

    测试项：功能用例/网络/接口/蜂窝网络
    测试点：SIM1 IPv4子网掩码设置255.0.0.0

    前置条件：
    1. 设备SIM1已插卡

    测试步骤：
    1. 设置蜂窝SIM1的IPv4子网掩码为255.0.0.0，保存并应用
       预期：蜂窝reload，重新驻网拨号上
    2. 查看蜂窝日志：/etc/urlog/cellular.log
       预期：日志中有发送AT指令：AT+QCFG="netmaskset",1,"255.0.0.0"
    3. 进入设备后台，执行ifconfig
       预期：蜂窝接口cellular0的掩码为255.0.0.0
    4. 进入网页"状态-蜂窝"
       预期：所有APN IPV4地址显示的掩码为8，如192.168.10.10/8
    5. 蜂窝为默认路由，LAN下PC访问外网
       预期：PC可以正常上网（可选，需要物理环境）
    """

    # 添加分类信息属性
    category = "功能用例/网络/接口/蜂窝网络"
    is_regression = True  # 标记为回归测试用例

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "SIM1 IPv4子网掩码设置255.0.0.0"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 从config中获取router_client
        self.router_client = self.create_router_client(config.router_config)

        # 测试参数
        self.target_netmask = "255.0.0.0"
        self.expected_at_command = f'AT+QCFG="netmaskset",1,"{self.target_netmask}"'

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
            step1_result = self._step1_set_netmask()
            self.step_results.append(("步骤1：设置子网掩码并应用", step1_result))
            if not step1_result:
                all_passed = False
                print("❌ 步骤1失败，终止测试")
                return False

            # 步骤1后置验证：查看日志中的reload信息
            print("\n步骤1后置验证：查看蜂窝日志中的reload信息")
            reload_result = self._verify_reload_in_log()
            if reload_result:
                print("✅ 预期1（后置）：蜂窝reload，重新驻网拨号上 - 验证通过")
            else:
                print("⚠️ 预期1（后置）：未找到reload日志，可能正在reload中")

            # 等待蜂窝重新注网（使用用户设置的超时时间）
            wait_time = min(self.timeout, 120)  # 最多等待120秒或用户设置的超时时间
            print(f"\n等待{wait_time}秒，让蜂窝重新注网...")
            time.sleep(wait_time)

            # 步骤2：查看蜂窝日志，验证AT指令
            step2_result = self._step2_verify_at_command_in_log()
            self.step_results.append(("步骤2：验证日志中AT指令", step2_result))
            if not step2_result:
                all_passed = False

            # 步骤3：执行ifconfig，验证cellular0掩码
            step3_result = self._step3_verify_ifconfig()
            self.step_results.append(("步骤3：验证ifconfig掩码", step3_result))
            if not step3_result:
                all_passed = False

            # 步骤4：查看网页状态-蜂窝，验证显示
            step4_result = self._step4_verify_web_page()
            self.step_results.append(("步骤4：验证网页显示", step4_result))
            if not step4_result:
                all_passed = False

            # 步骤5：PC访问外网测试
            step5_result = self._step5_test_pc_internet()
            self.step_results.append(("步骤5：PC访问外网测试", step5_result))
            if not step5_result:
                all_passed = False

            # 打印汇总结果
            self._print_summary()

            return all_passed

        except Exception as e:
            print(f"ERROR - {self.__class__.__name__}: ❌ 测试执行失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise

    def _step1_set_netmask(self):
        """步骤1：设置蜂窝SIM1的IPv4子网掩码为255.0.0.0，保存并应用"""
        print(f"\n{'='*70}")
        print("步骤1：设置蜂窝SIM1的IPv4子网掩码为255.0.0.0，保存并应用")
        print(f"{'='*70}")
        print(f"预期1：蜂窝reload，重新驻网拨号上")

        try:
            # 调用RouterClient的方法设置子网掩码
            result = self.router_client.set_cellular_netmask(self.target_netmask)

            if result:
                print(f"✅ 子网掩码设置并应用成功")
                return True
            else:
                print(f"❌ 子网掩码设置失败")
                return False

        except Exception as e:
            print(f"❌ 步骤1执行失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _verify_reload_in_log(self):
        """验证日志中的reload信息"""
        try:
            router_ip = self.router_client.router_ip

            # 设置重试参数
            max_retry_time = 30  # 最大重试30秒
            retry_interval = 3
            start_time = time.time()
            attempt = 0

            while time.time() - start_time < max_retry_time:
                attempt += 1
                elapsed_time = int(time.time() - start_time)
                print(f"第{attempt}次尝试查找reload日志 (已等待{elapsed_time}秒)...")

                # SSH连接
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    ssh.connect(router_ip, username=self.SSH_ROOT_USERNAME, password=self.SSH_ROOT_PASSWORD, timeout=10)

                    # 获取最近的日志（最后100行）
                    stdin, stdout, stderr = ssh.exec_command("tail -100 /etc/urlog/cellular.log")
                    log_content = stdout.read().decode('utf-8')
                    error = stderr.read().decode('utf-8')

                    if error:
                        print(f"SSH命令执行错误: {error}")
                        ssh.close()
                        time.sleep(retry_interval)
                        continue

                    # 查找reload关键字
                    if 'reload' in log_content.lower():
                        print(f"✅ 在日志中找到reload信息")
                        # 打印相关日志行
                        for line in log_content.split('\n'):
                            if 'reload' in line.lower():
                                print(f"  日志: {line}")
                        ssh.close()
                        return True

                except Exception as e:
                    print(f"SSH连接失败: {str(e)}")
                finally:
                    try:
                        ssh.close()
                    except:
                        pass

                time.sleep(retry_interval)

            return False

        except Exception as e:
            print(f"验证reload日志失败: {str(e)}")
            return False

    def _step2_verify_at_command_in_log(self):
        """步骤2：查看蜂窝日志，验证AT指令"""
        print(f"\n{'='*70}")
        print("步骤2：查看蜂窝日志：/etc/urlog/cellular.log")
        print(f"{'='*70}")
        print(f"预期2：日志中有发送AT指令：{self.expected_at_command}")

        try:
            router_ip = self.router_client.router_ip
            search_pattern = self.expected_at_command.lower()

            # 设置重试参数（使用用户设置的超时时间）
            max_retry_time = min(self.timeout // 2, 60)  # 最多重试超时时间的一半或60秒
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

                    # 查找AT命令
                    if search_pattern in log_content.lower():
                        print(f"✅ 预期2：成功在日志中找到AT指令")
                        # 打印相关日志行
                        for line in log_content.split('\n'):
                            if search_pattern in line.lower():
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
            print(f"❌ 预期2：在{max_retry_time}秒内未找到AT指令")
            return False

        except Exception as e:
            print(f"❌ 步骤2执行失败: {str(e)}")
            return False

    def _step3_verify_ifconfig(self):
        """步骤3：执行ifconfig，验证cellular0掩码"""
        print(f"\n{'='*70}")
        print("步骤3：进入设备后台，执行ifconfig")
        print(f"{'='*70}")
        print(f"预期3：蜂窝接口cellular0的掩码为{self.target_netmask}")

        try:
            router_ip = self.router_client.router_ip

            # 设置重试参数（等待设备获取IP地址）
            max_retry_time = min(self.timeout, 180)  # 最多等待超时时间或180秒
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
                    # 格式示例：inet addr:10.103.107.83  Bcast:10.255.255.255  Mask:255.0.0.0
                    mask_match = re.search(r'Mask:(\d+\.\d+\.\d+\.\d+)', ifconfig_output)

                    if mask_match:
                        actual_mask = mask_match.group(1)
                        print(f"实际掩码: {actual_mask}")

                        if actual_mask == self.target_netmask:
                            print(f"✅ 预期3：cellular0的掩码为{self.target_netmask} - 验证通过")
                            return True
                        else:
                            print(f"❌ 预期3：掩码不匹配，预期{self.target_netmask}，实际{actual_mask}")
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
            print(f"❌ 预期3：在{max_retry_time}秒内未能验证掩码")
            return False

        except Exception as e:
            print(f"❌ 步骤3执行失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _step4_verify_web_page(self):
        """步骤4：查看网页状态-蜂窝，验证显示"""
        print(f"\n{'='*70}")
        print('步骤4：检查网页IP地址显示')
        print(f"{'='*70}")
        print(f"预期4：所有APN IPV4地址显示的掩码为8，如192.168.10.10/8")

        try:
            # 额外等待5秒，确保设备IP已完全稳定并同步到Web界面
            print("\n等待5秒，确保Web界面IP地址已更新...")
            time.sleep(5)

            all_checks_passed = True

            # 检查1：路由器登录首页的 qwert_ip
            print("\n检查1：路由器登录首页 IP 地址显示")
            self.router_client.driver.get(f"http://{self.router_client.router_ip}")
            self.router_client.driver.refresh()
            time.sleep(3)

            try:
                from selenium.webdriver.common.by import By
                ip_element_home = self.router_client.driver.find_element(By.XPATH, '//*[@id="qwert_ip"]')
                ip_value_home = ip_element_home.text.strip()
                print(f"  首页 IP 地址: {ip_value_home}")

                if '/8' in ip_value_home:
                    print(f"  ✅ 首页 IP 地址显示掩码为 /8")
                else:
                    print(f"  ❌ 首页 IP 地址未显示掩码为 /8")
                    all_checks_passed = False
            except Exception as e:
                print(f"  ❌ 无法读取首页 IP 地址: {str(e)}")
                all_checks_passed = False

            # 检查2：状态-蜂窝页面的 1_ip
            print("\n检查2：状态-蜂窝页面 IP 地址显示")
            self.router_client.driver.get(f"http://{self.router_client.router_ip}/#status/cellular")
            self.router_client.driver.refresh()
            time.sleep(3)

            try:
                from selenium.webdriver.common.by import By
                ip_element_cellular = self.router_client.driver.find_element(By.XPATH, '//*[@id="1_ip"]')
                ip_value_cellular = ip_element_cellular.text.strip()
                print(f"  蜂窝状态页 IP 地址: {ip_value_cellular}")

                if '/8' in ip_value_cellular:
                    print(f"  ✅ 蜂窝状态页 IP 地址显示掩码为 /8")
                else:
                    print(f"  ❌ 蜂窝状态页 IP 地址未显示掩码为 /8")
                    all_checks_passed = False
            except Exception as e:
                print(f"  ❌ 无法读取蜂窝状态页 IP 地址: {str(e)}")
                all_checks_passed = False

            if all_checks_passed:
                print(f"\n✅ 预期4：所有页面 IP 地址都显示掩码为 /8 - 验证通过")
                return True
            else:
                print(f"\n❌ 预期4：部分页面 IP 地址未显示掩码为 /8 - 验证失败")
                return False

        except Exception as e:
            print(f"❌ 步骤4执行失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _step5_test_pc_internet(self):
        """步骤5：配置PC网卡并测试上网"""
        print(f"\n{'='*70}")
        print("步骤5：蜂窝为默认路由，LAN下PC访问外网")
        print(f"{'='*70}")
        print("预期5：PC可以正常上网")

        try:
            from utils.network_utils import network_utils

            # 使用 network_utils 的一站式方法检查外网连通性
            result = network_utils.check_pc_internet_via_adapter(adapter_name="TEST", timeout=30)

            if result:
                print(f"✅ 预期5：PC可以正常上网 - 验证通过")
            else:
                print(f"❌ 预期5：PC无法正常上网 - 验证失败")

            return result

        except Exception as e:
            print(f"❌ 步骤5执行失败: {str(e)}")
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
        print(f"INFO - {self.__class__.__name__}: 子网掩码测试完成")

        # 恢复网卡配置
        try:
            from utils.network_utils import network_utils
            print("\n恢复网卡TEST配置...")
            network_utils.restore_adapter_auto_config(adapter_name="TEST")
        except Exception as e:
            print(f"⚠️  恢复网卡配置时出错: {str(e)}")

        # 可选：恢复默认子网掩码（如需要）
        # print("恢复默认子网掩码...")
        # self.router_client.set_cellular_netmask("255.255.255.0")

        # 关闭浏览器
        if hasattr(self.router_client, 'close'):
            self.router_client.close()
