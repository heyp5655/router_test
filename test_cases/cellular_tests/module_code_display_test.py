from test_cases.base_test import BaseTest
import time
import paramiko
import re


class ModuleCodeDisplayTest(BaseTest):
    """模组代号显示测试

    测试项：功能用例/网络/接口/蜂窝网络
    测试点：模组代号显示

    前置条件：
    无特殊前置条件

    测试步骤：
    1. SSH进入设备后台，执行urtool -s -X{code}0011110写入代号
       输入密码XmLs@2013#0592
       执行urtool -g验证sonboardsn写入成功
       执行/etc/init.d/quagga restart重启服务
    2. 登录路由器首页，核对页面中//*[@id="qwert_model"]显示的内容后5位与代号一致

    测试说明：
    遍历所有模组代号，每个代号测试完成后继续下一个，直到全部遍历完成
    """

    # 添加分类信息属性
    category = "功能用例/网络/接口/蜂窝网络"
    is_regression = True  # 标记为回归测试用例

    # 所有需要测试的模组代号列表
    MODULE_CODES = [
        "500GL", "501EU", "502CN", "503CN", "504AE", "504NA", "505CN", "506CN", "507CN",
        "550AE", "551CN", "552CN", "554AE",
        "L00J0", "L00E0", "L00A0", "L00V0", "L00AU",
        "L01CN", "L01CE", "L04AU", "L04EU", "L04AF",
        "L02G", "L08AF", "L08EU", "L08AU",
        "L03AF", "L03A0", "L03V0", "L03AU", "L03EU",
        "L05AU", "L05EU", "L06CN", "L07CN", "L08GL", "L09NA",
        "L0ACN", "L90RI", "L0BEU", "L0CEU", "L0DEU", "L0EGL", "L0FEU", "L0GEU",
        "N01NB", "N00CN", "N02GL", "N03GL", "N04GL",
        "580CN", "570GL", "560GL", "540CN", "553AE",
        "U00E0", "U00A0", "U01E0", "U01A0", "U01G0",
        "L02E0", "L02A0", "L10EU", "L10NA", "L10SV", "L10AU",
        "L20C0", "L30G0"
    ]

    # urtool密码
    URTOOL_PASSWORD = "XmLs@2013#0592"

    def create_router_client(self, router_config):
        """创建路由器客户端"""
        try:
            from core.router_client import RouterClient
            print(f"✅ 成功从 core.router_client 导入 RouterClient")
            return RouterClient(router_config)
        except ImportError as e:
            print(f"❌ 无法从 core.router_client 导入: {e}")
            raise

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "模组代号显示"

    @property
    def description(self):
        """测试描述"""
        return "遍历所有模组代号，验证写入后页面显示是否正确"

    def setup(self):
        """测试准备"""
        # 获取路由器配置
        self.router_ip = self.config.router_config.router_ip

        print(f"\n{'='*70}")
        print(f"测试用例: {self.test_name}")
        print(f"测试分类: {self.category}")
        print(f"{'='*70}")
        print(f"路由器IP: {self.router_ip}")
        print(f"待测试代号数量: {len(self.MODULE_CODES)}")
        print(f"{'='*70}\n")

        # 初始化结果记录
        self.test_results = []
        self.passed_count = 0
        self.failed_count = 0

        # 创建router_client用于SSH检查
        self.router_client = self.create_router_client(self.config.router_config)

        # 检查并启用SSH（新版本固件默认关闭SSH）
        print("前置条件: 检查SSH启用状态...")
        if not self.router_client.ensure_ssh_enabled():
            raise Exception("SSH未启用且自动启用失败，无法继续测试")
        print("✅ SSH已就绪")

    def execute(self):
        """执行测试 - 遍历所有模组代号"""
        try:
            total = len(self.MODULE_CODES)

            for idx, code in enumerate(self.MODULE_CODES):
                print(f"\n{'='*70}")
                print(f"测试进度: {idx + 1}/{total}")
                print(f"当前测试代号: {code}")
                print(f"{'='*70}")

                # 执行单个代号的测试
                result = self._test_single_code(code)

                # 记录结果
                self.test_results.append({
                    'code': code,
                    'result': 'PASS' if result else 'FAIL'
                })

                if result:
                    self.passed_count += 1
                    print(f"代号 {code} 测试通过")
                else:
                    self.failed_count += 1
                    print(f"代号 {code} 测试失败")

                # 每个代号测试完成后短暂等待
                if idx < total - 1:
                    print(f"\n等待5秒后测试下一个代号...")
                    time.sleep(5)

            # 输出测试汇总
            print(f"\n{'='*70}")
            print(f"测试完成汇总")
            print(f"{'='*70}")
            print(f"总计测试: {total} 个代号")
            print(f"通过: {self.passed_count}")
            print(f"失败: {self.failed_count}")
            print(f"通过率: {self.passed_count/total*100:.1f}%")

            # 列出失败的代号
            failed_codes = [r['code'] for r in self.test_results if r['result'] == 'FAIL']
            if failed_codes:
                print(f"\n失败的代号列表:")
                for fc in failed_codes:
                    print(f"  - {fc}")

            # 判断整体结果
            if self.failed_count > 0:
                raise AssertionError(f"有 {self.failed_count} 个代号测试失败: {', '.join(failed_codes)}")

            return True

        except Exception as e:
            print(f"测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise

    def _test_single_code(self, code):
        """测试单个模组代号"""
        try:
            # 步骤1: SSH写入代号
            print(f"\n--- 步骤1: SSH写入代号 {code} ---")
            if not self._step1_write_code(code):
                print(f"步骤1失败: 写入代号 {code} 失败")
                return False

            # 等待服务重启完成
            print("等待30秒让服务重启完成...")
            time.sleep(30)

            # 步骤2: Web页面验证
            print(f"\n--- 步骤2: Web页面验证代号 {code} ---")
            if not self._step2_verify_web(code):
                print(f"步骤2失败: 页面验证代号 {code} 失败")
                return False

            return True

        except Exception as e:
            print(f"测试代号 {code} 时发生异常: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _step1_write_code(self, code):
        """步骤1: SSH写入模组代号"""
        ssh = None
        try:
            # 建立SSH连接 - 使用root用户
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            print(f"正在连接到路由器 {self.router_ip} (使用root用户)...")
            ssh.connect(
                self.router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )
            print("SSH连接成功")

            # 直接执行urtool命令
            write_cmd = f"urtool -s -X{code}0011110"
            print(f"执行命令: {write_cmd}")

            # 创建channel并执行命令
            channel = ssh.get_transport().open_session()
            channel.get_pty()  # 获取伪终端以便处理交互式命令
            channel.exec_command(write_cmd)

            # 等待密码提示
            output = ""
            password_received = False
            for i in range(30):
                time.sleep(0.3)
                if channel.recv_ready():
                    chunk = channel.recv(4096).decode('utf-8', errors='ignore')
                    output += chunk
                    if chunk.strip():
                        print(f"收到[{i}]: {chunk.strip()}")
                if "Password:" in output or "password:" in output.lower():
                    password_received = True
                    break

            print(f"完整输出: {output}")

            if not password_received:
                print("未收到密码提示")
                print(f"完整输出内容: [{output}]")
                channel.close()
                ssh.close()
                return False

            # 输入密码
            print(f"输入密码...")
            channel.send(self.URTOOL_PASSWORD + '\n')
            time.sleep(3)

            # 读取写入结果
            output = ""
            for _ in range(10):
                if channel.recv_ready():
                    output += channel.recv(4096).decode('utf-8', errors='ignore')
                time.sleep(0.3)

            print(f"写入结果: {output}")

            # 检查是否写入成功
            if "Writing from" in output or "Unlocking" in output:
                print("写入命令执行成功")
            else:
                print("警告: 写入命令可能未成功执行")

            channel.close()

            # 执行urtool -g验证
            print("执行命令: urtool -g")
            stdin, stdout, stderr = ssh.exec_command("urtool -g")
            output = stdout.read().decode('utf-8', errors='ignore')
            print(f"urtool -g输出:\n{output}")

            # 验证sonboardsn是否包含代号
            expected_sn = f"{code}0011110"
            if expected_sn in output or code in output:
                print(f"sonboardsn验证成功，包含代号 {code}")
            else:
                print(f"警告: 未在输出中找到预期的sonboardsn: {expected_sn}")

            # 执行quagga restart
            print("执行命令: /etc/init.d/quagga restart")
            stdin, stdout, stderr = ssh.exec_command("/etc/init.d/quagga restart")
            output = stdout.read().decode('utf-8', errors='ignore')
            print(f"quagga restart输出:\n{output}")

            if "done" in output.lower() or "starting" in output.lower():
                print("quagga重启命令执行成功")
            else:
                print("警告: quagga重启输出异常")

            ssh.close()
            return True

        except Exception as e:
            print(f"步骤1执行失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
            return False

    def _step2_verify_web(self, code):
        """步骤2: Web页面验证模组代号"""
        try:
            # 登录Web界面
            print("登录路由器Web界面...")
            if not self.router_client.login_web():
                print("Web登录失败")
                return False

            print("Web登录成功")

            # 等待页面加载
            time.sleep(3)

            # 获取型号显示元素
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            driver = self.router_client.driver

            # 导航到首页（如果需要）
            print("导航到首页...")
            driver.get(f"http://{self.router_ip}")
            time.sleep(3)

            # 查找型号元素
            print("查找型号显示元素 //*[@id='qwert_model']...")
            try:
                wait = WebDriverWait(driver, 15)
                model_element = wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="qwert_model"]'))
                )
                model_text = model_element.text.strip()
                print(f"页面显示型号: {model_text}")

                # 获取后5位
                if len(model_text) >= 5:
                    last_5_chars = model_text[-5:]
                    print(f"型号后5位: {last_5_chars}")

                    # 验证是否与代号一致
                    # 代号可能是5位或更短，需要灵活匹配
                    code_to_match = code[-5:] if len(code) >= 5 else code

                    if last_5_chars == code_to_match or code in model_text:
                        print(f"验证成功: 页面显示后5位 '{last_5_chars}' 与代号 '{code}' 匹配")
                        return True
                    else:
                        print(f"验证失败: 页面显示后5位 '{last_5_chars}' 与代号 '{code}' 不匹配")
                        return False
                else:
                    print(f"型号文本长度不足5位: {model_text}")
                    # 尝试直接匹配
                    if code in model_text:
                        print(f"验证成功: 型号文本包含代号 {code}")
                        return True
                    return False

            except Exception as e:
                print(f"查找型号元素失败: {str(e)}")
                return False

        except Exception as e:
            print(f"步骤2执行失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        # 关闭浏览器
        try:
            if hasattr(self, 'router_client') and self.router_client:
                self.router_client.close()
                print("已关闭浏览器")
        except Exception as e:
            print(f"关闭浏览器时出错: {str(e)}")

        print("测试清理完成")
