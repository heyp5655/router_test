# $language = "Python"
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
        screen.Send("X\r\n")
        time.sleep(0.5)

        # 等待密码提示
        crt.Dialog.MessageBox("等待密码提示...")
        screen.WaitForString("please input password:", 10)

        # 提示手动输入
        crt.Dialog.MessageBox("⚠️ 现在请手动输入密码！\n\n1. 点击确定后\n2. 立即在CRT窗口中手动输入密码\n3. 按回车\n\n输入完成后等待...")

        # 等待用户手动输入（足够长的时间）
        time.sleep(30)  # 给用户30秒

        # 再次确认
        crt.Dialog.MessageBox("请确认:\n\n已经手动输入密码并按回车了吗？\n\n点击确定继续检查结果")

        # 等待结果
        time.sleep(2)

        # 检查是否成功
        if "=>" in screen.Get(screen.CurrentRow, 0, screen.CurrentRow, screen.CurrentColumn):
            crt.Dialog.MessageBox("✅ 成功进入Boot模式！")
        else:
            crt.Dialog.MessageBox("❌ 失败")

    except Exception as e:
        crt.Dialog.MessageBox("错误: " + str(e))

Main()
