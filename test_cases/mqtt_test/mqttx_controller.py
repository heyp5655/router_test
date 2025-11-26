#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MQTTX Controller - 用于控制MQTTX软件的工具类
"""

import sqlite3
import json
import uuid
import os
from pathlib import Path


class MQTTXController:
    """MQTTX控制器类"""

    def __init__(self, db_path=None):
        """
        初始化MQTTX控制器

        Args:
            db_path: MQTTX数据库路径，如果为None则使用默认路径
        """
        if db_path is None:
            appdata = os.environ.get('APPDATA')
            db_path = Path(appdata) / 'MQTTX' / 'MQTTX.db'

        self.db_path = str(db_path)
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"MQTTX数据库文件不存在: {self.db_path}")

    def connect_db(self):
        """连接数据库"""
        return sqlite3.connect(self.db_path)

    def get_tables(self):
        """获取所有表名"""
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        return [table[0] for table in tables]

    def get_table_schema(self, table_name):
        """获取表结构"""
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        schema = cursor.fetchall()
        conn.close()
        return schema

    def get_all_connections(self):
        """获取所有MQTT连接配置"""
        conn = self.connect_db()
        cursor = conn.cursor()

        # 尝试不同的表名
        try:
            cursor.execute("SELECT * FROM ConnectionEntity")
            connections = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
        except sqlite3.OperationalError:
            try:
                cursor.execute("SELECT * FROM connections")
                connections = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
            except sqlite3.OperationalError:
                conn.close()
                return []

        conn.close()

        # 转换为字典列表
        result = []
        for conn_data in connections:
            result.append(dict(zip(columns, conn_data)))

        return result

    def create_connection(self, name, host, port, username, password,
                         client_id=None, use_tls=False, mqtt_version="5.0"):
        """
        创建新的MQTT连接配置

        Args:
            name: 连接名称
            host: MQTT服务器地址
            port: MQTT服务器端口
            username: 用户名
            password: 密码
            client_id: 客户端ID（可选，默认生成随机ID）
            use_tls: 是否使用TLS（默认False）
            mqtt_version: MQTT版本（默认5.0）

        Returns:
            connection_id: 创建的连接ID
        """
        if client_id is None:
            client_id = f"mqttx_{uuid.uuid4().hex[:8]}"

        connection_id = str(uuid.uuid4())
        will_id = str(uuid.uuid4())

        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        conn = self.connect_db()
        cursor = conn.cursor()

        # 先创建 WillEntity（遗嘱消息）
        cursor.execute("""
            INSERT INTO WillEntity (id, lastWillTopic, lastWillPayload, lastWillQos, lastWillRetain,
                                   willDelayInterval, payloadFormatIndicator, messageExpiryInterval,
                                   contentType, responseTopic, correlationData, willUserProperties)
            VALUES (?, '', '', 0, 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL)
        """, (will_id,))

        # 插入连接配置
        cursor.execute("""
            INSERT INTO ConnectionEntity (
                id, client_id, name, clean, protocol, host, port, keepalive, connectTimeout,
                reconnect, username, password, path, certType, ssl, mqttVersion,
                unreadMessageCount, clientIdWithTime, rejectUnauthorized, isCollection,
                createAt, updateAt, willId, reconnectPeriod
            ) VALUES (
                ?, ?, ?, 1, 'mqtt', ?, ?, 60, 10,
                0, ?, ?, '/mqtt', '', ?, ?,
                0, 0, 1, 0,
                ?, ?, ?, 4000
            )
        """, (connection_id, client_id, name, host, port, username, password,
              1 if use_tls else 0, mqtt_version, now, now, will_id))

        conn.commit()
        conn.close()

        print(f"[OK] 成功创建连接: {name} (ID: {connection_id})")
        return connection_id

    def update_connection(self, connection_id, **kwargs):
        """
        更新MQTT连接配置

        Args:
            connection_id: 连接ID
            **kwargs: 要更新的字段（host, port, username, password等）
        """
        if not kwargs:
            return

        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        kwargs['updateAt'] = now

        set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [connection_id]

        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE ConnectionEntity SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()

        print(f"[OK] 成功更新连接 (ID: {connection_id})")

    def get_connection_by_name(self, name):
        """根据名称查找连接"""
        connections = self.get_all_connections()
        for conn in connections:
            if conn.get('name') == name:
                return conn
        return None

    def test_connection_with_paho(self, connection_id=None, name=None):
        """
        使用paho-mqtt测试连接

        Args:
            connection_id: 连接ID（优先）
            name: 连接名称

        Returns:
            bool: 连接是否成功
        """
        # 获取连接配置
        if connection_id:
            connections = self.get_all_connections()
            conn_config = next((c for c in connections if c['id'] == connection_id), None)
        elif name:
            conn_config = self.get_connection_by_name(name)
        else:
            raise ValueError("必须提供 connection_id 或 name")

        if not conn_config:
            raise ValueError("未找到指定的连接配置")

        # 使用paho-mqtt进行测试
        try:
            import paho.mqtt.client as mqtt

            def on_connect(client, userdata, flags, rc, properties=None):
                if rc == 0:
                    print(f"[OK] 成功连接到MQTT服务器!")
                    userdata['connected'] = True
                else:
                    print(f"[FAIL] 连接失败，错误码: {rc}")
                    userdata['connected'] = False

            def on_disconnect(client, userdata, rc, properties=None):
                print(f"断开连接，错误码: {rc}")

            user_data = {'connected': False}

            # 创建MQTT客户端
            if conn_config['mqttVersion'] == '5.0':
                client = mqtt.Client(client_id=conn_config['client_id'],
                                   protocol=mqtt.MQTTv5,
                                   userdata=user_data)
            else:
                client = mqtt.Client(client_id=conn_config['client_id'],
                                   protocol=mqtt.MQTTv311,
                                   userdata=user_data)

            client.on_connect = on_connect
            client.on_disconnect = on_disconnect

            # 设置用户名和密码
            if conn_config['username']:
                client.username_pw_set(conn_config['username'], conn_config['password'])

            # 连接
            print(f"\n正在连接到 {conn_config['host']}:{conn_config['port']} ...")
            print(f"  用户名: {conn_config['username']}")
            print(f"  客户端ID: {conn_config['client_id']}")
            print(f"  MQTT版本: {conn_config['mqttVersion']}")
            print(f"  TLS: {'开启' if conn_config['ssl'] else '关闭'}")

            client.connect(conn_config['host'], conn_config['port'], 60)
            client.loop_start()

            # 等待连接结果
            import time
            for i in range(10):
                if user_data['connected']:
                    break
                time.sleep(0.5)

            client.loop_stop()
            client.disconnect()

            return user_data['connected']

        except ImportError:
            print("错误: 未安装 paho-mqtt 库")
            print("请运行: pip install paho-mqtt")
            return False
        except Exception as e:
            print(f"连接测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def delete_connection(self, connection_id):
        """删除MQTT连接配置"""
        conn = self.connect_db()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM ConnectionEntity WHERE id = ?", (connection_id,))
            conn.commit()
        except sqlite3.OperationalError:
            try:
                cursor.execute("DELETE FROM connections WHERE id = ?", (connection_id,))
                conn.commit()
            except sqlite3.OperationalError:
                pass

        conn.close()


def main():
    """主函数 - 用于测试和演示"""
    try:
        controller = MQTTXController()
        print("=" * 60)
        print("MQTTX Controller - MQTT连接管理工具")
        print("=" * 60)
        print(f"数据库路径: {controller.db_path}\n")

        # 获取所有连接配置
        print("当前的MQTT连接配置:")
        print("-" * 60)
        connections = controller.get_all_connections()
        if connections:
            for idx, conn in enumerate(connections, 1):
                print(f"\n【连接 {idx}】")
                print(f"  名称: {conn['name']}")
                print(f"  ID: {conn['id']}")
                print(f"  服务器: {conn['host']}:{conn['port']}")
                print(f"  用户名: {conn['username']}")
                print(f"  密码: {'*' * len(conn['password']) if conn['password'] else '(无)'}")
                print(f"  客户端ID: {conn['client_id']}")
                print(f"  MQTT版本: {conn['mqttVersion']}")
                print(f"  TLS: {'开启' if conn['ssl'] else '关闭'}")
                print(f"  创建时间: {conn['createAt']}")
                print(f"  更新时间: {conn['updateAt']}")
        else:
            print("  (暂无连接)")

        # 测试现有连接
        if connections:
            print("\n" + "=" * 60)
            print("测试MQTT连接")
            print("=" * 60)

            # 测试第一个连接
            first_conn = connections[0]
            print(f"\n正在测试连接: {first_conn['name']}")
            success = controller.test_connection_with_paho(connection_id=first_conn['id'])

            if success:
                print("\n[SUCCESS] 连接测试成功!")
                print("\nMQTTX配置正确，可以与MQTT服务器正常通信。")
                print("您现在可以在MQTTX软件中手动连接，或者通过此控制器进行自动化操作。")
            else:
                print("\n[FAILED] 连接测试失败")
                print("\n请检查:")
                print("  1. MQTT服务器是否运行在 192.168.50.36:1883")
                print("  2. 用户名密码是否正确")
                print("  3. 网络连接是否正常")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
