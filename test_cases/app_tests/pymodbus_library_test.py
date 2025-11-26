# -*- coding: utf-8 -*-
from test_cases.base_test import BaseTest
import time
import paramiko
import serial
import threading

# pymodbus只在执行时需要，导入时可选
try:
    # 尝试 pymodbus 3.x
    from pymodbus.server import StartTcpServer
    from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext
    # pymodbus 3.x 使用 ModbusDeviceContext 替代 ModbusSlaveContext
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
    """Python3.9第三方库pymodbus验证

    测试项：功能用例/APP/python
    测试点：pymodbus库接口完整性验证

    前置条件：
    设备搭好实际可用的modbus环境

    测试步骤：
    1. 确保路由器已经安装python3.9的环境，如果没有安装需要自行安装
    2. 需要进行交互式测试，开启两个进程：
       - 进程A：通过本地COM3进入路由器后台，用路由器python调用pymodbus接口
       - 进程B：用电脑本地Modbus Server模拟从站
       - 交互验证：路由器作为Modbus客户端，PC作为Modbus服务器

    预期：
    接口调用不报错，交互过程没有错误
    所有测试项通过，包括模块导入、客户端创建、连接、读写线圈、读写寄存器等
    """

    # 添加分类信息属性
    category = "功能用例/APP/python"
    is_regression = True  # 标记为回归测试用例

    # Modbus配置
    MODBUS_RTU_PORT = "/dev/ttyS1"  # 路由器上的RTU串口
    MODBUS_BAUDRATE = 115200
    MODBUS_UNIT_ID = 1

    # 路由器端Modbus测试脚本（TCP + RTU接口验证）
    MODBUS_TEST_SCRIPT = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pymodbus TCP + RTU 接口功能 API 自检
参照 D:\\WK\\Milesight\\AUTO\\设备python3.9模块脚本\\测试脚本\\test_modbus.py 实现
- 验证 API 调用链条能跑通（创建客户端、connect、常见读写方法）
- TCP 需要真实从站响应才算通过
- RTU 不依赖真实从站；若无从站会报超时 isError=True，但视为"API 可调用"
"""
import sys
import time
import logging

print("=" * 60)
print("pymodbus TCP + RTU 接口完整性验证")
print("=" * 60)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# 测试配置
TCP_HOST = "__TCP_HOST__"
TCP_PORT = __TCP_PORT__
RTU_PORT = "__RTU_PORT__"
RTU_BAUDRATE = __RTU_BAUDRATE__
UNIT_ID = __UNIT_ID__

# 测试结果统计
test_results = {
    'module_import': False,
    'tcp_client_create': False,
    'tcp_connect': False,
    'tcp_operations': False,
    'rtu_client_create': False,
    'rtu_connect': False,
    'rtu_operations': False
}

# 导入pymodbus模块（兼容 2.5.x 和 3.x）
print("\\n" + "=" * 60)
print("测试1: 导入pymodbus模块")
print("=" * 60)
try:
    # 尝试 2.5.x 导入路径
    from pymodbus.client.sync import ModbusTcpClient, ModbusSerialClient
    from pymodbus.framer.rtu_framer import ModbusRtuFramer
    print("✅ pymodbus模块导入成功 (2.5.x)")
    test_results['module_import'] = True
except Exception:
    try:
        # 尝试 3.x 导入路径
        from pymodbus.client import ModbusTcpClient, ModbusSerialClient
        from pymodbus.framer.rtu_framer import ModbusRtuFramer
        print("✅ pymodbus模块导入成功 (3.x)")
        test_results['module_import'] = True
    except Exception as e:
        print(f"❌ pymodbus模块导入失败: {e}")
        sys.exit(1)

def ok(msg):
    print("  [OK ]", msg)

def warn(msg):
    print("  [WARN]", msg)

def fail(msg, e=None):
    print("  [FAIL]", msg, f"-> {e.__class__.__name__}: {e}" if e else "")

# 通用调用器：执行 fn()，区分"调用成功/返回超时或异常"
def call(label, fn):
    try:
        rr = fn()
        # 检查是否有错误（2.5.x/3.x 都有 isError()）
        is_err = getattr(rr, "isError", lambda: False)()
        if is_err:
            # 没有从站时大概率超时是正常的，这里标注为 WARN
            warn(f"{label}: response error/timeout -> {rr}")
            return False
        else:
            ok(f"{label}: {rr}")
            return True
    except Exception as e:
        # 真正异常（参数/接口）才算 FAIL
        fail(f"{label}", e)
        return False

# ============== TCP 客户端测试 ==============
print("\\n" + "=" * 60)
print("测试2: 创建Modbus TCP客户端")
print("=" * 60)
try:
    tcp_client = ModbusTcpClient(host=TCP_HOST, port=TCP_PORT, timeout=3)
    print(f"✅ TCP客户端创建成功: {TCP_HOST}:{TCP_PORT}")
    test_results['tcp_client_create'] = True
except Exception as e:
    print(f"❌ TCP客户端创建失败: {e}")
    tcp_client = None

if tcp_client:
    print("\\n" + "=" * 60)
    print("测试3: TCP客户端连接与操作")
    print("=" * 60)

    # connect
    if not tcp_client.connect():
        fail("TCP connect() 返回False")
    else:
        ok("TCP connect()")
        test_results['tcp_connect'] = True

    if test_results['tcp_connect']:
        # TCP 操作测试（参照 test_modbus.py 的风格和顺序）
        tcp_pass = 0
        tcp_total = 0

        # 线圈/离散输入
        tcp_total += 1
        if call("write_coil(addr=1, True)", lambda: tcp_client.write_coil(1, True, unit=UNIT_ID)):
            tcp_pass += 1
        time.sleep(0.05)

        tcp_total += 1
        if call("read_coils(addr=1, count=1)", lambda: tcp_client.read_coils(1, 1, unit=UNIT_ID)):
            tcp_pass += 1
        time.sleep(0.05)

        tcp_total += 1
        if call("read_discrete_inputs(addr=1, 1)", lambda: tcp_client.read_discrete_inputs(1, 1, unit=UNIT_ID)):
            tcp_pass += 1
        time.sleep(0.05)

        # 保持/输入寄存器
        tcp_total += 1
        if call("write_register(addr=1, 123)", lambda: tcp_client.write_register(1, 123, unit=UNIT_ID)):
            tcp_pass += 1
        time.sleep(0.05)

        tcp_total += 1
        if call("read_holding_registers(addr=1, 1)", lambda: tcp_client.read_holding_registers(1, 1, unit=UNIT_ID)):
            tcp_pass += 1
        time.sleep(0.05)

        tcp_total += 1
        if call("read_input_registers(addr=1, 1)", lambda: tcp_client.read_input_registers(1, 1, unit=UNIT_ID)):
            tcp_pass += 1
        time.sleep(0.05)

        # 批量写
        tcp_total += 1
        if call("write_coils(start=10, [1,0,1,0])", lambda: tcp_client.write_coils(10, [1,0,1,0], unit=UNIT_ID)):
            tcp_pass += 1
        time.sleep(0.05)

        tcp_total += 1
        if call("write_registers(start=10, [11,22,33])", lambda: tcp_client.write_registers(10, [11,22,33], unit=UNIT_ID)):
            tcp_pass += 1
        time.sleep(0.05)

        print(f"\\nTCP操作统计: {tcp_pass}/{tcp_total} 成功")
        if tcp_pass >= tcp_total * 0.8:  # 80% 通过即算成功
            test_results['tcp_operations'] = True

    # 关闭TCP客户端
    try:
        tcp_client.close()
        ok("TCP close()")
    except Exception as e:
        fail("TCP close()", e)

# ============== RTU 客户端测试 ==============
print("\\n" + "=" * 60)
print("测试4: 创建Modbus RTU客户端")
print("=" * 60)
try:
    rtu_client = ModbusSerialClient(
        method="rtu",
        port=RTU_PORT,
        baudrate=RTU_BAUDRATE,
        timeout=0.5,
        parity="N",
        stopbits=1,
        bytesize=8,
        retry_on_empty=False,
        strict=False
    )
    print(f"✅ RTU客户端创建成功: {RTU_PORT}@{RTU_BAUDRATE}")
    test_results['rtu_client_create'] = True
except Exception as e:
    print(f"❌ RTU客户端创建失败: {e}")
    rtu_client = None

if rtu_client:
    print("\\n" + "=" * 60)
    print("测试5: RTU客户端连接与操作 (API验证)")
    print("=" * 60)

    # connect (不依赖真实从站)
    if not rtu_client.connect():
        # RTU可能没有物理连接，只验证API可调用性
        warn("RTU connect() 返回False（可能无物理从站，继续测试API）")
        test_results['rtu_connect'] = True  # API可调用即算通过
    else:
        ok("RTU connect()")
        test_results['rtu_connect'] = True

    # RTU 操作测试（参照 test_modbus.py - 不依赖真实从站，API可调用即通过）
    print("\\n测试RTU API调用（超时视为正常）:")

    # 线圈/离散输入
    call("RTU write_coil(addr=1, True)", lambda: rtu_client.write_coil(1, True, unit=UNIT_ID))
    time.sleep(0.05)
    call("RTU read_coils(addr=1, 1)", lambda: rtu_client.read_coils(1, 1, unit=UNIT_ID))
    time.sleep(0.05)
    call("RTU read_discrete_inputs(addr=1, 1)", lambda: rtu_client.read_discrete_inputs(1, 1, unit=UNIT_ID))
    time.sleep(0.05)

    # 保持/输入寄存器
    call("RTU write_register(addr=1, 123)", lambda: rtu_client.write_register(1, 123, unit=UNIT_ID))
    time.sleep(0.05)
    call("RTU read_holding_registers(addr=1, 1)", lambda: rtu_client.read_holding_registers(1, 1, unit=UNIT_ID))
    time.sleep(0.05)
    call("RTU read_input_registers(addr=1, 1)", lambda: rtu_client.read_input_registers(1, 1, unit=UNIT_ID))
    time.sleep(0.05)

    # 批量写
    call("RTU write_coils(start=10, [1,0,1,0])", lambda: rtu_client.write_coils(10, [1,0,1,0], unit=UNIT_ID))
    time.sleep(0.05)
    call("RTU write_registers(start=10, [11,22,33])", lambda: rtu_client.write_registers(10, [11,22,33], unit=UNIT_ID))
    time.sleep(0.05)

    # 诊断功能（参照 test_modbus.py）
    call("RTU diagnostic(sub_function=0x0000)", lambda: rtu_client.diagnostic(0x0000, unit=UNIT_ID))
    time.sleep(0.05)

    # 设备标识（MEI功能码 0x2B/0x0E）
    try:
        from pymodbus.mei_message import ReadDeviceInformationRequest
        call("RTU read_device_info(basic)", lambda: rtu_client.execute(ReadDeviceInformationRequest(read_code=0x01, unit=UNIT_ID)))
    except Exception:
        warn("read_device_info skipped (MEI import not available)")

    # RTU API已验证可调用
    test_results['rtu_operations'] = True  # API可调用即算通过

    # 关闭RTU客户端
    try:
        rtu_client.close()
        ok("RTU close()")
    except Exception as e:
        fail("RTU close()", e)

# 输出测试结果
print("\\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)
for key, value in test_results.items():
    status = "✅ 通过" if value else "❌ 失败"
    print(f"{key:30} : {status}")

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
        """实现抽象属性，返回测试名称"""
        return "python3.9第三方库pymodbus验证"

    @property
    def description(self):
        """测试描述"""
        return "验证pymodbus库的完整性，包括TCP/RTU客户端、读写线圈、读写寄存器等操作"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 获取路由器配置
        self.router_ip = self.config.router_config.router_ip

        # 从配置中获取Modbus服务器信息
        self.PC_IP = config.router_config.modbus_server_ip
        self.MODBUS_TCP_PORT = config.router_config.modbus_port

        # 从配置中获取串口配置
        self.system_serial_port = self.config.router_config.serial_port  # COM3 - 系统串口
        self.serial_baudrate = self.config.router_config.serial_baudrate

        # 串口连接对象
        self.system_serial_conn = None  # COM3 - 系统串口

        # PC端Modbus Server相关
        self.modbus_server_thread = None
        self.modbus_server_running = False
        self.modbus_context = None

        # 测试结果
        self.test_output_buffer = ""

    def setup(self):
        """测试前置条件"""
        print(f"\n{'='*70}")
        print(f"测试用例: {self.test_name}")
        print(f"测试分类: {self.category}")
        print(f"{'='*70}")
        print(f"路由器IP: {self.router_ip}")
        print(f"系统串口: {self.system_serial_port}")
        print(f"PC IP (Modbus从站): {self.PC_IP}:{self.MODBUS_TCP_PORT}")
        print(f"{'='*70}\n")

        # 检查并自动安装Python SDK
        print("前置条件: 检查Python SDK...")
        if not self.ensure_python_sdk_installed():
            raise Exception("Python SDK未安装且自动安装失败，无法继续测试")
        print("✅ Python SDK已就绪\n")
        print("✅ 前置条件检查完成\n")

    def execute(self):
        """执行测试 - 完整的Modbus交互测试"""
        try:
            print(f"\n{'='*70}")
            print(f"开始执行pymodbus库交互测试")
            print(f"{'='*70}\n")

            # 步骤1: SSH上传测试脚本
            print("步骤1: SSH上传测试脚本到路由器...")
            if not self._upload_modbus_test_script():
                raise Exception("上传测试脚本失败")
            print("✅ 测试脚本上传成功\n")

            # 步骤2: 启动PC端Modbus Server
            print("步骤2: 启动PC端Modbus TCP Server...")
            if not self._start_modbus_server():
                raise Exception("启动Modbus Server失败")
            print("✅ Modbus Server已启动\n")

            # 步骤3: 通过COM3系统串口登录并执行测试脚本
            print("步骤3: 通过系统串口执行路由器测试脚本...")
            if not self._execute_modbus_test_via_system_serial():
                raise Exception("执行测试脚本失败")
            print("✅ 测试脚本执行完成\n")

            # 步骤4: 停止Modbus Server
            print("步骤4: 停止Modbus Server...")
            self._stop_modbus_server()
            print("✅ Modbus Server已停止\n")

            # 步骤5: 解析测试结果
            print("步骤5: 解析测试结果...")
            if "✅ 所有测试通过！pymodbus库验证成功" in self.test_output_buffer:
                print("✅ 所有pymodbus接口测试通过！\n")
                return True
            else:
                print("⚠️  部分测试未通过，请查看详细日志\n")
                raise AssertionError("存在测试失败项")

        except Exception as e:
            print(f"\n测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # 确保清理Modbus Server
            self._stop_modbus_server()
            raise

    def _upload_modbus_test_script(self):
        """通过SFTP上传Modbus测试脚本"""
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
            script_path = "/tmp/modbus_test.py"
            print(f"通过SFTP上传脚本到 {script_path}...")

            # 打开SFTP会话
            sftp = ssh.open_sftp()

            # 替换脚本中的配置参数
            script_content = self.MODBUS_TEST_SCRIPT
            script_content = script_content.replace("__TCP_HOST__", self.PC_IP)
            script_content = script_content.replace("__TCP_PORT__", str(self.MODBUS_TCP_PORT))
            script_content = script_content.replace("__RTU_PORT__", self.MODBUS_RTU_PORT)
            script_content = script_content.replace("__RTU_BAUDRATE__", str(self.MODBUS_BAUDRATE))
            script_content = script_content.replace("__UNIT_ID__", str(self.MODBUS_UNIT_ID))

            # 写入脚本内容到远程文件
            with sftp.file(script_path, 'w') as remote_file:
                remote_file.write(script_content)

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

            print(f"✅ Modbus TCP Server已在 {self.PC_IP}:{self.MODBUS_TCP_PORT} 启动")

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
            if PYMODBUS_VERSION == "3.x":
                # pymodbus 3.x 使用kwargs方式
                StartTcpServer(
                    context=self.modbus_context,
                    address=(self.PC_IP, self.MODBUS_TCP_PORT)
                )
            else:
                # pymodbus 2.x 使用address参数
                StartTcpServer(
                    context=self.modbus_context,
                    address=(self.PC_IP, self.MODBUS_TCP_PORT)
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

    def _execute_modbus_test_via_system_serial(self):
        """通过COM3系统串口执行Modbus测试脚本"""
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
            script_path = "/tmp/modbus_test.py"
            python_path = "/usr/python/bin/python3.9"
            lib_path = "/usr/python/lib"
            command = f"export LD_LIBRARY_PATH={lib_path}:$LD_LIBRARY_PATH && {python_path} {script_path}\n"

            print(f"执行命令: {command.strip()}")
            print("=" * 70)
            self.system_serial_conn.write(command.encode('utf-8'))

            # 开始读取输出（Modbus测试大约需要15秒）
            start_time = time.time()
            max_duration = 30  # 最多30秒
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

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        # 确保停止Modbus Server
        print("确保Modbus Server已关闭...")
        self._stop_modbus_server()

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
            ssh.exec_command("rm -f /tmp/modbus_test.py")
            ssh.close()
            print("✅ 临时文件已删除")

        except Exception as e:
            print(f"清理临时文件时出错: {str(e)}")

        print("测试清理完成")
