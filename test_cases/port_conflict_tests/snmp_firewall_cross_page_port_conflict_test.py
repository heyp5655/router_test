#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SNMP与防火墙跨页面端口冲突检测测试用例
用例ID: 23
测试项: 功能用例/端口冲突检测
测试点: SNMP与防火墙自定义端口冲突检测

⚠️ 测试逻辑：
- 有弹窗 = ✅ 测试通过（跨页面端口冲突检测生效）
- 无弹窗 = ❌ 测试失败（跨页面端口冲突检测失效）

测试内容：
测试SNMP与防火墙FTP端口之间的跨页面端口冲突检测功能

测试流程：
1. 登录路由器Web界面
2. 步骤1：去防火墙界面配置FTP端口为1111
   - 跳转到 #network/firewall/security
   - 配置FTP端口为1111
   - 启用FTP勾选
   - 保存并点击应用
3. 步骤2：测试SNMP端口冲突
   - 跳转到 #industrial/snmp/snmp
   - 启用SNMP (//*[@id="0_enable"])
   - 填写Location字段 (//*[@id="0_location"] = "123")
   - 填写Contact字段 (//*[@id="0_contact"] = "admin")
   - 配置SNMP端口为1111 (//*[@id="0_port"])
   - 点击保存，验证是否弹出端口冲突提醒

⚠️ 重要说明：
   - SNMP所有字段都使用前缀 0_ (0_enable, 0_location, 0_contact, 0_port)
   - 必须填写Location和Contact才能保存配置

参考用例：
- ID12: 设备防火墙界面检查静态端口冲突
- ID19: OpenVPN与防火墙跨页面端口冲突检测
"""

import time
from test_cases.base_test import BaseTest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class SNMPFirewallCrossPagePortConflictTest(BaseTest):
    """SNMP与防火墙跨页面端口冲突检测测试（ID23）"""

    # 测试端口号（可以修改为其他端口）
    TEST_PORT = 1111

    def __init__(self, config):
        super().__init__(config)

    @property
    def test_name(self) -> str:
        """测试用例名称"""
        return "SNMP与防火墙跨页面端口冲突检测"

    @property
    def test_id(self) -> str:
        """测试用例ID"""
        return "ID23"

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

        # 备份SNMP配置
        self.snmp_config = self.router_client.backup_snmp_config()
        if self.snmp_config:
            print("✅ SNMP配置备份成功")
        else:
            print("⚠️  SNMP配置备份失败")

        print("✅ 前置条件完成")

    def execute(self):
        """执行测试"""
        print("\n" + "=" * 80)
        print("开始执行ID23：SNMP与防火墙跨页面端口冲突检测测试")
        print("=" * 80)

        print(f"\n📋 测试配置:")
        print(f"  测试端口: {self.TEST_PORT}")
        print(f"  测试场景: 防火墙FTP端口 vs SNMP端口")
        print(f"\n  ⚠️  测试逻辑: 跨页面端口冲突检测应该生效")
        print(f"      - 有弹窗 = ✅ 测试通过（冲突检测生效）")
        print(f"      - 无弹窗 = ❌ 测试失败（冲突检测失效）\n")

        snmp_conflict = False
        firewall_success = False

        try:
            # ====================================================================
            # 步骤1：配置防火墙FTP端口
            # ====================================================================
            print("\n" + "=" * 80)
            print("步骤1：防火墙界面配置FTP端口并应用")
            print("=" * 80)

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
            firewall_success = True

        except Exception as e:
            error_msg = f"步骤1失败 - 防火墙FTP配置失败: {e}"
            print(f"\n❌ {error_msg}")
            raise Exception(error_msg)

        # ====================================================================
        # 步骤2：测试SNMP端口冲突
        # ====================================================================
        print("\n" + "=" * 80)
        print("步骤2：测试SNMP端口冲突检测")
        print("=" * 80)

        try:
            # 2.1 跳转到SNMP页面
            print("\n2.1 跳转到SNMP页面...")
            self.router_client.navigate_to_page("#industrial/snmp/snmp")
            time.sleep(3)

            # F5强制刷新，防止空白页
            print("  F5强制刷新页面...")
            self.router_client.driver.refresh()
            time.sleep(3)
            print("  ✅ 页面已加载")

            # 2.2 启用SNMP
            # 注意：SNMP使用 //*[@id="0_enable"]
            print("\n2.2 启用SNMP...")
            enable_checkbox = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="0_enable"]'))
            )
            is_enabled = enable_checkbox.is_selected() or enable_checkbox.get_attribute("checked")
            if not is_enabled:
                enable_checkbox.click()
                time.sleep(2)
                print("  ✅ 已启用SNMP")
            else:
                print("  ℹ️  SNMP已启用")

            # 2.3 填写SNMP基本信息（Location和Contact）
            print("\n2.3 填写SNMP基本信息...")
            try:
                location_input = self.router_client.wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="0_location"]'))
                )
                location_input.clear()
                location_input.send_keys("123")
                print("  ✅ 已填写Location: 123")

                contact_input = self.router_client.driver.find_element(By.XPATH, '//*[@id="0_contact"]')
                contact_input.clear()
                contact_input.send_keys("admin")
                print("  ✅ 已填写Contact: admin")
                time.sleep(1)
            except Exception as e:
                print(f"  ⚠️  填写基本信息时出错: {e}，继续测试端口...")

            # 2.4 设置SNMP端口为1111
            # 注意：SNMP端口字段使用 //*[@id="0_port"]
            print(f"\n2.4 设置SNMP端口为 {self.TEST_PORT}...")
            try:
                # 等待端口字段可用
                port_field = self.router_client.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="0_port"]'))
                )
                print(f"  ✅ 找到端口字段元素")

                # 清空并输入端口
                current_value = port_field.get_attribute('value')
                print(f"  当前端口值: {current_value}")

                port_field.clear()
                time.sleep(0.5)
                port_field.send_keys(str(self.TEST_PORT))
                time.sleep(0.5)

                # 验证输入
                new_value = port_field.get_attribute('value')
                print(f"  ✅ 已输入端口: {new_value}")

                if new_value != str(self.TEST_PORT):
                    print(f"  ⚠️  警告: 输入值({new_value})与预期值({self.TEST_PORT})不一致")
            except Exception as e:
                print(f"  ❌ 设置端口时出错: {e}")
                raise

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
            try:
                ok_button = WebDriverWait(self.router_client.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                )
                snmp_conflict = True

                # 尝试获取弹窗文本
                try:
                    popup_text = self.router_client.driver.find_element(
                        By.XPATH, '/html/body/div[13]/div/div[2]'
                    ).text
                    print(f"\n  ✅ SNMP检测到端口冲突弹窗！")
                    print(f"  📋 弹窗内容: {popup_text}")
                except:
                    print(f"\n  ✅ SNMP检测到端口冲突弹窗！")

                # 点击OK关闭弹窗
                ok_button.click()
                print(f"  ✅ 已点击OK关闭弹窗")
                time.sleep(2)

            except TimeoutException:
                snmp_conflict = False
                print(f"\n  ❌ SNMP未检测到端口冲突弹窗（应该有弹窗）")

        except Exception as e:
            error_msg = f"步骤2失败 - SNMP配置或冲突检测失败: {e}"
            print(f"\n❌ {error_msg}")
            raise Exception(error_msg)

        # ====================================================================
        # 测试结果
        # ====================================================================
        print("\n" + "=" * 80)
        print("ID23 测试结果总结")
        print("=" * 80)
        print(f"步骤1 - 防火墙FTP配置: {'✅ 成功' if firewall_success else '❌ 失败'}")
        print(f"步骤2 - SNMP冲突检测: {'✅ 检测到冲突' if snmp_conflict else '❌ 未检测到冲突'}")
        print(f"测试结果: {'✅ 通过' if snmp_conflict else '❌ 失败'}")

        if not snmp_conflict:
            print(f"\n❌ 测试失败！SNMP未检测到与防火墙FTP端口 {self.TEST_PORT} 的冲突")
            print("   跨页面端口冲突检测功能失效")
            raise Exception("跨页面端口冲突检测失败 - 应该弹出冲突提示但没有")
        else:
            print(f"\n✅ 测试通过！SNMP成功检测到与防火墙FTP端口 {self.TEST_PORT} 的冲突")
            print("   跨页面端口冲突检测功能正常")

        print("=" * 80)

    def verify(self):
        """验证测试结果"""
        print("\n=== 验证测试结果 ===")
        print("✅ SNMP与防火墙跨页面端口冲突检测功能正常")
        print("   跨页面配置相同端口时能正确检测冲突并弹出提示")

    def cleanup(self):
        """测试清理"""
        print("\n=== 测试清理 ===")
        try:
            # 恢复SNMP配置
            if hasattr(self, 'snmp_config') and self.snmp_config:
                print("恢复SNMP配置...")
                if self.router_client.restore_snmp_config(self.snmp_config):
                    print("✅ SNMP配置已恢复")
                else:
                    print("⚠️  SNMP配置恢复失败")

            # 恢复防火墙配置
            if hasattr(self, 'firewall_config') and self.firewall_config:
                print("恢复防火墙Security配置...")
                if self.router_client.restore_firewall_security_config(self.firewall_config):
                    print("✅ 防火墙配置已恢复")
                else:
                    print("⚠️  防火墙配置恢复失败")

            if not (hasattr(self, 'firewall_config') and hasattr(self, 'snmp_config')):
                print("⚠️  没有备份配置，跳过恢复步骤")
                print("刷新页面清理测试状态...")
                self.router_client.driver.refresh()
                time.sleep(2)
        except Exception as e:
            print(f"⚠️  清理过程出错: {e}")

        super().cleanup()
        print("✅ 测试清理完成")
