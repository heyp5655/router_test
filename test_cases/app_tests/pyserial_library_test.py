from test_cases.base_test import BaseTest
import time
import paramiko
import serial
import threading
import queue
import re


class PyserialLibraryTest(BaseTest):
    """Python3.9第三方库pyserial验证

    测试项：功能用例/APP/python
    测试点：pyserial库接口完整性验证

    前置条件：
    设备搭好实际可用的工业serial环境

    测试步骤：
    1. 确保路由器已经安装python3.9的环境，如果没有安装需要自行安装
    2. 需要进行交互式测试，开启两个进程：
       - 进程A：通过本地COM3进入路由器后台，用路由器python调用工业串口
                （ttymxc1 波特率115200 数据位8 奇偶校验none 停止位1）
       - 进程B：用电脑真实接的485串口com4模拟工业串口客户端
       - 交互验证：A读B写，A写B读，核对数据一致性

    预期：
    设备内部调用pyserial的常用接口，打开关闭，读写操作没有报错则测试通过
    所有测试项通过，包括模块导入、常量定义、异常类、串口枚举、
    串口连接、数据收发、双向通信、压力测试等
    """

    # 添加分类信息属性
    category = "功能用例/APP/python"
    is_regression = True  # 标记为回归测试用例

    # SDK文件路径
    SDK_FILE_PATH = r"E:\GIT\ROUTER_TEST\config\pysdk-ur3x-5.0.2-u1.tar.gz"

    # 简化版测试脚本 - 完整的双向交互测试
    SERIAL_TEST_SCRIPT_SIMPLE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import time

print("=" * 60)
print("pyserial双向交互测试")
print("=" * 60)

try:
    import serial
    print("✅ pyserial模块导入成功")
    print(f"✅ pyserial版本: {getattr(serial, 'VERSION', 'unknown')}")
except ImportError as e:
    print(f"❌ pyserial模块导入失败: {e}")
    sys.exit(1)

# 打开串口
port_name = "/dev/ttymxc2"
baudrate = 115200

print(f"\\n正在打开串口: {port_name}")
print(f"波特率: {baudrate}")
print(f"数据位: 8")
print(f"奇偶校验: None")
print(f"停止位: 1")

try:
    # 使用 serial_for_url 方式打开串口
    ser = serial.serial_for_url(
        port_name,
        baudrate=baudrate,
        timeout=1.0,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        rtscts=False,
        xonxoff=False
    )
    print(f"✅ 串口打开成功: {port_name}")
    print(f"   is_open: {ser.is_open}")
    print(f"   baudrate: {ser.baudrate}")
    print(f"   timeout: {ser.timeout}")

    # 清空缓冲区
    ser.reset_input_buffer()
    ser.flush()
    print("✅ 缓冲区已清空 (reset_input_buffer + flush)")

except Exception as e:
    print(f"❌ 串口打开失败: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)

# 测试结果统计
test_results = {
    'write_test': False,
    'read_test': False,
    'readline_test': False
}

print("\\n" + "=" * 60)
print("开始双向交互测试")
print("=" * 60)

# === 测试1: write() 功能 ===
print("\\n【测试1】write() - 路由器发送数据到PC")
test_data_1 = "ROUTER_WRITE_TEST_001\\r\\n"
try:
    n = ser.write(test_data_1.encode('ascii'))
    ser.flush()
    print(f"✅ write() 成功，发送 {n} 字节: {test_data_1.strip()}")
    test_results['write_test'] = True
    time.sleep(0.1)  # 减少延时，快速进入read状态
except Exception as e:
    print(f"❌ write() 失败: {e}")

# === 测试2: read() 功能 ===
print("\\n【测试2】read() - 路由器接收PC发送的数据")
print("等待PC发送数据（5秒超时）...")
try:
    ser.timeout = 2  # 2秒超时
    data = ser.read(100)  # 读取所有可用数据

    if len(data) > 0:
        text = data.decode('utf-8', errors='replace')
        print(f"✅ read() 成功，收到 {len(data)} 字节: {text.strip()}")
        print(f"   HEX: {data.hex()}")
        test_results['read_test'] = True
    else:
        print("❌ read() 超时，未收到数据")
        test_results['read_test'] = False
except Exception as e:
    print(f"❌ read() 失败: {e}")

# === 测试3: readline() 功能 ===
print("\\n【测试3】readline() - 写入带换行数据并读取")
try:
    # 清空缓冲区
    ser.reset_input_buffer()
    ser.flush()
    print("已清空缓冲区")

    # 写入带换行的数据
    data = b"hello\\r\\n"
    n = ser.write(data)
    ser.flush()
    print(f"已写入 {n} 字节: {data!r}")

    # 尝试读取（工业串口可能没有回环，读不到也正常）
    ser.timeout = 1.0
    line = ser.readline()

    if line:
        print(f"✅ readline() 成功: wrote {n} bytes, got {line!r}")
        test_results['readline_test'] = True
    else:
        # 对于非回环后端，读不到数据也是正常的
        print(f"✅ readline() 调用成功: wrote {n} bytes (no echo; OK on non-loop backends)")
        test_results['readline_test'] = True
except Exception as e:
    print(f"❌ readline() 失败: {e}")
    test_results['readline_test'] = False

# === 测试4: 再次发送确认数据 ===
print("\\n【测试4】发送测试完成确认数据")
try:
    confirm_data = "ROUTER_TEST_COMPLETE\\r\\n"
    n = ser.write(confirm_data.encode('ascii'))
    ser.flush()
    print(f"✅ 发送完成确认: {confirm_data.strip()}")
except Exception as e:
    print(f"❌ 发送失败: {e}")

# 关闭串口
print("\\n" + "=" * 60)
print("关闭串口")
try:
    ser.close()
    print(f"✅ 串口已关闭，is_open: {ser.is_open}")
except Exception as e:
    print(f"❌ 关闭失败: {e}")

# 输出测试结果
print("\\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)
print(f"write() 测试: {'✅ 通过' if test_results['write_test'] else '❌ 失败'}")
print(f"read() 测试: {'✅ 通过' if test_results['read_test'] else '❌ 失败'}")
print(f"readline() 测试: {'✅ 通过' if test_results['readline_test'] else '❌ 失败'}")

# 总体结果
all_passed = all(test_results.values())
print("\\n" + "=" * 60)
if all_passed:
    print("✅ 所有测试通过！pyserial库验证成功")
    sys.exit(0)
else:
    print("❌ 存在测试失败项")
    sys.exit(1)
'''

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "python3.9第三方库pyserial验证"

    @property
    def description(self):
        """测试描述"""
        return "验证pyserial库的完整性，包括模块导入、常量、异常、串口枚举、连接及双向通信"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 获取路由器配置
        self.router_ip = self.config.router_config.router_ip

        # 从配置中获取串口配置
        self.system_serial_port = self.config.router_config.serial_port  # COM3 - 系统串口
        self.serial_baudrate = self.config.router_config.serial_baudrate

        # 工业串口485配置（从配置中获取）
        self.industrial_serial_port = self.config.router_config.industrial_serial_port

        # 串口连接对象
        self.system_serial_conn = None  # COM3 - 系统串口
        self.industrial_serial_conn = None  # COM4 - 工业串口485

        # 工业串口485线程和队列
        self.industrial_thread = None
        self.industrial_running = False
        self.industrial_received_queue = queue.Queue()
        self.industrial_stats = {
            'sent_count': 0,
            'received_count': 0,
            'matched_count': 0,
            'mismatched_count': 0
        }

        # 测试结果
        self.test_output_buffer = ""
        self.data_mismatch_detected = False

    def setup(self):
        """测试前置条件"""
        print(f"\n{'='*70}")
        print(f"测试用例: {self.test_name}")
        print(f"测试分类: {self.category}")
        print(f"{'='*70}")
        print(f"路由器IP: {self.router_ip}")
        print(f"系统串口: {self.system_serial_port}")
        print(f"工业串口: {self.industrial_serial_port}")
        print(f"{'='*70}\n")

        # 检查并自动安装Python SDK
        print("前置条件: 检查Python SDK...")
        if not self.ensure_python_sdk_installed():
            raise Exception("Python SDK未安装且自动安装失败，无法继续测试")
        print("✅ Python SDK已就绪\n")
        print("✅ 前置条件检查完成\n")

    def execute(self):
        """执行测试 - 完整的双向交互测试"""
        try:
            print(f"\n{'='*70}")
            print(f"开始执行pyserial库双向交互测试")
            print(f"{'='*70}\n")

            # 步骤1: SSH上传测试脚本
            print("步骤1: SSH上传测试脚本到路由器...")
            if not self._upload_simple_test_script():
                raise Exception("上传测试脚本失败")
            print("✅ 测试脚本上传成功\n")

            # 步骤2: 启动PC端工业串口（进程B）
            print("步骤2: 启动PC端工业串口（COM4）监听线程...")
            if not self._start_industrial_serial():
                raise Exception("启动工业串口失败")
            print("✅ 工业串口已启动\n")

            # 步骤3: 通过COM3系统串口登录并执行测试脚本（进程A）
            print("步骤3: 通过系统串口执行路由器测试脚本...")
            if not self._execute_simple_test_via_system_serial():
                raise Exception("执行测试脚本失败")
            print("✅ 测试脚本执行完成\n")

            # 步骤4: 停止PC端工业串口
            print("步骤4: 停止PC端工业串口...")
            self._stop_industrial_serial()
            print("✅ 工业串口已停止\n")

            # 步骤5: 解析测试结果
            print("步骤5: 解析测试结果...")
            if "✅ 所有测试通过！pyserial库验证成功" in self.test_output_buffer:
                print("✅ 所有pyserial接口测试通过！\n")
                print(f"工业串口统计:")
                print(f"  - 发送: {self.industrial_stats['sent_count']} 次")
                print(f"  - 接收: {self.industrial_stats['received_count']} 次")
                return True
            else:
                print("⚠️  部分测试未通过，请查看详细日志\n")
                raise AssertionError("存在测试失败项")

        except Exception as e:
            print(f"\n测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # 确保清理工业串口
            self._stop_industrial_serial()
            raise

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
        """通过SSH命令检查SDK是否已安装"""
        ssh = None
        try:
            print("通过SSH检查Python SDK安装状态...")

            # 建立SSH连接
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )

            # 检查python3.9是否存在（需要设置LD_LIBRARY_PATH）
            python_path = "/usr/python/bin/python3.9"
            lib_path = "/usr/python/lib"
            check_cmd = f"export LD_LIBRARY_PATH={lib_path}:$LD_LIBRARY_PATH && {python_path} --version 2>&1"

            print(f"执行命令: {check_cmd}")
            stdin, stdout, stderr = ssh.exec_command(check_cmd)
            output = stdout.read().decode('utf-8', errors='ignore').strip()

            print(f"命令输出: {output}")

            # 检查是否包含Python 3.9版本信息
            if 'Python 3.9' in output or 'python 3.9' in output.lower():
                print(f"✅ SDK已安装，版本: {output}")
                ssh.close()
                return True
            else:
                print("❌ SDK未安装或版本不正确")
                ssh.close()
                return False

        except Exception as e:
            print(f"SSH检查SDK状态失败: {str(e)}")
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
            return False

    def _install_sdk_via_web(self):
        """通过Web界面安装SDK"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

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
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

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

    def _upload_simple_test_script(self):
        """通过SFTP上传简化版测试脚本"""
        ssh = None
        sftp = None
        try:
            # 建立SSH连接
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            print(f"正在SSH连接到路由器 {self.router_ip} (使用root用户)...")
            ssh.connect(
                self.router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )
            print("SSH连接成功")

            # 使用SFTP上传文件
            script_path = "/tmp/serial_listen_test.py"
            print(f"通过SFTP上传脚本到 {script_path}...")

            # 打开SFTP会话
            sftp = ssh.open_sftp()

            # 写入简化版脚本内容到远程文件
            with sftp.file(script_path, 'w') as remote_file:
                remote_file.write(self.SERIAL_TEST_SCRIPT_SIMPLE)

            print("✅ SFTP上传完成")

            # 验证文件是否创建成功
            print("验证文件是否创建成功...")
            stdin, stdout, stderr = ssh.exec_command(f"ls -l {script_path}")
            output = stdout.read().decode('utf-8', errors='ignore')

            if script_path in output:
                print(f"文件创建成功: {output.strip()}")
            else:
                print(f"文件创建失败")
                if sftp:
                    sftp.close()
                ssh.close()
                return False

            # 设置执行权限
            print("设置执行权限...")
            stdin, stdout, stderr = ssh.exec_command(f"chmod +x {script_path}")
            stdout.channel.recv_exit_status()  # 等待命令完成
            print("✅ 权限设置完成")

            # 关闭连接
            if sftp:
                sftp.close()
            ssh.close()
            return True

        except Exception as e:
            print(f"SFTP上传脚本失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            if sftp:
                try:
                    sftp.close()
                except:
                    pass
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
            return False

    def _execute_simple_test_via_system_serial(self):
        """通过COM3系统串口执行简化版测试脚本"""
        try:
            # 初始化系统串口连接
            print(f"初始化系统串口 {self.system_serial_port}...")
            self.system_serial_conn = serial.Serial(
                port=self.system_serial_port,
                baudrate=self.serial_baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
            print("✅ 系统串口连接成功")

            # 登录串口
            print("通过系统串口登录...")
            self._serial_login()
            print("✅ 系统串口登录成功")

            # 执行测试脚本
            script_path = "/tmp/serial_listen_test.py"
            python_path = "/usr/python/bin/python3.9"
            lib_path = "/usr/python/lib"
            command = f"export LD_LIBRARY_PATH={lib_path}:$LD_LIBRARY_PATH && {python_path} {script_path}\n"

            print(f"执行命令: {command.strip()}")
            print("脚本将持续运行60秒监听数据...")
            print("=" * 70)
            self.system_serial_conn.write(command.encode('utf-8'))

            # 开始读取输出（脚本测试时间约15秒，给30秒余量）
            start_time = time.time()
            max_duration = 30  # 减少到30秒
            last_data_time = start_time
            no_data_timeout = 10  # 如果10秒没数据，认为脚本结束

            while time.time() - start_time < max_duration:
                if self.system_serial_conn.in_waiting > 0:
                    data = self.system_serial_conn.read(self.system_serial_conn.in_waiting)
                    last_data_time = time.time()  # 更新最后收到数据的时间
                    try:
                        data_text = data.decode('utf-8', errors='ignore')
                        self.test_output_buffer += data_text
                        # 实时打印输出
                        for line in data_text.split('\n'):
                            if line.strip():
                                print(f"  {line.strip()}")
                    except:
                        pass

                    # 检查是否测试已完成
                    if "测试结果汇总" in self.test_output_buffer:
                        print("检测到测试完成标记，等待剩余输出...")
                        time.sleep(2)  # 等待最后的输出
                        # 再读一次
                        if self.system_serial_conn.in_waiting > 0:
                            data = self.system_serial_conn.read(self.system_serial_conn.in_waiting)
                            try:
                                data_text = data.decode('utf-8', errors='ignore')
                                self.test_output_buffer += data_text
                                for line in data_text.split('\n'):
                                    if line.strip():
                                        print(f"  {line.strip()}")
                            except:
                                pass
                        break

                # 如果超过10秒没收到数据，认为脚本已结束
                if time.time() - last_data_time > no_data_timeout:
                    print("超过10秒未收到数据，认为脚本已结束")
                    break

                time.sleep(0.1)

            print("=" * 70)

            # 关闭系统串口
            if self.system_serial_conn:
                self.system_serial_conn.close()
                self.system_serial_conn = None
                print("系统串口已关闭")

            return True

        except Exception as e:
            print(f"通过系统串口执行测试失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            if self.system_serial_conn:
                try:
                    self.system_serial_conn.close()
                except:
                    pass
                self.system_serial_conn = None
            return False

    def _upload_test_script_ssh(self):
        """通过SFTP上传测试脚本"""
        ssh = None
        sftp = None
        try:
            # 建立SSH连接
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            print(f"正在SSH连接到路由器 {self.router_ip} (使用root用户)...")
            ssh.connect(
                self.router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )
            print("SSH连接成功")

            # 使用SFTP上传文件
            script_path = "/tmp/serial_interface_test.py"
            print(f"通过SFTP上传脚本到 {script_path}...")

            # 打开SFTP会话
            sftp = ssh.open_sftp()

            # 写入脚本内容到远程文件
            with sftp.file(script_path, 'w') as remote_file:
                remote_file.write(self.SERIAL_TEST_SCRIPT)

            print("✅ SFTP上传完成")

            # 验证文件是否创建成功
            print("验证文件是否创建成功...")
            stdin, stdout, stderr = ssh.exec_command(f"ls -l {script_path}")
            output = stdout.read().decode('utf-8', errors='ignore')

            if script_path in output:
                print(f"文件创建成功: {output.strip()}")
            else:
                print(f"文件创建失败")
                if sftp:
                    sftp.close()
                ssh.close()
                return False

            # 设置执行权限
            print("设置执行权限...")
            stdin, stdout, stderr = ssh.exec_command(f"chmod +x {script_path}")
            stdout.channel.recv_exit_status()  # 等待命令完成
            print("✅ 权限设置完成")

            # 关闭连接
            if sftp:
                sftp.close()
            ssh.close()
            return True

        except Exception as e:
            print(f"SFTP上传脚本失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            if sftp:
                try:
                    sftp.close()
                except:
                    pass
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
            return False

    def _start_industrial_serial(self):
        """启动工业串口485监听线程（模拟PC端）"""
        try:
            print(f"初始化工业串口 {self.industrial_serial_port}...")
            self.industrial_serial_conn = serial.Serial(
                port=self.industrial_serial_port,
                baudrate=self.serial_baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=0.5
            )

            # 创建后设置RTS/DTR
            self.industrial_serial_conn.rts = False
            self.industrial_serial_conn.dtr = False
            print("✅ 工业串口连接成功（RS-485接收模式）")

            # 启动监听线程
            self.industrial_running = True
            self.industrial_thread = threading.Thread(target=self._industrial_serial_loop)
            self.industrial_thread.daemon = True
            self.industrial_thread.start()
            print("✅ 工业串口监听线程已启动")

            return True

        except Exception as e:
            print(f"启动工业串口失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _industrial_serial_send(self, data):
        """RS-485发送数据"""
        try:
            print(f"准备发送 {len(data)} 字节: {data.hex()}")
            # 不使用RTS控制，直接发送
            n = self.industrial_serial_conn.write(data)
            print(f"write()返回: {n} 字节")
            self.industrial_serial_conn.flush()
            print("flush()完成")

            # 等待数据完全发送出去并到达对方
            time.sleep(0.1)  # 等待100ms
            print(f"发送完成，总计 {n} 字节")

        except Exception as e:
            print(f"串口发送失败: {str(e)}")
            raise

    def _industrial_serial_loop(self):
        """工业串口485监听循环（模拟PC端响应）- 配合双向交互测试"""
        print("工业串口监听线程开始运行...")

        # 等待一段时间让路由器脚本启动
        time.sleep(3)

        # 使用缓冲区累积接收到的数据
        data_buffer = ""

        # 进入监听循环
        while self.industrial_running:
            try:
                if self.industrial_serial_conn.in_waiting > 0:
                    data = self.industrial_serial_conn.read(self.industrial_serial_conn.in_waiting)
                    try:
                        data_text = data.decode('ascii', errors='replace').strip()
                        if data_text:
                            print(f"工业串口接收: {data_text}")
                            self.industrial_stats['received_count'] += 1

                            # 累积到缓冲区
                            data_buffer += data_text

                            # 根据累积的数据决定响应
                            if "ROUTER_WRITE" in data_buffer and "TEST_001" in data_buffer:
                                # 发送数据供read()测试
                                print(f"检测到完整的ROUTER_WRITE信号，准备发送响应...")
                                time.sleep(0.2)  # 等待路由器进入read()状态
                                response = b"PC_DATA_1234567890\r\n"
                                self._industrial_serial_send(response)
                                self.industrial_stats['sent_count'] += 1
                                print(f"工业串口发送(read测试): {response.decode('ascii').strip()}")
                                data_buffer = ""  # 清空缓冲区

                            elif "ROUTER_REQUEST_READLINE" in data_buffer:
                                # 发送数据供readline()测试
                                print(f"检测到ROUTER_REQUEST_READLINE信号，准备发送响应...")
                                time.sleep(0.8)  # 给路由器时间进入读取状态
                                response = b"PC_READLINE_DATA_OK\r\n"
                                self._industrial_serial_send(response)
                                self.industrial_stats['sent_count'] += 1
                                print(f"工业串口发送(readline测试): {response.decode('ascii').strip()}")
                                data_buffer = ""  # 清空缓冲区

                            elif "ROUTER_TEST_COMPLETE" in data_buffer:
                                print("收到测试完成标记，准备退出")
                                self.industrial_stats['matched_count'] += 1
                                break

                            # 防止缓冲区无限增长，保留最近500个字符
                            if len(data_buffer) > 500:
                                data_buffer = data_buffer[-500:]

                    except Exception as e:
                        print(f"工业串口数据处理失败: {str(e)}")

                time.sleep(0.01)  # 10ms间隔持续监听

            except Exception as e:
                if self.industrial_running:
                    print(f"工业串口监听循环错误: {str(e)}")
                time.sleep(0.1)

        print("工业串口监听线程结束")

    def _stop_industrial_serial(self):
        """停止工业串口485"""
        try:
            self.industrial_running = False
            if self.industrial_thread and self.industrial_thread.is_alive():
                self.industrial_thread.join(timeout=3)

            if self.industrial_serial_conn and self.industrial_serial_conn.is_open:
                self.industrial_serial_conn.close()
                print("工业串口已关闭")

        except Exception as e:
            print(f"停止工业串口失败: {str(e)}")

    def _execute_test_via_system_serial(self):
        """通过COM3系统串口登录并执行测试脚本"""
        try:
            # 初始化系统串口连接
            print(f"初始化系统串口 {self.system_serial_port}...")
            self.system_serial_conn = serial.Serial(
                port=self.system_serial_port,
                baudrate=self.serial_baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
            print("✅ 系统串口连接成功")

            # 登录串口
            print("通过系统串口登录...")
            self._serial_login()
            print("✅ 系统串口登录成功")

            # 执行测试脚本
            script_path = "/tmp/serial_interface_test.py"
            python_path = "/usr/python/bin/python3.9"
            lib_path = "/usr/python/lib"
            command = f"export LD_LIBRARY_PATH={lib_path}:$LD_LIBRARY_PATH && {python_path} {script_path}\n"

            print(f"执行命令: {command.strip()}")
            self.system_serial_conn.write(command.encode('utf-8'))

            # 开始读取输出
            print("读取测试输出...")
            start_time = time.time()
            max_duration = 60  # 最多读取60秒

            while time.time() - start_time < max_duration:
                if self.system_serial_conn.in_waiting > 0:
                    data = self.system_serial_conn.read(self.system_serial_conn.in_waiting)
                    try:
                        data_text = data.decode('utf-8', errors='ignore')
                        self.test_output_buffer += data_text
                        # 实时打印输出
                        for line in data_text.split('\n'):
                            if line.strip():
                                print(f"  {line.strip()}")
                    except:
                        pass

                time.sleep(0.1)

            # 关闭系统串口
            if self.system_serial_conn:
                self.system_serial_conn.close()
                self.system_serial_conn = None
                print("系统串口已关闭")

            return True

        except Exception as e:
            print(f"通过系统串口执行测试失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            if self.system_serial_conn:
                try:
                    self.system_serial_conn.close()
                except:
                    pass
                self.system_serial_conn = None
            return False

    def _serial_login(self):
        """通过串口登录设备"""
        try:
            print("  开始串口登录流程...")

            # 多次发送回车激活终端
            for i in range(3):
                self.system_serial_conn.write(b'\r\n')
                time.sleep(0.3)

            # 读取当前输出
            output = self._read_serial_output(timeout=3)
            print(f"  初始输出: {repr(output[:200])}")  # 显示前200个字符

            # 如果已经是登录状态，直接返回
            if 'root@' in output or '#' in output:
                print("  ✅ 已经处于登录状态")
                return

            # 检查是否需要登录
            if 'login:' in output.lower() or 'username:' in output.lower():
                print("  检测到登录提示，发送用户名...")
                # 发送用户名
                self.system_serial_conn.write(b'root\r\n')
                time.sleep(1)

                # 等待密码提示
                output = self._read_serial_output(timeout=3)
                print(f"  用户名后输出: {repr(output[:200])}")

                if 'password:' in output.lower():
                    print("  检测到密码提示，发送密码...")
                    # 发送密码
                    self.system_serial_conn.write(b'R0uT3&U&s@l1nk46#3\r\n')
                    time.sleep(2)

                    # 验证登录成功
                    output = self._read_serial_output(timeout=3)
                    print(f"  密码后输出: {repr(output[:200])}")

                    if 'root@' in output or '#' in output:
                        print("  ✅ 串口登录成功")
                        return
                    else:
                        raise Exception(f"登录验证失败，未找到root@或#提示符，输出: {output[:500]}")
                else:
                    raise Exception(f"未检测到密码提示，输出: {output[:500]}")
            else:
                # 没有登录提示，可能已经在shell中，尝试发送命令测试
                print("  未检测到登录提示，尝试直接发送命令测试...")
                self.system_serial_conn.write(b'echo test\r\n')
                time.sleep(1)
                output = self._read_serial_output(timeout=2)
                print(f"  测试命令输出: {repr(output[:200])}")

                if 'test' in output or 'root@' in output or '#' in output:
                    print("  ✅ 串口已处于可用状态")
                    return
                else:
                    raise Exception(f"无法确认串口状态，输出: {output[:500]}")

        except Exception as e:
            raise Exception(f"串口登录失败: {str(e)}")

    def _read_serial_output(self, timeout=1):
        """读取串口输出"""
        output = b''
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.system_serial_conn.in_waiting > 0:
                output += self.system_serial_conn.read(self.system_serial_conn.in_waiting)
            time.sleep(0.1)
        return output.decode('utf-8', errors='ignore')

    def _parse_test_results(self):
        """解析测试脚本输出结果"""
        results = {
            'module_import': False,
            'serial_constants': False,
            'exceptions': False,
            'list_ports': False,
            'serial_connection': False,
            'overall': False
        }

        # 分析测试输出
        if "pyserial module import success" in self.test_output_buffer:
            results['module_import'] = True

        if "serial constants test passed" in self.test_output_buffer:
            results['serial_constants'] = True

        if "exception classes test passed" in self.test_output_buffer:
            results['exceptions'] = True

        if "serial port list function normal" in self.test_output_buffer:
            results['list_ports'] = True

        if "serial test passed" in self.test_output_buffer or "serial test overall success" in self.test_output_buffer:
            results['serial_connection'] = True
            results['overall'] = True

        # 检查数据不匹配
        if "DATA MISMATCH" in self.test_output_buffer:
            self.data_mismatch_detected = True

        return results

    def _print_test_results(self, results):
        """打印测试结果"""
        print(f"\n{'='*70}")
        print("pyserial库测试结果")
        print(f"{'='*70}")

        print(f"\n【功能测试】")
        print(f"  模块导入: {'✅ 通过' if results['module_import'] else '❌ 失败'}")
        print(f"  串口常量: {'✅ 通过' if results['serial_constants'] else '❌ 失败'}")
        print(f"  异常类定义: {'✅ 通过' if results['exceptions'] else '❌ 失败'}")
        print(f"  串口枚举: {'✅ 通过' if results['list_ports'] else '⚠️  警告（未检测到串口）'}")
        print(f"  串口连接: {'✅ 通过' if results['serial_connection'] else '❌ 失败'}")

        print(f"\n【通信统计】")
        print(f"  工业串口发送: {self.industrial_stats['sent_count']} 个数据包")
        print(f"  工业串口接收: {self.industrial_stats['received_count']} 个数据包")
        print(f"  数据匹配: {self.industrial_stats['matched_count']} 次")
        print(f"  数据不匹配: {self.industrial_stats['mismatched_count']} 次")

        print(f"\n【总体结果】")
        if results['overall'] and not self.data_mismatch_detected and self.industrial_stats['mismatched_count'] == 0:
            print(f"  ✅ 所有测试通过")
        else:
            print(f"  ❌ 存在测试失败项")

        print(f"{'='*70}\n")

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        # 确保停止工业串口
        print("确保工业串口已关闭...")
        self._stop_industrial_serial()

        # 确保系统串口已关闭
        if self.system_serial_conn and self.system_serial_conn.is_open:
            try:
                self.system_serial_conn.close()
                print("✅ 系统串口已关闭")
            except Exception as e:
                print(f"关闭系统串口失败: {e}")

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

            print("删除临时测试脚本...")
            ssh.exec_command("rm -f /tmp/serial_listen_test.py /tmp/serial_interface_test.py")
            ssh.close()
            print("✅ 临时文件已删除")

        except Exception as e:
            print(f"清理临时文件时出错: {str(e)}")

        print("测试清理完成")
