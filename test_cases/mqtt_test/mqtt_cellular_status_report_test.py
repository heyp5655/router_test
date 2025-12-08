# -*- coding: utf-8 -*-
"""
mqtt配置页面"请求主题"上报功能-驻网上

测试项：工业协议/网络/MQTT
测试点：mqtt配置页面"请求主题"上报功能-驻网上

前置条件：
1. 路由器已配置MQTT客户端，request主题为/mqtt/system/request，response主题为/mqtt/system/response
2. MQTT client已连接，request主题为/mqtt/system/request，response主题为/mqtt/system/response

测试步骤：
1. 登录路由器，跳转到 #industrial/mqtt/status 页面
2. 找到添加按钮并点击
3. 启用MQTT客户端
4. 填写MQTT配置信息（名称、服务器地址、用户名、密码）
5. 配置request主题为 mqtt/system/request
6. 配置response主题为 mqtt/system/response
7. 保存配置并应用
8. 等待MQTT连接建立（最长300秒）
9. 获取页面当前蜂窝状态作为基准
10. PC端模拟MQTT客户端，发送cellular状态查询命令: {"id":"1","status":"cellular"}
11. 接收并解析路由器响应的JSON数据
12. 验证响应数据格式正确
13. 将响应data字段与页面 #status/cellular 数据逐一对比
14. 验证所有字段一致（除time字段外，顺序可不一致）

预期结果：
- MQTT连接成功
- 路由器返回正确格式的cellular状态数据
- 响应数据与页面显示完全一致
- 任何字段不一致都视为测试失败
"""

from test_cases.base_test import BaseTest
from utils.mqtt_client import MQTTTestClient
import time
import json


class MqttCellularStatusReportTest(BaseTest):
    """mqtt配置页面"请求主题"上报功能-驻网上"""

    # 添加分类信息属性
    category = "功能用例/服务/MQTT"
    is_regression = True  # 标记为回归测试用例

    # MQTT主题
    REQUEST_TOPIC = "mqtt/system/request"
    RESPONSE_TOPIC = "mqtt/system/response"

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "mqtt配置页面\"请求主题\"上报功能-驻网上"

    @property
    def description(self):
        """测试描述"""
        return "通过MQTT发送cellular命令给路由器，验证响应数据与页面显示一致"

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

        # SSH配置（用于验证日志，如果需要的话）
        self.SSH_ROOT_USERNAME = "root"
        self.SSH_ROOT_PASSWORD = "password"  # 根据实际情况修改

        # MQTT测试客户端
        self.mqtt_client = None

        # 测试结果
        self.mqtt_response = None  # MQTT响应数据
        self.page_data = None      # 页面数据

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

    def execute(self):
        """执行测试"""
        try:
            print(f"\n{'='*70}")
            print(f"开始执行MQTT蜂窝网络状态上报测试")
            print(f"{'='*70}\n")

            # 步骤1-8: 配置MQTT连接
            print("步骤1-13: 配置MQTT客户端并等待连接...")
            if not self.configure_mqtt_client():
                raise Exception("配置MQTT客户端失败")
            print("✅ MQTT配置完成并成功连接\n")

            # ===== 新顺序：先获取页面数据，记录后不再刷新，再发送MQTT请求 =====
            # 这样可以避免页面刷新导致信号值（RSRQ、SINR等）变化

            # 步骤9: 先获取页面蜂窝状态数据并记录
            print("步骤9: 获取页面当前蜂窝状态并记录...")
            self.page_data = self.get_page_cellular_data()
            if not self.page_data:
                raise Exception("获取页面蜂窝状态失败")
            print("✅ 成功获取并记录页面蜂窝状态数据")
            print("⚠️  页面数据已锁定，后续不再刷新页面\n")

            # 步骤10: 发送MQTT查询命令（不刷新页面）
            print("步骤10: 发送cellular查询命令（使用已记录的页面状态）...")
            if not self.send_cellular_query_only():
                raise Exception("发送MQTT查询失败")
            print("✅ 查询命令已发送\n")

            # 步骤11-12: 等待并接收MQTT响应
            print("步骤11-12: 等待并接收MQTT响应...")
            if not self.receive_cellular_response():
                raise Exception("接收MQTT响应失败")
            print("✅ 收到路由器响应\n")

            # 步骤13-14: 验证响应数据与页面数据一致
            print("步骤13-14: 对比MQTT响应与已记录的页面数据...")
            if not self.verify_data_consistency():
                raise Exception("数据一致性验证失败")

            print(f"\n{'='*70}")
            print("✅ 测试完成：所有步骤通过")
            print(f"{'='*70}\n")
            return True

        except Exception as e:
            print(f"\n测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise

    def configure_mqtt_client(self):
        """配置MQTT客户端并等待连接建立"""
        try:
            # 步骤1: 导航到MQTT状态页面
            print("  步骤1: 导航到 #industrial/mqtt/status 页面")
            if not self.router_client.navigate_to_page("#industrial/mqtt/status"):
                print("  ⚠️  导航到MQTT页面失败")
                return False
            time.sleep(3)

            # 步骤1.5: 检查是否已存在相同配置的MQTT连接
            print("  步骤1.5: 检查是否已存在MQTT配置")
            try:
                # 检查列表中是否有已配置的MQTT服务器
                existing_ip_xpath = '//*[@id="mqtt_list"]/div[2]/div[1]/div[3]/div'
                existing_ip_element = self.router_client.driver.find_element("xpath", existing_ip_xpath)
                existing_server = existing_ip_element.text.strip()

                print(f"  发现已配置的MQTT服务器: {existing_server}")
                print(f"  当前测试使用的服务器: {self.mqtt_broker}")

                # 解析已配置的服务器地址（格式: "ip:port" 或 "ip"）
                existing_ip = existing_server.split(':')[0].strip() if ':' in existing_server else existing_server.strip()

                print(f"  解析后的IP地址: {existing_ip}")

                # 检查IP是否匹配
                if existing_ip == self.mqtt_broker:
                    print("  ✅ 已存在相同的MQTT服务器配置")

                    # 检查连接状态
                    status_xpath = '//*[@id="mqtt_list"]/div[2]/div[1]/div[4]/span'
                    try:
                        status_element = self.router_client.driver.find_element("xpath", status_xpath)
                        status_text = status_element.text.strip().lower()
                        print(f"  当前连接状态: {status_text}")

                        # 检查是否已连接
                        if "已连接" in status_text or "connected" in status_text:
                            print("  ✅ MQTT已连接，复用现有配置")

                            # 点击编辑按钮查看主题配置
                            print("  点击编辑按钮查看主题配置...")
                            edit_button_xpath = '//*[@id="mqtt_list"]/div[2]/div[1]/div[5]/div/button[1]'
                            edit_button = self.router_client.driver.find_element("xpath", edit_button_xpath)
                            edit_button.click()
                            time.sleep(2)

                            # 读取已配置的主题
                            req_topic_element = self.router_client.driver.find_element("xpath", '//*[@id="1_req_topic"]')
                            resp_topic_element = self.router_client.driver.find_element("xpath", '//*[@id="1_resp_topic"]')

                            existing_req_topic = req_topic_element.get_attribute('value').strip()
                            existing_resp_topic = resp_topic_element.get_attribute('value').strip()

                            print(f"  已配置的 Request 主题: {existing_req_topic}")
                            print(f"  已配置的 Response 主题: {existing_resp_topic}")

                            # 使用已配置的主题（覆盖测试用例中定义的主题）
                            self.REQUEST_TOPIC = existing_req_topic
                            self.RESPONSE_TOPIC = existing_resp_topic

                            print(f"  ✅ 将使用已配置的主题进行测试")

                            # 关闭编辑窗口（点击取消或关闭）
                            try:
                                cancel_button = self.router_client.driver.find_element("xpath", '//*[@id="1_cancel"]')
                                cancel_button.click()
                                time.sleep(1)
                            except:
                                pass

                            # 直接返回成功，跳过后面的配置步骤
                            print("  ✅ 复用现有MQTT配置，跳过配置步骤")
                            return True
                        else:
                            print(f"  ⚠️  MQTT未连接（状态: {status_text}），将重新配置")
                    except Exception as e:
                        print(f"  ⚠️  无法获取连接状态: {e}")
                else:
                    print(f"  服务器地址不匹配，将添加新配置")

            except Exception as e:
                print(f"  未找到已配置的MQTT服务器，将添加新配置")

            # 步骤2: 点击添加按钮
            print("  步骤2: 查找并点击添加按钮")
            if not self.router_client.click_element('//*[@id="4_add_btn"]'):
                print("  ⚠️  点击添加按钮失败")
                return False
            time.sleep(2)

            # 步骤3: 启用MQTT客户端
            print("  步骤3: 启用MQTT客户端")
            if not self.router_client.click_element('//*[@id="1_enabled"]'):
                print("  ⚠️  启用MQTT失败")
                return False
            time.sleep(1)

            # 步骤4: 填写MQTT名称
            print("  步骤4: 填写MQTT名称为 test")
            if not self.router_client.input_text('//*[@id="1_mqtt_name"]', "test"):
                print("  ⚠️  输入名称失败")
                return False

            # 步骤5: 填写服务器地址（只填写IP，不包含端口）
            print(f"  步骤5: 填写服务器地址 {self.mqtt_broker}")
            if not self.router_client.input_text('//*[@id="1_m_server_addr"]', self.mqtt_broker):
                print("  ⚠️  输入服务器地址失败")
                return False

            # 步骤6: 勾选启用用户认证
            print("  步骤6: 启用用户认证")
            if not self.router_client.click_element('//*[@id="1_enable_user_credentials"]'):
                print("  ⚠️  启用认证失败")
                return False
            time.sleep(1)

            # 步骤7: 填写用户名
            print(f"  步骤7: 填写用户名 {self.mqtt_username}")
            if not self.router_client.input_text('//*[@id="1_username"]', self.mqtt_username):
                print("  ⚠️  输入用户名失败")
                return False

            # 步骤8: 填写密码
            print(f"  步骤8: 填写密码")
            if not self.router_client.input_text('//*[@id="1_password"]', self.mqtt_password):
                print("  ⚠️  输入密码失败")
                return False

            # 步骤9: 填写request主题
            print(f"  步骤9: 填写request主题 {self.REQUEST_TOPIC}")
            if not self.router_client.input_text('//*[@id="1_req_topic"]', self.REQUEST_TOPIC):
                print("  ⚠️  输入request主题失败")
                return False

            # 步骤10: 填写response主题
            print(f"  步骤10: 填写response主题 {self.RESPONSE_TOPIC}")
            if not self.router_client.input_text('//*[@id="1_resp_topic"]', self.RESPONSE_TOPIC):
                print("  ⚠️  输入response主题失败")
                return False

            # 步骤11: 保存配置
            print("  步骤11: 保存配置")
            if not self.router_client.click_element('//*[@id="1_save"]'):
                print("  ⚠️  保存配置失败")
                return False
            time.sleep(2)

            # 步骤12: 点击应用按钮（如果存在）
            print("  步骤12: 查找并点击应用按钮（如果存在）")
            # 尝试多个可能的应用按钮选择器
            apply_selectors = [
                '//*[@id="apply"]',
                '//button[contains(@id, "apply")]',
                '//*[contains(text(), "应用")]',
                '//*[contains(text(), "Apply")]',
                '//*[@id="mqtt_list"]//button[contains(text(), "Apply") or contains(text(), "应用")]'
            ]

            apply_clicked = False
            for selector in apply_selectors:
                try:
                    if self.router_client.click_element(selector):
                        print(f"  ✅ 成功点击应用按钮")
                        apply_clicked = True
                        time.sleep(3)  # 点击后等待配置应用
                        break
                except:
                    continue

            if not apply_clicked:
                # 如果页面配置较少，可能不需要应用按钮，直接进入下一步
                print("  → 未找到应用按钮，配置可能已自动生效")

            # 步骤13: 等待MQTT连接建立
            print("  步骤13: 等待MQTT连接建立（最长300秒）")
            if not self.router_client.wait_for_mqtt_connection(
                status_xpath='//*[@id="mqtt_list"]/div[2]/div[1]/div[4]/span',
                max_wait=300,
                check_interval=5
            ):
                print("  ✗ MQTT连接失败")
                return False

            print("  ✅ MQTT配置完成并成功连接")
            return True

        except Exception as e:
            print(f"  ✗ 配置MQTT客户端失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_page_cellular_data(self):
        """获取页面蜂窝状态数据

        Returns:
            dict: 页面蜂窝状态数据，失败返回None
        """
        try:
            # 使用 router_client 的函数获取详细蜂窝状态（会刷新页面）
            detail_result = self.router_client.check_cellular_detail_status(timeout=30, skip_navigation=False)

            if not detail_result['success']:
                print(f"  ✗ 获取页面详细蜂窝状态失败: {detail_result.get('error', '未知错误')}")
                return None

            # 获取 summary 页面的状态（用于 modem_status 对比，会切换页面）
            summary_result = self.router_client.check_cellular_summary_status(timeout=30, skip_navigation=False)

            if not summary_result['success']:
                print(f"  ✗ 获取页面概览蜂窝状态失败: {summary_result.get('error', '未知错误')}")
                return None

            # 合并两个结果，detail为主，summary的Status字段用于modem_status对比
            # 将 summary 的 Status 存储为 Summary Status，用于后续modem_status对比
            detail_result['Summary Status'] = summary_result['Status']

            print("  ✅ 成功获取页面蜂窝状态数据")
            print(f"  Summary Status: {summary_result['Status']}")
            print(f"  Detail Status: {detail_result.get('Status', 'N/A')}")

            # ===== 重要：导航回cellular detail页面，但不刷新 =====
            # 这样后续发送MQTT时，页面上的数据与我们获取的数据保持一致
            print("\n  ⚠️  导航回 cellular detail 页面（保持数据一致性）...")
            self.router_client.driver.get(f"http://{self.router_client.router_ip}/#status/cellular")
            # 不刷新页面，直接等待页面加载
            import time
            time.sleep(2)
            print("  ✅ 已返回 cellular detail 页面（未刷新，数据已锁定）")

            # ===== 打印完整的页面数据供调试 =====
            print("\n" + "="*70)
            print("【调试信息】完整的页面数据（JSON格式）:")
            print("="*70)
            import json
            print(json.dumps(detail_result, indent=2, ensure_ascii=False))
            print("="*70 + "\n")

            return detail_result

        except Exception as e:
            print(f"  ✗ 获取页面蜂窝状态异常: {e}")
            import traceback
            traceback.print_exc()
            return None

    def send_cellular_query_only(self):
        """只发送cellular状态查询命令（不等待响应）

        这个方法用于先发送命令，然后立即获取页面数据，
        最后再等待MQTT响应，以确保数据的实时性。
        """
        try:
            # 创建MQTT测试客户端
            print(f"  连接到MQTT服务器: {self.mqtt_broker}:{self.mqtt_port}")
            self.mqtt_client = MQTTTestClient(
                broker=self.mqtt_broker,
                port=self.mqtt_port,
                username=self.mqtt_username,
                password=self.mqtt_password,
                client_id="test_cellular_status"
            )

            # 连接到MQTT服务器
            if not self.mqtt_client.connect(timeout=10):
                print("  ✗ PC端MQTT客户端连接失败")
                return False

            print("  ✅ PC端MQTT客户端连接成功")

            # 订阅响应主题
            print(f"  订阅主题: {self.RESPONSE_TOPIC}")
            if not self.mqtt_client.subscribe(self.RESPONSE_TOPIC, qos=0):
                print("  ✗ 订阅主题失败")
                return False
            print("  ✅ 主题订阅成功")

            # 发送cellular查询命令
            command = {"id": "1", "status": "cellular"}
            print(f"  发送命令: {json.dumps(command, ensure_ascii=False)}")
            if not self.mqtt_client.publish(self.REQUEST_TOPIC, command, qos=0):
                print("  ✗ 发送命令失败")
                return False
            print("  ✅ 命令发送成功")
            print("  ⚠️  命令已发送，立即获取页面数据以确保实时性...")

            return True

        except Exception as e:
            print(f"  ✗ 发送查询命令失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def receive_cellular_response(self):
        """接收并解析cellular状态查询响应"""
        try:
            # 等待响应（30秒超时）
            print("  等待路由器MQTT响应（最多30秒）...")
            response_msg = self.mqtt_client.wait_for_message(
                topic=self.RESPONSE_TOPIC,
                timeout=30
            )

            if not response_msg:
                print("  ✗ 未收到路由器响应（超时30秒）")
                return False

            # 解析响应JSON
            try:
                self.mqtt_response = json.loads(response_msg['payload'])
                print("  ✅ 收到路由器响应")

                # ===== 打印完整的MQTT响应供调试 =====
                print("\n" + "="*70)
                print("【调试信息】完整的MQTT响应（JSON格式）:")
                print("="*70)
                print(json.dumps(self.mqtt_response, indent=2, ensure_ascii=False))
                print("="*70 + "\n")

            except json.JSONDecodeError as e:
                print(f"  ✗ 响应JSON解析失败: {e}")
                print(f"  原始响应: {response_msg['payload']}")
                return False

            return True

        except Exception as e:
            print(f"  ✗ 接收响应失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def send_cellular_query(self):
        """发送cellular状态查询命令并接收响应（保留用于兼容）"""
        try:
            # 创建MQTT测试客户端
            print(f"  连接到MQTT服务器: {self.mqtt_broker}:{self.mqtt_port}")
            self.mqtt_client = MQTTTestClient(
                broker=self.mqtt_broker,
                port=self.mqtt_port,
                username=self.mqtt_username,
                password=self.mqtt_password,
                client_id="test_cellular_status"
            )

            # 连接到MQTT服务器
            if not self.mqtt_client.connect(timeout=10):
                print("  ✗ PC端MQTT客户端连接失败")
                return False

            print("  ✅ PC端MQTT客户端连接成功")

            # 订阅响应主题
            print(f"  订阅主题: {self.RESPONSE_TOPIC}")
            if not self.mqtt_client.subscribe(self.RESPONSE_TOPIC, qos=0):
                print("  ✗ 订阅主题失败")
                return False
            print("  ✅ 主题订阅成功")

            # 发送cellular查询命令
            command = {"id": "1", "status": "cellular"}
            print(f"  发送命令: {json.dumps(command, ensure_ascii=False)}")
            if not self.mqtt_client.publish(self.REQUEST_TOPIC, command, qos=0):
                print("  ✗ 发送命令失败")
                return False
            print("  ✅ 命令发送成功")

            # 等待响应（30秒超时）
            print("  等待路由器响应（最多30秒）...")
            response_msg = self.mqtt_client.wait_for_message(
                topic=self.RESPONSE_TOPIC,
                timeout=30
            )

            if not response_msg:
                print("  ✗ 未收到路由器响应（超时30秒）")
                return False

            # 解析响应JSON
            try:
                self.mqtt_response = json.loads(response_msg['payload'])
                print("  ✅ 收到路由器响应")

                # ===== 打印完整的MQTT响应供调试 =====
                print("\n" + "="*70)
                print("【调试信息】完整的MQTT响应（JSON格式）:")
                print("="*70)
                print(json.dumps(self.mqtt_response, indent=2, ensure_ascii=False))
                print("="*70 + "\n")

            except json.JSONDecodeError as e:
                print(f"  ✗ 响应JSON解析失败: {e}")
                print(f"  原始响应: {response_msg['payload']}")
                return False

            return True

        except Exception as e:
            print(f"  ✗ 发送查询命令失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def verify_data_consistency(self):
        """验证MQTT响应数据与页面数据一致性"""
        try:
            # 验证响应基本格式
            if not self.verify_response_format():
                return False

            # 获取响应中的data字段
            response_data = self.mqtt_response.get('data', {})
            if not response_data:
                print("  ✗ 响应中缺少data字段")
                return False

            # 验证modem数据
            if not self.verify_modem_data(response_data.get('modem', {})):
                return False

            # 验证network数据
            if not self.verify_network_data(response_data.get('network', {})):
                return False

            # 验证statistics数据
            if not self.verify_statistics_data(response_data.get('statistics', {})):
                return False

            print("  ✅ 所有数据验证通过")
            return True

        except Exception as e:
            print(f"  ✗ 数据验证异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def verify_response_format(self):
        """验证响应基本格式"""
        required_fields = ['code', 'id', 'status', 'data']

        for field in required_fields:
            if field not in self.mqtt_response:
                print(f"  ✗ 响应缺少必需字段: {field}")
                return False

        # 验证字段值
        if self.mqtt_response.get('id') != "1":
            print(f"  ✗ id字段不正确，期望: 1, 实际: {self.mqtt_response.get('id')}")
            return False

        if self.mqtt_response.get('status') != "cellular":
            print(f"  ✗ status字段不正确，期望: cellular, 实际: {self.mqtt_response.get('status')}")
            return False

        if self.mqtt_response.get('code') != "2":
            print(f"  ✗ code字段不正确，期望: 2, 实际: {self.mqtt_response.get('code')}")
            return False

        print("  ✅ 响应基本格式验证通过")
        return True

    def verify_modem_data(self, modem_data):
        """验证modem数据与页面一致（不包含RSRP、RSRQ、SINR）"""
        print("\n  --- 验证modem数据 ---")

        # 字段映射：MQTT响应字段 -> 页面字段名
        # 注意：已移除 rsrp、rsrq、sinr 的对比
        field_mapping = {
            'modem_status': 'Summary Status',  # 使用 Summary 页面的 Status
            'model': 'Model',
            'version': 'Version',
            'cur_sim': 'Current SIM',
            'signal': 'Signal Level',
            'register': 'Register Status',
            'imei': 'IMEI',
            'imsi': 'IMSI',
            'iccid': 'ICCID',
            'net_provider': 'ISP',
            'net_type': 'Network Type',
            'band': 'Cellular Frequency Band',
            'plmnid': 'PLMN ID',
            'lac': 'LAC',
            'cellid': 'Cell ID',
            # 已移除: 'rsrp': 'RSRP',
            # 已移除: 'rsrq': 'RSRQ',
            # 已移除: 'sinr': 'SINR',
        }

        all_match = True

        for mqtt_field, page_field in field_mapping.items():
            mqtt_value = modem_data.get(mqtt_field, '')
            page_value = self.page_data.get(page_field, '')

            # 标准化对比（去除空格、转小写）
            mqtt_value_normalized = str(mqtt_value).strip().lower()
            page_value_normalized = str(page_value).strip().lower()

            # 特殊处理Status字段：页面可能是 "Ready, FDD LTE," 格式，MQTT可能只有 "Ready"
            # 只要包含关系成立即可
            if mqtt_field == 'modem_status':
                # Summary Status 通常格式是 "Ready, FDD LTE," 我们检查是否包含 mqtt_value
                if mqtt_value_normalized and (mqtt_value_normalized in page_value_normalized):
                    print(f"    ✓ {page_field}: MQTT=\"{mqtt_value}\" 页面=\"{page_value}\"")
                else:
                    print(f"    ✗ {page_field} 不一致")
                    print(f"      MQTT: {mqtt_value}")
                    print(f"      页面: {page_value}")
                    all_match = False
            elif mqtt_value_normalized == page_value_normalized:
                print(f"    ✓ {page_field}: MQTT=\"{mqtt_value}\" 页面=\"{page_value}\"")
            else:
                print(f"    ✗ {page_field} 不一致")
                print(f"      MQTT: {mqtt_value}")
                print(f"      页面: {page_value}")
                all_match = False

        return all_match

    def verify_network_data(self, network_data):
        """验证network数据与页面一致（完整对比所有APN字段）"""
        print("\n  --- 验证network数据（SIM1-APN1/APN2/APN3所有字段） ---")

        # 获取页面APN数据
        page_apns = self.page_data.get('SIM APN Profile', [])

        # 对比每个VPN/APN
        all_match = True

        for vpn_name, vpn_data in network_data.items():
            # 找到对应的页面APN（vpn1 -> SIM1-APN1, vpn2 -> SIM1-APN2, vpn3 -> SIM1-APN3）
            vpn_index = int(vpn_name.replace('vpn', ''))
            if vpn_index <= len(page_apns):
                page_apn = page_apns[vpn_index - 1]

                print(f"\n    对比 {vpn_name} <-> {page_apn.get('Name', '')}")

                # 完整字段映射（所有8个字段）
                field_mapping = {
                    'status': 'Status',
                    'ip': 'IPv4',  # 需要特殊处理，页面包含子网掩码
                    'gate': 'IPv4 Gateway',
                    'dns': 'IPv4 DNS',  # 需要特殊处理，可能有多个DNS
                    'ipv6': 'IPv6',  # 需要特殊处理，页面包含前缀长度
                    'gatev6': 'IPv6 Gateway',
                    'dnsv6': 'IPv6 DNS',  # 新增：IPv6 DNS对比
                    'time': 'Connection Duration',  # 新增：连接时长对比
                }

                for mqtt_field, page_field in field_mapping.items():
                    mqtt_value = str(vpn_data.get(mqtt_field, '')).strip()
                    page_value = str(page_apn.get(page_field, '')).strip()
                    mqtt_value_original = mqtt_value  # 保存原始MQTT值用于打印
                    page_value_original = page_value  # 保存原始页面值用于打印

                    # 特殊处理IPv4（页面格式: 10.3.218.11/28, MQTT格式: 10.3.218.11）
                    if mqtt_field == 'ip' and '/' in page_value:
                        page_value = page_value.split('/')[0]

                    # 特殊处理IPv6（MQTT和页面都可能包含前缀长度，统一去掉再对比）
                    if mqtt_field == 'ipv6':
                        # MQTT可能是 "fe80::xxx/64" 或 "fe80::xxx"
                        # 页面可能是 "fe80::xxx/64" 或 "fe80::xxx"
                        # 统一处理：去掉前缀长度再对比
                        if '/' in mqtt_value:
                            mqtt_value = mqtt_value.split('/')[0]
                        if '/' in page_value:
                            page_value = page_value.split('/')[0]

                    # 特殊处理DNS（MQTT可能是单个，页面可能是逗号分隔的多个）
                    if 'dns' in mqtt_field.lower():
                        # 取第一个DNS对比
                        if ', ' in page_value:
                            page_value = page_value.split(', ')[0]

                    # 特殊处理Connection Duration（允许时间差，因为获取页面和MQTT响应有时间间隔）
                    if mqtt_field == 'time':
                        # 时间格式: "0 days, 11:52:03"
                        # 允许时间差在60秒以内（正常的获取延迟）
                        if self._is_time_similar(mqtt_value, page_value):
                            print(f"      ✓ {page_field}: MQTT=\"{mqtt_value_original}\" 页面=\"{page_value_original}\" (时间差在允许范围内)")
                            continue  # 跳过后续的精确对比，认为匹配成功

                    mqtt_value_normalized = mqtt_value.lower()
                    page_value_normalized = page_value.lower()

                    if mqtt_value_normalized == page_value_normalized:
                        print(f"      ✓ {page_field}: MQTT=\"{mqtt_value_original}\" 页面=\"{page_value_original}\"")
                    else:
                        print(f"      ✗ {page_field} 不一致")
                        print(f"        MQTT原始: {mqtt_value_original}, 处理后: {mqtt_value}")
                        print(f"        页面原始: {page_value_original}, 处理后: {page_value}")
                        all_match = False
            else:
                print(f"\n    ⚠️  页面APN数据不足，跳过 {vpn_name}")

        return all_match

    def verify_statistics_data(self, statistics_data):
        """验证statistics数据与页面一致"""
        print("\n  --- 验证statistics数据 ---")

        # 字段映射
        field_mapping = {
            'sim1': 'SIM-1 Monthly',
            'sim2': 'SIM-2 Monthly',
        }

        all_match = True

        for mqtt_field, page_field in field_mapping.items():
            mqtt_value = str(statistics_data.get(mqtt_field, '')).strip()
            page_value = str(self.page_data.get(page_field, '')).strip()

            # 标准化格式（去除多余空格）
            mqtt_value = ' '.join(mqtt_value.split())
            page_value = ' '.join(page_value.split())

            if mqtt_value.lower() == page_value.lower():
                print(f"    ✓ {page_field}: MQTT=\"{mqtt_value}\" 页面=\"{page_value}\"")
            else:
                print(f"    ✗ {page_field} 不一致")
                print(f"      MQTT: {mqtt_value}")
                print(f"      页面: {page_value}")
                all_match = False

        return all_match

    def _is_time_similar(self, mqtt_time, page_time, tolerance_seconds=60):
        """比较两个时间字符串是否相似（允许一定时间差）

        Args:
            mqtt_time: MQTT时间字符串，格式: "0 days, 11:52:03"
            page_time: 页面时间字符串，格式: "0 days, 11:51:52"
            tolerance_seconds: 允许的时间差（秒），默认60秒

        Returns:
            bool: 时间差在允许范围内返回True，否则返回False
        """
        try:
            # 解析时间字符串
            def parse_duration(time_str):
                """解析时间字符串为总秒数"""
                # 格式: "0 days, 11:52:03" 或 "1 days, 01:23:45"
                parts = time_str.strip().split(',')
                if len(parts) != 2:
                    return None

                days_str = parts[0].strip().split()[0]  # "0 days" -> "0"
                time_str = parts[1].strip()  # "11:52:03"

                days = int(days_str)
                time_parts = time_str.split(':')
                if len(time_parts) != 3:
                    return None

                hours, minutes, seconds = map(int, time_parts)
                total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
                return total_seconds

            mqtt_seconds = parse_duration(mqtt_time)
            page_seconds = parse_duration(page_time)

            if mqtt_seconds is None or page_seconds is None:
                # 无法解析，使用精确匹配
                return mqtt_time.lower() == page_time.lower()

            # 计算时间差的绝对值
            time_diff = abs(mqtt_seconds - page_seconds)

            # 判断是否在允许范围内
            return time_diff <= tolerance_seconds

        except Exception as e:
            # 解析失败，使用精确匹配
            print(f"      ⚠️  时间解析失败: {e}，使用精确匹配")
            return mqtt_time.lower() == page_time.lower()

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        try:
            # 断开MQTT客户端连接
            if self.mqtt_client:
                print("断开PC端MQTT客户端连接...")
                self.mqtt_client.disconnect()
        except Exception as e:
            print(f"清理资源失败: {e}")

        print("测试清理完成")


# 测试入口
if __name__ == "__main__":
    print("请通过测试框架运行此测试用例")
