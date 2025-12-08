# -*- coding: utf-8 -*-
from test_cases.base_test import BaseTest
import time
import paramiko
import serial
import threading
import queue
import paho.mqtt.client as mqtt


class PahoMqttLibraryTest(BaseTest):
    """Python3.9第三方库paho-mqtt验证

    测试项：功能用例/APP/python
    测试点：paho-mqtt库接口完整性验证

    前置条件：
    实际环境中已有可用的MQTT服务器

    测试步骤：
    1. 确保路由器已经安装python3.9的环境，如果没有安装需要自行安装
    2. 需要进行交互式测试，开启两个进程：
       - 进程A：通过本地COM3进入路由器后台，用路由器python调用MQTT接口
       - 进程B：用电脑本地MQTT客户端模拟另一个客户端
       - 交互验证：A发布→B订阅，B发布→A订阅

    预期：
    接口调用不报错，交互过程没有错误
    所有测试项通过，包括模块导入、客户端创建、连接、发布、订阅、回调等
    """

    # 添加分类信息属性
    category = "功能用例/APP/python"
    is_regression = True  # 标记为回归测试用例

    # 测试主题
    TOPIC_ROUTER_TO_PC = "test/router_to_pc"
    TOPIC_PC_TO_ROUTER = "test/pc_to_router"

    # 路由器端MQTT测试脚本（参考完整版接口验证）
    MQTT_TEST_SCRIPT = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import time
import threading

print("=" * 60)
print("paho-mqtt接口完整性验证")
print("=" * 60)

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
TOPIC_BASE = "__TOPIC_PUB__"
TOPIC_ECHO = "__TOPIC_SUB__"

# 测试结果统计
test_results = {
    'module_import': True,  # 已通过
    'client_create': False,
    'will_set': False,
    'auth_set': False,
    'connect': False,
    'subscribe': False,
    'publish_qos0': False,
    'publish_qos1': False,
    'publish_qos2': False,
    'message_received': False,
    'unsubscribe': False,
    'disconnect': False
}

# 接收到的消息
received_messages = []
connected_event = threading.Event()
subscribed_event = threading.Event()
message_received_event = threading.Event()
publish_mid_done = set()
publish_lock = threading.Lock()

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
    print(f"   主题: {msg.topic}, QoS: {msg.qos}, Retain: {msg.retain}")
    received_messages.append((msg.topic, payload, msg.qos))
    test_results['message_received'] = True
    message_received_event.set()

def on_publish(client, userdata, mid):
    with publish_lock:
        publish_mid_done.add(mid)
    print(f"【回调】on_publish触发，mid={mid}")

def on_disconnect(client, userdata, rc):
    print(f"\\n【回调】on_disconnect触发，rc={rc}")

def on_unsubscribe(client, userdata, mid):
    print(f"\\n【回调】on_unsubscribe触发，mid={mid}")

print("\\n" + "=" * 60)
print("测试1: 创建MQTT客户端")
print("=" * 60)
try:
    client = mqtt.Client(client_id="router_test_client", clean_session=True)
    print("✅ 客户端创建成功")
    test_results['client_create'] = True

    # 设置回调函数
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.on_unsubscribe = on_unsubscribe
    print("✅ 回调函数设置成功")
except Exception as e:
    print(f"❌ 客户端创建失败: {e}")
    sys.exit(1)

print("\\n" + "=" * 60)
print("测试2: 设置遗嘱(will_set)")
print("=" * 60)
try:
    client.will_set(TOPIC_BASE + "/will", b"client_offline", qos=1, retain=True)
    print("✅ 遗嘱设置成功")
    test_results['will_set'] = True
except Exception as e:
    print(f"❌ 遗嘱设置失败: {e}")

print("\\n" + "=" * 60)
print("测试3: 设置认证信息")
print("=" * 60)
try:
    client.username_pw_set(USERNAME, PASSWORD)
    print("✅ 认证信息设置成功")
    test_results['auth_set'] = True
except Exception as e:
    print(f"❌ 认证设置失败: {e}")

print("\\n" + "=" * 60)
print("测试4: 连接MQTT服务器")
print("=" * 60)
try:
    print(f"连接到 {BROKER}:{PORT}")
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()  # 启动后台循环
    print("✅ loop_start()已启动")

    # 等待连接建立
    if connected_event.wait(timeout=5):
        print("✅ 连接成功（通过事件确认）")
    else:
        print("❌ 连接超时")
        sys.exit(1)
except Exception as e:
    print(f"❌ 连接失败: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)

print("\\n" + "=" * 60)
print("测试5: 订阅主题")
print("=" * 60)
try:
    result = client.subscribe(TOPIC_ECHO, qos=2)
    print(f"订阅主题: {TOPIC_ECHO}, QoS=2")

    if subscribed_event.wait(timeout=3):
        print("✅ 订阅确认（通过事件）")
    else:
        print("⚠️  订阅可能超时")
except Exception as e:
    print(f"❌ 订阅失败: {e}")

print("\\n" + "=" * 60)
print("测试6: 发布消息 - QoS 0/1/2")
print("=" * 60)

# QoS 0
try:
    test_message = "ROUTER_MESSAGE_QOS0"
    info = client.publish(TOPIC_BASE, test_message, qos=0)
    print(f"✅ QoS 0 发布成功: {test_message}")
    test_results['publish_qos0'] = True
except Exception as e:
    print(f"❌ QoS 0 发布失败: {e}")

# QoS 1
try:
    test_message = "ROUTER_MESSAGE_QOS1"
    info = client.publish(TOPIC_BASE, test_message, qos=1)
    # 等待mid确认
    time.sleep(0.5)
    with publish_lock:
        if info.mid in publish_mid_done:
            print(f"✅ QoS 1 发布成功: {test_message}, mid={info.mid}")
            test_results['publish_qos1'] = True
        else:
            print(f"⚠️  QoS 1 mid={info.mid} 未确认")
except Exception as e:
    print(f"❌ QoS 1 发布失败: {e}")

# QoS 2
try:
    test_message = "ROUTER_MESSAGE_QOS2"
    info = client.publish(TOPIC_BASE, test_message, qos=2)
    # 等待mid确认
    time.sleep(0.5)
    with publish_lock:
        if info.mid in publish_mid_done:
            print(f"✅ QoS 2 发布成功: {test_message}, mid={info.mid}")
            test_results['publish_qos2'] = True
        else:
            print(f"⚠️  QoS 2 mid={info.mid} 未确认")
except Exception as e:
    print(f"❌ QoS 2 发布失败: {e}")

print("\\n" + "=" * 60)
print("测试7: 等待接收PC发布的消息")
print("=" * 60)
print("等待5秒...")
if message_received_event.wait(timeout=5):
    print(f"✅ 成功接收到 {len(received_messages)} 条消息")
    for i, (topic, msg, qos) in enumerate(received_messages, 1):
        print(f"   消息{i}: topic={topic}, qos={qos}, payload={msg}")
else:
    print("⚠️  未收到消息（可能PC端未发送）")

print("\\n" + "=" * 60)
print("测试8: 取消订阅")
print("=" * 60)
try:
    client.unsubscribe(TOPIC_ECHO)
    print(f"✅ 已取消订阅: {TOPIC_ECHO}")
    test_results['unsubscribe'] = True
    time.sleep(0.5)
except Exception as e:
    print(f"❌ 取消订阅失败: {e}")

print("\\n" + "=" * 60)
print("测试9: 断开连接")
print("=" * 60)
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
for key, value in test_results.items():
    status = "✅ 通过" if value else "❌ 失败"
    print(f"{key:20} : {status}")

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
        """实现抽象属性，返回测试名称"""
        return "python3.9第三方库paho-mqtt验证"

    @property
    def description(self):
        """测试描述"""
        return "验证paho-mqtt库的完整性，包括模块导入、客户端创建、连接、发布、订阅及双向通信"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 获取路由器配置
        self.router_ip = self.config.router_config.router_ip

        # 从配置中获取MQTT服务器信息
        self.MQTT_BROKER = config.router_config.mqtt_broker
        self.MQTT_PORT = config.router_config.mqtt_port
        self.MQTT_USERNAME = "admin"
        self.MQTT_PASSWORD = "password"

        # 从配置中获取串口配置
        self.system_serial_port = self.config.router_config.serial_port  # COM3 - 系统串口
        self.serial_baudrate = self.config.router_config.serial_baudrate

        # 串口连接对象
        self.system_serial_conn = None  # COM3 - 系统串口

        # PC端MQTT客户端相关
        self.pc_mqtt_client = None
        self.pc_mqtt_thread = None
        self.pc_mqtt_running = False
        self.pc_received_messages = []
        self.pc_message_queue = queue.Queue()

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
        print(f"MQTT服务器: {self.MQTT_BROKER}:{self.MQTT_PORT}")
        print(f"{'='*70}\n")

        # 检查并自动安装Python SDK
        print("前置条件: 检查Python SDK...")
        if not self.ensure_python_sdk_installed():
            raise Exception("Python SDK未安装且自动安装失败，无法继续测试")
        print("✅ Python SDK已就绪\n")
        print("✅ 前置条件检查完成\n")

    def execute(self):
        """执行测试 - 完整的MQTT双向交互测试"""
        try:
            print(f"\n{'='*70}")
            print(f"开始执行paho-mqtt库双向交互测试")
            print(f"{'='*70}\n")

            # 步骤1: SSH上传测试脚本
            print("步骤1: SSH上传测试脚本到路由器...")
            if not self._upload_mqtt_test_script():
                raise Exception("上传测试脚本失败")
            print("✅ 测试脚本上传成功\n")

            # 步骤2: 启动PC端MQTT客户端
            print("步骤2: 启动PC端MQTT客户端...")
            if not self._start_pc_mqtt_client():
                raise Exception("启动PC端MQTT客户端失败")
            print("✅ PC端MQTT客户端已启动\n")

            # 步骤3: 通过COM3系统串口登录并执行测试脚本
            print("步骤3: 通过系统串口执行路由器测试脚本...")
            if not self._execute_mqtt_test_via_system_serial():
                raise Exception("执行测试脚本失败")
            print("✅ 测试脚本执行完成\n")

            # 步骤4: 停止PC端MQTT客户端
            print("步骤4: 停止PC端MQTT客户端...")
            self._stop_pc_mqtt_client()
            print("✅ PC端MQTT客户端已停止\n")

            # 步骤5: 解析测试结果
            print("步骤5: 解析测试结果...")
            if "✅ 所有测试通过！paho-mqtt库验证成功" in self.test_output_buffer:
                print("✅ 所有paho-mqtt接口测试通过！\n")
                print(f"PC端统计:")
                print(f"  - 接收到的消息: {len(self.pc_received_messages)} 条")
                for i, msg in enumerate(self.pc_received_messages, 1):
                    print(f"    {i}. {msg}")
                return True
            else:
                print("⚠️  部分测试未通过，请查看详细日志\n")
                raise AssertionError("存在测试失败项")

        except Exception as e:
            print(f"\n测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # 确保清理MQTT客户端
            self._stop_pc_mqtt_client()
            raise

    def _upload_mqtt_test_script(self):
        """通过SFTP上传MQTT测试脚本"""
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
            script_path = "/tmp/mqtt_test.py"
            print(f"通过SFTP上传脚本到 {script_path}...")

            # 打开SFTP会话
            sftp = ssh.open_sftp()

            # 使用字符串替换而不是format()来避免转义问题
            script_content = self.MQTT_TEST_SCRIPT
            script_content = script_content.replace("__BROKER__", self.MQTT_BROKER)
            script_content = script_content.replace("__PORT__", str(self.MQTT_PORT))
            script_content = script_content.replace("__USERNAME__", self.MQTT_USERNAME)
            script_content = script_content.replace("__PASSWORD__", self.MQTT_PASSWORD)
            script_content = script_content.replace("__TOPIC_PUB__", self.TOPIC_ROUTER_TO_PC)
            script_content = script_content.replace("__TOPIC_SUB__", self.TOPIC_PC_TO_ROUTER)

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

    def _start_pc_mqtt_client(self):
        """启动PC端MQTT客户端"""
        try:
            print(f"连接到MQTT服务器 {self.MQTT_BROKER}:{self.MQTT_PORT}...")

            # 创建MQTT客户端
            self.pc_mqtt_client = mqtt.Client(client_id="pc_test_client", clean_session=True)
            self.pc_mqtt_client.username_pw_set(self.MQTT_USERNAME, self.MQTT_PASSWORD)

            # 设置回调
            self.pc_mqtt_client.on_connect = self._on_pc_connect
            self.pc_mqtt_client.on_message = self._on_pc_message

            # 连接到服务器
            self.pc_mqtt_client.connect(self.MQTT_BROKER, self.MQTT_PORT, keepalive=60)

            # 启动监听线程
            self.pc_mqtt_running = True
            self.pc_mqtt_thread = threading.Thread(target=self._pc_mqtt_loop)
            self.pc_mqtt_thread.daemon = True
            self.pc_mqtt_thread.start()

            print("✅ PC端MQTT客户端连接成功")

            # 等待连接建立
            time.sleep(2)

            return True

        except Exception as e:
            print(f"启动PC端MQTT客户端失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
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
        """PC端消息回调 - 自动响应路由器的测试消息"""
        payload = msg.payload.decode('utf-8')
        print(f"PC端收到消息: topic={msg.topic}, qos={msg.qos}, payload={payload}")
        self.pc_received_messages.append(payload)

        # 自动响应路由器的测试消息
        if "ROUTER_MESSAGE" in payload:
            # 根据收到的QoS级别，回复相应的消息
            if "QOS0" in payload:
                response = "PC_RESPONSE_QOS0_OK"
                qos = 0
            elif "QOS1" in payload:
                response = "PC_RESPONSE_QOS1_OK"
                qos = 1
            elif "QOS2" in payload:
                response = "PC_RESPONSE_QOS2_OK"
                qos = 2
            else:
                response = "PC_RESPONSE_OK"
                qos = 1

            time.sleep(0.5)  # 延迟0.5秒回复
            print(f"PC端自动回复: {response} (QoS={qos})")
            client.publish(self.TOPIC_PC_TO_ROUTER, response, qos=qos)

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
                # 不需要join，因为是daemon线程
        except Exception as e:
            print(f"停止PC端MQTT客户端失败: {str(e)}")

    def _execute_mqtt_test_via_system_serial(self):
        """通过COM3系统串口执行MQTT测试脚本"""
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

            # 验证Python环境（新增）
            print("\n验证Python环境...")
            script_path = "/tmp/mqtt_test.py"
            python_path = "/usr/python/bin/python3.9"
            lib_path = "/usr/python/lib"

            validation_commands = [
                ("检查Python解释器", f"ls -l {python_path} 2>&1"),
                ("检查库路径", f"ls -ld {lib_path} 2>&1"),
                ("测试Python版本", f"{python_path} --version 2>&1"),
                ("测试导入paho-mqtt", f"{python_path} -c 'import paho.mqtt.client; print(\"paho-mqtt OK\")' 2>&1"),
            ]

            validation_failed = False
            for desc, cmd in validation_commands:
                print(f"  {desc}...")
                self.system_serial_conn.write(f"{cmd}\n".encode('utf-8'))
                time.sleep(1.5)  # 等待命令执行

                if self.system_serial_conn.in_waiting > 0:
                    output = self.system_serial_conn.read(self.system_serial_conn.in_waiting).decode('utf-8', errors='ignore')
                    # 只显示输出的前150个字符，避免过长
                    output_preview = output.strip()[:150]

                    # 检查是否有错误
                    if "No such file" in output or "cannot" in output.lower() or "error" in output.lower():
                        print(f"    ❌ 失败: {output_preview}")
                        validation_failed = True
                    else:
                        print(f"    ✅ 成功: {output_preview}")
                else:
                    print(f"    ⚠️  未收到输出")

            if validation_failed:
                print("\n⚠️  环境验证发现问题，但继续执行测试以获取更多诊断信息...\n")
            else:
                print("\n✅ Python环境验证通过\n")

            # 执行测试脚本
            # 添加 2>&1 将stderr重定向到stdout，捕获所有错误信息
            command = f"export LD_LIBRARY_PATH={lib_path}:$LD_LIBRARY_PATH && {python_path} {script_path} 2>&1\n"

            print(f"执行命令: {command.strip()}")
            print("=" * 70)
            self.system_serial_conn.write(command.encode('utf-8'))

            # 开始读取输出（MQTT测试大约需要15秒）
            start_time = time.time()
            max_duration = 60  # 最多60秒（增加容错时间）
            last_data_time = start_time
            no_data_timeout = 20  # 如果20秒没数据，认为脚本结束（增加容错时间）

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

        # 确保停止MQTT客户端
        print("确保PC端MQTT客户端已关闭...")
        self._stop_pc_mqtt_client()

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
            ssh.exec_command("rm -f /tmp/mqtt_test.py")
            ssh.close()
            print("✅ 临时文件已删除")

        except Exception as e:
            print(f"清理临时文件时出错: {str(e)}")

        print("测试清理完成")
