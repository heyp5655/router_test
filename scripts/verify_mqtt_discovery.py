#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证MQTT测试用例是否能被发现"""

import sys
import os

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, r'E:\GIT\ROUTER_TEST')

print("=" * 60)
print("验证MQTT测试用例是否能被TestRunner发现")
print("=" * 60)

try:
    from core.test_runner import TestRunner

    print("\n创建TestRunner实例...")
    runner = TestRunner()

    print(f"\n发现的测试用例总数: {len(runner.available_cases)}")

    # 查找MQTT测试用例
    mqtt_tests = [test for test in runner.available_cases if 'mqtt' in test['module_path'].lower()]

    if mqtt_tests:
        print(f"\n找到 {len(mqtt_tests)} 个MQTT测试用例:")
        for test in mqtt_tests:
            print(f"  - {test['name']}")
            print(f"    类名: {test['class_name']}")
            print(f"    模块: {test['module_path']}")
            print(f"    分类: {test['category']}")
            print()
        print("[成功] MQTT测试用例已被正确发现!")
    else:
        print("\n[失败] 未找到MQTT测试用例!")
        sys.exit(1)

except Exception as e:
    print(f"\n[错误] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
