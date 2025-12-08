"""
交互式Boot密码测试工具
让用户手动从TXT粘贴密码，验证密码是否正确
"""

import time
import serial
from utils.serial_client import SerialClient


def interactive_boot_test():
    """交互式测试Boot密码"""

    print("="*80)
    print("交互式Boot密码测试工具")
    print("="*80)

    port = "COM8"

    try:
        # 1. 创建串口客户端
        print(f"\n步骤1: 打开串口 {port}...")
        client = SerialClient(port=port, baudrate=115200, timeout=30)
        if not client.open():
            print("❌ 串口打开失败")
            return False
        print(f"✅ 串口已打开")

        # 2. 登录
        print("\n步骤2: 登录路由器...")
        if not client.login():
            print("❌ 登录失败")
            client.close()
            return False
        print("✅ 登录成功")

        # 3. 发送reboot
        print("\n步骤3: 发送reboot命令...")
        client.send_command("reboot", wait_time=2)

        # 4. 等待U-Boot
        print("\n步骤4: 等待U-Boot启动...")
        found, output = client.read_until("Normal Boot", timeout=30)
        if not found:
            print("❌ 未检测到Normal Boot")
            client.close()
            return False
        print("✅ 检测到Normal Boot")

        # 5. 发送q进入User Menu
        print("\n步骤5: 发送q进入User Menu...")
        client.send_command("q", wait_time=1)

        # 6. 等待User Menu
        print("\n步骤6: 等待User Menu...")
        found, output = client.read_until("User Menu", timeout=10)
        if not found:
            print("❌ 未检测到User Menu")
            client.close()
            return False
        print("✅ 检测到User Menu")

        # 7. 等待Enter提示
        print("\n步骤7: 等待Enter提示...")
        buffer = ""
        start_time = time.time()
        while time.time() - start_time < 10:
            time.sleep(0.5)
            if client.serial.in_waiting > 0:
                data = client.serial.read(client.serial.in_waiting).decode('utf-8', errors='ignore')
                buffer += data
                print(data, end='', flush=True)
                if "Enter :" in buffer:
                    print("\n✅ 检测到Enter提示")
                    break

        # 8. 发送X+回车
        print("\n步骤8: 发送X+回车...")
        time.sleep(0.3)
        client.serial.write(b'X\r\n')
        time.sleep(0.5)

        # 9. 等待密码提示
        print("\n步骤9: 等待密码提示...")
        found, output = client.read_until("please input password:", timeout=10)
        if not found:
            print("❌ 未检测到密码提示")
            client.close()
            return False
        print("✅ 检测到密码提示")

        # 10. ⚠️ 交互式：让用户输入密码
        print("\n" + "="*80)
        print("⚠️ 重要：请按以下步骤操作")
        print("="*80)
        print("1. 打开您桌面的 '工作笔记.txt' 文件")
        print("2. 找到密码: ys23#2ls29#4")
        print("3. 用鼠标选中并复制密码")
        print("4. 回到这个窗口")
        print("5. 粘贴密码（Ctrl+V 或右键粘贴）")
        print("6. 按回车键发送")
        print("="*80)

        user_password = input("\n请粘贴密码（从TXT复制）: ").strip()

        print(f"\n您输入的密码: '{user_password}'")
        print(f"密码长度: {len(user_password)}")
        print(f"密码十六进制: {user_password.encode('utf-8').hex()}")

        # 对比代码中的密码
        code_password = "ys23#2ls29#4"
        print(f"\n代码中的密码: '{code_password}'")
        print(f"代码密码十六进制: {code_password.encode('utf-8').hex()}")

        if user_password == code_password:
            print("✅ 密码与代码相同")
        else:
            print("❌ 密码与代码不同！")
            print(f"差异: TXT有{len(user_password)}字符，代码有{len(code_password)}字符")

        input("\n按回车键发送密码到设备...")

        # 11. 发送用户粘贴的密码
        print("\n步骤11: 发送密码...")
        time.sleep(1.0)
        client.serial.write(user_password.encode('utf-8'))
        print(f"已发送: '{user_password}'")
        time.sleep(0.5)
        client.serial.write(b'\r\n')
        print("已发送回车")

        # 12. 等待响应
        print("\n步骤12: 等待设备响应...")
        time.sleep(3.0)

        if client.serial.in_waiting > 0:
            response = client.serial.read(client.serial.in_waiting).decode('utf-8', errors='ignore')
            print(f"设备响应:\n{response}")

            if "=>" in response:
                print("\n" + "="*80)
                print("✅✅✅ 成功进入Boot模式！")
                print("="*80)
                return True
            else:
                print("\n❌ 未进入Boot模式")
                return False
        else:
            print("⚠️ 设备无响应")
            return False

    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            client.close()
        except:
            pass


if __name__ == "__main__":
    interactive_boot_test()
