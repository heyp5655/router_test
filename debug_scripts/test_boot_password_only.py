#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Boot密码输入专项调试工具
前提：设备已经在User Menu界面
功能：只测试从User Menu输入密码进入Boot模式
"""

import serial
import time
import os

# 配置
COM_PORT = "COM8"
BAUDRATE = 115200
BOOT_PASSWORD = "ys23#2ls29#4"

print("=" * 80)
print("Boot密码输入专项调试")
print("=" * 80)
print(f"\n前提条件: 设备已经在User Menu界面")
print(f"  串口: {COM_PORT}")
print(f"  波特率: {BAUDRATE}")
print(f"  Boot密码: '{BOOT_PASSWORD}'")
print(f"\n测试流程:")
print(f"  1. 发送 'X' 进入Boot模式")
print(f"  2. 等待密码提示")
print(f"  3. 一次性发送密码+回车")
print(f"  4. 验证是否进入Boot模式")
print("=" * 80)

input("\n按回车键开始测试...")

# 打开串口
print(f"\n步骤1: 打开串口 {COM_PORT}...")
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
    exit(1)

# 清空缓冲区
if ser.in_waiting > 0:
    old_data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    print(f"清空旧数据: {len(old_data)} 字节")

print("\n步骤2: 发送 'X' 进入Boot模式...")
print("发送: X<CR>")
ser.write(b'X\r\n')
ser.flush()

# 等待密码提示
print("\n步骤3: 等待密码提示 'please input password:'...")
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
    print(f"接收到的内容:\n{buffer}")
    ser.close()
    exit(1)

# 等待设备准备好
print(f"\n步骤4: 等待设备准备好接收密码（50ms）...")
time.sleep(0.05)

# 方案1: 一次性发送密码+回车
print(f"\n步骤5: 一次性发送密码+回车...")
print(f"发送: '{BOOT_PASSWORD}\\r\\n' (一次性)")

# 显示发送的字节
complete_string = BOOT_PASSWORD + '\r\n'
send_bytes = complete_string.encode('utf-8')
print(f"字节: {send_bytes}")
print(f"十六进制: {send_bytes.hex()}")
print(f"长度: {len(send_bytes)} 字节")

# 发送
send_time = time.time()
ser.write(send_bytes)
ser.flush()
print(f"✅ 发送完成 (耗时 {(time.time() - send_time)*1000:.1f}ms)")

# 等待验证
print(f"\n步骤6: 等待密码验证结果...")
time.sleep(2.0)

# 读取响应
print(f"\n步骤7: 读取设备响应...")
response = ""
if ser.in_waiting > 0:
    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    print(f"设备响应:\n{response}")

# 检查是否成功
print(f"\n" + "=" * 80)
print("结果分析")
print("=" * 80)

if "=>" in response:
    print("✅ 成功进入Boot模式！")
    print("检测到Boot提示符: '=>'")
elif "Enter :" in response and BOOT_PASSWORD in response:
    print("❌ 密码被显示，未进入Boot模式")
    print(f"密码被显示: {BOOT_PASSWORD}")
    print("\n可能原因:")
    print("  1. 密码发送太慢，超过时间窗口")
    print("  2. 设备还没准备好接收密码")
    print("  3. 发送格式不对")
elif "command not found" in response:
    print("❌ 密码被当作命令执行")
    print("\n可能原因:")
    print("  1. 密码输入超时，返回User Menu")
    print("  2. 密码格式错误")
else:
    print("⚠️ 未知响应")
    print(f"响应内容:\n{response}")

# 关闭串口
print(f"\n关闭串口...")
ser.close()
print("✅ 串口已关闭")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
