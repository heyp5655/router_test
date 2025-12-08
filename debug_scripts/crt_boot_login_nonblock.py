# $language = "Python"
# $interface = "1.0"

"""
SecureCRT脚本 - 非阻塞版本
关键发现：WaitForString会阻塞用户输入
解决方案：使用ReadString代替
"""

import time

def Main():
    '''自动进入Boot模式 - 非阻塞版本'''

    tab = crt.GetScriptTab()
    screen = tab.Screen

    if not tab.Session.Connected:
        crt.Dialog.MessageBox("错误：串口未连接！")
        return

    # 关键：关闭同步模式！
    screen.Synchronous = False

    try:
        # ============================================================
        # 步骤1: 等待User Menu
        # ============================================================
        crt.Dialog.MessageBox("步骤1: 确保设备在User Menu\n\n准备发送X")

        # ============================================================
        # 步骤2: 发送 X
        # ============================================================
        screen.Send("X")
        screen.Send("\r")

        crt.Dialog.MessageBox("已发送 X\n\n等待密码提示...")

        # 等待密码提示（使用非阻塞方式）
        time.sleep(1)

        # ============================================================
        # 步骤3: 等待密码提示后，暂停脚本
        # ============================================================
        result = crt.Dialog.MessageBox(
            "现在应该看到密码提示了\n\n"
            "请手动输入密码: ys23#2ls29#4\n"
            "然后按回车\n\n"
            "输入完成后点击确定",
            "手动输入测试",
            64  # 信息图标
        )

        # 等待5秒让用户看到结果
        time.sleep(5)

        # ============================================================
        # 步骤4: 检查结果
        # ============================================================
        # 读取屏幕最后几行
        lines = []
        current_row = screen.CurrentRow
        for i in range(max(0, current_row - 5), current_row + 1):
            try:
                line = screen.Get(i, 0, i, screen.Columns - 1)
                lines.append(line)
            except:
                pass

        content = "\n".join(lines)

        if "=>" in content:
            crt.Dialog.MessageBox("✅✅✅ 成功！\n\n手动输入成功进入Boot模式！\n\n这证明：\n1. 脚本可以正确发送X\n2. 问题在于自动发送密码\n3. 需要找到正确的自动发送方法")
        else:
            crt.Dialog.MessageBox("结果：\n\n" + content + "\n\n如果密码被显示，说明输入被接受了")

    except Exception as e:
        crt.Dialog.MessageBox("错误: " + str(e))

Main()
