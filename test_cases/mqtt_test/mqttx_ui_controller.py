#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MQTTX软件UI自动化控制脚本
通过pywinauto和pyautogui控制MQTTX软件界面
"""

import time
import subprocess
import pyautogui
import pywinauto
from pywinauto import Application
from pywinauto.findwindows import ElementNotFoundError


class MQTTXUIController:
    """MQTTX软件UI自动化控制器"""

    def __init__(self, mqttx_path=r"D:\MQTTClient2\MQTTX\MQTTX.exe"):
        """
        初始化控制器

        Args:
            mqttx_path: MQTTX软件的路径
        """
        self.mqttx_path = mqttx_path
        self.app = None
        self.window = None

        # 设置PyAutoGUI安全设置
        pyautogui.PAUSE = 1.0  # 每次操作后暂停1秒
        pyautogui.FAILSAFE = True  # 鼠标移到左上角时停止

    def start_mqttx(self):
        """启动MQTTX软件"""
        print("=" * 60)
        print("启动MQTTX软件")
        print("=" * 60)

        try:
            # 检查MQTTX是否已经在运行
            print("\n检查MQTTX是否已在运行...")
            result = subprocess.run(
                ["powershell", "-Command", "Get-Process -Name MQTTX -ErrorAction SilentlyContinue"],
                capture_output=True,
                text=True
            )

            if "MQTTX" in result.stdout:
                print("[INFO] MQTTX已在运行")
                # 尝试连接到已运行的实例
                try:
                    self.app = Application(backend="uia").connect(path=self.mqttx_path, timeout=5)
                    print("[OK] 已连接到运行中的MQTTX")
                except:
                    print("[INFO] 无法连接到现有实例，将启动新实例")
                    subprocess.Popen([self.mqttx_path])
                    time.sleep(3)
            else:
                print("[INFO] 正在启动MQTTX...")
                subprocess.Popen([self.mqttx_path])
                time.sleep(5)  # 等待软件启动

            # 尝试连接到MQTTX应用
            print("\n正在连接到MQTTX应用...")
            self.app = Application(backend="uia").connect(path=self.mqttx_path, timeout=10)

            print("[OK] MQTTX软件已启动")
            return True

        except Exception as e:
            print(f"[ERROR] 启动MQTTX失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def find_mqttx_window(self):
        """查找MQTTX窗口"""
        print("\n正在查找MQTTX窗口...")

        try:
            # 尝试通过窗口标题查找
            windows = pyautogui.getWindowsWithTitle("MQTTX")
            if windows:
                window = windows[0]
                print(f"[OK] 找到MQTTX窗口: {window.title}")

                # 激活窗口
                if window.isMinimized:
                    window.restore()
                window.activate()
                time.sleep(1)

                return True
            else:
                print("[WARN] 未找到MQTTX窗口")
                return False

        except Exception as e:
            print(f"[ERROR] 查找窗口失败: {e}")
            return False

    def click_connect_button(self):
        """点击连接按钮"""
        print("\n" + "=" * 60)
        print("点击连接按钮")
        print("=" * 60)

        try:
            # 方法1: 使用图像识别（需要截图连接按钮）
            # 这里我们使用键盘快捷键或鼠标点击特定位置

            print("[INFO] 寻找连接按钮...")
            print("[INFO] 请确保MQTTX窗口在前台显示")

            # 获取屏幕尺寸
            screen_width, screen_height = pyautogui.size()
            print(f"[INFO] 屏幕分辨率: {screen_width}x{screen_height}")

            # 提示用户
            print("\n[提示] 接下来将使用屏幕坐标点击")
            print("[提示] 如果您知道连接按钮的位置，可以手动指定坐标")
            print("[提示] 或者我们可以使用OCR识别文字")

            # 使用PyAutoGUI在屏幕上查找"连接"按钮
            # 这里需要您提供连接按钮的截图或坐标

            return True

        except Exception as e:
            print(f"[ERROR] 点击连接按钮失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_window_info(self):
        """获取MQTTX窗口信息（调试用）"""
        print("\n" + "=" * 60)
        print("MQTTX窗口信息")
        print("=" * 60)

        try:
            # 获取所有窗口
            windows = pyautogui.getAllWindows()

            print("\n所有包含'MQTTX'的窗口:")
            for win in windows:
                if 'MQTTX' in win.title or 'mqttx' in win.title.lower():
                    print(f"\n窗口标题: {win.title}")
                    print(f"  位置: ({win.left}, {win.top})")
                    print(f"  大小: {win.width}x{win.height}")
                    print(f"  最小化: {win.isMinimized}")
                    print(f"  最大化: {win.isMaximized}")
                    print(f"  激活状态: {win.isActive}")

            # 获取当前鼠标位置
            x, y = pyautogui.position()
            print(f"\n当前鼠标位置: ({x}, {y})")

            return True

        except Exception as e:
            print(f"[ERROR] 获取窗口信息失败: {e}")
            return False


def main():
    """主函数 - 演示启动和连接"""
    controller = MQTTXUIController()

    try:
        # 步骤1: 启动MQTTX软件
        if not controller.start_mqttx():
            print("\n[FAILED] 无法启动MQTTX")
            return

        print("\n[SUCCESS] MQTTX已启动")

        # 步骤2: 查找MQTTX窗口
        time.sleep(2)
        if not controller.find_mqttx_window():
            print("\n[WARN] 无法自动找到MQTTX窗口")

        # 步骤3: 获取窗口信息
        controller.get_window_info()

        # 提示信息
        print("\n" + "=" * 60)
        print("MQTTX软件已打开")
        print("=" * 60)
        print("\n接下来需要:")
        print("  1. 手动在MQTTX中找到您的连接配置 '123'")
        print("  2. 点击连接按钮")
        print("  3. 或者提供连接按钮的屏幕坐标，我可以自动点击")
        print("\n提示: 您可以移动鼠标到连接按钮上，")
        print("      然后在命令行中运行 pyautogui.position() 查看坐标")

        # 等待用户操作
        print("\n按 Ctrl+C 退出...")
        try:
            time.sleep(300)  # 等待5分钟
        except KeyboardInterrupt:
            print("\n\n用户退出")

    except Exception as e:
        print(f"\n[ERROR] 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
