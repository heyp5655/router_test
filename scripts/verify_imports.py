#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证导入路径的测试脚本"""

import sys
import os

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, r'E:\GIT\ROUTER_TEST')

print("=" * 60)
print("验证项目导入路径")
print("=" * 60)

errors = []
success = []

# 测试1: 导入MQTT测试用例
try:
    from test_cases.mqtt_test.mqtt_router_command_reboot_test import MqttRouterCommandRebootTest
    success.append("[OK] MQTT测试用例导入成功")
except Exception as e:
    errors.append(f"[FAIL] MQTT测试用例导入失败: {e}")

# 测试2: 导入utils工具类
try:
    from utils.mqtt_client import MQTTTestClient
    success.append("[OK] MQTT客户端工具导入成功")
except Exception as e:
    errors.append(f"[FAIL] MQTT客户端工具导入失败: {e}")

try:
    from utils.network_utils import network_utils
    success.append("[OK] 网络工具导入成功")
except Exception as e:
    errors.append(f"[FAIL] 网络工具导入失败: {e}")

# 测试3: 导入core模块
try:
    from core.router_client import RouterClient
    success.append("[OK] 路由器客户端导入成功")
except Exception as e:
    errors.append(f"[FAIL] 路由器客户端导入失败: {e}")

# 测试4: 导入测试基类
try:
    from test_cases.base_test import BaseTest
    success.append("[OK] 测试基类导入成功")
except Exception as e:
    errors.append(f"[FAIL] 测试基类导入失败: {e}")

# 测试5: 导入其他测试用例
try:
    from test_cases.wan_tests.pppoe_test import PPPoETest
    success.append("[OK] PPPoE测试用例导入成功")
except Exception as e:
    errors.append(f"[FAIL] PPPoE测试用例导入失败: {e}")

try:
    from test_cases.cellular_tests.pin_function_test import PinFunctionTest
    success.append("[OK] PIN测试用例导入成功")
except Exception as e:
    errors.append(f"[FAIL] PIN测试用例导入失败: {e}")

# 显示结果
print("\n成功导入:")
for s in success:
    print(f"  {s}")

if errors:
    print("\n导入失败:")
    for e in errors:
        print(f"  {e}")
    print(f"\n总结: {len(success)} 成功, {len(errors)} 失败")
    sys.exit(1)
else:
    print(f"\n总结: 所有 {len(success)} 项测试通过!")
    sys.exit(0)
