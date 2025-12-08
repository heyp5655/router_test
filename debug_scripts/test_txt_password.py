"""
最终测试：使用TXT文件中的密码
"""
import time
import serial
import sys
import os


def test_with_txt_password():
    """从TXT文件读取密码并测试"""

    print("="*80)
    print("最终测试：使用TXT文件中的密码")
    print("="*80)

    # 1. 读取TXT文件中的密码
    txt_path = r"C:\Users\admin\Desktop\工作笔记.txt"

    if not os.path.exists(txt_path):
        print(f"❌ 找不到文件: {txt_path}")
        return False

    print(f"\n正在读取: {txt_path}")

    # 尝试多种编码
    password_from_txt = None
    for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']:
        try:
            with open(txt_path, 'r', encoding=encoding) as f:
                content = f.read()

            # 查找密码行
            for line in content.split('\n'):
                if 'ys23' in line:
                    # 提取密码
                    import re
                    match = re.search(r'(ys23#2ls29#4)', line)
                    if match:
                        password_from_txt = match.group(1)
                        print(f"✅ 成功读取密码（编码: {encoding}）")
                        break

            if password_from_txt:
                break
        except:
            continue

    if not password_from_txt:
        print("❌ 未能从TXT提取密码")
        return False

    print(f"\nTXT中的密码: '{password_from_txt}'")
    print(f"密码长度: {len(password_from_txt)}")
    print(f"字符列表: {[c for c in password_from_txt]}")
    print(f"十六进制: {password_from_txt.encode('utf-8').hex()}")

    # 对比代码中的密码
    code_password = "ys23#2ls29#4"
    print(f"\n代码中的密码: '{code_password}'")
    print(f"代码密码长度: {len(code_password)}")
    print(f"代码十六进制: {code_password.encode('utf-8').hex()}")

    if password_from_txt == code_password:
        print("\n✅ 两个密码完全相同")
    else:
        print("\n❌ 两个密码不同！")
        return False

    # 2. 使用TXT密码测试Boot登录
    print("\n" + "="*80)
    print("开始测试Boot登录")
    print("="*80)

    port = "COM8"

    input("\n请确保设备在User Menu的 'Enter :' 提示下，然后按回车继续...")

    try:
        # 打开串口
        print(f"\n打开串口 {port}...")
        ser = serial.Serial(port=port, baudrate=115200, timeout=1)
        print("✅ 串口已打开")

        time.sleep(0.5)

        # 发送X
        print("\n发送 X+回车...")
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

        # 发送密码（使用TXT中的密码，一次性发送）
        print(f"\n发送密码: '{password_from_txt}'")
        ser.write(password_from_txt.encode('utf-8'))
        time.sleep(0.3)

        # 发送回车
        print("发送回车")
        ser.write(b'\r\n')

        # 等待响应
        print("\n等待设备响应（3秒）...")
        time.sleep(3)

        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print(f"\n设备响应:\n{response}")

            if "=>" in response:
                print("\n" + "="*80)
                print("✅✅✅ 成功进入Boot模式！")
                print("="*80)
                return True
            else:
                print("\n❌ 未进入Boot模式")
                if password_from_txt in response:
                    print("⚠️ 密码被显示: 验证失败")
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
    success = test_with_txt_password()

    if success:
        print("\n✅ 测试成功！")
        print("说明TXT中的密码是正确的")
        sys.exit(0)
    else:
        print("\n❌ 测试失败！")
        print("需要进一步排查问题")
        sys.exit(1)
