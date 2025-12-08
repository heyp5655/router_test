# $language = "Python"
# $interface = "1.0"

"""
测试不同的等待时间
找出从发送X到发送密码的最佳延迟
"""

import time

def test_with_delay(delay_seconds):
    """测试指定延迟"""
    tab = crt.GetScriptTab()
    screen = tab.Screen

    # 发送 X
    screen.Send("X\r")

    # 等待指定时间
    time.sleep(delay_seconds)

    # 发送密码
    screen.Send("ys23#2ls29#4\r")

    # 等待结果
    time.sleep(3)

    # 检查结果
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
        return True, "成功"
    elif "ys23#2ls29#4" in content:
        return False, "密码被显示"
    else:
        return False, "未知: " + content[-100:]

def Main():
    tab = crt.GetScriptTab()
    screen = tab.Screen

    if not tab.Session.Connected:
        crt.Dialog.MessageBox("错误：串口未连接！")
        return

    # 测试不同延迟
    delays = [0.5, 1.0, 1.5, 2.0]

    for delay in delays:
        crt.Dialog.MessageBox("测试延迟: " + str(delay) + " 秒\n\n确保设备在User Menu")

        success, msg = test_with_delay(delay)

        if success:
            crt.Dialog.MessageBox("✅ 找到最佳延迟！\n\n" + str(delay) + " 秒\n\n" + msg)
            return
        else:
            result = crt.Dialog.MessageBox(
                "❌ 延迟 " + str(delay) + " 秒失败\n\n" + msg + "\n\n继续测试下一个？",
                "测试结果",
                4  # Yes/No
            )
            if result == 7:  # No
                return

    crt.Dialog.MessageBox("所有延迟都失败了")

Main()
