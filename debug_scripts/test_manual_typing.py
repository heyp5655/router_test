#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
精确模拟手动输入的测试
既然手动输入成功，我们就完全模拟手动打字
"""

import serial
import time

COM_PORT = "COM8"
BAUDRATE = 115200
BOOT_PASSWORD = "ys23#2ls29#4"

print("=" * 80)
print("精确模拟手动输入测试")
print("=" * 80)
print(f"\n密码: '{BOOT_PASSWORD}'")
print(f"策略: 完全模拟人类手动打字")
print(f"  - 逐字符发送")
print(f"  - 每个字符间隔50ms（模拟打字速度）")
print(f"  - 密码输完后，停顿200ms")
print(f"  - 然后按回车")
print("=" * 80)

input("\n确保设备在User Menu，按回车开始...")

# 打开串口
print(f"\n打开串口 {COM_PORT}...")
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
    print(f"❌ 失败: {e}")
    exit(1)

# 清空缓冲区
if ser.in_waiting > 0:
    ser.read(ser.in_waiting)

# 发送 X
print("\n步骤1: 发送 'X' 进入Boot...")
ser.write(b'X\r\n')
ser.flush()
time.sleep(0.5)

# 等待密码提示
print("步骤2: 等待密码提示...")
start_time = time.time()
buffer = ""
found = False

while time.time() - start_time < 10:
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
    exit(1)

# 稍微等待一下
time.sleep(0.1)

# 逐字符发送密码（模拟打字）
print(f"\n步骤3: 逐字符发送密码（模拟人类打字）...")
print(f"密码: ", end='', flush=True)

for i, char in enumerate(BOOT_PASSWORD):
    print(f"{char}", end='', flush=True)
    ser.write(char.encode('utf-8'))
    ser.flush()

    # 每个字符后等待50ms（模拟打字速度）
    if i < len(BOOT_PASSWORD) - 1:
        time.sleep(0.05)

print()  # 换行

# 密码输完后，停顿一下（模拟人思考）
print("步骤4: 停顿200ms（模拟人停顿）...")
time.sleep(0.2)

# 按回车
print("步骤5: 按回车...")
ser.write(b'\r\n')
ser.flush()

# 等待验证
print("步骤6: 等待验证结果...")
time.sleep(2.0)

# 读取响应
print("\n步骤7: 读取响应...")
response = ""
if ser.in_waiting > 0:
    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    print(f"\n设备响应:\n{response}")

# 检查结果
print("\n" + "=" * 80)
if "=>" in response:
    print("✅ 成功进入Boot模式！")
    print("方法有效: 逐字符发送 + 停顿200ms + 回车")
elif BOOT_PASSWORD in response:
    print(f"❌ 密码被显示")
elif "command not found" in response:
    print(f"❌ 密码被当作命令")
else:
    print("⚠️ 未知响应")

print("=" * 80)

ser.close()
