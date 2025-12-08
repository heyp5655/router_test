"""
逐字符发送密码测试 - 观察每个字符的发送情况
"""
import time
import serial
import sys


def test_char_by_char():
    """逐字符发送密码并观察"""

    print("="*80)
    print("逐字符发送密码测试")
    print("="*80)

    port = "COM8"
    password = "ys23#2ls29#4"

    print(f"\n密码: '{password}'")
    print(f"长度: {len(password)}")
    print(f"字符: {[c for c in password]}")
    print(f"ASCII码: {[ord(c) for c in password]}")

    input("\n请确保设备在User Menu的 'Enter :' 提示下，然后按回车继续...")

    try:
        # 打开串口
        print(f"\n打开串口 {port}...")
        ser = serial.Serial(port=port, baudrate=115200, timeout=1)
        print("✅ 串口已打开")

        time.sleep(0.5)

        # 发送X
        print("\n步骤1: 发送 X+回车...")
        ser.write(b'X\r\n')
        time.sleep(1)

        # 读取响应
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print(f"设备响应:\n{data}")

            if "please input password:" not in data:
                print("\n❌ 未检测到密码提示")
                return False

            print("\n✅ 检测到密码提示")

        # 等待一下
        time.sleep(0.5)

        # 逐字符发送密码
        print(f"\n步骤2: 逐字符发送密码...")
        for i, char in enumerate(password):
            print(f"  发送第{i+1}个字符: '{char}' (ASCII: {ord(char)}, HEX: 0x{ord(char):02x})")

            # 发送单个字符
            ser.write(char.encode('utf-8'))
            ser.flush()  # 立即刷新缓冲区

            time.sleep(0.1)  # 每个字符间隔100ms

        print(f"\n✅ 已发送 {len(password)} 个字符")

        # 等待一下
        time.sleep(0.5)

        # 发送回车
        print("\n步骤3: 发送回车...")
        ser.write(b'\r\n')
        ser.flush()

        # 等待响应
        print("\n步骤4: 等待设备响应（3秒）...")
        time.sleep(3)

        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print(f"\n设备响应:\n{response}")

            # 分析响应
            if "=>" in response:
                print("\n" + "="*80)
                print("✅✅✅ 成功进入Boot模式！")
                print("="*80)
                return True
            elif password in response:
                print(f"\n❌ 完整密码被显示: '{password}'")
                print("说明：密码验证失败")
                return False
            elif any(char in response for char in password):
                print("\n⚠️ 部分密码字符被显示")
                for char in password:
                    if char in response:
                        print(f"  字符 '{char}' 出现在响应中")
                return False
            else:
                print("\n❌ 未进入Boot模式，密码也未显示")
                print("可能密码被接受但验证失败")
                return False
        else:
            print("⚠️ 设备无响应")
            return False

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            ser.close()
            print("\n✅ 串口已关闭")
        except:
            pass


if __name__ == "__main__":
    print("\n这个测试会：")
    print("1. 逐字符发送密码，每个字符间隔100ms")
    print("2. 显示每个字符的详细信息")
    print("3. 观察设备响应中哪些字符被显示")
    print("4. 帮助定位是哪个字符导致了问题")

    input("\n按回车键开始...")

    success = test_char_by_char()

    if success:
        print("\n✅ 测试成功！")
        sys.exit(0)
    else:
        print("\n❌ 测试失败！")
        sys.exit(1)
