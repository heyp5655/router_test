#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试不同的回车格式
既然密码可以显示，问题可能在回车格式上
"""

import serial
import time

COM_PORT = "COM8"
BAUDRATE = 115200
BOOT_PASSWORD = "ys23#2ls29#4"

def test_enter_format(enter_name, enter_bytes):
    """测试一种回车格式"""
    print("\n" + "=" * 80)
    print(f"测试: {enter_name}")
    print(f"字节: {enter_bytes}")
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
        print(f"✅ 串口打开")
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

    # 清空
    if ser.in_waiting > 0:
        ser.read(ser.in_waiting)

    # 发送 X
    print("\n发送 'X' 进入Boot...")
    ser.write(b'X\r\n')
    ser.flush()

    # 等待密码提示
    print("等待密码提示...")
    start = time.time()
    buffer = ""
    found = False

    while time.time() - start < 10:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            buffer += data
            print(data, end='', flush=True)

            if "please input password:" in buffer:
                found = True
                print(f"\n✅ 检测到密码提示")
                break
        time.sleep(0.05)

    if not found:
        print(f"\n❌ 未检测到密码提示")
        ser.close()
        return False

    # 等待一下
    time.sleep(0.1)

    # 发送密码
    print(f"\n发送密码: '{BOOT_PASSWORD}'")
    ser.write(BOOT_PASSWORD.encode('utf-8'))
    ser.flush()

    # 等待一下，让密码显示出来
    time.sleep(0.5)

    # 发送回车
    print(f"发送回车: {enter_name}")
    ser.write(enter_bytes)
    ser.flush()

    # 等待验证
    print("等待验证...")
    time.sleep(2.0)

    # 读取响应
    response = ""
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"\n设备响应:\n{response}")

    # 检查
    success = "=>" in response
    if success:
        print("\n✅ 成功进入Boot模式！")
    else:
        print("\n❌ 失败")

    ser.close()

    if not success:
        print("\n请重新进入User Menu后继续...")
        input("按回车继续...")

    return success

# ============================================================================
# 主程序
# ============================================================================
print("=" * 80)
print("回车格式测试")
print("=" * 80)
print(f"\n说明:")
print(f"  既然密码可以显示出来，问题可能在回车格式")
print(f"  测试不同的回车格式：")
print(f"    1. \\r\\n (CRLF) - Windows标准")
print(f"    2. \\r (CR) - Mac老标准")
print(f"    3. \\n (LF) - Unix/Linux标准")
print("=" * 80)

input("\n确保设备在User Menu，按回车开始...")

# 测试方案
tests = [
    ("\\r\\n (CRLF)", b'\r\n'),
    ("\\r (CR)", b'\r'),
    ("\\n (LF)", b'\n'),
]

for name, enter_bytes in tests:
    success = test_enter_format(name, enter_bytes)
    if success:
        print("\n" + "=" * 80)
        print(f"✅ 找到有效格式: {name}")
        print("=" * 80)
        break
else:
    print("\n" + "=" * 80)
    print("❌ 所有格式都失败")
    print("=" * 80)
