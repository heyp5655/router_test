#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
精确时序测试
手动输入成功：密码隐藏，不显示
Python失败：密码显示，说明没进入隐藏模式

测试不同的等待时机，找到正确的时间窗口
"""

import serial
import time

COM_PORT = "COM8"
BAUDRATE = 115200
BOOT_PASSWORD = "ys23#2ls29#4"

def test_with_delay(delay_ms):
    """
    测试特定延迟

    Args:
        delay_ms: 从检测到密码提示到发送密码的延迟（毫秒）

    Returns:
        bool: 是否成功
    """
    print("\n" + "=" * 80)
    print(f"测试: 延迟 {delay_ms}ms")
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
    except Exception as e:
        print(f"❌ 打开串口失败: {e}")
        return False

    # 清空缓冲区
    if ser.in_waiting > 0:
        ser.read(ser.in_waiting)

    # 发送 X
    print("发送 'X'...")
    ser.write(b'X\r\n')
    ser.flush()

    # 等待密码提示
    print("等待 'please input password:'...")
    start = time.time()
    buffer = ""
    prompt_time = None

    while time.time() - start < 10:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            buffer += data
            print(data, end='', flush=True)

            if "please input password:" in buffer and prompt_time is None:
                prompt_time = time.time()
                print(f"\n✅ 检测到密码提示")
                break

        time.sleep(0.01)  # 精确到10ms

    if prompt_time is None:
        print("\n❌ 未检测到密码提示")
        ser.close()
        return False

    # 等待指定的延迟
    delay_sec = delay_ms / 1000.0
    print(f"\n等待 {delay_ms}ms...")
    time.sleep(delay_sec)

    # 发送密码（逐字符，模拟打字）
    print("发送密码（逐字符）...")
    for char in BOOT_PASSWORD:
        ser.write(char.encode('utf-8'))
        ser.flush()
        time.sleep(0.01)  # 每字符10ms

    # 立即发送回车
    ser.write(b'\r\n')
    ser.flush()

    send_time = time.time()
    total_delay = (send_time - prompt_time) * 1000
    print(f"密码发送完成，总延迟: {total_delay:.0f}ms")

    # 等待验证
    print("等待验证...")
    time.sleep(2.0)

    # 读取响应
    response = ""
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')

    # 检查结果
    success = False
    if "=>" in response:
        print("✅ 成功！密码未显示，进入Boot模式")
        print(f"响应: {response[:100]}")
        success = True
    elif BOOT_PASSWORD in response:
        print(f"❌ 失败：密码被显示")
        # 找到密码显示的位置
        idx = response.find(BOOT_PASSWORD)
        context = response[max(0, idx-30):min(len(response), idx+50)]
        print(f"显示位置: ...{context}...")
    elif "command not found" in response:
        print("❌ 失败：密码被当作命令")
    else:
        print("⚠️ 未知响应")
        print(f"响应: {response[:200]}")

    ser.close()

    if not success:
        print("\n请重新进入User Menu...")
        input("准备好后按回车继续...")

    return success

# ============================================================================
# 主程序
# ============================================================================
print("=" * 80)
print("精确时序测试")
print("=" * 80)
print(f"\n目标: 找到正确的时间窗口")
print(f"\n观察:")
print(f"  - 手动输入：密码隐藏（正常）")
print(f"  - Python：密码显示（异常）")
print(f"\n假设:")
print(f"  - 设备需要一定时间切换到密码输入模式")
print(f"  - 如果发送太快，还没准备好")
print(f"  - 如果发送太慢，超时返回User Menu")
print(f"\n策略:")
print(f"  - 测试不同延迟：100ms, 200ms, 300ms, 500ms")
print(f"  - 找到最佳时间窗口")
print("=" * 80)

input("\n确保设备在User Menu，按回车开始...")

# 测试不同延迟
delays = [100, 200, 300, 500]

for delay in delays:
    success = test_with_delay(delay)
    if success:
        print("\n" + "=" * 80)
        print(f"✅ 找到最佳延迟: {delay}ms")
        print("=" * 80)
        break
else:
    print("\n" + "=" * 80)
    print("❌ 所有延迟都失败")
    print("=" * 80)
    print("\n可能原因:")
    print("  1. 时间窗口非常短，需要更精确的时序")
    print("  2. 需要特殊的发送方式")
    print("  3. 串口配置问题（流控等）")
    print("\n建议:")
    print("  1. 检查CRT的串口配置")
    print("  2. 尝试在CRT中启用日志记录原始数据")
    print("  3. 对比CRT和Python的字节流")
