#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MQTTX自动化操作脚本 - 连接、订阅和发送消息
"""

import paho.mqtt.client as mqtt
import time
import json
from test_cases.mqtt_test.mqttx_controller import MQTTXController


class MQTTXAutomation:
    """MQTTX自动化操作类"""

    def __init__(self):
        self.controller = MQTTXController()
        self.client = None
        self.connected = False
        self.subscribed_topics = []
        self.received_messages = []

    def on_connect(self, client, userdata, flags, rc, properties=None):
        """连接回调"""
        if rc == 0:
            print("[OK] 成功连接到MQTT服务器!")
            self.connected = True
        else:
            print(f"[FAIL] 连接失败，错误码: {rc}")
            self.connected = False

    def on_disconnect(self, client, userdata, rc, properties=None):
        """断开连接回调"""
        print(f"[INFO] 断开连接，错误码: {rc}")
        self.connected = False

    def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        """订阅回调"""
        print(f"[OK] 订阅成功，消息ID: {mid}, QoS: {granted_qos}")

    def on_message(self, client, userdata, msg):
        """消息接收回调"""
        try:
            payload = msg.payload.decode('utf-8')
            print(f"\n[收到消息]")
            print(f"  主题: {msg.topic}")
            print(f"  内容: {payload}")
            print(f"  QoS: {msg.qos}")

            # 保存消息
            self.received_messages.append({
                'topic': msg.topic,
                'payload': payload,
                'qos': msg.qos,
                'timestamp': time.time()
            })
        except Exception as e:
            print(f"[ERROR] 处理消息时出错: {e}")

    def on_publish(self, client, userdata, mid, properties=None):
        """发布消息回调"""
        print(f"[OK] 消息发送成功，消息ID: {mid}")

    def connect_to_server(self, connection_name="123"):
        """
        连接到MQTT服务器

        Args:
            connection_name: MQTTX中配置的连接名称

        Returns:
            bool: 是否连接成功
        """
        print("=" * 60)
        print("步骤 1: 连接到MQTT服务器")
        print("=" * 60)

        # 获取连接配置
        conn_config = self.controller.get_connection_by_name(connection_name)
        if not conn_config:
            print(f"[ERROR] 未找到连接配置: {connection_name}")
            return False

        print(f"\n使用连接配置:")
        print(f"  名称: {conn_config['name']}")
        print(f"  服务器: {conn_config['host']}:{conn_config['port']}")
        print(f"  用户名: {conn_config['username']}")
        print(f"  客户端ID: {conn_config['client_id']}")
        print(f"  MQTT版本: {conn_config['mqttVersion']}")

        try:
            # 创建MQTT客户端
            if conn_config['mqttVersion'] == '5.0':
                self.client = mqtt.Client(
                    client_id=conn_config['client_id'],
                    protocol=mqtt.MQTTv5
                )
            else:
                self.client = mqtt.Client(
                    client_id=conn_config['client_id'],
                    protocol=mqtt.MQTTv311
                )

            # 设置回调函数
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_subscribe = self.on_subscribe
            self.client.on_message = self.on_message
            self.client.on_publish = self.on_publish

            # 设置用户名和密码
            if conn_config['username']:
                self.client.username_pw_set(
                    conn_config['username'],
                    conn_config['password']
                )

            # 连接
            print(f"\n正在连接到 {conn_config['host']}:{conn_config['port']} ...")
            self.client.connect(conn_config['host'], conn_config['port'], 60)
            self.client.loop_start()

            # 等待连接成功
            for i in range(20):
                if self.connected:
                    break
                time.sleep(0.5)

            if not self.connected:
                print("[ERROR] 连接超时")
                return False

            print("\n[SUCCESS] 已连接到MQTT服务器")
            return True

        except Exception as e:
            print(f"[ERROR] 连接失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def subscribe_topic(self, topic, qos=0):
        """
        订阅主题

        Args:
            topic: 主题名称
            qos: QoS等级 (0, 1, 2)

        Returns:
            bool: 是否订阅成功
        """
        if not self.connected:
            print("[ERROR] 未连接到服务器")
            return False

        try:
            print(f"\n正在订阅主题: {topic} (QoS={qos})")
            result = self.client.subscribe(topic, qos)

            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self.subscribed_topics.append(topic)
                time.sleep(0.5)  # 等待订阅确认
                return True
            else:
                print(f"[ERROR] 订阅失败，错误码: {result[0]}")
                return False

        except Exception as e:
            print(f"[ERROR] 订阅主题时出错: {e}")
            return False

    def publish_message(self, topic, message, qos=0):
        """
        发送消息

        Args:
            topic: 主题名称
            message: 消息内容（字符串或字典）
            qos: QoS等级 (0, 1, 2)

        Returns:
            bool: 是否发送成功
        """
        if not self.connected:
            print("[ERROR] 未连接到服务器")
            return False

        try:
            # 如果消息是字典，转换为JSON字符串
            if isinstance(message, dict):
                message = json.dumps(message, ensure_ascii=False)

            print(f"\n正在发送消息到主题: {topic}")
            print(f"  消息内容: {message}")
            print(f"  QoS: {qos}")

            result = self.client.publish(topic, message, qos)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                time.sleep(0.5)  # 等待发送确认
                return True
            else:
                print(f"[ERROR] 发送失败，错误码: {result.rc}")
                return False

        except Exception as e:
            print(f"[ERROR] 发送消息时出错: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.client:
            print("\n正在断开连接...")
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            print("[OK] 已断开连接")

    def wait_for_messages(self, timeout=5):
        """
        等待接收消息

        Args:
            timeout: 等待时间（秒）
        """
        print(f"\n等待接收消息 ({timeout}秒)...")
        time.sleep(timeout)


def main():
    """主函数 - 执行自动化操作"""
    automation = MQTTXAutomation()

    try:
        # 步骤1: 连接到MQTT服务器
        if not automation.connect_to_server(connection_name="123"):
            print("\n[FAILED] 无法连接到MQTT服务器")
            return

        # 步骤2: 订阅第一个主题 mqtt/system/request
        print("\n" + "=" * 60)
        print("步骤 2: 订阅主题 mqtt/system/request")
        print("=" * 60)
        if not automation.subscribe_topic("mqtt/system/request", qos=0):
            print("[FAILED] 订阅主题失败")
            automation.disconnect()
            return
        print("[SUCCESS] 已订阅主题: mqtt/system/request")

        # 步骤3: 订阅第二个主题 mqtt/system/response
        print("\n" + "=" * 60)
        print("步骤 3: 订阅主题 mqtt/system/response")
        print("=" * 60)
        if not automation.subscribe_topic("mqtt/system/response", qos=0):
            print("[FAILED] 订阅主题失败")
            automation.disconnect()
            return
        print("[SUCCESS] 已订阅主题: mqtt/system/response")

        # 步骤4: 发送消息到第一个主题
        print("\n" + "=" * 60)
        print("步骤 4: 发送消息到 mqtt/system/request")
        print("=" * 60)

        message = {
            "id": "1",
            "status": "reboot"
        }

        if not automation.publish_message("mqtt/system/request", message, qos=0):
            print("[FAILED] 发送消息失败")
            automation.disconnect()
            return
        print("[SUCCESS] 消息已发送")

        # 步骤5: 等待接收响应消息
        print("\n" + "=" * 60)
        print("步骤 5: 等待接收响应消息")
        print("=" * 60)
        automation.wait_for_messages(timeout=10)

        # 显示接收到的消息统计
        print("\n" + "=" * 60)
        print("消息接收统计")
        print("=" * 60)
        if automation.received_messages:
            print(f"\n共接收到 {len(automation.received_messages)} 条消息:")
            for idx, msg in enumerate(automation.received_messages, 1):
                print(f"\n消息 {idx}:")
                print(f"  主题: {msg['topic']}")
                print(f"  内容: {msg['payload']}")
                print(f"  QoS: {msg['qos']}")
        else:
            print("\n未接收到任何消息")

        # 断开连接
        print("\n" + "=" * 60)
        automation.disconnect()

        print("\n" + "=" * 60)
        print("所有操作已完成!")
        print("=" * 60)
        print("\n已完成的操作:")
        print("  1. 连接到MQTT服务器 (192.168.50.36:1883)")
        print("  2. 订阅主题: mqtt/system/request")
        print("  3. 订阅主题: mqtt/system/response")
        print('  4. 发送消息: {"id":"1", "status":"reboot"} 到 mqtt/system/request')
        print(f"  5. 接收到 {len(automation.received_messages)} 条消息")

    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        automation.disconnect()
    except Exception as e:
        print(f"\n[ERROR] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        automation.disconnect()


if __name__ == "__main__":
    main()
