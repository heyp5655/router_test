# $language = "Python"
# $interface = "1.0"

"""
最简单的测试：只发送X，然后立即退出
让你完全手动输入密码
"""

def Main():
    tab = crt.GetScriptTab()
    screen = tab.Screen

    if not tab.Session.Connected:
        crt.Dialog.MessageBox("错误：串口未连接！")
        return

    # 关键：不设置任何模式
    # screen.Synchronous = False  # 不设置

    # 只发送X
    screen.Send("X\r")

    # 立即显示消息并退出
    crt.Dialog.MessageBox(
        "已发送 X\n\n"
        "现在请立即手动输入密码\n\n"
        "点击确定后，脚本退出，不会干扰你的输入"
    )

    # 脚本结束，不再干扰

Main()
