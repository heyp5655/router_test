#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
完全模拟CRT配置的测试
基于用户提供的CRT截图配置
"""

import serial
import time

COM_PORT = "COM8"
BAUDRATE = 115200
BOOT_PASSWORD = "ys23#2ls29#4"

print("=" * 80)
print("完全模拟CRT配置测试")
print("=" * 80)
print("\nCRT配置:")
print("  端口: COM8")
print("  波特率: 115200")
print("  数据位: 8")
print("  停止位: 1")
print("  奇偶校验: None")
print("  流控: 全部关闭")
print("  终端: VT100")
print("  字符编码: UTF-8")
print("  仿真模式: 换行勾选")
print("=" * 80)

input("\n确保设备在User Menu，按回车开始...")

# 完全按照CRT配置打开串口
try:
    ser = serial.Serial(
        port=COM_PORT,
        baudrate=BAUDRATE,
        bytesize=8,           # 数据位
        parity='N',           # 奇偶校验：None
        stopbits=1,           # 停止位
        timeout=1,
        xonxoff=False,        # XON/XOFF：关闭
        rtscts=False,         # RTS/CTS：关闭
        dsrdtr=False          # DTR/DSR：关闭
    )
    print("\n✅ 串口打开成功（使用CRT相同配置）")
except Exception as e:
    print(f"\n❌ 打开串口失败: {e}")
    exit(1)

# 清空缓冲区
if ser.in_waiting > 0:
    ser.read(ser.in_waiting)

print("\n步骤1: 发送 'X' 进入Boot...")
print("  发送: X<CR><LF>")
ser.write(b'X\r\n')
ser.flush()

# 等待密码提示
print("\n步骤2: 等待密码提示...")
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

    time.sleep(0.01)

if not found:
    print("\n❌ 未检测到密码提示")
    ser.close()
    exit(1)

# 关键：等待一下让设备准备好
print("\n步骤3: 等待设备准备好（100ms）...")
time.sleep(0.1)

# 测试多种发送方式
print("\n" + "=" * 80)
print("测试方式1: 逐字符慢速发送（模拟打字）")
print("=" * 80)

# 逐字符发送
for i, char in enumerate(BOOT_PASSWORD):
    ser.write(char.encode('utf-8'))
    ser.flush()
    print(f"发送字符 [{i+1}/{len(BOOT_PASSWORD)}]: '{char}'")
    time.sleep(0.05)  # 每字符50ms

print("发送完毕，等待500ms...")
time.sleep(0.5)

# 发送回车
print("发送回车: <CR><LF>")
ser.write(b'\r\n')
ser.flush()

# 等待响应
print("\n等待响应...")
time.sleep(2.0)

# 读取响应
response = ""
if ser.in_waiting > 0:
    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')

print("\n" + "=" * 80)
print("设备响应:")
print("=" * 80)
print(response)

# 检查结果
print("\n" + "=" * 80)
print("结果分析:")
print("=" * 80)

if "=>" in response:
    print("✅ 成功进入Boot模式！")
    print("方法: 逐字符慢速发送 + 等待500ms + 回车")
elif BOOT_PASSWORD in response:
    print(f"❌ 密码被显示: {BOOT_PASSWORD}")
    print("说明: 密码输入超时，返回User Menu")
elif "command not found" in response:
    print("❌ 密码被当作命令执行")
    print("说明: 完全超时，字符被当作User Menu命令")
else:
    print("⚠️ 未知响应，请检查输出")

ser.close()
print("\n串口已关闭")
