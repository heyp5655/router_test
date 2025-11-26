#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MQTT测试工具类
提供MQTT连接、订阅、发布等功能，用于路由器MQTT功能测试
"""

import paho.mqtt.client as mqtt
import time
import json
import threading
from typing import Callable, Optional, List, Dict, Any


class MQTTTestClient:
    """MQTT测试客户端类"""

    def __init__(self,
                 broker: str = "192.168.50.36",
                 port: int = 1883,
                 username: Optional[str] = "admin",
                 password: Optional[str] = "password",
                 client_id: Optional[str] = None,
                 mqtt_version: str = "5.0"):
        """
        初始化MQTT测试客户端

        Args:
            broker: MQTT服务器地址
            port: MQTT服务器端口
            username: 用户名
            password: 密码
            client_id: 客户端ID（可选）
            mqtt_version: MQTT版本（"3.1.1" 或 "5.0"）
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id or f"test_client_{int(time.time())}"
        self.mqtt_version = mqtt_version

        self.client = None
        self.connected = False
        self.subscribed_topics = {}
        self.received_messages = []
        self.message_callbacks = {}
        self._lock = threading.Lock()

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """连接回调"""
        if rc == 0:
            print(f"[MQTT] 成功连接到 {self.broker}:{self.port}")
            self.connected = True
        else:
            print(f"[MQTT] 连接失败，错误码: {rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, rc, properties=None):
        """断开连接回调"""
        print(f"[MQTT] 断开连接，错误码: {rc}")
        self.connected = False

    def _on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        """订阅回调"""
        print(f"[MQTT] 订阅成功，消息ID: {mid}, QoS: {granted_qos}")

    def _on_message(self, client, userdata, msg):
        """消息接收回调"""
        try:
            payload = msg.payload.decode('utf-8')

            with self._lock:
                # 保存消息
                message_data = {
                    'topic': msg.topic,
                    'payload': payload,
                    'qos': msg.qos,
                    'timestamp': time.time()
                }
                self.received_messages.append(message_data)

            print(f"[MQTT] 收到消息 - 主题: {msg.topic}, 内容: {payload}")

            # 调用用户注册的回调函数
            if msg.topic in self.message_callbacks:
                self.message_callbacks[msg.topic](msg.topic, payload)

        except Exception as e:
            print(f"[MQTT] 处理消息时出错: {e}")

    def _on_publish(self, client, userdata, mid, properties=None):
        """发布消息回调"""
        print(f"[MQTT] 消息发送成功，消息ID: {mid}")

    def connect(self, timeout: int = 10) -> bool:
        """
        连接到MQTT服务器

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 是否连接成功
        """
        try:
            # 创建MQTT客户端
            if self.mqtt_version == "5.0":
                self.client = mqtt.Client(
                    client_id=self.client_id,
                    protocol=mqtt.MQTTv5
                )
            else:
                self.client = mqtt.Client(
                    client_id=self.client_id,
                    protocol=mqtt.MQTTv311
                )

            # 设置回调函数
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_subscribe = self._on_subscribe
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish

            # 设置用户名和密码
            if self.username:
                self.client.username_pw_set(self.username, self.password)

            # 连接
            print(f"[MQTT] 正在连接到 {self.broker}:{self.port} ...")
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()

            # 等待连接成功
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if not self.connected:
                print("[MQTT] 连接超时")
                return False

            return True

        except Exception as e:
            print(f"[MQTT] 连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.client:
            print("[MQTT] 正在断开连接...")
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

    def subscribe(self, topic: str, qos: int = 0, callback: Optional[Callable] = None) -> bool:
        """
        订阅主题

        Args:
            topic: 主题名称
            qos: QoS等级 (0, 1, 2)
            callback: 消息回调函数，签名为 callback(topic: str, payload: str)

        Returns:
            bool: 是否订阅成功
        """
        if not self.connected:
            print("[MQTT] 未连接到服务器")
            return False

        try:
            print(f"[MQTT] 订阅主题: {topic} (QoS={qos})")
            result = self.client.subscribe(topic, qos)

            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self.subscribed_topics[topic] = qos

                # 注册回调函数
                if callback:
                    self.message_callbacks[topic] = callback

                time.sleep(0.5)  # 等待订阅确认
                return True
            else:
                print(f"[MQTT] 订阅失败，错误码: {result[0]}")
                return False

        except Exception as e:
            print(f"[MQTT] 订阅主题时出错: {e}")
            return False

    def unsubscribe(self, topic: str) -> bool:
        """
        取消订阅主题

        Args:
            topic: 主题名称

        Returns:
            bool: 是否成功
        """
        if not self.connected:
            print("[MQTT] 未连接到服务器")
            return False

        try:
            result = self.client.unsubscribe(topic)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                if topic in self.subscribed_topics:
                    del self.subscribed_topics[topic]
                if topic in self.message_callbacks:
                    del self.message_callbacks[topic]
                print(f"[MQTT] 已取消订阅: {topic}")
                return True
            else:
                print(f"[MQTT] 取消订阅失败，错误码: {result[0]}")
                return False
        except Exception as e:
            print(f"[MQTT] 取消订阅时出错: {e}")
            return False

    def publish(self, topic: str, payload: Any, qos: int = 0) -> bool:
        """
        发布消息

        Args:
            topic: 主题名称
            payload: 消息内容（字符串、字典或其他可序列化对象）
            qos: QoS等级 (0, 1, 2)

        Returns:
            bool: 是否发送成功
        """
        if not self.connected:
            print("[MQTT] 未连接到服务器")
            return False

        try:
            # 如果消息是字典，转换为JSON字符串
            if isinstance(payload, dict):
                payload = json.dumps(payload, ensure_ascii=False)
            elif not isinstance(payload, str):
                payload = str(payload)

            print(f"[MQTT] 发送消息到 {topic}: {payload}")

            result = self.client.publish(topic, payload, qos)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                time.sleep(0.2)  # 等待发送确认
                return True
            else:
                print(f"[MQTT] 发送失败，错误码: {result.rc}")
                return False

        except Exception as e:
            print(f"[MQTT] 发送消息时出错: {e}")
            return False

    def wait_for_message(self, topic: str, timeout: int = 10,
                        condition: Optional[Callable[[str], bool]] = None) -> Optional[Dict[str, Any]]:
        """
        等待接收指定主题的消息

        Args:
            topic: 主题名称
            timeout: 超时时间（秒）
            condition: 可选的条件函数，用于过滤消息。签名为 condition(payload: str) -> bool

        Returns:
            收到的消息字典，包含 topic, payload, qos, timestamp；超时返回 None
        """
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            with self._lock:
                # 查找匹配的消息
                for msg in reversed(self.received_messages):
                    if msg['topic'] == topic:
                        # 如果提供了条件函数，检查是否满足条件
                        if condition is None or condition(msg['payload']):
                            return msg

            time.sleep(0.1)

        print(f"[MQTT] 等待消息超时: {topic}")
        return None

    def get_received_messages(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取接收到的消息

        Args:
            topic: 可选，过滤指定主题的消息

        Returns:
            消息列表
        """
        with self._lock:
            if topic:
                return [msg for msg in self.received_messages if msg['topic'] == topic]
            else:
                return self.received_messages.copy()

    def clear_received_messages(self):
        """清空接收到的消息"""
        with self._lock:
            self.received_messages.clear()
        print("[MQTT] 已清空消息队列")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connected


# 使用示例
if __name__ == "__main__":
    # 创建MQTT客户端
    client = MQTTTestClient(
        broker="192.168.50.36",
        port=1883,
        username="admin",
        password="password"
    )

    # 连接到服务器
    if client.connect():
        print("\n[成功] 已连接到MQTT服务器\n")

        # 订阅主题
        client.subscribe("mqtt/system/request")
        client.subscribe("mqtt/system/response")

        # 发送消息
        message = {"id": "1", "status": "reboot"}
        client.publish("mqtt/system/request", message)

        # 等待接收消息
        print("\n等待接收消息（10秒）...\n")
        time.sleep(10)

        # 显示接收到的消息
        messages = client.get_received_messages()
        print(f"\n共接收到 {len(messages)} 条消息:")
        for idx, msg in enumerate(messages, 1):
            print(f"\n消息 {idx}:")
            print(f"  主题: {msg['topic']}")
            print(f"  内容: {msg['payload']}")

        # 断开连接
        client.disconnect()
    else:
        print("\n[失败] 无法连接到MQTT服务器")
