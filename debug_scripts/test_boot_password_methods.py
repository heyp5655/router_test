#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Boot密码多方案测试工具
测试不同的密码发送方式，找出正确方法
"""

import serial
import time

# 配置
COM_PORT = "COM8"
BAUDRATE = 115200
BOOT_PASSWORD = "ys23#2ls29#4"

def test_method(method_name, send_func):
    """
    测试一种发送方法

    Args:
        method_name: 方法名称
        send_func: 发送函数，参数为serial对象

    Returns:
        bool: 是否成功
    """
    print("\n" + "=" * 80)
    print(f"测试方法: {method_name}")
    print("=" * 80)

    # 打开串口
    try:
        ser = serial.Serial(
            port=COM_PORT,
            baudrate=BAUDRATE,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1
        )
        print(f"✅ 串口打开成功")
    except Exception as e:
        print(f"❌ 打开串口失败: {e}")
        return False

    # 清空缓冲区
    if ser.in_waiting > 0:
        ser.read(ser.in_waiting)

    # 发送 X 进入Boot
    print("\n发送 'X' 进入Boot模式...")
    ser.write(b'X\r\n')
    ser.flush()

    # 等待密码提示
    print("等待密码提示...")
    start_time = time.time()
    buffer = ""
    password_prompt_found = False

    while time.time() - start_time < 10:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            buffer += data
            print(data, end='', flush=True)

            if "please input password:" in buffer:
                password_prompt_found = True
                print(f"\n✅ 检测到密码提示")
                break

        time.sleep(0.05)

    if not password_prompt_found:
        print(f"\n❌ 未检测到密码提示")
        ser.close()
        return False

    # 等待50ms
    time.sleep(0.05)

    # 调用发送函数
    print(f"\n使用方法: {method_name}")
    send_func(ser)

    # 等待验证
    print("等待验证结果...")
    time.sleep(2.0)

    # 读取响应
    response = ""
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"\n设备响应:\n{response}")

    # 检查结果
    success = False
    if "=>" in response:
        print("\n✅ 成功进入Boot模式！")
        success = True
    elif BOOT_PASSWORD in response:
        print(f"\n❌ 密码被显示: {BOOT_PASSWORD}")
    elif "command not found" in response:
        print("\n❌ 密码被当作命令执行")
    else:
        print("\n⚠️ 未知响应")

    # 关闭串口
    ser.close()

    if not success:
        print("\n需要重新进入User Menu才能继续测试下一个方法")
        input("准备好后按回车继续...")

    return success

# ============================================================================
# 方法1: 一次性发送密码+回车
# ============================================================================
def method1_all_at_once(ser):
    """方法1: 一次性发送密码+\\r\\n"""
    print("一次性发送: 密码+\\r\\n")
    complete = BOOT_PASSWORD + '\r\n'
    ser.write(complete.encode('utf-8'))
    ser.flush()
    print(f"发送: {len(complete)} 字符")

# ============================================================================
# 方法2: 密码和回车分两次发送，间隔极短（10ms）
# ============================================================================
def method2_separate_10ms(ser):
    """方法2: 密码和回车分两次，间隔10ms"""
    print("分两次发送:")
    print("  1. 密码")
    ser.write(BOOT_PASSWORD.encode('utf-8'))
    ser.flush()

    time.sleep(0.01)  # 10ms

    print("  2. 回车（10ms后）")
    ser.write(b'\r\n')
    ser.flush()

# ============================================================================
# 方法3: 密码和回车分两次发送，间隔稍长（50ms）
# ============================================================================
def method3_separate_50ms(ser):
    """方法3: 密码和回车分两次，间隔50ms"""
    print("分两次发送:")
    print("  1. 密码")
    ser.write(BOOT_PASSWORD.encode('utf-8'))
    ser.flush()

    time.sleep(0.05)  # 50ms

    print("  2. 回车（50ms后）")
    ser.write(b'\r\n')
    ser.flush()

# ============================================================================
# 方法4: 只发送\\r（不含\\n）
# ============================================================================
def method4_only_cr(ser):
    """方法4: 密码+\\r（不含\\n）"""
    print("发送: 密码+\\r（不含\\n）")
    complete = BOOT_PASSWORD + '\r'
    ser.write(complete.encode('utf-8'))
    ser.flush()

# ============================================================================
# 方法5: 逐字符快速发送（模拟打字，每字符5ms）
# ============================================================================
def method5_char_by_char_5ms(ser):
    """方法5: 逐字符发送，每字符5ms间隔"""
    print("逐字符快速发送（每字符5ms）:")
    for i, char in enumerate(BOOT_PASSWORD):
        ser.write(char.encode('utf-8'))
        ser.flush()
        if i < len(BOOT_PASSWORD) - 1:
            time.sleep(0.005)  # 5ms

    # 发送回车
    ser.write(b'\r\n')
    ser.flush()
    print(f"总耗时: {len(BOOT_PASSWORD) * 5}ms")

# ============================================================================
# 方法6: 使用ascii编码
# ============================================================================
def method6_ascii_encoding(ser):
    """方法6: 使用ASCII编码"""
    print("一次性发送: 密码+\\r\\n (ASCII编码)")
    complete = BOOT_PASSWORD + '\r\n'
    ser.write(complete.encode('ascii'))
    ser.flush()

# ============================================================================
# 主程序
# ============================================================================
print("=" * 80)
print("Boot密码多方案测试")
print("=" * 80)
print(f"\n串口: {COM_PORT}")
print(f"波特率: {BAUDRATE}")
print(f"Boot密码: '{BOOT_PASSWORD}'")
print(f"\n说明:")
print(f"  1. 每个方法测试失败后需要重新进入User Menu")
print(f"  2. 在CRT中输入'r'重启 → 按'q'进入User Menu")
print(f"  3. 准备好后按回车继续下一个测试")
print("=" * 80)

input("\n确保设备在User Menu，按回车开始...")

methods = [
    ("方法1: 一次性发送密码+\\r\\n", method1_all_at_once),
    ("方法2: 密码和回车分两次，间隔10ms", method2_separate_10ms),
    ("方法3: 密码和回车分两次，间隔50ms", method3_separate_50ms),
    ("方法4: 只发送\\r（不含\\n）", method4_only_cr),
    ("方法5: 逐字符快速发送（每字符5ms）", method5_char_by_char_5ms),
    ("方法6: 使用ASCII编码", method6_ascii_encoding),
]

for name, func in methods:
    success = test_method(name, func)
    if success:
        print("\n" + "=" * 80)
        print(f"✅ 找到有效方法: {name}")
        print("=" * 80)
        break
else:
    print("\n" + "=" * 80)
    print("❌ 所有方法都失败了")
    print("=" * 80)
    print("\n建议:")
    print("  1. 检查密码是否正确")
    print("  2. 尝试在CRT中手动输入密码（不粘贴）")
    print("  3. 检查CRT的会话选项 -> 终端设置")
