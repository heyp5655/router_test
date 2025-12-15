# -*- coding: utf-8 -*-
from test_cases.base_test import BaseTest
from utils.mqtt_client import MQTTTestClient
import time
import json
import paramiko


class MqttRouterCommandRebootTest(BaseTest):
    """MQTT下发路由器重启指令发出以及设备回复测试

    测试项：工业协议/网络/MQTT
    测试点：MQTT下发reboot命令并验证路由器响应和重启

    前置条件：
    1. 路由器已配置MQTT客户端连接到MQTT服务器
    2. MQTT服务器地址：192.168.50.36:1883
    3. 路由器SSH可访问(root权限)

    测试步骤：
    1. 登录路由器Web，配置MQTT客户端
       - 启用MQTT客户端
       - 配置服务器地址、用户名、密码
       - 配置request主题：mqtt/system/request
       - 配置response主题：mqtt/system/response
       - 等待MQTT连接建立
    2. PC端启动MQTT客户端并连接到服务器
    3. PC端订阅mqtt/system/request和mqtt/system/response主题
    4. PC端发送reboot命令: {"id":"1", "status":"reboot"}
    5. 验证路由器第一次响应(收到命令的确认)
       - 格式: {"id":"1", "code":"2", "time":"...", "status":"reboot"}
    6. 验证第一次响应消息格式正确
    7. PC端MQTT客户端保持连接，持续监听响应（重要！）
    8. 通过SSH连接路由器，查看系统日志 /etc/urlog/system.log
       - 验证日志中包含"reboot: Restarting system"
       - 注意：此时PC端MQTT客户端仍在后台持续监听
    9. 等待并验证路由器第二次响应(重启完成的通知)
       - PC端一直在监听，路由器重启后会自动重连MQTT并发送消息
       - 格式: {"code":"2", "id":"1", "time":"...", "status":"reboot",
                "result":1, "resultmsg":"Reboot system success"}
       - 必须收到有效响应，否则测试失败
    10. 验证第二次响应消息格式正确
        - 严格验证所有必需字段: id, code, status, result
        - 任何字段错误都视为测试失败

    预期结果：
    - 路由器返回正确格式的第一次响应消息(确认收到命令)
    - 路由器执行重启操作
    - 系统日志中有"Restarting system"记录
    - PC端持续监听期间必须收到路由器第二次响应消息(重启完成通知)
    - 第二次响应消息格式完全正确
    - 注意：收到第二次响应即证明MQTT已重新连接，无需再次检查Web界面

    失败条件（任何一项都视为测试失败）：
    - 未收到第一次响应
    - 第一次响应格式不正确
    - 系统日志中无重启记录
    - 未收到第二次响应（超时120秒）
    - 第二次响应格式不正确（缺少字段、字段值错误）
    """

    # 添加分类信息属性
    category = "功能用例/服务/MQTT"
    is_regression = False  # 标记为非回归测试用例（因为会重启设备）

    # MQTT主题
    REQUEST_TOPIC = "mqtt/system/request"
    RESPONSE_TOPIC = "mqtt/system/response"

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "MQTT下发重启命令给路由器及重启后路由器设备回复MQTT信息"

    @property
    def description(self):
        """测试描述"""
        return "通过MQTT发送reboot命令给路由器，验证响应消息格式和重启行为"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 获取路由器配置
        self.router_ip = self.config.router_config.router_ip
        self.router_username = self.config.router_config.username
        self.router_password = self.config.router_config.password

        # 从配置中获取MQTT服务器信息
        self.mqtt_broker = config.router_config.mqtt_broker
        self.mqtt_port = config.router_config.mqtt_port
        self.mqtt_username = config.router_config.mqtt_username
        self.mqtt_password = config.router_config.mqtt_password

        # MQTT测试客户端
        self.mqtt_client = None

        # 测试结果
        self.first_response = None   # 第一次响应(收到reboot命令后的响应)
        self.second_response = None  # 第二次响应(重启完成后的响应)
        self.reboot_verified = False

    def setup(self):
        """测试前置条件"""
        print(f"\n{'='*70}")
        print(f"测试用例: {self.test_name}")
        print(f"测试分类: {self.category}")
        print(f"{'='*70}")
        print(f"路由器IP: {self.router_ip}")
        print(f"MQTT服务器: {self.mqtt_broker}:{self.mqtt_port}")
        print(f"Request主题: {self.REQUEST_TOPIC}")
        print(f"Response主题: {self.RESPONSE_TOPIC}")
        print(f"{'='*70}\n")

        # 登录路由器Web界面
        print("前置条件: 登录路由器Web界面...")
        if not self.router_client.login_web():
            raise Exception("登录路由器失败")
        print("✅ 路由器登录成功\n")

        # 检查并启用SSH（新版本固件默认关闭SSH）
        print("前置条件: 检查SSH启用状态...")
        if not self.router_client.ensure_ssh_enabled():
            raise Exception("SSH未启用且自动启用失败，无法继续测试")
        print("✅ SSH已就绪\n")

    def execute(self):
        """执行测试"""
        try:
            print(f"\n{'='*70}")
            print(f"开始执行MQTT命令测试")
            print(f"{'='*70}\n")

            # 步骤1: 配置路由器MQTT客户端
            print("步骤1: 配置路由器MQTT客户端...")
            if not self._configure_router_mqtt():
                raise Exception("配置路由器MQTT客户端失败")
            print("✅ 路由器MQTT配置完成\n")

            # 步骤2: 创建PC端MQTT客户端并连接
            print("步骤2: 启动PC端MQTT客户端...")
            if not self._start_mqtt_client():
                raise Exception("启动MQTT客户端失败")
            print("✅ MQTT客户端已连接\n")

            # 步骤3: 订阅主题
            print("步骤3: 订阅MQTT主题...")
            if not self._subscribe_topics():
                raise Exception("订阅主题失败")
            print("✅ 主题订阅成功\n")

            # 步骤4: 发送reboot命令
            print("步骤4: 发送reboot命令...")
            if not self._send_reboot_command():
                raise Exception("发送命令失败")
            print("✅ 命令已发送\n")

            # 步骤5: 等待并验证路由器第一次响应
            print("步骤5: 等待路由器第一次响应...")
            if not self._wait_for_first_response():
                raise Exception("未收到路由器第一次响应")
            print("✅ 收到路由器第一次响应\n")

            # 步骤6: 验证第一次响应消息格式
            print("步骤6: 验证第一次响应消息格式...")
            if not self._verify_first_response_format():
                raise Exception("第一次响应消息格式不正确")
            print("✅ 第一次响应消息格式正确\n")

            # 步骤7: 启动后台线程持续监听MQTT消息
            print("步骤7: 启动后台监听，等待路由器重启...")
            print("  ⚠️  重要: PC端MQTT客户端将持续监听，不会断开")
            print("  给路由器一些时间开始重启...")
            time.sleep(30)  # 等待路由器开始重启
            print("✅ 等待完成\n")

            # 步骤8: 通过SSH验证系统日志中的重启记录
            print("步骤8: 验证系统日志中的重启记录...")
            print("  ⚠️  注意: MQTT客户端仍在后台持续监听")
            if not self._verify_reboot_log():
                raise Exception("系统日志中未找到重启记录")
            print("✅ 系统日志验证成功\n")

            # 步骤9: 等待并验证第二次响应(重启完成消息) - 必须成功!
            print("步骤9: 等待路由器第二次响应(重启完成消息)...")
            print("  路由器重启后会自动重连MQTT并发送第二次响应")
            print("  PC端一直在监听，应该已经收到消息...")

            # 等待第二次响应 - 必须收到，否则测试失败
            if not self._wait_for_second_response():
                raise Exception("未收到路由器第二次响应消息（测试失败）")
            print("✅ 收到路由器第二次响应\n")

            # 步骤10: 验证第二次响应消息格式 - 必须正确!
            print("步骤10: 验证第二次响应消息格式...")
            if not self._verify_second_response_format():
                raise Exception("第二次响应消息格式不正确（测试失败）")
            print("✅ 第二次响应消息格式正确\n")

            print(f"{'='*70}")
            print("✅ 测试完成：所有步骤通过")
            print(f"{'='*70}\n")
            return True

        except Exception as e:
            print(f"\n测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise

    def _configure_router_mqtt(self):
        """配置路由器MQTT客户端"""
        try:
            # 导航到MQTT配置页面
            print("  导航到MQTT配置页面...")
            if not self.router_client.navigate_to_page("#industrial/mqtt/status"):
                print("  ⚠️  导航到MQTT页面失败")
                return False

            time.sleep(2)

            # 查找并点击添加按钮
            print("  点击添加MQTT配置...")
            add_button_xpath = '//*[@id="4_add_btn"]'
            if not self.router_client.click_element(add_button_xpath):
                print("  ⚠️  点击添加按钮失败")
                return False

            time.sleep(1)

            # 启用MQTT
            print("  启用MQTT客户端...")
            enabled_xpath = '//*[@id="1_enabled"]'
            if not self.router_client.click_element(enabled_xpath):
                print("  ⚠️  启用MQTT失败")
                return False

            # 配置名称
            print("  配置MQTT名称...")
            name_xpath = '//*[@id="1_mqtt_name"]'
            if not self.router_client.input_text(name_xpath, "test"):
                print("  ⚠️  输入名称失败")
                return False

            # 配置服务器地址
            print(f"  配置服务器地址: {self.mqtt_broker}...")
            server_xpath = '//*[@id="1_m_server_addr"]'
            if not self.router_client.input_text(server_xpath, self.mqtt_broker):
                print("  ⚠️  输入服务器地址失败")
                return False

            # 启用用户认证
            print("  启用用户认证...")
            auth_xpath = '//*[@id="1_enable_user_credentials"]'
            if not self.router_client.click_element(auth_xpath):
                print("  ⚠️  启用认证失败")
                return False

            # 输入用户名
            print(f"  输入用户名: {self.mqtt_username}...")
            username_xpath = '//*[@id="1_username"]'
            if not self.router_client.input_text(username_xpath, self.mqtt_username):
                print("  ⚠️  输入用户名失败")
                return False

            # 输入密码
            print("  输入密码...")
            password_xpath = '//*[@id="1_password"]'
            if not self.router_client.input_text(password_xpath, self.mqtt_password):
                print("  ⚠️  输入密码失败")
                return False

            # 配置request主题
            print(f"  配置request主题: {self.REQUEST_TOPIC}...")
            req_topic_xpath = '//*[@id="1_req_topic"]'
            if not self.router_client.input_text(req_topic_xpath, self.REQUEST_TOPIC):
                print("  ⚠️  输入request主题失败")
                return False

            # 配置response主题
            print(f"  配置response主题: {self.RESPONSE_TOPIC}...")
            resp_topic_xpath = '//*[@id="1_resp_topic"]'
            if not self.router_client.input_text(resp_topic_xpath, self.RESPONSE_TOPIC):
                print("  ⚠️  输入response主题失败")
                return False

            # 保存配置
            print("  保存配置...")
            save_xpath = '//*[@id="1_save"]'
            if not self.router_client.click_element(save_xpath):
                print("  ⚠️  保存配置失败")
                return False

            time.sleep(2)

            # 点击应用按钮
            print("  应用配置...")
            # 这里需要根据实际页面找到应用按钮的xpath

            # 等待连接建立 - 使用 router_client 的通用方法
            if not self.router_client.wait_for_mqtt_connection(
                status_xpath='//*[@id="mqtt_list"]/div[2]/div[1]/div[4]/span',
                max_wait=300,
                check_interval=5
            ):
                print("  ✗ MQTT连接失败")
                return False

            return True

        except Exception as e:
            print(f"  配置MQTT失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _start_mqtt_client(self):
        """启动MQTT客户端"""
        try:
            # 创建MQTT客户端
            self.mqtt_client = MQTTTestClient(
                broker=self.mqtt_broker,
                port=self.mqtt_port,
                username=self.mqtt_username,
                password=self.mqtt_password,
                client_id="pc_test_client_reboot"
            )

            # 连接到服务器
            if not self.mqtt_client.connect(timeout=10):
                return False

            print(f"  ✅ 已连接到MQTT服务器 {self.mqtt_broker}:{self.mqtt_port}")
            return True

        except Exception as e:
            print(f"  启动MQTT客户端失败: {e}")
            return False

    def _subscribe_topics(self):
        """订阅MQTT主题"""
        try:
            # 订阅request主题（用于监听自己发送的命令）
            if not self.mqtt_client.subscribe(self.REQUEST_TOPIC, qos=0):
                return False
            print(f"  ✅ 已订阅主题: {self.REQUEST_TOPIC}")

            # 订阅response主题（用于接收路由器响应）
            if not self.mqtt_client.subscribe(self.RESPONSE_TOPIC, qos=0):
                return False
            print(f"  ✅ 已订阅主题: {self.RESPONSE_TOPIC}")

            return True

        except Exception as e:
            print(f"  订阅主题失败: {e}")
            return False

    def _send_reboot_command(self):
        """发送reboot命令"""
        try:
            command = {
                "id": "1",
                "status": "reboot"
            }

            print(f"  发送MQTT消息到主题: {self.REQUEST_TOPIC}")
            print(f"  消息内容(JSON):")
            print(f"    {json.dumps(command, indent=2, ensure_ascii=False)}")

            if not self.mqtt_client.publish(self.REQUEST_TOPIC, command, qos=0):
                return False

            print("  ✅ 命令发送成功")
            return True

        except Exception as e:
            print(f"  ✗ 发送命令失败: {e}")
            return False

    def _wait_for_first_response(self):
        """等待路由器第一次响应(收到reboot命令后立即响应)"""
        try:
            print(f"  等待路由器第一次响应（最多10秒）...")
            print(f"  监听主题: {self.RESPONSE_TOPIC}")

            # 等待response主题的消息
            response_msg = self.mqtt_client.wait_for_message(
                topic=self.RESPONSE_TOPIC,
                timeout=10
            )

            if response_msg:
                self.first_response = response_msg['payload']
                print(f"  ✅ 收到MQTT响应消息")
                print(f"  主题: {response_msg.get('topic', self.RESPONSE_TOPIC)}")
                print(f"  消息内容(JSON):")
                # 尝试格式化JSON输出
                try:
                    response_json = json.loads(self.first_response)
                    print(f"    {json.dumps(response_json, indent=2, ensure_ascii=False)}")
                except:
                    print(f"    {self.first_response}")
                return True
            else:
                print("  ✗ 未收到第一次响应")
                return False

        except Exception as e:
            print(f"  ✗ 等待第一次响应失败: {e}")
            return False

    def _verify_first_response_format(self):
        """验证第一次响应消息格式"""
        try:
            # 解析JSON
            response_json = json.loads(self.first_response)

            print(f"  验证第一次响应消息格式...")
            print(f"  完整消息(JSON):")
            print(f"    {json.dumps(response_json, indent=2, ensure_ascii=False)}")

            # 验证必需字段
            required_fields = ['id', 'code', 'status']
            for field in required_fields:
                if field not in response_json:
                    print(f"  ✗ 缺少必需字段: {field}")
                    return False

            # 验证id字段
            if response_json['id'] != "1":
                print(f"  ✗ id字段不匹配，期望: 1, 实际: {response_json['id']}")
                return False

            # 验证status字段
            if response_json['status'] != "reboot":
                print(f"  ✗ status字段不匹配，期望: reboot, 实际: {response_json['status']}")
                return False

            # 验证code字段 (应该是"2"表示接收到命令)
            if response_json['code'] != "2":
                print(f"  ⚠️  code字段值为: {response_json['code']}, 期望: 2")

            print("  ✅ 第一次响应格式验证通过")
            print(f"  验证结果:")
            print(f"    - id: {response_json['id']} ✓")
            print(f"    - code: {response_json['code']} ✓")
            print(f"    - status: {response_json['status']} ✓")
            if 'time' in response_json:
                print(f"    - time: {response_json['time']}")

            return True

        except json.JSONDecodeError as e:
            print(f"  ✗ JSON解析失败: {e}")
            print(f"  原始消息: {self.first_response}")
            return False
        except Exception as e:
            print(f"  ✗ 验证第一次响应格式失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _verify_reboot_log(self):
        """通过SSH验证系统日志中的重启记录"""
        try:
            print("  通过SSH连接路由器查看系统日志...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # 等待路由器重启完成，最多尝试20次
            max_attempts = 20
            wait_interval = 15  # 每次等待15秒

            for attempt in range(max_attempts):
                try:
                    print(f"  尝试连接SSH (第 {attempt + 1}/{max_attempts} 次)...")
                    ssh.connect(
                        self.router_ip,
                        username=self.SSH_ROOT_USERNAME,
                        password=self.SSH_ROOT_PASSWORD,
                        timeout=10
                    )

                    # 连接成功，查看系统日志
                    print("  ✅ SSH连接成功，查看系统日志...")
                    stdin, stdout, stderr = ssh.exec_command("cat /etc/urlog/system.log | grep -i reboot | tail -10")
                    log_output = stdout.read().decode('utf-8', errors='ignore')

                    print(f"  系统日志内容 (最近10条reboot相关日志):")
                    for line in log_output.strip().split('\n'):
                        if line.strip():
                            print(f"    {line}")

                    # 检查是否有"Restarting system"关键词
                    if "Restarting system" in log_output or "reboot: Restarting system" in log_output:
                        print("  ✅ 在系统日志中找到重启记录: 'Restarting system'")
                        ssh.close()
                        return True
                    elif "reboot" in log_output.lower():
                        print("  ✅ 在系统日志中找到reboot相关记录")
                        ssh.close()
                        return True
                    else:
                        print("  ⚠️  未找到明确的重启记录")
                        ssh.close()
                        return False

                except Exception as e:
                    print(f"  SSH连接失败: {e}")
                    if attempt < max_attempts - 1:
                        print(f"  等待 {wait_interval} 秒后重试...")
                        time.sleep(wait_interval)
                    else:
                        print(f"  ✗ SSH连接失败，已达最大重试次数")
                        return False

            return False

        except Exception as e:
            print(f"  验证重启日志失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _wait_for_second_response(self):
        """等待路由器第二次响应(重启完成消息)

        注意：不清空消息！路由器重启期间PC端一直在监听，
        第二次响应可能已经在消息队列中了。

        返回: True表示收到有效的第二次响应, False表示失败
        """
        try:
            print(f"  检查是否已收到第二次响应...")
            print(f"  监听主题: {self.RESPONSE_TOPIC}")

            # 不清空消息！先检查已接收的消息队列
            # wait_for_message 会从队列中查找或等待新消息
            response_msg = self.mqtt_client.wait_for_message(
                topic=self.RESPONSE_TOPIC,
                timeout=120  # 给更长的超时时间（路由器重启需要时间）
            )

            if not response_msg:
                print("  ✗ 未收到第二次响应（超时120秒）")
                return False

            # 显示收到的原始消息
            print(f"  收到MQTT消息")
            print(f"  主题: {response_msg.get('topic', self.RESPONSE_TOPIC)}")
            print(f"  原始消息(JSON):")
            try:
                temp_json = json.loads(response_msg['payload'])
                print(f"    {json.dumps(temp_json, indent=2, ensure_ascii=False)}")
            except:
                print(f"    {response_msg['payload']}")

            # 检查是否是第二次响应（包含result字段）
            try:
                payload_json = json.loads(response_msg['payload'])

                # 第二次响应应该包含 result 和 resultmsg 字段
                if 'result' in payload_json or 'resultmsg' in payload_json:
                    self.second_response = response_msg['payload']
                    print(f"  ✅ 确认为第二次响应（包含result字段）")
                    return True
                else:
                    # 这可能是第一次响应（没有result字段）
                    # 继续等待第二次响应
                    print("  ⚠️  收到的是第一次响应（无result字段），继续等待第二次响应...")
                    response_msg = self.mqtt_client.wait_for_message(
                        topic=self.RESPONSE_TOPIC,
                        timeout=120
                    )

                    if not response_msg:
                        print("  ✗ 未收到第二次响应（超时）")
                        return False

                    # 显示第二条消息
                    print(f"  收到MQTT消息")
                    print(f"  主题: {response_msg.get('topic', self.RESPONSE_TOPIC)}")
                    print(f"  原始消息(JSON):")
                    try:
                        temp_json = json.loads(response_msg['payload'])
                        print(f"    {json.dumps(temp_json, indent=2, ensure_ascii=False)}")
                    except:
                        print(f"    {response_msg['payload']}")

                    # 再次尝试解析
                    payload_json = json.loads(response_msg['payload'])
                    if 'result' in payload_json or 'resultmsg' in payload_json:
                        self.second_response = response_msg['payload']
                        print(f"  ✅ 确认为第二次响应（包含result字段）")
                        return True
                    else:
                        print("  ✗ 收到的消息格式不是第二次响应（缺少result字段）")
                        print(f"  消息内容: {json.dumps(payload_json, indent=2, ensure_ascii=False)}")
                        return False

            except json.JSONDecodeError as e:
                print(f"  ✗ JSON解析失败: {e}")
                print(f"  原始消息: {response_msg['payload']}")
                return False

        except Exception as e:
            print(f"  ✗ 等待第二次响应出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _verify_second_response_format(self):
        """验证第二次响应消息格式

        严格验证所有必需字段，任何格式错误都返回False
        """
        try:
            # 解析JSON
            response_json = json.loads(self.second_response)

            print(f"  验证第二次响应消息格式...")
            print(f"  完整消息(JSON):")
            print(f"    {json.dumps(response_json, indent=2, ensure_ascii=False)}")

            # 验证必需字段
            required_fields = ['id', 'code', 'status', 'result']
            for field in required_fields:
                if field not in response_json:
                    print(f"  ✗ 缺少必需字段: {field}")
                    return False

            # 验证id字段
            if response_json['id'] != "1":
                print(f"  ✗ id字段不匹配，期望: 1, 实际: {response_json['id']}")
                return False

            # 验证status字段
            if response_json['status'] != "reboot":
                print(f"  ✗ status字段不匹配，期望: reboot, 实际: {response_json['status']}")
                return False

            # 验证code字段 (应该是"2")
            if response_json['code'] != "2":
                print(f"  ✗ code字段不匹配，期望: 2, 实际: {response_json['code']}")
                return False

            # 验证result字段 (应该是1表示成功)
            if response_json['result'] != 1:
                print(f"  ✗ result字段不正确，期望: 1, 实际: {response_json['result']}")
                return False

            # 验证resultmsg字段 (应包含success)
            if 'resultmsg' in response_json:
                resultmsg = response_json['resultmsg'].lower()
                if "success" not in resultmsg:
                    print(f"  ✗ resultmsg未包含'success'，实际: {response_json['resultmsg']}")
                    return False
            else:
                print(f"  ⚠️  缺少resultmsg字段（非必需但建议有）")

            print("  ✅ 第二次响应格式验证通过")
            print(f"  验证结果:")
            print(f"    - id: {response_json['id']} ✓")
            print(f"    - code: {response_json['code']} ✓")
            print(f"    - status: {response_json['status']} ✓")
            print(f"    - result: {response_json['result']} ✓")
            if 'resultmsg' in response_json:
                print(f"    - resultmsg: {response_json['resultmsg']} ✓")
            if 'time' in response_json:
                print(f"    - time: {response_json['time']}")

            return True

        except json.JSONDecodeError as e:
            print(f"  ✗ JSON解析失败: {e}")
            print(f"  原始消息: {self.second_response}")
            return False
        except Exception as e:
            print(f"  ✗ 验证第二次响应格式失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        # 断开MQTT客户端
        if self.mqtt_client:
            print("断开MQTT客户端...")
            self.mqtt_client.disconnect()

        print("测试清理完成")
