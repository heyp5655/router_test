"""
简化版密码测试工具
只负责在密码提示时接收和发送密码
需要手动操作到 'please input password:' 阶段
"""

import time
import serial
import sys


def simple_password_test():
    """简单的密码测试"""

    print("="*80)
    print("简化版Boot密码测试工具")
    print("="*80)

    port = "COM8"

    print("\n请先手动操作：")
    print("1. 用串口工具（PuTTY等）连接设备")
    print("2. 登录路由器")
    print("3. 发送 reboot")
    print("4. 等待U-Boot，按 q 进入 User Menu")
    print("5. 在 'Enter :' 提示下输入 X 并回车")
    print("6. 等待出现 'please input password:'")
    print("7. 关闭串口工具（释放串口）")
    print("8. 回到这里继续")

    input("\n完成上述步骤后，按回车继续...")

    try:
        # 打开串口
        print(f"\n正在打开串口 {port}...")
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1
        )
        print(f"✅ 串口 {port} 已打开")

        # 等待一下
        time.sleep(1)

        # 读取当前串口内容
        print("\n正在读取串口状态...")
        time.sleep(1)

        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print(f"串口输出:\n{data}")

            if "please input password:" in data:
                print("\n✅ 检测到密码提示")
            else:
                print("\n⚠️ 未检测到密码提示，但继续...")
        else:
            print("⚠️ 串口无数据，但继续...")

        # 获取密码
        print("\n" + "="*80)
        print("请输入Boot密码")
        print("="*80)
        print("\n方法1: 直接输入密码（不推荐，因为有特殊字符）")
        print("方法2: 从TXT复制后，在这里按 Ctrl+V 粘贴")
        print("方法3: 留空直接回车，使用代码中的默认密码")

        user_input = input("\n请输入密码（或留空使用默认）: ")

        if user_input.strip():
            user_password = user_input.strip()
            print(f"\n✅ 使用您输入的密码")
        else:
            user_password = "ys23#2ls29#4"
            print(f"\n✅ 使用默认密码")

        print(f"\n密码: '{user_password}'")
        print(f"长度: {len(user_password)}")
        print(f"字符: {[c for c in user_password]}")
        print(f"十六进制: {user_password.encode('utf-8').hex()}")

        # 对比
        code_password = "ys23#2ls29#4"
        if user_password == code_password:
            print(f"\n✅ 与代码密码相同")
        else:
            print(f"\n❌ 与代码密码不同")
            print(f"代码密码: '{code_password}'")
            print(f"代码长度: {len(code_password)}")
            print(f"代码十六进制: {code_password.encode('utf-8').hex()}")

        input("\n按回车键发送密码...")

        # 发送密码
        print(f"\n发送密码中...")
        ser.write(user_password.encode('utf-8'))
        print(f"✅ 已发送: '{user_password}'")

        time.sleep(0.3)

        # 发送回车
        ser.write(b'\r\n')
        print("✅ 已发送回车")

        # 等待响应
        print("\n等待设备响应（5秒）...")
        time.sleep(5)

        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print(f"\n设备响应:\n{response}")

            if "=>" in response:
                print("\n" + "="*80)
                print("✅✅✅ 成功进入Boot模式！")
                print("="*80)

                # 保持串口打开，让用户继续操作
                print("\n串口保持打开状态，您可以继续在Boot模式下操作")
                print("按 Ctrl+C 退出")

                try:
                    while True:
                        time.sleep(0.1)
                        if ser.in_waiting > 0:
                            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                            print(data, end='', flush=True)
                except KeyboardInterrupt:
                    print("\n\n退出...")

                return True
            else:
                print("\n❌ 未检测到Boot提示符 '=>'")

                if user_password in response:
                    print("⚠️ 密码被显示出来: 密码验证失败")

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
    success = simple_password_test()

    if success:
        print("\n✅ 测试成功！")
        sys.exit(0)
    else:
        print("\n❌ 测试失败！")
        sys.exit(1)
