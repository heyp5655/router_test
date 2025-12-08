#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通过SecureCRT执行Boot模式登录

使用CRT的脚本功能自动化操作
既然CRT手动能成功，我们就用CRT的自动化
"""

import os
import time
import subprocess

# 配置
COM_PORT = "COM8"
BAUDRATE = 115200
BOOT_PASSWORD = "ys23#2ls29#4"

# CRT脚本内容（VBScript格式）
CRT_SCRIPT = f"""# $language = "VBScript"
# $interface = "1.0"

' SecureCRT自动化脚本
' 功能：自动进入Boot模式

Sub Main
    ' 获取当前会话
    Dim objTab
    Set objTab = crt.GetScriptTab

    If Not objTab.Session.Connected Then
        crt.Dialog.MessageBox "请先连接到串口！"
        Exit Sub
    End If

    ' 等待User Menu
    crt.Screen.Synchronous = True
    crt.Screen.WaitForString "Enter :", 10

    ' 发送 X 进入Boot
    crt.Screen.Send "X" & chr(13)
    crt.Sleep 500

    ' 等待密码提示
    crt.Screen.WaitForString "please input password:", 10

    ' 发送密码
    crt.Screen.Send "{BOOT_PASSWORD}" & chr(13)

    ' 等待Boot提示符
    If crt.Screen.WaitForString "=>", 5 Then
        crt.Dialog.MessageBox "成功进入Boot模式！"
    Else
        crt.Dialog.MessageBox "进入Boot模式失败！"
    End If

End Sub
"""

# Python格式的CRT脚本（SecureCRT支持Python脚本）
CRT_PYTHON_SCRIPT = f"""# $language = "Python"
# $interface = "1.0"

import time

def Main():
    '''SecureCRT Python脚本 - 自动进入Boot模式'''

    # 获取当前会话
    tab = crt.GetScriptTab()
    screen = tab.Screen

    if not tab.Session.Connected:
        crt.Dialog.MessageBox("请先连接到串口！")
        return

    # 设置同步模式
    screen.Synchronous = True

    try:
        # 等待User Menu
        crt.Dialog.MessageBox("等待User Menu...")
        screen.WaitForString("Enter :", 10)

        # 发送 X
        crt.Dialog.MessageBox("发送 X 进入Boot...")
        screen.Send("X\\r\\n")
        time.sleep(0.5)

        # 等待密码提示
        crt.Dialog.MessageBox("等待密码提示...")
        screen.WaitForString("please input password:", 10)

        # 发送密码
        crt.Dialog.MessageBox("发送密码...")
        screen.Send("{BOOT_PASSWORD}\\r\\n")

        # 等待结果
        time.sleep(2)

        # 检查是否成功
        if "=>" in screen.Get(screen.CurrentRow, 0, screen.CurrentRow, screen.CurrentColumn):
            crt.Dialog.MessageBox("✅ 成功进入Boot模式！")
        else:
            crt.Dialog.MessageBox("❌ 失败")

    except Exception as e:
        crt.Dialog.MessageBox(f"错误: {{str(e)}}")

Main()
"""

print("=" * 80)
print("通过SecureCRT执行自动化登录")
print("=" * 80)

print("\n方案说明:")
print("  既然CRT手动操作能成功，我们使用CRT的脚本自动化功能")
print("  SecureCRT支持VBScript和Python脚本")

print("\n" + "=" * 80)
print("方案1: 使用SecureCRT的Python脚本")
print("=" * 80)

# 保存脚本
script_file = "crt_boot_login.py"
with open(script_file, "w", encoding="utf-8") as f:
    f.write(CRT_PYTHON_SCRIPT)

print(f"\n✅ 已创建脚本: {script_file}")

print("\n使用步骤:")
print("  1. 打开SecureCRT")
print(f"  2. 连接到串口 {COM_PORT} (波特率 {BAUDRATE})")
print("  3. 确保设备在User Menu界面")
print("  4. 在CRT菜单中: Script -> Run...")
print(f"  5. 选择脚本: {os.path.abspath(script_file)}")
print("  6. 观察执行结果")

print("\n" + "=" * 80)
print("方案2: 使用SecureCRT命令行启动")
print("=" * 80)

print("\n如果知道SecureCRT的安装路径，可以用命令行启动:")
print("  SecureCRT.exe /SCRIPT:<脚本路径> /ARG:<参数>")

# 常见的CRT安装路径
crt_paths = [
    r"C:\Program Files\VanDyke Software\SecureCRT\SecureCRT.exe",
    r"C:\Program Files (x86)\VanDyke Software\SecureCRT\SecureCRT.exe",
    r"C:\Program Files\VanDyke Software\Clients\SecureCRT.exe",
]

crt_exe = None
for path in crt_paths:
    if os.path.exists(path):
        crt_exe = path
        print(f"\n✅ 找到SecureCRT: {path}")
        break

if crt_exe:
    print("\n可以使用命令行启动:")
    print(f'  "{crt_exe}" /SCRIPT:"{os.path.abspath(script_file)}"')
else:
    print("\n⚠️ 未找到SecureCRT，请手动指定路径")

print("\n" + "=" * 80)
print("方案3: 使用expect自动化（推荐）")
print("=" * 80)

# 创建expect脚本（如果系统支持）
expect_script = f"""#!/usr/bin/expect -f
# Expect脚本 - 自动进入Boot模式

set timeout 10

# 打开串口
spawn -open [open {COM_PORT} w+]
stty {BAUDRATE} < {COM_PORT}

# 等待User Menu
expect "Enter :"

# 发送 X
send "X\\r"

# 等待密码提示
expect "please input password:"

# 发送密码
send "{BOOT_PASSWORD}\\r"

# 等待Boot提示符
expect {{
    "=>" {{
        puts "✅ 成功进入Boot模式"
        exit 0
    }}
    timeout {{
        puts "❌ 超时"
        exit 1
    }}
}}
"""

expect_file = "boot_login.exp"
with open(expect_file, "w", encoding="utf-8") as f:
    f.write(expect_script)

print(f"\n✅ 已创建Expect脚本: {expect_file}")
print("\n注意: Expect在Windows上需要Cygwin或WSL")
print("  如果有Cygwin: expect boot_login.exp")
print("  如果有WSL: wsl expect boot_login.exp")

print("\n" + "=" * 80)
print("方案4: 分析CRT配置")
print("=" * 80)

print("\n请提供CRT的会话配置文件:")
print("  1. 在CRT中，右键点击会话 -> Properties")
print("  2. 查看以下配置:")
print("     - Connection -> Serial")
print("       - 波特率、数据位、停止位、奇偶校验")
print("       - 流控: None / XON/XOFF / RTS/CTS / DTR/DSR")
print("     - Terminal")
print("       - 终端类型: VT100 / ANSI / etc")
print("       - 字符编码")
print("       - 回车发送: CR / LF / CRLF")
print("     - Emulation")
print("       - 本地回显设置")
print("\n这些配置可能影响密码输入的行为！")

print("\n" + "="*80)
