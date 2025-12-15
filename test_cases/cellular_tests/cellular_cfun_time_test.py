from test_cases.base_test import BaseTest
import time
import paramiko
import re
from datetime import datetime, timedelta


class CellularCfunTimeTest(BaseTest):
    """蜂窝cfun到拨号上的时间测试

    测试项：功能用例/网络/接口/蜂窝网络
    测试点：蜂窝cfun到拨号上的时间

    前置条件：
    无特殊前置条件

    测试步骤：
    1. SSH进入设备后台，分别执行如下命令
       vtysh（如果返回ROUTER>代表成功）
       然后输入en返回ROUTER#
       然后输入con t返回ROUTER(config)#
       cellular reload force
       预期：蜂窝开始重拨，记录运行reload，到出现AT+CFUN=0的时间
    2. 查看蜂窝日志：/etc/urlog/cellular.log（网关在system.log）
       预期：记录AT+CFUN=0到SIM1 is up的时间，驻网时间不可超过2min
    """

    # 添加分类信息属性
    category = "功能用例/网络/接口/蜂窝网络"
    is_regression = True  # 标记为回归测试用例

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "蜂窝cfun到拨号上的时间"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 此测试用例不需要router_client（不需要Web操作）
        self.router_ip = config.router_config.router_ip

        # 测试参数
        self.max_network_registration_time = 120  # 最大驻网时间：2分钟（120秒）

        # 从config获取超时时间
        self.timeout = config.timeout if hasattr(config, 'timeout') else 300
        print(f"测试超时设置: {self.timeout}秒")

        # 存储各步骤验证结果和时间记录
        self.step_results = []
        self.time_measurements = {}

    def setup(self):
        """测试前置条件"""
        print(f"INFO - {self.__class__.__name__}: 前置条件检查")

        # 虽然不需要Web登录，但需要验证SSH连通性
        print("前置条件: 检查SSH连通性...")
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.router_ip, username=self.SSH_ROOT_USERNAME, password=self.SSH_ROOT_PASSWORD, timeout=10)
            ssh.close()
            print("✅ SSH连接成功")
        except Exception as e:
            raise Exception(f"SSH连接失败: {str(e)}")

        print("✅ 前置条件：无特殊要求（此用例不需要Web登录）")

    def execute(self):
        """执行测试"""
        try:
            print(f"INFO - {self.__class__.__name__}: 开始执行测试")
            print(f"\n{'='*70}")
            print(f"测试用例：{self.test_name}")
            print(f"超时设置：{self.timeout}秒")
            print(f"{'='*70}\n")

            all_passed = True

            # 步骤1：SSH执行cellular reload force并记录时间
            step1_result = self._step1_cellular_reload()
            self.step_results.append(("步骤1：执行cellular reload force", step1_result))
            if not step1_result:
                all_passed = False
                print("❌ 步骤1失败，终止测试")
                return False

            # 步骤2：查看日志并计算时间
            step2_result = self._step2_verify_cfun_time()
            self.step_results.append(("步骤2：验证CFUN时间和驻网时间", step2_result))
            if not step2_result:
                all_passed = False

            # 打印时间测量结果
            self._print_time_measurements()

            # 打印汇总结果
            self._print_summary()

            return all_passed

        except Exception as e:
            print(f"ERROR - {self.__class__.__name__}: ❌ 测试执行失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise

    def _step1_cellular_reload(self):
        """步骤1：SSH执行cellular reload force命令"""
        print(f"\n{'='*70}")
        print("步骤1：SSH进入设备后台，执行cellular reload force")
        print(f"{'='*70}")
        print("预期1：蜂窝开始重拨，记录运行reload到出现AT+CFUN=0的时间")

        try:
            router_ip = self.router_ip

            # 建立SSH连接
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            print(f"正在连接到路由器 {router_ip}...")
            ssh.connect(router_ip, username=self.SSH_ROOT_USERNAME, password=self.SSH_ROOT_PASSWORD, timeout=10)
            print("✅ SSH连接成功")

            # 获取shell
            print("创建交互式shell...")
            shell = ssh.invoke_shell()
            time.sleep(1)

            # 清空初始输出
            if shell.recv_ready():
                shell.recv(4096)

            # 执行vtysh
            print("执行命令: vtysh")
            shell.send('vtysh\n')
            time.sleep(1)
            output = shell.recv(4096).decode('utf-8', errors='ignore')
            print(f"vtysh输出:\n{output}")

            if 'ROUTER>' not in output:
                print("⚠️ 未看到ROUTER>提示符，但继续执行")

            # 执行en
            print("执行命令: en")
            shell.send('en\n')
            time.sleep(1)
            output = shell.recv(4096).decode('utf-8', errors='ignore')
            print(f"en输出:\n{output}")

            if 'ROUTER#' not in output:
                print("⚠️ 未看到ROUTER#提示符，但继续执行")

            # 执行con t (configure terminal)
            print("执行命令: con t")
            shell.send('con t\n')
            time.sleep(1)
            output = shell.recv(4096).decode('utf-8', errors='ignore')
            print(f"con t输出:\n{output}")

            if 'ROUTER(config)#' not in output:
                print("⚠️ 未看到ROUTER(config)#提示符，但继续执行")

            # 记录reload开始时间
            reload_start_time = datetime.now()
            self.time_measurements['reload_start'] = reload_start_time
            print(f"\n记录reload开始时间: {reload_start_time.strftime('%H:%M:%S.%f')[:-3]}")

            # 执行cellular reload force
            print("执行命令: cellular reload force")
            shell.send('cellular reload force\n')
            time.sleep(2)
            output = shell.recv(4096).decode('utf-8', errors='ignore')
            print(f"cellular reload force输出:\n{output}")

            # 退出shell
            print("退出vtysh...")
            shell.send('exit\n')
            time.sleep(0.5)
            shell.send('exit\n')
            time.sleep(0.5)
            shell.send('exit\n')

            shell.close()
            ssh.close()

            print(f"✅ cellular reload force命令执行成功")
            print(f"✅ reload开始时间已记录: {reload_start_time.strftime('%H:%M:%S.%f')[:-3]}")

            return True

        except Exception as e:
            print(f"❌ 步骤1执行失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            try:
                ssh.close()
            except:
                pass
            return False

    def _step2_verify_cfun_time(self):
        """步骤2：查看日志并验证CFUN时间"""
        print(f"\n{'='*70}")
        print("步骤2：查看蜂窝日志，计算时间")
        print(f"{'='*70}")
        print("预期2：记录AT+CFUN=0到SIM1 is up的时间，驻网时间不可超过2min")

        try:
            router_ip = self.router_ip
            reload_start_time = self.time_measurements.get('reload_start')

            if not reload_start_time:
                print("❌ 未找到reload开始时间记录")
                return False

            # 等待一段时间让日志生成
            print("\n等待10秒，让蜂窝开始reload...")
            time.sleep(10)

            # 设置重试参数，查找CFUN和SIM up日志
            max_retry_time = min(self.timeout, 180)  # 最多重试3分钟
            retry_interval = 5
            start_time = time.time()
            attempt = 0

            cfun_time = None
            sim_up_time = None

            while time.time() - start_time < max_retry_time:
                attempt += 1
                elapsed_time = int(time.time() - start_time)
                print(f"\n第{attempt}次尝试查找日志 (已等待{elapsed_time}秒)...")

                # SSH连接
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    ssh.connect(router_ip, username=self.SSH_ROOT_USERNAME, password=self.SSH_ROOT_PASSWORD, timeout=10)

                    # 获取cellular.log日志（读取最新的500行）
                    stdin, stdout, stderr = ssh.exec_command("tail -500 /etc/urlog/cellular.log")
                    log_content = stdout.read().decode('utf-8', errors='ignore')

                    ssh.close()

                    # 解析日志，查找reload后的CFUN和SIM up时间
                    cfun_time, sim_up_time = self._parse_log_times(log_content, reload_start_time)

                    if cfun_time and sim_up_time:
                        print("\n✅ 成功找到CFUN和SIM up时间")
                        break
                    else:
                        if not cfun_time:
                            print(f"⚠️ 第{attempt}次尝试：未找到AT+CFUN=0日志（reload后）")
                        if not sim_up_time:
                            print(f"⚠️ 第{attempt}次尝试：未找到SIM1 is up日志（reload后）")

                        # 如果还没超时，继续重试
                        if time.time() - start_time < max_retry_time:
                            print(f"{retry_interval}秒后重试...")
                            time.sleep(retry_interval)
                        continue

                except Exception as e:
                    print(f"❌ SSH连接失败: {str(e)}")
                    try:
                        ssh.close()
                    except:
                        pass

                    # 如果还没超时，继续重试
                    if time.time() - start_time < max_retry_time:
                        time.sleep(retry_interval)
                    continue

            # 验证是否找到了所需的时间点
            if not cfun_time:
                print(f"\n❌ 在{max_retry_time}秒内未找到AT+CFUN=0日志（reload之后的）")
                print("提示：请检查日志格式和时间戳是否正确")
                return False

            if not sim_up_time:
                print(f"\n❌ 在{max_retry_time}秒内未找到SIM1 is up日志（reload之后的）")
                print("提示：请检查日志格式和时间戳是否正确")
                return False

            # 计算时间差
            reload_to_cfun = (cfun_time - reload_start_time).total_seconds()
            cfun_to_sim_up = (sim_up_time - cfun_time).total_seconds()

            # 记录时间测量结果
            self.time_measurements['cfun_time'] = cfun_time
            self.time_measurements['sim_up_time'] = sim_up_time
            self.time_measurements['reload_to_cfun_seconds'] = reload_to_cfun
            self.time_measurements['cfun_to_sim_up_seconds'] = cfun_to_sim_up

            # 打印时间测量结果
            print(f"\n{'='*70}")
            print("时间测量结果：")
            print(f"{'='*70}")
            print(f"reload开始时间:     {reload_start_time.strftime('%H:%M:%S.%f')[:-3]}")
            print(f"AT+CFUN=0时间:       {cfun_time.strftime('%H:%M:%S.%f')[:-3]}")
            print(f"SIM1 is up时间:      {sim_up_time.strftime('%H:%M:%S.%f')[:-3]}")
            print(f"\nreload到CFUN时间:    {reload_to_cfun:.2f} 秒")
            print(f"CFUN到SIM up时间:    {cfun_to_sim_up:.2f} 秒 (驻网时间)")
            print(f"{'='*70}")

            # 验证预期1：reload到CFUN的时间（记录即可，无硬性要求）
            print(f"\n✅ 预期1：已记录reload到AT+CFUN=0的时间 = {reload_to_cfun:.2f}秒")

            # 验证预期2：驻网时间不可超过2分钟
            if cfun_to_sim_up <= self.max_network_registration_time:
                print(f"✅ 预期2：驻网时间 {cfun_to_sim_up:.2f}秒 ≤ {self.max_network_registration_time}秒 - 验证通过")
                return True
            else:
                print(f"❌ 预期2：驻网时间 {cfun_to_sim_up:.2f}秒 > {self.max_network_registration_time}秒 - 验证失败")
                return False

        except Exception as e:
            print(f"❌ 步骤2执行失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _parse_log_times(self, log_content, reload_start_time):
        """解析日志，查找CFUN和SIM up的时间

        Args:
            log_content: 日志内容
            reload_start_time: reload开始时间

        Returns:
            tuple: (cfun_time, sim_up_time) 或 (None, None)
        """
        try:
            cfun_time = None
            sim_up_time = None

            # 日志时间格式示例：[2025-11-19 17:45:18.483]
            log_time_pattern = r'\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\]'

            # 按行处理日志
            lines = log_content.split('\n')
            print(f"日志解析：共读取 {len(lines)} 行日志")
            print(f"查找范围：reload开始时间 {reload_start_time.strftime('%H:%M:%S.%f')[:-3]} 之后的日志")

            lines_after_reload = 0
            lines_with_cfun = 0
            lines_with_sim_up = 0

            for line in lines:
                # 查找时间戳
                time_match = re.search(log_time_pattern, line)
                if not time_match:
                    continue

                log_time_str = time_match.group(1)
                try:
                    log_time = datetime.strptime(log_time_str, '%Y-%m-%d %H:%M:%S.%f')
                except:
                    continue

                # 只处理reload之后的日志
                if log_time < reload_start_time:
                    continue

                lines_after_reload += 1

                # 查找AT+CFUN=0
                if 'AT+CFUN=0' in line:
                    lines_with_cfun += 1
                    if not cfun_time:
                        cfun_time = log_time
                        print(f"✅ 找到AT+CFUN=0日志: {log_time_str}")
                        print(f"   日志内容: {line.strip()}")

                # 查找SIM1 is up
                if 'SIM1 is up' in line or 'SIM 1 is up' in line:
                    lines_with_sim_up += 1
                    if not sim_up_time:
                        sim_up_time = log_time
                        print(f"✅ 找到SIM1 is up日志: {log_time_str}")
                        print(f"   日志内容: {line.strip()}")

                # 如果两个时间都找到了，可以提前退出
                if cfun_time and sim_up_time:
                    break

            # 打印解析统计信息
            print(f"日志解析统计：reload后的日志行数 = {lines_after_reload}")
            print(f"日志解析统计：包含'AT+CFUN=0'的行数 = {lines_with_cfun}")
            print(f"日志解析统计：包含'SIM1 is up'的行数 = {lines_with_sim_up}")

            if not cfun_time:
                print(f"⚠️ 未找到AT+CFUN=0日志（在reload时间 {reload_start_time.strftime('%H:%M:%S.%f')[:-3]} 之后）")
            if not sim_up_time:
                print(f"⚠️ 未找到SIM1 is up日志（在reload时间 {reload_start_time.strftime('%H:%M:%S.%f')[:-3]} 之后）")

            return cfun_time, sim_up_time

        except Exception as e:
            print(f"❌ 解析日志时间失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None, None

    def _print_time_measurements(self):
        """打印时间测量结果汇总"""
        print(f"\n{'='*70}")
        print("时间测量汇总")
        print(f"{'='*70}")

        if 'reload_start' in self.time_measurements:
            print(f"reload开始时间:     {self.time_measurements['reload_start'].strftime('%H:%M:%S.%f')[:-3]}")

        if 'cfun_time' in self.time_measurements:
            print(f"AT+CFUN=0时间:       {self.time_measurements['cfun_time'].strftime('%H:%M:%S.%f')[:-3]}")

        if 'sim_up_time' in self.time_measurements:
            print(f"SIM1 is up时间:      {self.time_measurements['sim_up_time'].strftime('%H:%M:%S.%f')[:-3]}")

        if 'reload_to_cfun_seconds' in self.time_measurements:
            print(f"\nreload到CFUN时间:    {self.time_measurements['reload_to_cfun_seconds']:.2f} 秒")

        if 'cfun_to_sim_up_seconds' in self.time_measurements:
            cfun_to_sim_up = self.time_measurements['cfun_to_sim_up_seconds']
            status = "✅ 通过" if cfun_to_sim_up <= self.max_network_registration_time else "❌ 超时"
            print(f"CFUN到SIM up时间:    {cfun_to_sim_up:.2f} 秒 (驻网时间) - {status}")
            print(f"最大允许驻网时间:    {self.max_network_registration_time} 秒")

        print(f"{'='*70}\n")

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
        print(f"INFO - {self.__class__.__name__}: CFUN时间测试完成")
        # 此测试用例不需要Web资源清理（只使用SSH）
