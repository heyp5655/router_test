#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
串口数据监听工具
监听CRT发送的原始字节，找出差异
"""

import serial
import time
from datetime import datetime

COM_PORT = "COM8"
BAUDRATE = 115200

print("=" * 80)
print("串口数据监听工具")
print("=" * 80)
print(f"\n配置:")
print(f"  端口: {COM_PORT}")
print(f"  波特率: {BAUDRATE}")
print(f"\n说明:")
print(f"  1. 这个工具会监听并记录串口上的所有数据")
print(f"  2. 包括发送和接收的原始字节")
print(f"  3. 运行后，在CRT中手动操作一次")
print(f"  4. 我们会看到CRT具体发送了什么")
print("=" * 80)

input("\n按回车开始监听...")

# 打开串口
try:
    ser = serial.Serial(
        port=COM_PORT,
        baudrate=BAUDRATE,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=0.1,  # 非阻塞
        xonxoff=False,
        rtscts=False,
        dsrdtr=False
    )
    print(f"\n✅ 串口监听已启动")
    print(f"⏰ 开始时间: {datetime.now().strftime('%H:%M:%S')}")
    print("\n" + "=" * 80)
    print("现在请在CRT中操作:")
    print("  1. 输入 'X' 按回车")
    print("  2. 看到密码提示后输入密码")
    print("  3. 按回车")
    print("\n监听中... (按 Ctrl+C 停止)")
    print("=" * 80 + "\n")
except Exception as e:
    print(f"❌ 打开串口失败: {e}")
    exit(1)

# 监听数据
log_file = f"serial_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
last_data_time = time.time()

try:
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"串口监听日志\n")
        f.write(f"端口: {COM_PORT}\n")
        f.write(f"波特率: {BAUDRATE}\n")
        f.write(f"开始时间: {datetime.now()}\n")
        f.write("=" * 80 + "\n\n")

        while True:
            # 读取数据
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]

                # 解码显示
                try:
                    text = data.decode('utf-8', errors='ignore')
                except:
                    text = "[无法解码]"

                # 十六进制表示
                hex_str = ' '.join([f'{b:02x}' for b in data])

                # 输出到控制台
                print(f"[{timestamp}] 接收 {len(data)} 字节")
                print(f"  HEX: {hex_str}")
                print(f"  ASCII: {repr(text)}")
                print(f"  显示: {text}")
                print()

                # 写入日志
                f.write(f"[{timestamp}] 接收 {len(data)} 字节\n")
                f.write(f"  HEX: {hex_str}\n")
                f.write(f"  ASCII: {repr(text)}\n")
                f.write(f"  显示: {text}\n")
                f.write("\n")
                f.flush()

                last_data_time = time.time()

            # 如果3秒没有数据，提示一下
            if time.time() - last_data_time > 3:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 等待数据...")
                last_data_time = time.time()

            time.sleep(0.01)

except KeyboardInterrupt:
    print("\n\n" + "=" * 80)
    print("监听已停止")
    print("=" * 80)
    print(f"\n✅ 日志已保存: {log_file}")
    ser.close()

