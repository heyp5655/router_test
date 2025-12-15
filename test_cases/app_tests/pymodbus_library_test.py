# -*- coding: utf-8 -*-
"""
测试用例ID8: Python3.9第三方库pymodbus验证

测试项：功能用例/APP/python
测试点：python3.9第三方库pymodbus验证
前置条件：设备搭好实际可用的modbus环境

测试步骤：
1. 确保路由器已经安装python3.9的环境，如果没有安装需要自行安装
2. 需要进行交互式测试，开启两个进程：
   - 进程A：通过本地COM3进入路由器后台，用路由器python调用pymodbus接口
   - 进程B：用电脑本地Modbus Poll模拟Modbus从站
   - 交互验证：路由器作为Modbus客户端，PC作为Modbus服务器

预期：
接口调用不报错，交互过程没有错误
"""
from test_cases.base_test import BaseTest
import time
import paramiko
import serial
import threading

# pymodbus导入（可选）
try:
    from pymodbus.server import StartTcpServer
    from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext
    try:
        from pymodbus.datastore import ModbusSlaveContext
        PYMODBUS_VERSION = "2.x"
    except ImportError:
        from pymodbus.datastore import ModbusDeviceContext as ModbusSlaveContext
        PYMODBUS_VERSION = "3.x"
    PYMODBUS_AVAILABLE = True
except ImportError:
    PYMODBUS_AVAILABLE = False
    PYMODBUS_VERSION = "None"


class PymodbusLibraryTest(BaseTest):
    """Python3.9第三方库pymodbus验证"""

    category = "功能用例/APP/python"
    is_regression = True

    # Modbus配置
    MODBUS_TCP_PORT = 502
    MODBUS_RTU_PORT = "/dev/ttyS1"
    MODBUS_BAUDRATE = 115200
    MODBUS_UNIT_ID = 1

    # 路由器端pymodbus测试脚本
    PYMODBUS_TEST_SCRIPT = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路由器端pymodbus接口验证脚本"""
import sys
import time

print("=" * 60)
print("pymodbus接口验证测试")
print("=" * 60)

# 步骤1: 导入pymodbus模块（兼容2.x和3.x）
print("\\n步骤1: 导入pymodbus模块")
try:
    # 尝试 2.5.x 导入路径
    from pymodbus.client.sync import ModbusTcpClient
    from pymodbus.framer.rtu_framer import ModbusRtuFramer
    print("✅ pymodbus模块导入成功 (2.5.x)")
except Exception:
    try:
        # 尝试 3.x 导入路径
        from pymodbus.client import ModbusTcpClient
        from pymodbus.framer.rtu_framer import ModbusRtuFramer
        print("✅ pymodbus模块导入成功 (3.x)")
    except Exception as e:
        print(f"❌ pymodbus模块导入失败: {e}")
        sys.exit(1)

# Modbus配置
TCP_HOST = "__TCP_HOST__"
TCP_PORT = __TCP_PORT__
UNIT_ID = __UNIT_ID__

# 测试结果统计
test_results = {
    'module_import': True,
    'tcp_client_create': False,
    'tcp_connect': False,
    'write_coil': False,
    'read_coils': False,
    'write_register': False,
    'read_holding_registers': False,
    'disconnect': False
}

# 步骤2: 创建Modbus TCP客户端
print("\\n步骤2: 创建Modbus TCP客户端")
try:
    client = ModbusTcpClient(host=TCP_HOST, port=TCP_PORT, timeout=3)
    print(f"✅ TCP客户端创建成功: {TCP_HOST}:{TCP_PORT}")
    test_results['tcp_client_create'] = True
except Exception as e:
    print(f"❌ TCP客户端创建失败: {e}")
    sys.exit(1)

# 步骤3: 连接MODBUS服务器
print("\\n步骤3: 连接Modbus服务器")
try:
    if client.connect():
        print("✅ 连接成功")
        test_results['tcp_connect'] = True
    else:
        print("❌ 连接失败")
        sys.exit(1)
except Exception as e:
    print(f"❌ 连接失败: {e}")
    sys.exit(1)

# 步骤4: 写线圈（write_coil）
print("\\n步骤4: 写线圈 - write_coil()")
try:
    result = client.write_coil(1, True, unit=UNIT_ID)
    # 检查是否有错误
    is_err = getattr(result, "isError", lambda: False)()
    if not is_err:
        print(f"✅ write_coil成功: 地址1, 值True")
        test_results['write_coil'] = True
    else:
        print(f"⚠️  write_coil返回错误: {result}")
    time.sleep(0.1)
except Exception as e:
    print(f"❌ write_coil失败: {e}")

# 步骤5: 读线圈（read_coils）
print("\\n步骤5: 读线圈 - read_coils()")
try:
    result = client.read_coils(1, 1, unit=UNIT_ID)
    is_err = getattr(result, "isError", lambda: False)()
    if not is_err:
        print(f"✅ read_coils成功: {result.bits}")
        test_results['read_coils'] = True
    else:
        print(f"⚠️  read_coils返回错误: {result}")
    time.sleep(0.1)
except Exception as e:
    print(f"❌ read_coils失败: {e}")

# 步骤6: 写寄存器（write_register）
print("\\n步骤6: 写寄存器 - write_register()")
try:
    result = client.write_register(1, 123, unit=UNIT_ID)
    is_err = getattr(result, "isError", lambda: False)()
    if not is_err:
        print(f"✅ write_register成功: 地址1, 值123")
        test_results['write_register'] = True
    else:
        print(f"⚠️  write_register返回错误: {result}")
    time.sleep(0.1)
except Exception as e:
    print(f"❌ write_register失败: {e}")

# 步骤7: 读保持寄存器（read_holding_registers）
print("\\n步骤7: 读保持寄存器 - read_holding_registers()")
try:
    result = client.read_holding_registers(1, 1, unit=UNIT_ID)
    is_err = getattr(result, "isError", lambda: False)()
    if not is_err:
        print(f"✅ read_holding_registers成功: {result.registers}")
        test_results['read_holding_registers'] = True
    else:
        print(f"⚠️  read_holding_registers返回错误: {result}")
    time.sleep(0.1)
except Exception as e:
    print(f"❌ read_holding_registers失败: {e}")

# 步骤8: 断开连接
print("\\n步骤8: 断开连接")
try:
    client.close()
    print("✅ 连接已关闭")
    test_results['disconnect'] = True
except Exception as e:
    print(f"❌ 关闭连接失败: {e}")

# 输出测试结果
print("\\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)
print(f"模块导入: {'✅ 通过' if test_results['module_import'] else '❌ 失败'}")
print(f"创建客户端: {'✅ 通过' if test_results['tcp_client_create'] else '❌ 失败'}")
print(f"连接服务器: {'✅ 通过' if test_results['tcp_connect'] else '❌ 失败'}")
print(f"写线圈: {'✅ 通过' if test_results['write_coil'] else '❌ 失败'}")
print(f"读线圈: {'✅ 通过' if test_results['read_coils'] else '❌ 失败'}")
print(f"写寄存器: {'✅ 通过' if test_results['write_register'] else '❌ 失败'}")
print(f"读寄存器: {'✅ 通过' if test_results['read_holding_registers'] else '❌ 失败'}")
print(f"断开连接: {'✅ 通过' if test_results['disconnect'] else '❌ 失败'}")

# 总体结果
all_passed = all(test_results.values())
print("\\n" + "=" * 60)
if all_passed:
    print("✅ 所有测试通过！pymodbus库验证成功")
    sys.exit(0)
else:
    failed_tests = [k for k, v in test_results.items() if not v]
    print(f"❌ 存在测试失败项: {failed_tests}")
    sys.exit(1)
'''

    @property
    def test_name(self):
        return "python3.9第三方库pymodbus验证"

    @property
    def description(self):
        return "验证pymodbus库接口完整性，包括TCP/RTU客户端、读写线圈、读写寄存器等操作"

    def __init__(self, config):
        super().__init__(config)

        # 路由器配置
        self.router_ip = self.config.router_config.router_ip

        # Modbus服务器配置
        self.pc_ip = config.router_config.modbus_server_ip
        self.modbus_tcp_port = config.router_config.modbus_port

        # 系统串口配置（COM3）
        self.system_serial_port = self.config.router_config.serial_port
        self.serial_baudrate = self.config.router_config.serial_baudrate

        # 串口连接对象
        self.system_serial_conn = None

        # PC端Modbus Server
        self.modbus_server_thread = None
        self.modbus_server_running = False
        self.modbus_context = None

        # 测试结果
        self.test_output_buffer = ""

    def setup(self):
        """测试前置条件"""
        print(f"\n{'='*70}")
        print(f"测试用例ID8: {self.test_name}")
        print(f"测试分类: {self.category}")
        print(f"{'='*70}")
        print(f"路由器IP: {self.router_ip}")
        print(f"系统串口: {self.system_serial_port}")
        print(f"PC IP (Modbus Server): {self.pc_ip}:{self.modbus_tcp_port}")
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
            print(f"开始执行pymodbus交互测试")
            print(f"{'='*70}\n")

            # 步骤1: 上传测试脚本到路由器
            print("步骤1: 上传测试脚本到路由器...")
            if not self._upload_test_script():
                raise Exception("上传测试脚本失败")
            print("✅ 测试脚本上传成功\n")

            # 步骤2: 启动PC端Modbus Server（进程B）
            print("步骤2: 启动PC端Modbus TCP Server...")
            if not self._start_modbus_server():
                raise Exception("启动Modbus Server失败")
            print("✅ Modbus Server已启动\n")

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

            # 步骤4: 停止Modbus Server
            print("步骤4: 停止Modbus Server...")
            self._stop_modbus_server()
            print("✅ Modbus Server已停止\n")

            # 步骤5: 解析测试结果
            print("步骤5: 解析测试结果...")
            print(f"\n{'='*70}")
            print("路由器端输出内容:")
            print(f"{'='*70}")
            print(self.test_output_buffer if self.test_output_buffer else "（无输出）")
            print(f"{'='*70}\n")

            if "✅ 所有测试通过！pymodbus库验证成功" in self.test_output_buffer:
                print("✅ 所有pymodbus接口测试通过！\n")
                return True
            else:
                print("❌ 部分测试未通过\n")
                raise AssertionError("存在测试失败项")

        except Exception as e:
            print(f"\n❌ 测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            self._stop_modbus_server()
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
            script_content = self.PYMODBUS_TEST_SCRIPT
            script_content = script_content.replace("__TCP_HOST__", self.pc_ip)
            script_content = script_content.replace("__TCP_PORT__", str(self.modbus_tcp_port))
            script_content = script_content.replace("__UNIT_ID__", str(self.MODBUS_UNIT_ID))

            # 上传脚本
            script_path = "/tmp/modbus_test.py"
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

    def _start_modbus_server(self):
        """启动PC端Modbus TCP Server"""
        try:
            # 检查pymodbus是否可用
            if not PYMODBUS_AVAILABLE:
                raise ImportError("PC端未安装pymodbus库，请先安装: pip install pymodbus")

            print(f"初始化Modbus数据存储...")

            # 创建数据块 (地址0-99，初始值为0)
            store = ModbusSlaveContext(
                di=ModbusSequentialDataBlock(0, [0]*100),  # 离散输入
                co=ModbusSequentialDataBlock(0, [0]*100),  # 线圈
                hr=ModbusSequentialDataBlock(0, [0]*100),  # 保持寄存器
                ir=ModbusSequentialDataBlock(0, [0]*100)   # 输入寄存器
            )

            # pymodbus 3.x使用devices参数，2.x使用slaves参数
            if PYMODBUS_VERSION == "3.x":
                self.modbus_context = ModbusServerContext(devices=store, single=True)
            else:
                self.modbus_context = ModbusServerContext(slaves=store, single=True)
            print("✅ 数据存储初始化完成")

            # 在后台线程启动服务器
            self.modbus_server_running = True
            self.modbus_server_thread = threading.Thread(
                target=self._run_modbus_server,
                daemon=True
            )
            self.modbus_server_thread.start()

            print(f"✅ Modbus TCP Server已在 {self.pc_ip}:{self.modbus_tcp_port} 启动")

            # 等待服务器启动
            time.sleep(2)

            return True

        except Exception as e:
            print(f"启动Modbus Server失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def _run_modbus_server(self):
        """运行Modbus Server（在后台线程中）"""
        try:
            # 启动TCP服务器（兼容pymodbus 2.x和3.x）
            StartTcpServer(
                context=self.modbus_context,
                address=(self.pc_ip, self.modbus_tcp_port)
            )
        except Exception as e:
            print(f"Modbus Server运行出错: {str(e)}")

    def _stop_modbus_server(self):
        """停止Modbus Server"""
        try:
            self.modbus_server_running = False
            if self.modbus_server_thread and self.modbus_server_thread.is_alive():
                print("正在停止Modbus Server...")
                # 因为是daemon线程，会自动退出
                time.sleep(1)
            print("✅ Modbus Server已停止")
        except Exception as e:
            print(f"停止Modbus Server失败: {str(e)}")

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
            script_path = "/tmp/modbus_test.py"
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
            script_path = "/tmp/modbus_test.py"
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

        # 停止Modbus Server
        self._stop_modbus_server()

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
            ssh.exec_command("rm -f /tmp/modbus_test.py")
            ssh.close()
            print("✅ 临时文件已删除")
        except Exception as e:
            print(f"清理临时文件失败: {str(e)}")

        print("测试清理完成")
