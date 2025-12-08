#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试不同的回车格式
CRT的"换行"设置可能影响回车发送格式
"""

import serial
import time

COM_PORT = "COM8"
BAUDRATE = 115200
BOOT_PASSWORD = "ys23#2ls29#4"

def test_one_method(method_name, password_send_func):
    """测试一种发送方法"""
    print("\n" + "=" * 80)
    print(f"测试: {method_name}")
    print("=" * 80)

    # 打开串口
    ser = serial.Serial(
        port=COM_PORT,
        baudrate=BAUDRATE,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=1,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False
    )

    # 清空
    if ser.in_waiting > 0:
        ser.read(ser.in_waiting)

    # 发送 X
    print("发送 'X'...")
    ser.write(b'X\r\n')
    ser.flush()

    # 等待密码提示
    start = time.time()
    buffer = ""
    while time.time() - start < 10:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            buffer += data
            print(data, end='', flush=True)
            if "please input password:" in buffer:
                print("\n✅ 检测到密码提示")
                break
        time.sleep(0.01)

    if "please input password:" not in buffer:
        print("\n❌ 未检测到密码提示")
        ser.close()
        return False

    # 等待
    time.sleep(0.1)

    # 调用发送函数
    password_send_func(ser)

    # 等待响应
    time.sleep(2.0)

    # 读取响应
    response = ""
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')

    # 检查
    success = "=>" in response
    if success:
        print(f"\n✅ 成功！方法有效: {method_name}")
    elif BOOT_PASSWORD in response:
        print(f"\n❌ 失败：密码被显示")
    else:
        print(f"\n❌ 失败")

    print(f"\n响应:\n{response[:200]}")

    ser.close()

    if not success:
        input("\n请重新进入User Menu后按回车继续...")

    return success

# ========================================================================
# 不同的发送方法
# ========================================================================

def method1_password_cr_lf(ser):
    """方法1: 密码 + \\r\\n"""
    print("发送: 密码 + \\r\\n")
    ser.write((BOOT_PASSWORD + '\r\n').encode('utf-8'))
    ser.flush()

def method2_password_cr_only(ser):
    """方法2: 密码 + \\r (只有回车，无换行)"""
    print("发送: 密码 + \\r")
    ser.write((BOOT_PASSWORD + '\r').encode('utf-8'))
    ser.flush()

def method3_slow_typing_cr_lf(ser):
    """方法3: 逐字符慢速 + \\r\\n"""
    print("逐字符发送密码...")
    for char in BOOT_PASSWORD:
        ser.write(char.encode('utf-8'))
        ser.flush()
        time.sleep(0.05)
    time.sleep(0.2)
    print("发送回车: \\r\\n")
    ser.write(b'\r\n')
    ser.flush()

def method4_slow_typing_cr_only(ser):
    """方法4: 逐字符慢速 + \\r"""
    print("逐字符发送密码...")
    for char in BOOT_PASSWORD:
        ser.write(char.encode('utf-8'))
        ser.flush()
        time.sleep(0.05)
    time.sleep(0.2)
    print("发送回车: \\r")
    ser.write(b'\r')
    ser.flush()

def method5_fast_typing_cr(ser):
    """方法5: 逐字符快速(10ms) + \\r"""
    print("逐字符快速发送密码...")
    for char in BOOT_PASSWORD:
        ser.write(char.encode('utf-8'))
        ser.flush()
        time.sleep(0.01)
    time.sleep(0.1)
    print("发送回车: \\r")
    ser.write(b'\r')
    ser.flush()

# ========================================================================
# 主程序
# ========================================================================
print("=" * 80)
print("Boot密码 - 多方案全面测试")
print("=" * 80)
print("\n基于CRT配置测试5种不同方案")
print("=" * 80)

input("\n确保设备在User Menu，按回车开始...")

methods = [
    ("方法1: 一次性密码+\\r\\n", method1_password_cr_lf),
    ("方法2: 一次性密码+\\r", method2_password_cr_only),
    ("方法3: 慢速逐字符+\\r\\n", method3_slow_typing_cr_lf),
    ("方法4: 慢速逐字符+\\r", method4_slow_typing_cr_only),
    ("方法5: 快速逐字符+\\r", method5_fast_typing_cr),
]

for name, func in methods:
    success = test_one_method(name, func)
    if success:
        print("\n" + "=" * 80)
        print(f"✅✅✅ 找到有效方法: {name}")
        print("=" * 80)
        break
else:
    print("\n" + "=" * 80)
    print("❌ 所有方法都失败")
    print("=" * 80)
