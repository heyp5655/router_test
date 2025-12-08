"""
实时Boot密码测试工具
保持串口连接，让用户实时输入密码测试
"""

import time
import serial
import sys


def realtime_boot_test():
    """实时测试Boot密码"""

    print("="*80)
    print("实时Boot密码测试工具")
    print("="*80)

    port = "COM8"
    baudrate = 115200

    try:
        # 打开串口
        print(f"\n正在打开串口 {port}...")
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1
        )
        print(f"✅ 串口 {port} 已打开")

        # 清空缓冲区
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        print("\n" + "="*80)
        print("串口已准备好，开始监听...")
        print("="*80)
        print("\n请在串口工具中操作：")
        print("1. 登录路由器")
        print("2. 发送 reboot")
        print("3. 等待 U-Boot，按 q 进入 User Menu")
        print("4. 在 'Enter :' 提示下输入 X")
        print("5. 看到 'please input password:' 后")
        print("6. 回到这个窗口，输入密码")
        print("\n" + "="*80)

        buffer = ""
        password_prompt_detected = False

        while True:
            # 读取串口数据
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                buffer += data
                print(data, end='', flush=True)

                # 检测密码提示
                if "please input password:" in buffer and not password_prompt_detected:
                    password_prompt_detected = True
                    print("\n\n" + "="*80)
                    print("✅ 检测到密码提示！")
                    print("="*80)

                    # 让用户输入密码
                    print("\n⚠️ 请输入密码（从TXT复制粘贴）：")
                    user_password = input("密码: ").strip()

                    print(f"\n您输入的密码: '{user_password}'")
                    print(f"密码长度: {len(user_password)}")
                    print(f"字符列表: {[c for c in user_password]}")
                    print(f"十六进制: {user_password.encode('utf-8').hex()}")

                    # 对比代码中的密码
                    code_password = "ys23#2ls29#4"
                    print(f"\n代码中的密码: '{code_password}'")
                    print(f"代码密码长度: {len(code_password)}")
                    print(f"代码十六进制: {code_password.encode('utf-8').hex()}")

                    if user_password == code_password:
                        print("\n✅ 密码与代码完全相同")
                    else:
                        print("\n❌ 密码与代码不同！")
                        if len(user_password) != len(code_password):
                            print(f"   长度差异: 您的={len(user_password)}, 代码={len(code_password)}")
                        for i in range(min(len(user_password), len(code_password))):
                            if user_password[i] != code_password[i]:
                                print(f"   位置{i}: 您的='{user_password[i]}'(0x{ord(user_password[i]):02x}) vs 代码='{code_password[i]}'(0x{ord(code_password[i]):02x})")

                    input("\n按回车键发送密码...")

                    # 发送密码
                    print(f"\n发送密码...")
                    ser.write(user_password.encode('utf-8'))
                    print(f"✅ 已发送: '{user_password}'")

                    time.sleep(0.3)

                    # 发送回车
                    ser.write(b'\r\n')
                    print("✅ 已发送回车")

                    print("\n等待设备响应...")
                    time.sleep(3)

                    # 读取响应
                    if ser.in_waiting > 0:
                        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                        print(f"\n设备响应:\n{response}")

                        if "=>" in response:
                            print("\n" + "="*80)
                            print("✅✅✅ 成功进入Boot模式！")
                            print("="*80)

                            # 询问是否继续测试
                            choice = input("\n是否继续测试？(y/n): ").strip().lower()
                            if choice != 'y':
                                break
                            else:
                                buffer = ""
                                password_prompt_detected = False
                        else:
                            print("\n❌ 未检测到Boot提示符 '=>'")
                            print("密码验证可能失败")

                            # 询问是否重试
                            choice = input("\n是否重新测试？(y/n): ").strip().lower()
                            if choice != 'y':
                                break
                            else:
                                buffer = ""
                                password_prompt_detected = False
                    else:
                        print("⚠️ 设备无响应")
                        buffer = ""
                        password_prompt_detected = False

                # 检测Boot提示符
                if "=>" in data:
                    print("\n\n" + "="*80)
                    print("✅ 检测到Boot提示符 '=>'")
                    print("="*80)

            # 检查用户是否想退出
            # （注：这里无法检测键盘输入，因为input()会阻塞）
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            ser.close()
            print("\n✅ 串口已关闭")
        except:
            pass


if __name__ == "__main__":
    print("\n实时Boot密码测试工具")
    print("此工具会监听串口，当检测到密码提示时，让您输入密码")
    print("\n注意：")
    print("- 请确保没有其他程序占用COM8")
    print("- 请准备好您的工作笔记.txt文件")
    print("- 检测到密码提示后，请从TXT复制粘贴密码")

    input("\n按回车键开始...")

    realtime_boot_test()
