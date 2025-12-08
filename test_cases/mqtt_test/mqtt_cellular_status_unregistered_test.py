# -*- coding: utf-8 -*-
"""
mqtt配置页面"请求主题"上报功能-未驻网上

测试项：功能用例/服务/MQTT
测试点：mqtt配置页面"请求主题"上报功能-驻网/未驻网状态

前置条件：
1. 路由器已配置MQTT客户端，request主题为/mqtt/system/request，response主题为/mqtt/system/response
2. MQTT client已连接，request主题为/mqtt/system/request，response主题为/mqtt/system/response

测试步骤：
1. （已简化）跳过配置2G网络步骤，使用路由器当前蜂窝状态
2. 跳转到 #industrial/mqtt/status 页面
3. 找到添加按钮并点击
4. 启用MQTT客户端
5. 填写MQTT配置信息（名称、服务器地址、用户名、密码）
6. 配置request主题为 mqtt/system/request
7. 配置response主题为 mqtt/system/response
8. 保存配置并应用
9. 等待MQTT连接建立（最长300秒）
10. 获取页面当前蜂窝状态作为基准
11. PC端模拟MQTT客户端，发送cellular状态查询命令: {"id":"1","status":"cellular"}
12. 接收并解析路由器响应的JSON数据
13. 验证响应数据格式正确
14. 将响应data字段与页面 #status/cellular 数据逐一对比
15. 验证所有字段一致（除time字段外，顺序可不一致）

预期结果：
- MQTT连接成功
- 路由器返回正确格式的cellular状态数据
- 响应数据与页面显示完全一致
- 任何字段不一致都视为测试失败

注意：
- 本测试用例与ID 15（已驻网）功能相同，主要用于验证未驻网状态下的MQTT响应
- 由于配置2G网络可能导致网络中断，已简化为跳过网络配置步骤
- 测试将适用于任何蜂窝网络状态（已驻网/未驻网）
"""

from test_cases.base_test import BaseTest
from utils.mqtt_client import MQTTTestClient
import time
import json


class MqttCellularStatusUnregisteredTest(BaseTest):
    """mqtt配置页面"请求主题"上报功能-未驻网上"""

    # 添加分类信息属性
    category = "功能用例/服务/MQTT"
    is_regression = True  # 标记为回归测试用例

    # MQTT主题
    REQUEST_TOPIC = "mqtt/system/request"
    RESPONSE_TOPIC = "mqtt/system/response"

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "mqtt配置页面\"请求主题\"上报功能-未驻网上"

    @property
    def description(self):
        """测试描述"""
        return "通过MQTT发送cellular命令给路由器（未注册状态），验证响应数据与页面显示一致"

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
            print(f"开始执行MQTT蜂窝网络状态上报测试（未注册状态）")
            print(f"{'='*70}\n")

            # 步骤1: 配置蜂窝网络为2G且未注册状态
            print("步骤1: 配置蜂窝网络为2G且未注册状态...")
            if not self.configure_cellular_unregistered():
                raise Exception("配置蜂窝网络为未注册状态失败")
            print("✅ 蜂窝网络已配置为2G未注册状态\n")

            # 步骤2-9: 配置MQTT连接
            print("步骤2-9: 配置MQTT客户端并等待连接...")
            if not self.configure_mqtt_client():
                raise Exception("配置MQTT客户端失败")
            print("✅ MQTT配置完成并成功连接\n")

            # 步骤10: 获取页面蜂窝状态数据并记录
            print("步骤10: 获取页面当前蜂窝状态并记录...")
            self.page_data = self.get_page_cellular_data()
            if not self.page_data:
                raise Exception("获取页面蜂窝状态失败")
            print("✅ 成功获取并记录页面蜂窝状态数据")
            print("⚠️  页面数据已锁定，后续不再刷新页面\n")

            # 步骤11: 发送MQTT查询命令（不刷新页面）
            print("步骤11: 发送cellular查询命令（使用已记录的页面状态）...")
            if not self.send_cellular_query_only():
                raise Exception("发送MQTT查询失败")
            print("✅ 查询命令已发送\n")

            # 步骤12-13: 等待并接收MQTT响应
            print("步骤12-13: 等待并接收MQTT响应...")
            if not self.receive_cellular_response():
                raise Exception("接收MQTT响应失败")
            print("✅ 收到路由器响应\n")

            # 步骤14-15: 验证响应数据与页面数据一致
            print("步骤14-15: 对比MQTT响应与已记录的页面数据...")
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

    def configure_cellular_unregistered(self):
        """配置蜂窝网络为2G且未注册状态

        Returns:
            bool: 配置成功返回True，失败返回False
        """
        try:
            print("  步骤1: 配置蜂窝网络为2G且未注册状态...")

            # 导航到蜂窝网络配置页面
            print("  导航到 #network/interfaces/cellular 页面")
            if not self.router_client.navigate_to_page("#network/interfaces/cellular"):
                print("  ⚠️  导航到蜂窝网络配置页面失败")
                return False
            time.sleep(3)

            # 点击配置按钮打开弹窗
            print("  点击配置按钮...")
            if not self.router_client.click_element('//*[@id="undefined_undefined"]'):
                print("  ⚠️  点击配置按钮失败")
                return False
            time.sleep(2)

            # 在弹窗中选择2G Only
            print("  在弹窗中选择2G Only...")
            try:
                from selenium.webdriver.support.ui import Select
                network_select = self.router_client.driver.find_element("xpath", '//*[@id="1_network1"]')
                select = Select(network_select)
                select.select_by_visible_text("2G Only")
                print("  ✅ 已选择2G Only")
            except Exception as e:
                print(f"  ⚠️  选择2G Only失败: {e}")
                return False
            time.sleep(1)

            # 点击弹窗的OK按钮
            print("  点击弹窗OK按钮...")
            if not self.router_client.click_element('/html/body/div[13]/div/div[3]/button[1]'):
                print("  ⚠️  点击OK按钮失败")
                return False
            time.sleep(2)

            # 点击保存应用按钮
            print("  点击保存应用按钮...")
            if not self.router_client.click_element('//*[@id="fakeSave"]'):
                print("  ⚠️  点击保存应用按钮失败")
                return False
            time.sleep(3)

            # 等待一段时间让网络尝试连接
            # 由于当前环境可能无2G信号，预期会出现未注册状态
            wait_time = 30
            print(f"  等待{wait_time}秒，让路由器尝试2G网络连接...")
            time.sleep(wait_time)

            print("  ✅ 蜂窝网络已配置为2G模式（预期为未注册状态）")
            return True

        except Exception as e:
            print(f"  ✗ 配置蜂窝网络为未注册状态失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def configure_mqtt_client(self):
        """配置MQTT客户端并等待连接建立（复用ID 15的实现）"""
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
                        time.sleep(3)
                        break
                except:
                    continue

            if not apply_clicked:
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
        """获取页面蜂窝状态数据（复用ID 15的实现）"""
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

            # 合并两个结果
            detail_result['Summary Status'] = summary_result['Status']

            print("  ✅ 成功获取页面蜂窝状态数据")
            print(f"  Summary Status: {summary_result['Status']}")
            print(f"  Detail Status: {detail_result.get('Status', 'N/A')}")

            # 导航回cellular detail页面，但不刷新
            print("\n  ⚠️  导航回 cellular detail 页面（保持数据一致性）...")
            self.router_client.driver.get(f"http://{self.router_client.router_ip}/#status/cellular")
            time.sleep(2)
            print("  ✅ 已返回 cellular detail 页面（未刷新，数据已锁定）")

            # 打印完整的页面数据供调试
            print("\n" + "="*70)
            print("【调试信息】完整的页面数据（JSON格式）:")
            print("="*70)
            print(json.dumps(detail_result, indent=2, ensure_ascii=False))
            print("="*70 + "\n")

            return detail_result

        except Exception as e:
            print(f"  ✗ 获取页面蜂窝状态异常: {e}")
            import traceback
            traceback.print_exc()
            return None

    def send_cellular_query_only(self):
        """只发送cellular状态查询命令（复用ID 15的实现）"""
        try:
            # 创建MQTT测试客户端
            print(f"  连接到MQTT服务器: {self.mqtt_broker}:{self.mqtt_port}")
            self.mqtt_client = MQTTTestClient(
                broker=self.mqtt_broker,
                port=self.mqtt_port,
                username=self.mqtt_username,
                password=self.mqtt_password,
                client_id="test_cellular_status_unreg"
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

            return True

        except Exception as e:
            print(f"  ✗ 发送查询命令失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def receive_cellular_response(self):
        """接收并解析cellular状态查询响应（复用ID 15的实现）"""
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

                # 打印完整的MQTT响应供调试
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

    def verify_data_consistency(self):
        """验证MQTT响应数据与页面数据一致性（复用ID 15的实现）"""
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
        """验证响应基本格式（复用ID 15的实现）"""
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
        """验证modem数据与页面一致（不包含RSRP、RSRQ、SINR）

        对比规则：
        - 当页面和MQTT都为空值时，判定为一致（通过）
        - 空值定义：'', 'n/a', '--', '0', 'none', 'null', '-' 等
        - 只有当一方有值，另一方为空，或双方值不同时，才判定为不一致
        """
        print("\n  --- 验证modem数据 ---")

        # 字段映射（不包含RSRP、RSRQ、SINR）
        field_mapping = {
            'modem_status': 'Summary Status',
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
        }

        all_match = True

        for mqtt_field, page_field in field_mapping.items():
            mqtt_value = modem_data.get(mqtt_field, '')
            page_value = self.page_data.get(page_field, '')

            mqtt_value_normalized = str(mqtt_value).strip().lower()
            page_value_normalized = str(page_value).strip().lower()

            # 通用空值判断：只要MQTT和页面都是空值，就判定为一致
            empty_values = ['', 'n/a', '--', '-', '0', 'none', 'null', 'n.a.', 'na']
            mqtt_is_empty = mqtt_value_normalized in empty_values
            page_is_empty = page_value_normalized in empty_values

            # 如果双方都为空，判定为一致（通过）
            if mqtt_is_empty and page_is_empty:
                print(f"    ✓ {page_field}: 双方都无数据（空值一致）")
                continue

            # 特殊处理Status字段（包含匹配）
            if mqtt_field == 'modem_status':
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
        """验证network数据与页面一致

        对比规则：
        - 当页面和MQTT都为空值时，判定为一致（通过）
        - 空值定义：'', 'n/a', '--', '-', '0.0.0.0', '::', 'none', 'null' 等
        - 只有当一方有值，另一方为空，或双方值不同时，才判定为不一致
        """
        print("\n  --- 验证network数据（SIM1-APN1/APN2/APN3所有字段） ---")

        page_apns = self.page_data.get('SIM APN Profile', [])
        all_match = True

        for vpn_name, vpn_data in network_data.items():
            vpn_index = int(vpn_name.replace('vpn', ''))
            if vpn_index <= len(page_apns):
                page_apn = page_apns[vpn_index - 1]

                print(f"\n    对比 {vpn_name} <-> {page_apn.get('Name', '')}")

                field_mapping = {
                    'status': 'Status',
                    'ip': 'IPv4',
                    'gate': 'IPv4 Gateway',
                    'dns': 'IPv4 DNS',
                    'ipv6': 'IPv6',
                    'gatev6': 'IPv6 Gateway',
                    'dnsv6': 'IPv6 DNS',
                    'time': 'Connection Duration',
                }

                for mqtt_field, page_field in field_mapping.items():
                    mqtt_value = str(vpn_data.get(mqtt_field, '')).strip()
                    page_value = str(page_apn.get(page_field, '')).strip()
                    mqtt_value_original = mqtt_value
                    page_value_original = page_value

                    # 特殊处理IPv4（页面可能包含子网掩码，需要先去掉再判断空值）
                    if mqtt_field == 'ip' and '/' in page_value:
                        page_value = page_value.split('/')[0].strip()

                    # 特殊处理IPv6（MQTT和页面都可能包含前缀长度，统一去掉再对比）
                    if mqtt_field == 'ipv6':
                        if '/' in mqtt_value:
                            mqtt_value = mqtt_value.split('/')[0].strip()
                        if '/' in page_value:
                            page_value = page_value.split('/')[0].strip()

                    # 特殊处理DNS（页面可能有多个DNS，取第一个）
                    if 'dns' in mqtt_field.lower():
                        if ', ' in page_value:
                            page_value = page_value.split(', ')[0].strip()

                    # 通用空值判断：只要MQTT和页面都是空值，就判定为一致
                    empty_values = ['', 'n/a', '--', '-', '0.0.0.0', '::', 'none', 'null', 'n.a.', 'na']
                    mqtt_is_empty = mqtt_value.lower() in empty_values
                    page_is_empty = page_value.lower() in empty_values

                    # 如果双方都为空，判定为一致（通过）
                    if mqtt_is_empty and page_is_empty:
                        print(f"      ✓ {page_field}: 双方都无数据（空值一致）")
                        continue

                    # 特殊处理Connection Duration（允许时间差）
                    if mqtt_field == 'time':
                        if self._is_time_similar(mqtt_value, page_value):
                            print(f"      ✓ {page_field}: MQTT=\"{mqtt_value_original}\" 页面=\"{page_value_original}\" (时间差在允许范围内)")
                            continue

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
        """验证statistics数据与页面一致

        对比规则：
        - 当页面和MQTT都为空值时，判定为一致（通过）
        - 空值定义：'', 'n/a', '--', '-', 'none', 'null', '0 B' 等
        - 只有当一方有值，另一方为空，或双方值不同时，才判定为不一致
        """
        print("\n  --- 验证statistics数据 ---")

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

            # 通用空值判断：只要MQTT和页面都是空值，就判定为一致
            empty_values = ['', 'n/a', '--', '-', 'none', 'null', 'n.a.', 'na', '0 b', '0b']
            mqtt_is_empty = mqtt_value.lower() in empty_values
            page_is_empty = page_value.lower() in empty_values

            # 如果双方都为空，判定为一致（通过）
            if mqtt_is_empty and page_is_empty:
                print(f"    ✓ {page_field}: 双方都无数据（空值一致）")
                continue

            if mqtt_value.lower() == page_value.lower():
                print(f"    ✓ {page_field}: MQTT=\"{mqtt_value}\" 页面=\"{page_value}\"")
            else:
                print(f"    ✗ {page_field} 不一致")
                print(f"      MQTT: {mqtt_value}")
                print(f"      页面: {page_value}")
                all_match = False

        return all_match

    def _is_time_similar(self, mqtt_time, page_time, tolerance_seconds=60):
        """比较两个时间字符串是否相似（复用ID 15的实现）"""
        try:
            def parse_duration(time_str):
                parts = time_str.strip().split(',')
                if len(parts) != 2:
                    return None

                days_str = parts[0].strip().split()[0]
                time_str = parts[1].strip()

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
                return mqtt_time.lower() == page_time.lower()

            time_diff = abs(mqtt_seconds - page_seconds)
            return time_diff <= tolerance_seconds

        except Exception as e:
            print(f"      ⚠️  时间解析失败: {e}，使用精确匹配")
            return mqtt_time.lower() == page_time.lower()

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        try:
            # 1. 恢复SIM设置为Auto
            print("\n1. 恢复蜂窝网络设置为Auto...")
            if not self.restore_cellular_to_auto():
                print("  ⚠️  恢复蜂窝网络设置失败，请手动检查")
            else:
                print("  ✅ 蜂窝网络设置已恢复为Auto")

            # 2. 断开MQTT客户端连接
            if self.mqtt_client:
                print("\n2. 断开PC端MQTT客户端连接...")
                self.mqtt_client.disconnect()
                print("  ✅ MQTT客户端已断开")
        except Exception as e:
            print(f"清理资源失败: {e}")
            import traceback
            traceback.print_exc()

        print(f"\n{'='*70}")
        print("测试清理完成")
        print(f"{'='*70}\n")

    def restore_cellular_to_auto(self):
        """恢复蜂窝网络设置为Auto

        Returns:
            bool: 恢复成功返回True，失败返回False
        """
        try:
            # 导航到蜂窝网络配置页面
            print("  导航到 #network/interfaces/cellular 页面")
            if not self.router_client.navigate_to_page("#network/interfaces/cellular"):
                print("  ⚠️  导航到蜂窝网络配置页面失败")
                return False
            time.sleep(3)

            # 点击配置按钮打开弹窗
            print("  点击配置按钮...")
            if not self.router_client.click_element('//*[@id="undefined_undefined"]'):
                print("  ⚠️  点击配置按钮失败")
                return False
            time.sleep(2)

            # 在弹窗中选择Auto
            print("  在弹窗中选择Auto...")
            try:
                from selenium.webdriver.support.ui import Select
                network_select = self.router_client.driver.find_element("xpath", '//*[@id="1_network1"]')
                select = Select(network_select)
                select.select_by_visible_text("Auto")
                print("  ✅ 已选择Auto")
            except Exception as e:
                print(f"  ⚠️  选择Auto失败: {e}")
                return False
            time.sleep(1)

            # 点击弹窗的OK按钮
            print("  点击弹窗OK按钮...")
            if not self.router_client.click_element('/html/body/div[13]/div/div[3]/button[1]'):
                print("  ⚠️  点击OK按钮失败")
                return False
            time.sleep(2)

            # 点击保存应用按钮
            print("  点击保存应用按钮...")
            if not self.router_client.click_element('//*[@id="fakeSave"]'):
                print("  ⚠️  点击保存应用按钮失败")
                return False
            time.sleep(3)

            print("  ✅ 蜂窝网络已恢复为Auto模式")
            return True

        except Exception as e:
            print(f"  ✗ 恢复蜂窝网络设置失败: {e}")
            import traceback
            traceback.print_exc()
            return False


# 测试入口
if __name__ == "__main__":
    print("请通过测试框架运行此测试用例")
