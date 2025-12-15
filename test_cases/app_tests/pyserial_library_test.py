# -*- coding: utf-8 -*-
"""
测试用例ID3: Python3.9第三方库pyserial验证

测试项：功能用例/APP/python
测试点：python3.9第三方库pyserial验证
前置条件：设备搭好实际可用的工业serial环境

测试步骤：
1. 确保路由器已经安装python3.9的环境，如果没有安装需要自行安装
2. 需要进行交互式测试，开启两个进程：
   - 进程A：通过本地COM3进入路由器后台，用路由器python调用工业串口（ttymxc2 波特率115200）
   - 进程B：用电脑真实接的485串口com4模拟工业串口客户端
   - 交互验证：A读B写，A写B读，核对数据一致性

预期：
设备内部调用pyserial的常用接口，打开关闭，读写操作没有报错则测试通过
"""
from test_cases.base_test import BaseTest
import time
import paramiko
import serial
import threading
import queue


class PyserialLibraryTest(BaseTest):
    """Python3.9第三方库pyserial验证"""

    category = "功能用例/APP/python"
    is_regression = True

    # 工业串口配置（路由器端）
    ROUTER_SERIAL_PORT = "/dev/ttymxc2"  # 路由器工业串口
    SERIAL_BAUDRATE = 115200

    # 路由器端pyserial测试脚本
    PYSERIAL_TEST_SCRIPT = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路由器端pyserial接口验证脚本"""
import sys
import time

print("=" * 60)
print("pyserial接口验证测试")
print("=" * 60)

# 步骤1: 导入pyserial模块
print("\\n步骤1: 导入pyserial模块")
try:
    import serial
    print("✅ pyserial模块导入成功")
    print(f"   版本: {getattr(serial, 'VERSION', 'unknown')}")
except ImportError as e:
    print(f"❌ pyserial模块导入失败: {e}")
    sys.exit(1)

# 步骤2: 打开工业串口
PORT = "__PORT__"
BAUDRATE = __BAUDRATE__

print(f"\\n步骤2: 打开工业串口 {PORT}")
print(f"   波特率: {BAUDRATE}")
print(f"   数据位: 8")
print(f"   奇偶校验: None")
print(f"   停止位: 1")

try:
    ser = serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=2.0
    )
    print(f"✅ 串口打开成功")
    print(f"   is_open: {ser.is_open}")
    print(f"   baudrate: {ser.baudrate}")
    print(f"   timeout: {ser.timeout}")
except Exception as e:
    print(f"❌ 串口打开失败: {e}")
    sys.exit(1)

# 清空缓冲区
ser.reset_input_buffer()
ser.reset_output_buffer()
print("✅ 缓冲区已清空")

# 测试结果统计
test_results = {
    'open': True,
    'write': False,
    'read': False,
    'close': False
}

# 步骤3: write()测试 - 路由器发送数据给PC
print("\\n步骤3: write()测试 - 路由器发送数据")
test_data = "ROUTER_TO_PC_TEST_DATA_123\\r\\n"
try:
    n = ser.write(test_data.encode('utf-8'))
    ser.flush()
    print(f"✅ 发送成功: {n} 字节")
    print(f"   数据: {test_data.strip()}")
    test_results['write'] = True
    time.sleep(0.5)  # 等待PC接收
except Exception as e:
    print(f"❌ 发送失败: {e}")

# 步骤4: read()测试 - 路由器接收PC发送的数据
print("\\n步骤4: read()测试 - 等待接收PC发送的数据")
print("   等待5秒...")
try:
    ser.timeout = 5.0
    data = ser.read(100)

    if len(data) > 0:
        text = data.decode('utf-8', errors='replace')
        print(f"✅ 接收成功: {len(data)} 字节")
        print(f"   数据: {text.strip()}")

        # 验证数据格式
        if "PC_TO_ROUTER" in text:
            print(f"✅ 数据格式正确")
            test_results['read'] = True
        else:
            print(f"⚠️  数据格式不符合预期")
    else:
        print(f"❌ 接收超时，未收到数据")
except Exception as e:
    print(f"❌ 接收失败: {e}")

# 步骤5: 关闭串口
print("\\n步骤5: 关闭串口")
try:
    ser.close()
    print(f"✅ 串口已关闭")
    print(f"   is_open: {ser.is_open}")
    test_results['close'] = True
except Exception as e:
    print(f"❌ 关闭失败: {e}")

# 输出测试结果
print("\\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)
print(f"串口打开: {'✅ 通过' if test_results['open'] else '❌ 失败'}")
print(f"write()测试: {'✅ 通过' if test_results['write'] else '❌ 失败'}")
print(f"read()测试: {'✅ 通过' if test_results['read'] else '❌ 失败'}")
print(f"串口关闭: {'✅ 通过' if test_results['close'] else '❌ 失败'}")

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
        return "python3.9第三方库pyserial验证"

    @property
    def description(self):
        return "验证pyserial库接口完整性，包括串口打开、读写操作、关闭等功能"

    def __init__(self, config):
        super().__init__(config)

        # 路由器配置
        self.router_ip = self.config.router_config.router_ip

        # 系统串口配置（COM3）
        self.system_serial_port = self.config.router_config.serial_port
        self.serial_baudrate = self.config.router_config.serial_baudrate

        # 工业串口配置（COM4）
        self.industrial_serial_port = self.config.router_config.industrial_serial_port

        # 串口连接对象
        self.system_serial_conn = None
        self.industrial_serial_conn = None

        # PC端工业串口监听线程
        self.industrial_thread = None
        self.industrial_running = False
        self.received_data_queue = queue.Queue()

        # 测试结果
        self.test_output_buffer = ""

    def setup(self):
        """测试前置条件"""
        print(f"\n{'='*70}")
        print(f"测试用例ID3: {self.test_name}")
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

    def execute(self):
        """执行测试"""
        try:
            print(f"\n{'='*70}")
            print(f"开始执行pyserial双向交互测试")
            print(f"{'='*70}\n")

            # 步骤1: 上传测试脚本到路由器
            print("步骤1: 上传测试脚本到路由器...")
            if not self._upload_test_script():
                raise Exception("上传测试脚本失败")
            print("✅ 测试脚本上传成功\n")

            # 步骤2: 启动PC端工业串口监听（进程B）
            print("步骤2: 启动PC端工业串口监听线程...")
            if not self._start_pc_industrial_serial():
                raise Exception("启动工业串口失败")
            print("✅ 工业串口已启动\n")

            # 步骤3: 智能选择执行方式（SSH优先，串口备用）
            print("步骤3: 执行路由器测试脚本...")

            # 先尝试SSH
            exec_method = self._check_python_via_ssh()

            if exec_method == "ssh":
                print("使用SSH方式执行（推荐）")
                if not self._execute_test_via_ssh():
                    print("⚠️  SSH执行失败，降级使用串口...")
                    exec_method = None

            # 如果SSH失败，降级到串口
            if not exec_method:
                print("使用串口方式执行（备用）")
                if not self._execute_test_via_system_serial():
                    raise Exception("串口执行测试脚本也失败")

            print("✅ 测试脚本执行完成\n")

            # 步骤4: 停止PC端工业串口
            print("步骤4: 停止PC端工业串口...")
            self._stop_pc_industrial_serial()
            print("✅ 工业串口已停止\n")

            # 步骤5: 解析测试结果
            print("步骤5: 解析测试结果...")
            print(f"\n{'='*70}")
            print("路由器端输出内容:")
            print(f"{'='*70}")
            print(self.test_output_buffer if self.test_output_buffer else "（无输出）")
            print(f"{'='*70}\n")

            if "✅ 所有测试通过！pyserial库验证成功" in self.test_output_buffer:
                print("✅ 所有pyserial接口测试通过！\n")
                return True
            else:
                print("❌ 部分测试未通过\n")
                raise AssertionError("存在测试失败项")

        except Exception as e:
            print(f"\n❌ 测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            self._stop_pc_industrial_serial()
            raise

    def _upload_test_script(self):
        """通过SSH上传测试脚本"""
        ssh = None
        sftp = None
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

            # 替换脚本中的配置参数
            script_content = self.PYSERIAL_TEST_SCRIPT
            script_content = script_content.replace("__PORT__", self.ROUTER_SERIAL_PORT)
            script_content = script_content.replace("__BAUDRATE__", str(self.SERIAL_BAUDRATE))

            # 上传脚本
            script_path = "/tmp/pyserial_test.py"
            sftp = ssh.open_sftp()
            with sftp.file(script_path, 'w') as remote_file:
                remote_file.write(script_content)

            # 设置执行权限
            ssh.exec_command(f"chmod +x {script_path}")

            if sftp:
                sftp.close()
            ssh.close()
            return True

        except Exception as e:
            print(f"上传脚本失败: {str(e)}")
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

    def _start_pc_industrial_serial(self):
        """启动PC端工业串口监听"""
        try:
            # 打开工业串口
            self.industrial_serial_conn = serial.Serial(
                port=self.industrial_serial_port,
                baudrate=self.SERIAL_BAUDRATE,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=0.5
            )
            print(f"✅ 工业串口 {self.industrial_serial_port} 打开成功")

            # 启动监听线程
            self.industrial_running = True
            self.industrial_thread = threading.Thread(target=self._industrial_serial_loop)
            self.industrial_thread.daemon = True
            self.industrial_thread.start()

            return True

        except Exception as e:
            print(f"启动工业串口失败: {str(e)}")
            return False

    def _industrial_serial_loop(self):
        """PC端工业串口监听循环"""
        print("工业串口监听线程开始运行...")

        # 等待路由器脚本启动
        time.sleep(3)

        while self.industrial_running:
            try:
                # 读取路由器发送的数据
                if self.industrial_serial_conn.in_waiting > 0:
                    data = self.industrial_serial_conn.read(self.industrial_serial_conn.in_waiting)
                    text = data.decode('utf-8', errors='replace').strip()

                    if text:
                        print(f"PC端接收到数据: {text}")
                        self.received_data_queue.put(text)

                        # 如果收到路由器的测试数据，回复数据
                        if "ROUTER_TO_PC" in text:
                            time.sleep(0.5)  # 延迟0.5秒后回复
                            response = "PC_TO_ROUTER_RESPONSE_456\r\n"
                            self.industrial_serial_conn.write(response.encode('utf-8'))
                            self.industrial_serial_conn.flush()
                            print(f"PC端发送响应: {response.strip()}")

                time.sleep(0.01)

            except Exception as e:
                if self.industrial_running:
                    print(f"工业串口监听出错: {str(e)}")
                time.sleep(0.1)

        print("工业串口监听线程结束")

    def _stop_pc_industrial_serial(self):
        """停止PC端工业串口"""
        try:
            self.industrial_running = False
            if self.industrial_thread and self.industrial_thread.is_alive():
                self.industrial_thread.join(timeout=3)

            if self.industrial_serial_conn and self.industrial_serial_conn.is_open:
                self.industrial_serial_conn.close()
                print("工业串口已关闭")
        except Exception as e:
            print(f"停止工业串口失败: {str(e)}")

    def _check_python_via_ssh(self):
        """通过SSH检查Python环境"""
        ssh = None
        try:
            print("尝试通过SSH检查Python环境...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )

            # 测试Python是否可执行
            stdin, stdout, stderr = ssh.exec_command(
                "export LD_LIBRARY_PATH=/usr/python/lib:$LD_LIBRARY_PATH && "
                "/usr/python/bin/python3.9 --version 2>&1"
            )
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()

            if "Python 3.9" in output or "Python 3.9" in error:
                print(f"✅ SSH Python环境正常: {output}")
                ssh.close()
                return "ssh"
            else:
                print(f"⚠️  SSH Python环境异常: {output} {error}")
                ssh.close()
                return None

        except Exception as e:
            print(f"⚠️  SSH检查失败: {str(e)}")
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
            return None

    def _verify_python_environment_serial(self):
        """通过串口验证Python环境"""
        try:
            print("通过串口检查Python环境...")

            # 测试Python是否可执行
            test_cmd = "export LD_LIBRARY_PATH=/usr/python/lib:$LD_LIBRARY_PATH && /usr/python/bin/python3.9 --version 2>&1\n"
            self.system_serial_conn.write(test_cmd.encode('utf-8'))
            time.sleep(2)

            output = ""
            if self.system_serial_conn.in_waiting > 0:
                data = self.system_serial_conn.read(self.system_serial_conn.in_waiting)
                output = data.decode('utf-8', errors='ignore')
                print(f"  Python版本检查: {output.strip()}")

            if "Python 3.9" in output:
                print("✅ 串口Python环境正常")
                return "serial"
            else:
                print(f"❌ 串口Python环境异常: {output.strip()}")
                return None

        except Exception as e:
            print(f"❌ 串口检查失败: {str(e)}")
            return None

    def _execute_test_via_ssh(self):
        """通过SSH执行测试脚本"""
        ssh = None
        try:
            print("通过SSH执行测试脚本...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )

            # 执行测试脚本
            python_path = "/usr/python/bin/python3.9"
            lib_path = "/usr/python/lib"
            script_path = "/tmp/pyserial_test.py"
            command = f"export LD_LIBRARY_PATH={lib_path}:$LD_LIBRARY_PATH && {python_path} -u {script_path} 2>&1"

            print(f"执行命令: {command}")
            print("=" * 70)

            stdin, stdout, stderr = ssh.exec_command(command, timeout=60)

            # 实时读取输出
            for line in stdout:
                line_text = line.strip()
                if line_text:
                    print(f"  {line_text}")
                self.test_output_buffer += line

            # 读取错误输出
            error_output = stderr.read().decode('utf-8', errors='ignore')
            if error_output:
                print(f"  [STDERR] {error_output}")
                self.test_output_buffer += error_output

            print("=" * 70)
            ssh.close()
            return True

        except Exception as e:
            print(f"SSH执行失败: {str(e)}")
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
            return False

    def _execute_test_via_system_serial(self):
        """通过系统串口执行测试脚本"""
        try:
            # 打开系统串口
            self.system_serial_conn = serial.Serial(
                port=self.system_serial_port,
                baudrate=self.serial_baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
            print(f"✅ 系统串口 {self.system_serial_port} 打开成功")

            # 登录串口
            print("登录路由器...")
            self._serial_login()
            print("✅ 登录成功")

            # 验证Python环境
            exec_method = self._verify_python_environment_serial()
            if not exec_method:
                raise Exception("串口Python环境验证失败，无法继续执行测试")

            # 执行测试脚本
            python_path = "/usr/python/bin/python3.9"
            lib_path = "/usr/python/lib"
            script_path = "/tmp/pyserial_test.py"
            command = f"export LD_LIBRARY_PATH={lib_path}:$LD_LIBRARY_PATH && {python_path} -u {script_path} 2>&1\n"

            print(f"通过串口执行命令: {command.strip()}")
            print("=" * 70)
            self.system_serial_conn.write(command.encode('utf-8'))

            # 持续收集输出（60秒）
            start_time = time.time()
            wait_duration = 60

            while time.time() - start_time < wait_duration:
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

            print("=" * 70)

            # 关闭系统串口
            if self.system_serial_conn:
                self.system_serial_conn.close()
                self.system_serial_conn = None

            return True

        except Exception as e:
            print(f"执行测试脚本失败: {str(e)}")
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
            # 发送回车激活终端
            for i in range(3):
                self.system_serial_conn.write(b'\r\n')
                time.sleep(0.3)

            # 读取输出
            output = self._read_serial_output(timeout=3)

            # 如果已登录，直接返回
            if 'root@' in output or '#' in output:
                print("  已处于登录状态")
                return

            # 检查是否需要登录
            if 'login:' in output.lower():
                # 发送用户名
                self.system_serial_conn.write(b'root\r\n')
                time.sleep(1)

                # 等待密码提示
                output = self._read_serial_output(timeout=3)
                if 'password:' in output.lower():
                    # 发送密码
                    self.system_serial_conn.write(b'R0uT3&U&s@l1nk46#3\r\n')
                    time.sleep(2)

                    # 验证登录成功
                    output = self._read_serial_output(timeout=3)
                    if 'root@' in output or '#' in output:
                        return
                    else:
                        raise Exception("登录失败")
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

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        # 停止工业串口
        self._stop_pc_industrial_serial()

        # 关闭系统串口
        if self.system_serial_conn and self.system_serial_conn.is_open:
            try:
                self.system_serial_conn.close()
                print("✅ 系统串口已关闭")
            except Exception as e:
                print(f"关闭系统串口失败: {e}")

        # 删除临时文件
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )
            ssh.exec_command("rm -f /tmp/pyserial_test.py")
            ssh.close()
            print("✅ 临时文件已删除")
        except Exception as e:
            print(f"清理临时文件失败: {str(e)}")

        print("测试清理完成")
