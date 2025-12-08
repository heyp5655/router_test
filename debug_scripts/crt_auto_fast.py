# $language = "Python"
# $interface = "1.0"

"""
SecureCRT自动化脚本 - 完全自动化版本
关键：不使用WaitForString，不阻塞输入
策略：发送命令后立即发送密码，不等待
"""

import time

def Main():
    tab = crt.GetScriptTab()
    screen = tab.Screen

    if not tab.Session.Connected:
        crt.Dialog.MessageBox("错误：串口未连接！")
        return

    try:
        crt.Dialog.MessageBox("准备开始\n\n确保设备在User Menu")

        # ============================================================
        # 步骤1: 发送 X
        # ============================================================
        screen.Send("X\r")

        # 等待密码提示出现（但不使用WaitForString）
        time.sleep(1)

        # ============================================================
        # 步骤2: 立即发送密码（不等待，不检查）
        # ============================================================
        # 方案A: 一次性发送
        screen.Send("ys23#2ls29#4\r")

        crt.Dialog.MessageBox("已发送:\n1. X\n2. 密码\n\n等待结果...")

        # 等待验证
        time.sleep(3)

        # ============================================================
        # 步骤3: 检查结果
        # ============================================================
        lines = []
        current_row = screen.CurrentRow
        for i in range(max(0, current_row - 10), current_row + 1):
            try:
                line = screen.Get(i, 0, i, screen.Columns - 1)
                lines.append(line)
            except:
                pass

        content = "\n".join(lines)

        if "=>" in content:
            crt.Dialog.MessageBox("✅✅✅ 成功进入Boot模式！\n\n方案A有效：\n- 发送X\n- 等1秒\n- 发送密码")
        elif "ys23#2ls29#4" in content:
            crt.Dialog.MessageBox("❌ 失败：密码被显示\n\n可能原因：\n- 等待时间不够\n- 需要更长延迟\n\n" + content[-200:])
        else:
            crt.Dialog.MessageBox("结果未知\n\n" + content[-200:])

    except Exception as e:
        crt.Dialog.MessageBox("错误: " + str(e))

Main()
