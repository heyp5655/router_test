# -*- coding: utf-8 -*-
"""
测试用例ID4: Python3.9第三方库paho-mqtt验证

测试项：功能用例/APP/python
测试点：python3.9第三方库paho-mqtt验证
前置条件：实际环境中已有可用的MQTT服务器

测试步骤：
1. 确保路由器已经安装python3.9的环境，如果没有安装需要自行安装
2. 需要进行交互式测试，开启两个进程：
   - 进程A：通过本地COM3进入路由器后台，用路由器python调用MQTT接口连接MQTT服务器
   - 进程B：用电脑本地MQTT客户端连接同一个MQTT服务器
   - 交互验证：A发布→B订阅，B发布→A订阅

预期：
接口调用不报错，交互过程没有错误
"""
from test_cases.base_test import BaseTest
import time
import paramiko
import serial
import threading
import paho.mqtt.client as mqtt


class PahoMqttLibraryTest(BaseTest):
    """Python3.9第三方库paho-mqtt验证"""

    category = "功能用例/APP/python"
    is_regression = True

    # MQTT测试主题
    TOPIC_ROUTER_TO_PC = "test/router_to_pc"
    TOPIC_PC_TO_ROUTER = "test/pc_to_router"

    # 路由器端paho-mqtt测试脚本
    MQTT_TEST_SCRIPT = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路由器端paho-mqtt接口验证脚本"""
import sys
import time
import threading

print("=" * 60)
print("paho-mqtt接口验证测试")
print("=" * 60)

# 步骤1: 导入paho-mqtt模块
print("\\n步骤1: 导入paho-mqtt模块")
try:
    import paho.mqtt.client as mqtt
    print("✅ paho-mqtt模块导入成功")
except ImportError as e:
    print(f"❌ paho-mqtt模块导入失败: {e}")
    sys.exit(1)

# MQTT配置
BROKER = "__BROKER__"
PORT = __PORT__
USERNAME = "__USERNAME__"
PASSWORD = "__PASSWORD__"
TOPIC_PUB = "__TOPIC_PUB__"
TOPIC_SUB = "__TOPIC_SUB__"

# 测试结果统计
test_results = {
    'client_create': False,
    'connect': False,
    'subscribe': False,
    'publish': False,
    'message_received': False,
    'disconnect': False
}

# 事件标记
connected_event = threading.Event()
subscribed_event = threading.Event()
message_received_event = threading.Event()
received_messages = []

# 回调函数
def on_connect(client, userdata, flags, rc):
    print(f"\\n【回调】on_connect触发，rc={rc}")
    if rc == 0:
        print(f"✅ 连接成功")
        test_results['connect'] = True
        connected_event.set()
    else:
        print(f"❌ 连接失败，返回码: {rc}")

def on_subscribe(client, userdata, mid, granted_qos):
    print(f"\\n【回调】on_subscribe触发，mid={mid}, qos={granted_qos}")
    print(f"✅ 订阅成功")
    test_results['subscribe'] = True
    subscribed_event.set()

def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8')
    print(f"\\n【回调】on_message触发")
    print(f"✅ 收到消息: {payload}")
    print(f"   主题: {msg.topic}, QoS: {msg.qos}")
    received_messages.append(payload)
    test_results['message_received'] = True
    message_received_event.set()

def on_disconnect(client, userdata, rc):
    print(f"\\n【回调】on_disconnect触发，rc={rc}")

# 步骤2: 创建MQTT客户端
print("\\n步骤2: 创建MQTT客户端")
try:
    client = mqtt.Client(client_id="router_test_client", clean_session=True)
    print("✅ 客户端创建成功")
    test_results['client_create'] = True

    # 设置回调函数
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    print("✅ 回调函数设置成功")
except Exception as e:
    print(f"❌ 客户端创建失败: {e}")
    sys.exit(1)

# 步骤3: 设置认证信息
print("\\n步骤3: 设置认证信息")
try:
    client.username_pw_set(USERNAME, PASSWORD)
    print("✅ 认证信息设置成功")
except Exception as e:
    print(f"❌ 认证设置失败: {e}")

# 步骤4: 连接MQTT服务器
print("\\n步骤4: 连接MQTT服务器")
try:
    print(f"连接到 {BROKER}:{PORT}")
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()
    print("✅ loop_start()已启动")

    # 等待连接建立
    if connected_event.wait(timeout=10):
        print("✅ 连接成功（通过事件确认）")
    else:
        print("❌ 连接超时")
        sys.exit(1)
except Exception as e:
    print(f"❌ 连接失败: {e}")
    sys.exit(1)

# 步骤5: 订阅主题
print("\\n步骤5: 订阅主题")
try:
    result = client.subscribe(TOPIC_SUB, qos=1)
    print(f"订阅主题: {TOPIC_SUB}, QoS=1")

    if subscribed_event.wait(timeout=5):
        print("✅ 订阅确认")
    else:
        print("⚠️  订阅可能超时")
except Exception as e:
    print(f"❌ 订阅失败: {e}")

# 步骤6: 发布消息
print("\\n步骤6: 发布消息")
try:
    test_message = "ROUTER_MESSAGE_TO_PC_TEST_123"
    info = client.publish(TOPIC_PUB, test_message, qos=1)
    print(f"✅ 发布成功: {test_message}")
    test_results['publish'] = True
    time.sleep(1)
except Exception as e:
    print(f"❌ 发布失败: {e}")

# 步骤7: 等待接收PC发布的消息
print("\\n步骤7: 等待接收PC发布的消息")
print("等待10秒...")
if message_received_event.wait(timeout=10):
    print(f"✅ 成功接收到 {len(received_messages)} 条消息")
    for i, msg in enumerate(received_messages, 1):
        print(f"   消息{i}: {msg}")
else:
    print("⚠️  未收到消息（可能PC端未发送）")

# 步骤8: 断开连接
print("\\n步骤8: 断开连接")
try:
    client.loop_stop()
    client.disconnect()
    print("✅ 已断开连接")
    test_results['disconnect'] = True
    time.sleep(1)
except Exception as e:
    print(f"❌ 断开连接失败: {e}")

# 输出测试结果
print("\\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)
print(f"客户端创建: {'✅ 通过' if test_results['client_create'] else '❌ 失败'}")
print(f"连接服务器: {'✅ 通过' if test_results['connect'] else '❌ 失败'}")
print(f"订阅主题: {'✅ 通过' if test_results['subscribe'] else '❌ 失败'}")
print(f"发布消息: {'✅ 通过' if test_results['publish'] else '❌ 失败'}")
print(f"接收消息: {'✅ 通过' if test_results['message_received'] else '❌ 失败'}")
print(f"断开连接: {'✅ 通过' if test_results['disconnect'] else '❌ 失败'}")

# 总体结果
all_passed = all(test_results.values())
print("\\n" + "=" * 60)
if all_passed:
    print("✅ 所有测试通过！paho-mqtt库验证成功")
    sys.exit(0)
else:
    failed_tests = [k for k, v in test_results.items() if not v]
    print(f"❌ 存在测试失败项: {failed_tests}")
    sys.exit(1)
'''

    @property
    def test_name(self):
        return "python3.9第三方库paho-mqtt验证"

    @property
    def description(self):
        return "验证paho-mqtt库接口完整性，包括客户端创建、连接、发布、订阅及双向通信"

    def __init__(self, config):
        super().__init__(config)

        # 路由器配置
        self.router_ip = self.config.router_config.router_ip

        # MQTT服务器配置
        self.mqtt_broker = config.router_config.mqtt_broker
        self.mqtt_port = config.router_config.mqtt_port
        self.mqtt_username = "admin"
        self.mqtt_password = "password"

        # 系统串口配置（COM3）
        self.system_serial_port = self.config.router_config.serial_port
        self.serial_baudrate = self.config.router_config.serial_baudrate

        # 串口连接对象
        self.system_serial_conn = None

        # PC端MQTT客户端
        self.pc_mqtt_client = None
        self.pc_mqtt_thread = None
        self.pc_mqtt_running = False
        self.pc_received_messages = []

        # 测试结果
        self.test_output_buffer = ""

    def setup(self):
        """测试前置条件"""
        print(f"\n{'='*70}")
        print(f"测试用例ID4: {self.test_name}")
        print(f"测试分类: {self.category}")
        print(f"{'='*70}")
        print(f"路由器IP: {self.router_ip}")
        print(f"系统串口: {self.system_serial_port}")
        print(f"MQTT服务器: {self.mqtt_broker}:{self.mqtt_port}")
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
            print(f"开始执行paho-mqtt双向交互测试")
            print(f"{'='*70}\n")

            # 步骤1: 上传测试脚本到路由器
            print("步骤1: 上传测试脚本到路由器...")
            if not self._upload_test_script():
                raise Exception("上传测试脚本失败")
            print("✅ 测试脚本上传成功\n")

            # 步骤2: 启动PC端MQTT客户端（进程B）
            print("步骤2: 启动PC端MQTT客户端...")
            if not self._start_pc_mqtt_client():
                raise Exception("启动PC端MQTT客户端失败")
            print("✅ PC端MQTT客户端已启动\n")

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

            # 步骤4: 停止PC端MQTT客户端
            print("步骤4: 停止PC端MQTT客户端...")
            self._stop_pc_mqtt_client()
            print("✅ PC端MQTT客户端已停止\n")

            # 步骤5: 解析测试结果
            print("步骤5: 解析测试结果...")
            print(f"\n{'='*70}")
            print("路由器端输出内容:")
            print(f"{'='*70}")
            print(self.test_output_buffer if self.test_output_buffer else "（无输出）")
            print(f"{'='*70}\n")

            if "✅ 所有测试通过！paho-mqtt库验证成功" in self.test_output_buffer:
                print("✅ 所有paho-mqtt接口测试通过！\n")
                print(f"PC端接收到的消息: {len(self.pc_received_messages)} 条")
                for i, msg in enumerate(self.pc_received_messages, 1):
                    print(f"  {i}. {msg}")
                return True
            else:
                print("❌ 部分测试未通过\n")
                raise AssertionError("存在测试失败项")

        except Exception as e:
            print(f"\n❌ 测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            self._stop_pc_mqtt_client()
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
            script_content = self.MQTT_TEST_SCRIPT
            script_content = script_content.replace("__BROKER__", self.mqtt_broker)
            script_content = script_content.replace("__PORT__", str(self.mqtt_port))
            script_content = script_content.replace("__USERNAME__", self.mqtt_username)
            script_content = script_content.replace("__PASSWORD__", self.mqtt_password)
            script_content = script_content.replace("__TOPIC_PUB__", self.TOPIC_ROUTER_TO_PC)
            script_content = script_content.replace("__TOPIC_SUB__", self.TOPIC_PC_TO_ROUTER)

            # 上传脚本
            script_path = "/tmp/mqtt_test.py"
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

    def _start_pc_mqtt_client(self):
        """启动PC端MQTT客户端"""
        try:
            # 创建MQTT客户端
            self.pc_mqtt_client = mqtt.Client(client_id="pc_test_client", clean_session=True)
            self.pc_mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)

            # 设置回调
            self.pc_mqtt_client.on_connect = self._on_pc_connect
            self.pc_mqtt_client.on_message = self._on_pc_message

            # 连接到服务器
            self.pc_mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)

            # 启动监听线程
            self.pc_mqtt_running = True
            self.pc_mqtt_thread = threading.Thread(target=self._pc_mqtt_loop)
            self.pc_mqtt_thread.daemon = True
            self.pc_mqtt_thread.start()

            print(f"✅ PC端MQTT客户端连接到 {self.mqtt_broker}:{self.mqtt_port}")

            # 等待连接建立
            time.sleep(2)

            return True

        except Exception as e:
            print(f"启动PC端MQTT客户端失败: {str(e)}")
            return False

    def _on_pc_connect(self, client, userdata, flags, rc):
        """PC端连接回调"""
        if rc == 0:
            print("PC端MQTT客户端连接成功")
            # 订阅路由器发布的主题
            client.subscribe(self.TOPIC_ROUTER_TO_PC)
            print(f"PC端已订阅主题: {self.TOPIC_ROUTER_TO_PC}")
        else:
            print(f"PC端MQTT客户端连接失败，返回码: {rc}")

    def _on_pc_message(self, client, userdata, msg):
        """PC端消息回调 - 自动响应路由器的消息"""
        payload = msg.payload.decode('utf-8')
        print(f"PC端收到消息: topic={msg.topic}, payload={payload}")
        self.pc_received_messages.append(payload)

        # 如果收到路由器的测试消息，自动回复
        if "ROUTER_MESSAGE" in payload:
            time.sleep(0.5)  # 延迟0.5秒后回复
            response = "PC_RESPONSE_TO_ROUTER_456"
            client.publish(self.TOPIC_PC_TO_ROUTER, response, qos=1)
            print(f"PC端自动回复: {response}")

    def _pc_mqtt_loop(self):
        """PC端MQTT循环"""
        self.pc_mqtt_client.loop_forever()

    def _stop_pc_mqtt_client(self):
        """停止PC端MQTT客户端"""
        try:
            if self.pc_mqtt_client:
                self.pc_mqtt_client.loop_stop()
                self.pc_mqtt_client.disconnect()
                print("PC端MQTT客户端已断开")

            if self.pc_mqtt_thread and self.pc_mqtt_thread.is_alive():
                self.pc_mqtt_running = False
        except Exception as e:
            print(f"停止PC端MQTT客户端失败: {str(e)}")

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
            script_path = "/tmp/mqtt_test.py"
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
            script_path = "/tmp/mqtt_test.py"
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

        # 停止MQTT客户端
        self._stop_pc_mqtt_client()

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
            ssh.exec_command("rm -f /tmp/mqtt_test.py")
            ssh.close()
            print("✅ 临时文件已删除")
        except Exception as e:
            print(f"清理临时文件失败: {str(e)}")

        print("测试清理完成")
