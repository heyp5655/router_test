from test_cases.base_test import BaseTest
import time
import paramiko
import re
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PythonModuleCheckTest(BaseTest):
    """Python模块检查测试

    测试项：功能用例/APP/python
    测试点：Python3.0 SDK模块完整性检查

    测试步骤：
    1. 检查Python版本是否为3.9
    2. 检查SDK是否已安装，如未安装则自动安装
    3. SSH登录路由器
    4. 自动上传selftest.py脚本到路由器
    5. 执行selftest.py检查Python模块
    6. 解析输出结果，验证必须模块、可选模块、第三方模块是否正常

    预期：
    Python版本为3.9，所有MUST模块都OK，EXTRA模块中的关键库（paho.mqtt.client, pymodbus, serial等）都OK
    """

    # 添加分类信息属性
    category = "功能用例/APP/python"
    is_regression = True  # 标记为回归测试用例

    # SDK文件路径
    SDK_FILE_PATH = r"E:\GIT\ROUTER_TEST\config\pysdk-ur3x-5.0.2-u1.tar.gz"

    # selftest.py 脚本内容
    SELFTEST_SCRIPT = '''# selftest.py
import importlib, sys

# 必须库
must = [
    "json", "logging", "os", "sys", "time", "datetime",
    "subprocess", "shutil", "math", "re", "copy",
    "inspect", "struct", "codecs"
]

# 可选的 C 扩展
opt = [
    "zlib", "_ssl", "_sqlite3", "readline", "_ctypes",
    "pyexpat", "select", "_io", "_struct", "_datetime"
]

# 第三方和标准额外库
extra = [
    "certifi", "future", "meld3", "nanomsg", "setuptools", "pkg_resources",
    "paho.mqtt.client", "pymodbus", "serial", "six",
    "strict_rfc3339", "supervisor",
]

def get_version(mod):
    """通用获取版本号的函数"""
    for attr in ("__version__", "VERSION", "version"):
        if hasattr(mod, attr):
            v = getattr(mod, attr)
            if isinstance(v, (str, bytes)):
                return v
            elif isinstance(v, (tuple, list)):
                return ".".join(map(str, v))
    return "unknown"

def check(lst, title):
    ok, missing = [], []
    for m in lst:
        try:
            mod = importlib.import_module(m)
            ver = get_version(mod)
            ok.append((m, ver))
        except Exception as e:
            missing.append(f"{m} -> {e.__class__.__name__}: {e}")
    print(f"\\n[{title}]")
    if ok:
        for m, ver in ok:
            print(f"  OK: {m:25s} (version: {ver})")
    if missing:
        for m in missing:
            print(f"  MISSING: {m}")

print("sys.path=", *sys.path, sep="\\n")
check(must, "MUST")
check(opt, "OPTIONAL")
check(extra, "EXTRA (from doc)")
'''

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "python3.9核心库和拓展库自动化验证"

    @property
    def description(self):
        """测试描述"""
        return "自动上传selftest.py脚本到路由器，检查Python3.0 SDK模块完整性"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 获取路由器配置
        self.router_ip = self.config.router_config.router_ip

        # 从配置中获取串口配置
        self.serial_port = self.config.router_config.serial_port
        self.serial_baudrate = self.config.router_config.serial_baudrate

        # 串口连接对象
        self.serial_conn = None

        # 测试结果统计
        self.must_ok = []
        self.must_missing = []
        self.opt_ok = []
        self.opt_missing = []
        self.extra_ok = []
        self.extra_missing = []

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

        # 前置1: 检查并安装SDK（必须先安装SDK才能有python3命令）
        print("前置条件1: 检查SDK安装状态...")
        if not self._ensure_sdk_installed():
            raise Exception("SDK安装失败")
        print("✅ SDK已就绪\n")

        # 前置2: 检查Python版本
        print("前置条件2: 检查Python版本...")
        if not self._check_python_version():
            raise Exception("Python版本检查失败")
        print("✅ Python版本检查通过\n")

    def execute(self):
        """执行测试"""
        try:
            print(f"\n{'='*70}")
            print(f"开始执行Python模块检查测试")
            print(f"{'='*70}\n")

            # 步骤1: SSH上传脚本
            print("步骤1: SSH上传selftest.py脚本到路由器...")
            if not self._upload_script():
                raise Exception("上传脚本失败")
            print("✅ 脚本上传成功\n")

            # 步骤2: 执行脚本
            print("步骤2: 执行selftest.py...")
            output = self._execute_script()
            if output is None:
                raise Exception("执行脚本失败")
            print("✅ 脚本执行成功\n")

            # 步骤3: 解析结果
            print("步骤3: 解析测试结果...")
            if not self._parse_output(output):
                raise Exception("解析结果失败")
            print("✅ 结果解析成功\n")

            # 步骤4: 验证结果
            print("步骤4: 验证测试结果...")
            self._print_results()

            # 验证必须模块
            if self.must_missing:
                raise AssertionError(
                    f"必须模块缺失: {', '.join(self.must_missing)}"
                )

            # 验证关键的第三方模块
            critical_modules = ['paho.mqtt.client', 'pymodbus', 'serial']
            missing_critical = [m for m in critical_modules if m in self.extra_missing]
            if missing_critical:
                raise AssertionError(
                    f"关键第三方模块缺失: {', '.join(missing_critical)}"
                )

            print("✅ Python模块检查全部通过\n")
            return True

        except Exception as e:
            print(f"\n测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise

    def _check_python_version(self):
        """检查Python版本是否为3.9"""
        print(f"SSH连接到路由器 {self.router_ip}...")

        # 首先尝试SSH方式
        ssh = None
        try:
            # 建立SSH连接
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh.connect(
                self.router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )

            # 使用完整路径执行python3 --version，设置环境变量
            python_path = "/usr/python/bin/python3.9"
            lib_path = "/usr/python/lib"

            # 设置 LD_LIBRARY_PATH 环境变量
            command = f"export LD_LIBRARY_PATH={lib_path}:$LD_LIBRARY_PATH && {python_path} --version"
            print(f"执行命令: {command}")
            stdin, stdout, stderr = ssh.exec_command(command)

            # 读取输出
            version_output = stdout.read().decode('utf-8', errors='ignore').strip()
            error_output = stderr.read().decode('utf-8', errors='ignore').strip()

            # Python 3.x 可能将版本信息输出到stderr
            full_output = version_output or error_output

            print(f"Python版本输出: {full_output}")

            # 检查输出中是否有错误信息
            if 'Error' in full_output or 'No such file' in full_output:
                print(f"❌ SSH执行Python出错: {full_output}")
                ssh.close()
                # SSH失败，尝试串口
                print("⚠️ SSH方式失败，尝试使用串口...")
                return self._check_python_version_via_serial()

            # 检查版本是否为3.9.x格式（精确匹配版本号格式）
            if 'Python 3.9' in full_output and not 'Error' in full_output:
                print(f"✅ Python版本正确: {full_output}")
                ssh.close()
                return True
            else:
                print(f"❌ Python版本不正确，期望Python 3.9.x，实际: {full_output}")
                ssh.close()
                # 尝试串口
                print("⚠️ SSH方式失败，尝试使用串口...")
                return self._check_python_version_via_serial()

        except Exception as e:
            print(f"SSH检查Python版本失败: {str(e)}")
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
            # SSH失败，尝试串口
            print("⚠️ SSH方式失败，尝试使用串口...")
            return self._check_python_version_via_serial()

    def _ensure_sdk_installed(self):
        """确保SDK已安装，如未安装则自动安装"""
        try:
            # 检查SDK是否已安装
            if self._check_sdk_installed():
                print("SDK已安装")
                return True

            # 未安装，需要安装
            print("SDK未安装，开始自动安装...")
            return self._install_sdk_via_web()

        except Exception as e:
            print(f"确保SDK安装失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _check_sdk_installed(self):
        """检查SDK是否已安装"""
        try:
            # 登录Web界面
            print("登录路由器Web界面...")
            if not self.router_client.login_web():
                print("Web登录失败")
                return False

            # 导航到Python状态页面
            print("导航到Python状态页面...")
            if not self._navigate_to_python_status():
                print("导航失败")
                return False

            # 检查状态元素
            driver = self.router_client.driver
            status_elem1_xpath = '//*[@id="status_python"]/div[2]/div[3]/div[2]'
            status_elem2_xpath = '//*[@id="status_python"]/div[2]/div[4]/div[2]'

            time.sleep(2)  # 等待页面加载

            try:
                elem1 = driver.find_element(By.XPATH, status_elem1_xpath)
                elem2 = driver.find_element(By.XPATH, status_elem2_xpath)

                # 如果元素有内容，说明已安装
                if elem1.text.strip() and elem2.text.strip():
                    print(f"SDK已安装，版本信息: {elem1.text}, {elem2.text}")
                    return True
                else:
                    print("SDK未安装（状态元素为空）")
                    return False

            except:
                print("SDK未安装（状态元素不存在）")
                return False

        except Exception as e:
            print(f"检查SDK安装状态失败: {str(e)}")
            return False

    def _install_sdk_via_web(self):
        """通过Web界面安装SDK"""
        try:
            driver = self.router_client.driver
            wait = WebDriverWait(driver, 10)

            print("开始通过Web界面安装SDK...")

            # 确保在Python状态页面
            if not self._navigate_to_python_status():
                print("导航到Python状态页面失败")
                return False

            time.sleep(2)

            # 查找文件上传输入框
            print("查找文件上传输入框...")
            upload_input = None

            locators = [
                ("ID: 0_sdkfile_url", By.XPATH, '//*[@id="0_sdkfile_url"]'),
                ("type=file", By.XPATH, '//input[@type="file"]'),
                ("name包含sdk", By.XPATH, '//input[contains(@name, "sdk") and @type="file"]'),
            ]

            for desc, by, xpath in locators:
                try:
                    print(f"尝试定位器: {desc}")
                    elem = driver.find_element(by, xpath)
                    elem_type = elem.get_attribute('type')
                    if elem_type == 'file':
                        print(f"✅ 找到文件上传框: {desc}")
                        driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                        time.sleep(0.5)
                        upload_input = elem
                        break
                except Exception as e:
                    print(f"✗ {desc} 定位失败: {str(e)}")
                    continue

            if not upload_input:
                print("❌ 无法找到文件上传输入框")
                return False

            # 上传文件
            print(f"上传SDK文件: {self.SDK_FILE_PATH}")
            upload_input.send_keys(self.SDK_FILE_PATH)
            print("✅ send_keys执行完成")

            time.sleep(2)

            # 验证文件是否上传
            files_length = driver.execute_script("return arguments[0].files.length;", upload_input)
            print(f"文件对象数量: {files_length}")

            if files_length == 0:
                print("❌ 文件选择失败")
                return False

            file_name = driver.execute_script("return arguments[0].files[0].name;", upload_input)
            print(f"✅ 文件已选择: {file_name}")

            # 点击安装按钮
            print("查找并点击安装按钮...")
            install_btn_xpath = '//*[@id="0_sdkfile_import"]'
            install_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, install_btn_xpath))
            )
            print(f"找到安装按钮，文本: {install_btn.text}")
            install_btn.click()
            print("✅ 已点击安装按钮，等待安装完成...")

            # 等待安装完成
            status_elem1_xpath = '//*[@id="status_python"]/div[2]/div[3]/div[2]'
            status_elem2_xpath = '//*[@id="status_python"]/div[2]/div[4]/div[2]'

            max_wait = 300
            elapsed = 0
            print("等待安装完成（最多300秒）...")

            while elapsed < max_wait:
                try:
                    elem1 = driver.find_element(By.XPATH, status_elem1_xpath)
                    elem2 = driver.find_element(By.XPATH, status_elem2_xpath)

                    elem1_text = elem1.text.strip()
                    elem2_text = elem2.text.strip()

                    if elem1_text and elem2_text:
                        print(f"✅ SDK安装完成！")
                        print(f"   状态信息: {elem1_text}, {elem2_text}")
                        return True

                    if elapsed % 10 == 0 and elapsed > 0:
                        print(f"等待中... ({elapsed}秒)")

                except:
                    pass

                time.sleep(1)
                elapsed += 1

            print("❌ 安装超时")
            return False

        except Exception as e:
            print(f"通过Web安装SDK失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _navigate_to_python_status(self):
        """导航到Python SDK状态页面"""
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
                return True

            except Exception as e:
                print(f"❌ 页面跳转失败: {str(e)}")
                return False

        except Exception as e:
            print(f"导航失败: {str(e)}")
            return False

    def _upload_script(self):
        """通过SSH上传脚本到路由器"""
        ssh = None
        try:
            # 建立SSH连接
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

            # 使用 cat << EOF 方式创建文件
            script_path = "/tmp/selftest.py"
            print(f"上传脚本到 {script_path}...")

            # 转义脚本内容中的特殊字符
            script_content = self.SELFTEST_SCRIPT.replace('\\', '\\\\').replace('$', '\\$').replace('`', '\\`')

            # 创建上传命令
            upload_cmd = f"cat > {script_path} << 'SELFTEST_EOF'\n{self.SELFTEST_SCRIPT}\nSELFTEST_EOF"

            print(f"执行上传命令...")
            stdin, stdout, stderr = ssh.exec_command(upload_cmd)

            # 等待命令执行完成
            exit_status = stdout.channel.recv_exit_status()
            stderr_output = stderr.read().decode('utf-8', errors='ignore')

            if exit_status != 0:
                print(f"上传失败，错误: {stderr_output}")
                ssh.close()
                return False

            # 验证文件是否创建成功
            print("验证文件是否创建成功...")
            stdin, stdout, stderr = ssh.exec_command(f"ls -l {script_path}")
            output = stdout.read().decode('utf-8', errors='ignore')

            if script_path in output:
                print(f"文件创建成功: {output.strip()}")
            else:
                print(f"文件创建失败")
                ssh.close()
                return False

            ssh.close()
            return True

        except Exception as e:
            print(f"上传脚本失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
            return False

    def _execute_script(self):
        """执行selftest.py脚本"""
        print(f"连接到路由器 {self.router_ip}...")

        # 首先尝试SSH方式
        ssh = None
        try:
            # 建立SSH连接
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh.connect(
                self.router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )

            # 执行脚本（使用完整路径和环境变量）
            script_path = "/tmp/selftest.py"
            python_path = "/usr/python/bin/python3.9"
            lib_path = "/usr/python/lib"

            # 设置 LD_LIBRARY_PATH 环境变量
            command = f"export LD_LIBRARY_PATH={lib_path}:$LD_LIBRARY_PATH && {python_path} {script_path}"
            print(f"执行命令: {command}")

            stdin, stdout, stderr = ssh.exec_command(command)

            # 读取输出
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')

            print("\n--- 脚本输出 ---")
            print(output)
            if error:
                print("\n--- 错误输出 ---")
                print(error)
            print("--- 输出结束 ---\n")

            ssh.close()

            # 检查是否有错误
            if error and ('Error' in error or 'error' in error.lower()):
                print(f"❌ SSH执行脚本时发生错误: {error}")
                # SSH失败，尝试串口
                print("⚠️ SSH方式失败，尝试使用串口...")
                return self._execute_script_via_serial()

            # 检查输出是否为空
            if not output or not output.strip():
                print(f"❌ SSH执行脚本没有输出")
                # 尝试串口
                print("⚠️ SSH方式失败，尝试使用串口...")
                return self._execute_script_via_serial()

            # 返回标准输出
            return output

        except Exception as e:
            print(f"SSH执行脚本失败: {str(e)}")
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
            # SSH失败，尝试串口
            print("⚠️ SSH方式失败，尝试使用串口...")
            return self._execute_script_via_serial()

    def _parse_output(self, output):
        """解析selftest.py的输出"""
        try:
            lines = output.split('\n')
            current_section = None

            for line in lines:
                line = line.strip()

                # 识别section
                if line.startswith('[MUST]'):
                    current_section = 'MUST'
                    continue
                elif line.startswith('[OPTIONAL]'):
                    current_section = 'OPTIONAL'
                    continue
                elif line.startswith('[EXTRA'):
                    current_section = 'EXTRA'
                    continue

                # 解析模块状态
                if current_section and line:
                    if line.startswith('OK:'):
                        # 解析 OK 行: "OK: json                       (version: 2.0.9)"
                        match = re.match(r'OK:\s+(\S+)', line)
                        if match:
                            module_name = match.group(1)
                            if current_section == 'MUST':
                                self.must_ok.append(module_name)
                            elif current_section == 'OPTIONAL':
                                self.opt_ok.append(module_name)
                            elif current_section == 'EXTRA':
                                self.extra_ok.append(module_name)

                    elif line.startswith('MISSING:'):
                        # 解析 MISSING 行: "MISSING: nanomsg -> ModuleNotFoundError: ..."
                        match = re.match(r'MISSING:\s+(\S+)', line)
                        if match:
                            module_name = match.group(1)
                            if current_section == 'MUST':
                                self.must_missing.append(module_name)
                            elif current_section == 'OPTIONAL':
                                self.opt_missing.append(module_name)
                            elif current_section == 'EXTRA':
                                self.extra_missing.append(module_name)

            # 检查是否有任何有效的解析结果
            total_items = (len(self.must_ok) + len(self.must_missing) +
                          len(self.opt_ok) + len(self.opt_missing) +
                          len(self.extra_ok) + len(self.extra_missing))

            if total_items == 0:
                print("❌ 解析失败：没有找到任何模块检查结果")
                print("   这可能是因为脚本执行失败或输出格式不正确")
                return False

            return True

        except Exception as e:
            print(f"解析输出失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _print_results(self):
        """打印测试结果统计"""
        print(f"\n{'='*70}")
        print("Python模块检查结果统计")
        print(f"{'='*70}")

        print(f"\n【必须模块 MUST】")
        print(f"  ✅ OK: {len(self.must_ok)} 个")
        if self.must_ok:
            for m in self.must_ok:
                print(f"     - {m}")
        print(f"  ❌ MISSING: {len(self.must_missing)} 个")
        if self.must_missing:
            for m in self.must_missing:
                print(f"     - {m}")

        print(f"\n【可选模块 OPTIONAL】")
        print(f"  ✅ OK: {len(self.opt_ok)} 个")
        print(f"  ⚠️  MISSING: {len(self.opt_missing)} 个")

        print(f"\n【第三方模块 EXTRA】")
        print(f"  ✅ OK: {len(self.extra_ok)} 个")
        if self.extra_ok:
            for m in self.extra_ok:
                print(f"     - {m}")
        print(f"  ❌ MISSING: {len(self.extra_missing)} 个")
        if self.extra_missing:
            for m in self.extra_missing:
                print(f"     - {m}")

        print(f"\n{'='*70}")

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        # 清理路由器上的临时文件
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )

            print("删除临时脚本文件...")
            ssh.exec_command("rm -f /tmp/selftest.py")
            ssh.close()
            print("✅ 临时文件已删除")

        except Exception as e:
            print(f"清理临时文件时出错: {str(e)}")

        print("测试清理完成")

    # ===== 串口相关方法 =====

    def _init_serial_connection(self):
        """初始化串口连接"""
        try:
            import serial
            print(f"\n初始化串口连接 {self.serial_port}...")
            self.serial_conn = serial.Serial(
                port=self.serial_port,
                baudrate=self.serial_baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
            print("✅ 串口连接成功")

            # 登录串口
            self._serial_login()
            print("✅ 串口登录成功")
            return True

        except Exception as e:
            print(f"串口初始化失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _serial_login(self):
        """通过串口登录设备"""
        try:
            # 发送回车激活终端
            self.serial_conn.write(b'\n')
            time.sleep(0.5)

            # 读取当前输出
            output = self._read_serial_output(timeout=2)

            # 如果已经是登录状态，直接返回
            if 'root@' in output or '#' in output:
                print("  已经处于登录状态")
                return

            # 发送用户名
            self.serial_conn.write(b'root\n')
            time.sleep(0.5)

            # 等待密码提示
            output = self._read_serial_output(timeout=2)

            # 发送密码
            self.serial_conn.write(b'R0uT3&U&s@l1nk46#3\n')
            time.sleep(1)

            # 验证登录成功
            output = self._read_serial_output(timeout=2)
            if 'root@' not in output and '#' not in output:
                raise Exception("串口登录失败")

        except Exception as e:
            raise Exception(f"串口登录失败: {str(e)}")

    def _read_serial_output(self, timeout=1):
        """读取串口输出"""
        output = b''
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.serial_conn.in_waiting > 0:
                output += self.serial_conn.read(self.serial_conn.in_waiting)
            time.sleep(0.1)
        return output.decode('utf-8', errors='ignore')

    def _check_python_version_via_serial(self):
        """通过串口检查Python版本"""
        try:
            # 初始化串口连接
            if not self._init_serial_connection():
                return False

            print("通过串口检查Python版本...")

            # 使用完整路径和环境变量
            python_path = "/usr/python/bin/python3.9"
            lib_path = "/usr/python/lib"
            command = f"export LD_LIBRARY_PATH={lib_path}:$LD_LIBRARY_PATH && {python_path} --version\n"

            print(f"串口执行命令: {command.strip()}")

            # 发送命令
            self.serial_conn.write(command.encode('utf-8'))
            time.sleep(1)

            # 读取输出
            output = self._read_serial_output(timeout=3)
            print(f"Python版本输出: {output}")

            # 关闭串口
            if self.serial_conn:
                self.serial_conn.close()
                self.serial_conn = None

            # 检查输出
            if 'Error' in output or 'No such file' in output:
                print(f"❌ 串口执行Python出错: {output}")
                return False

            if 'Python 3.9' in output:
                print(f"✅ Python版本正确: {output}")
                return True
            else:
                print(f"❌ Python版本不正确: {output}")
                return False

        except Exception as e:
            print(f"串口检查Python版本失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            if self.serial_conn:
                try:
                    self.serial_conn.close()
                except:
                    pass
                self.serial_conn = None
            return False

    def _execute_script_via_serial(self):
        """通过串口执行selftest.py脚本"""
        try:
            # 初始化串口连接
            if not self._init_serial_connection():
                return None

            print("通过串口执行selftest.py...")

            # 使用完整路径和环境变量
            script_path = "/tmp/selftest.py"
            python_path = "/usr/python/bin/python3.9"
            lib_path = "/usr/python/lib"
            command = f"export LD_LIBRARY_PATH={lib_path}:$LD_LIBRARY_PATH && {python_path} {script_path}\n"

            print(f"串口执行命令: {command.strip()}")

            # 发送命令
            self.serial_conn.write(command.encode('utf-8'))

            # 等待执行完成（根据脚本复杂度可能需要更长时间）
            time.sleep(5)

            # 读取输出
            output = self._read_serial_output(timeout=10)

            print("\n--- 脚本输出 ---")
            print(output)
            print("--- 输出结束 ---\n")

            # 关闭串口
            if self.serial_conn:
                self.serial_conn.close()
                self.serial_conn = None

            # 检查输出是否为空
            if not output or not output.strip():
                print(f"❌ 串口执行脚本没有输出")
                return None

            # 返回输出
            return output

        except Exception as e:
            print(f"串口执行脚本失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            if self.serial_conn:
                try:
                    self.serial_conn.close()
                except:
                    pass
                self.serial_conn = None
            return None
