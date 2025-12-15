#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenVPN与防火墙跨页面端口冲突检测测试用例
用例ID: 19
测试项: 功能用例/端口冲突检测
测试点: OpenVPN Server与防火墙自定义端口冲突检测

⚠️ 测试逻辑：
- 有弹窗 = ✅ 测试通过（跨页面端口冲突检测生效）
- 无弹窗 = ❌ 测试失败（跨页面端口冲突检测失效）

测试内容：
测试OpenVPN服务器与防火墙FTP端口之间的跨页面端口冲突检测功能

测试流程（严格按照用例步骤.xlsx）：
1. 登录路由器Web界面
2. 步骤1：去防火墙界面配置FTP端口为1111
   - 跳转到 #network/firewall/security
   - 配置FTP端口为1111
   - 启用FTP勾选
   - 保存并点击应用
3. 步骤2：去OpenVPN界面配置端口为1111
   - 跳转到 #network/vpn/server
   - 启用OpenVPN服务器
   - 配置服务器IP (Listen IP): 192.168.40.47
   - 配置本地虚拟IP (Local Virtual IP): 192.168.50.16
   - 配置远程虚拟IP (Remote Virtual IP): 192.168.50.47
   - 配置OpenVPN端口为1111
   - 点击保存
   - 验证是否弹出端口冲突提醒（需要弹窗才算通过）

参考用例：
- ID12: 设备防火墙界面检查静态端口冲突
- ID18: 设备OpenVPN界面端口冲突
"""

import time
from test_cases.base_test import BaseTest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class OpenVPNFirewallCrossPagePortConflictTest(BaseTest):
    """OpenVPN与防火墙跨页面端口冲突检测测试（ID19）"""

    # 测试端口号（可以修改为其他端口）
    TEST_PORT = 1111

    def __init__(self, config):
        super().__init__(config)

    @property
    def test_name(self) -> str:
        """测试用例名称"""
        return "OpenVPN与防火墙跨页面端口冲突检测"

    @property
    def test_id(self) -> str:
        """测试用例ID"""
        return "ID19"

    @property
    def category(self) -> str:
        """测试分类"""
        return "功能用例/端口冲突检测"

    def setup(self):
        """测试前置条件"""
        print("\n=== 测试前置条件 ===")
        print("1. 设备出厂状态")
        print("2. 登录路由器Web界面")

        # 登录路由器
        if not self.router_client.login_web():
            raise Exception("无法登录路由器Web界面")

        # 备份防火墙Security配置（只备份FTP端口）
        self.firewall_config = self.router_client.backup_firewall_security_config()
        if self.firewall_config:
            print("✅ 防火墙配置备份成功")
        else:
            print("⚠️  防火墙配置备份失败")

        # 备份OpenVPN配置
        self.openvpn_config = self.router_client.backup_openvpn_config()
        if self.openvpn_config:
            print("✅ OpenVPN配置备份成功")
        else:
            print("⚠️  OpenVPN配置备份失败")

        print("✅ 前置条件完成")

    def execute(self):
        """执行测试"""
        print("\n" + "=" * 80)
        print("开始执行ID19：OpenVPN与防火墙跨页面端口冲突检测测试")
        print("=" * 80)

        print(f"\n📋 测试配置:")
        print(f"  测试端口: {self.TEST_PORT}")
        print(f"  测试场景: 防火墙FTP端口 vs OpenVPN服务器端口")
        print(f"\n  ⚠️  测试逻辑: 跨页面端口冲突检测应该生效")
        print(f"      - 有弹窗 = ✅ 测试通过（冲突检测生效）")
        print(f"      - 无弹窗 = ❌ 测试失败（冲突检测失效）\n")

        # ====================================================================
        # 步骤1：防火墙界面配置FTP端口为1111
        # ====================================================================
        print("\n" + "=" * 80)
        print("步骤1：防火墙界面配置FTP端口并应用")
        print("=" * 80)

        try:
            # 1.1 跳转到防火墙Security页面
            print("\n1.1 跳转到防火墙Security页面...")
            self.router_client.navigate_to_page(
                "#network/firewall/security",
                sub_tab_selector="network/firewall/security"
            )
            time.sleep(3)

            # F5强制刷新，防止空白页
            print("  F5强制刷新页面...")
            self.router_client.driver.refresh()
            time.sleep(3)
            print("  ✅ 页面已加载")

            # 1.2 配置FTP端口为1111
            print(f"\n1.2 配置FTP端口为 {self.TEST_PORT}...")
            ftp_port_field = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_ftp_port"]'))
            )
            ftp_port_field.clear()
            ftp_port_field.send_keys(str(self.TEST_PORT))
            print(f"  ✅ 已输入FTP端口: {self.TEST_PORT}")

            # 1.3 启用FTP功能
            print(f"\n1.3 启用FTP功能...")
            ftp_enable_checkbox = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_ftp_local"]'))
            )

            is_enabled = ftp_enable_checkbox.is_selected() or ftp_enable_checkbox.get_attribute("checked")
            if not is_enabled:
                ftp_enable_checkbox.click()
                time.sleep(1)
                print("  ✅ 已启用FTP功能")
            else:
                print("  ℹ️  FTP功能已启用")

            # 1.4 保存并应用配置
            print(f"\n1.4 保存并应用配置...")
            save_button = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
            )
            save_button.click()
            print("  ✅ 已点击保存按钮")
            time.sleep(2)

            # 处理可能的确认弹窗
            try:
                ok_button = WebDriverWait(self.router_client.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                )
                ok_button.click()
                print("  ✅ 已关闭确认弹窗")
                time.sleep(2)
            except TimeoutException:
                print("  ℹ️  无确认弹窗")

            # 点击应用按钮
            try:
                apply_button = self.router_client.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="apply"]'))
                )
                apply_button.click()
                print("  ✅ 已点击应用按钮")
                time.sleep(5)  # 等待配置应用

                # 等待应用完成的确认弹窗
                try:
                    confirm_button = WebDriverWait(self.router_client.driver, 8).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                    )
                    confirm_button.click()
                    print("  ✅ 已关闭应用完成弹窗")
                    time.sleep(2)
                except TimeoutException:
                    print("  ℹ️  无应用完成弹窗")

            except Exception as e:
                print(f"  ⚠️  应用配置时出错: {e}")
                print("  ℹ️  继续执行测试...")

            print(f"\n✅ 防火墙FTP端口配置完成: {self.TEST_PORT}")

        except Exception as e:
            error_msg = f"步骤1失败 - 防火墙FTP配置失败: {e}"
            print(f"\n❌ {error_msg}")
            raise Exception(error_msg)

        # ====================================================================
        # 步骤2：OpenVPN界面配置端口为1111
        # ====================================================================
        print("\n" + "=" * 80)
        print("步骤2：OpenVPN界面配置端口并检测冲突")
        print("=" * 80)

        try:
            # 2.1 跳转到OpenVPN服务器页面
            print("\n2.1 跳转到OpenVPN服务器页面...")
            self.router_client.navigate_to_page("#network/vpn/server")
            time.sleep(3)

            # F5强制刷新，防止空白页
            print("  F5强制刷新页面...")
            self.router_client.driver.refresh()
            time.sleep(3)
            print("  ✅ 页面已加载")

            # 2.2 启用OpenVPN服务器
            print("\n2.2 启用OpenVPN服务器...")
            enable_btn = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]'))
            )

            is_enabled = enable_btn.is_selected() or enable_btn.get_attribute("checked")
            if not is_enabled:
                enable_btn.click()
                time.sleep(1)
                print("  ✅ 已启用OpenVPN服务器")
            else:
                print("  ℹ️  OpenVPN服务器已启用")

            # 2.3 配置OpenVPN服务器必填字段
            print("\n2.3 配置OpenVPN服务器必填字段...")

            # 服务器IP (Listen IP)
            print("  配置服务器IP...")
            listen_ip_field = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_listen_ip"]'))
            )
            listen_ip_field.clear()
            listen_ip_field.send_keys("192.168.40.47")
            print("  ✅ 已输入服务器IP: 192.168.40.47")

            # 本地虚拟IP (Local Virtual IP)
            print("  配置本地虚拟IP...")
            local_virtual_ip_field = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_local_virtual_ip"]'))
            )
            local_virtual_ip_field.clear()
            local_virtual_ip_field.send_keys("192.168.50.16")
            print("  ✅ 已输入本地虚拟IP: 192.168.50.16")

            # 远程虚拟IP (Remote Virtual IP)
            print("  配置远程虚拟IP...")
            remote_virtual_ip_field = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_remote_virtual_ip"]'))
            )
            remote_virtual_ip_field.clear()
            remote_virtual_ip_field.send_keys("192.168.50.47")
            print("  ✅ 已输入远程虚拟IP: 192.168.50.47")

            # 2.4 配置OpenVPN端口为1111
            print(f"\n2.4 配置OpenVPN端口为 {self.TEST_PORT}...")
            port_field = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_port"]'))
            )
            port_field.clear()
            port_field.send_keys(str(self.TEST_PORT))
            print(f"  ✅ 已输入OpenVPN端口: {self.TEST_PORT}")

            # 2.5 点击保存按钮
            print("\n2.5 点击保存按钮...")
            save_button = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
            )
            save_button.click()
            print("  ✅ 已点击保存按钮")
            time.sleep(2)

            # 2.6 检测端口冲突弹窗（关键步骤）
            print("\n2.6 检测端口冲突弹窗...")
            has_conflict_popup = False
            try:
                ok_button = WebDriverWait(self.router_client.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                )
                has_conflict_popup = True

                # 尝试获取弹窗文本
                try:
                    popup_text = self.router_client.driver.find_element(
                        By.XPATH, '/html/body/div[13]/div/div[2]'
                    ).text
                    print(f"\n  ✅ 检测到端口冲突弹窗！")
                    print(f"  📋 弹窗内容: {popup_text}")
                except:
                    print(f"\n  ✅ 检测到端口冲突弹窗！")

                # 点击OK关闭弹窗
                ok_button.click()
                print(f"  ✅ 已点击OK关闭弹窗")
                time.sleep(2)

            except TimeoutException:
                has_conflict_popup = False
                print(f"\n  ❌ 未检测到端口冲突弹窗（应该有弹窗）")

        except Exception as e:
            error_msg = f"步骤2失败 - OpenVPN配置或冲突检测失败: {e}"
            print(f"\n❌ {error_msg}")
            raise Exception(error_msg)

        # ====================================================================
        # 测试结果
        # ====================================================================
        print("\n" + "=" * 80)
        print("ID19 测试结果总结")
        print("=" * 80)
        print(f"步骤1 - 防火墙FTP配置: ✅ 成功")
        print(f"步骤2 - OpenVPN冲突检测: {'✅ 检测到冲突' if has_conflict_popup else '❌ 未检测到冲突'}")
        print(f"测试结果: {'✅ 通过' if has_conflict_popup else '❌ 失败'}")

        if not has_conflict_popup:
            print(f"\n❌ 测试失败！OpenVPN未检测到与防火墙FTP端口 {self.TEST_PORT} 的冲突")
            print("   跨页面端口冲突检测功能失效")
            raise Exception("跨页面端口冲突检测失败 - 应该弹出冲突提示但没有")
        else:
            print(f"\n✅ 测试通过！OpenVPN成功检测到与防火墙FTP端口 {self.TEST_PORT} 的冲突")
            print("   跨页面端口冲突检测功能正常")

        print("=" * 80)

    def verify(self):
        """验证测试结果"""
        print("\n=== 验证测试结果 ===")
        print("✅ OpenVPN与防火墙跨页面端口冲突检测功能正常")
        print("   跨页面配置相同端口时能正确检测冲突并弹出提示")

    def cleanup(self):
        """测试清理"""
        print("\n=== 测试清理 ===")
        try:
            # 恢复OpenVPN配置
            if hasattr(self, 'openvpn_config') and self.openvpn_config:
                print("恢复OpenVPN配置...")
                if self.router_client.restore_openvpn_config(self.openvpn_config):
                    print("✅ OpenVPN配置已恢复")
                else:
                    print("⚠️  OpenVPN配置恢复失败")

            # 恢复防火墙配置
            if hasattr(self, 'firewall_config') and self.firewall_config:
                print("恢复防火墙Security配置...")
                if self.router_client.restore_firewall_security_config(self.firewall_config):
                    print("✅ 防火墙配置已恢复")
                else:
                    print("⚠️  防火墙配置恢复失败")

            if not (hasattr(self, 'firewall_config') and hasattr(self, 'openvpn_config')):
                print("⚠️  没有备份配置，跳过恢复步骤")
                print("刷新页面清理测试状态...")
                self.router_client.driver.refresh()
                time.sleep(2)
        except Exception as e:
            print(f"⚠️  清理过程出错: {e}")

        super().cleanup()
        print("✅ 测试清理完成")
