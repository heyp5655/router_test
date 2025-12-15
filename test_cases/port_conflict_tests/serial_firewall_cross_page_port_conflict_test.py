#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
串口1/2与防火墙跨页面端口冲突检测测试用例
用例ID: 21
测试项: 功能用例/端口冲突检测
测试点: Serial1/2与防火墙自定义端口冲突检测

⚠️ 测试逻辑：
- 有弹窗 = ✅ 测试通过（跨页面端口冲突检测生效）
- 无弹窗 = ❌ 测试失败（跨页面端口冲突检测失效）

测试内容：
测试Serial1和Serial2与防火墙FTP端口之间的跨页面端口冲突检测功能

测试流程：
1. 登录路由器Web界面
2. 步骤1：去防火墙界面配置FTP端口为1111
   - 跳转到 #network/firewall/security
   - 配置FTP端口为1111
   - 启用FTP勾选
   - 保存并点击应用
3. 步骤2：测试Serial1端口冲突（遍历三种协议模式）
   - 跳转到 #industrial/serialport/serial1
   - 启用Serial1 (//*[@id="1_enable"])
   - 设置Mode为DTU Mode (//*[@id="1_mode"] = "1")
   - 遍历测试三种协议模式：
     a) Modbus (protocol=2, port_field=1_local_port_1)
     b) TCP Server (protocol=3, port_field=1_local_port_2)
     c) UDP Server (protocol=4, port_field=1_local_port_2)
   - 每种模式都：设置protocol → 设置端口为1111 → 保存 → 检测冲突弹窗
4. 步骤3：测试Serial2端口冲突（遍历三种协议模式）
   - 跳转到 #industrial/serialport/serial2
   - 启用Serial2（使用相同元素ID: //*[@id="1_enable"]）
   - 遍历测试三种协议模式（同Serial1，使用相同元素ID）

⚠️ 重要说明：
   - Serial1和Serial2页面使用相同的元素ID
   - Modbus协议使用端口字段 1_local_port_1
   - TCP/UDP Server协议使用端口字段 1_local_port_2

参考用例：
- ID12: 设备防火墙界面检查静态端口冲突
- ID19: OpenVPN与防火墙跨页面端口冲突检测
"""

import time
from test_cases.base_test import BaseTest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class SerialFirewallCrossPagePortConflictTest(BaseTest):
    """串口1/2与防火墙跨页面端口冲突检测测试（ID21）"""

    # 测试端口号（可以修改为其他端口）
    TEST_PORT = 1111

    # 串口工作模式配置
    # 需要先设置mode为DTU Mode (1)，然后设置protocol
    SERIAL_MODES = [
        {"name": "Modbus", "protocol_value": "2"},      # 2=Modbus
        {"name": "TCP Server", "protocol_value": "3"},  # 3=TCP Server
        {"name": "UDP Server", "protocol_value": "4"},  # 4=UDP Server
    ]

    def __init__(self, config):
        super().__init__(config)

    @property
    def test_name(self) -> str:
        """测试用例名称"""
        return "串口1/2与防火墙跨页面端口冲突检测"

    @property
    def test_id(self) -> str:
        """测试用例ID"""
        return "ID21"

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

        # 备份Serial1配置
        self.serial1_config = self.router_client.backup_serial_config(1)
        if self.serial1_config:
            print("✅ Serial1配置备份成功")
        else:
            print("⚠️  Serial1配置备份失败")

        # 备份Serial2配置
        self.serial2_config = self.router_client.backup_serial_config(2)
        if self.serial2_config:
            print("✅ Serial2配置备份成功")
        else:
            print("⚠️  Serial2配置备份失败")

        print("✅ 前置条件完成")

    def test_serial_port_conflict(self, serial_num: int, mode_config: dict) -> bool:
        """
        测试指定串口在指定模式下的端口冲突检测

        Args:
            serial_num: 串口编号（1或2）- 注意：Serial1和Serial2都使用相同的元素ID
            mode_config: 模式配置字典 {"name": "模式名", "protocol_value": "协议值"}

        Returns:
            bool: 是否检测到端口冲突弹窗
        """
        mode_name = mode_config["name"]
        protocol_value = mode_config["protocol_value"]

        print(f"\n{'─'*60}")
        print(f"  测试模式: {mode_name}")
        print(f"{'─'*60}")

        try:
            # 步骤1: 设置mode为DTU Mode
            # 注意：Serial1和Serial2都使用 //*[@id="1_mode"]
            print(f"  设置Mode为DTU Mode...")
            mode_select_element = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_mode"]'))
            )
            mode_select = Select(mode_select_element)
            mode_select.select_by_value("1")  # DTU Mode
            time.sleep(1)
            print(f"  ✅ 已选择DTU Mode")

            # 步骤2: 设置protocol
            # 注意：Serial1和Serial2都使用 //*[@id="1_protocol"]
            print(f"  设置Protocol为 {mode_name}...")
            protocol_select_element = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_protocol"]'))
            )
            protocol_select = Select(protocol_select_element)
            protocol_select.select_by_value(protocol_value)
            time.sleep(1)
            print(f"  ✅ 已选择 {mode_name} 协议")

            # 步骤3: 设置本地端口
            # Modbus使用1_local_port_1, TCP/UDP Server使用1_local_port_2
            port_field_id = "1_local_port_1" if mode_name == "Modbus" else "1_local_port_2"
            print(f"  设置本地端口为 {self.TEST_PORT}...")
            port_field = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, f'//*[@id="{port_field_id}"]'))
            )
            port_field.clear()
            port_field.send_keys(str(self.TEST_PORT))
            print(f"  ✅ 已输入端口: {self.TEST_PORT}")

            # 点击保存按钮
            print(f"  点击保存按钮...")
            save_button = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
            )
            save_button.click()
            print(f"  ✅ 已点击保存按钮")
            time.sleep(2)

            # 检测端口冲突弹窗（关键步骤）
            print(f"  检测端口冲突弹窗...")
            try:
                ok_button = WebDriverWait(self.router_client.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[13]/div/div[3]/button'))
                )

                # 尝试获取弹窗文本
                try:
                    popup_text = self.router_client.driver.find_element(
                        By.XPATH, '/html/body/div[13]/div/div[2]'
                    ).text
                    print(f"  ✅ 检测到端口冲突弹窗！")
                    print(f"  📋 弹窗内容: {popup_text}")
                except:
                    print(f"  ✅ 检测到端口冲突弹窗！")

                # 点击OK关闭弹窗
                ok_button.click()
                print(f"  ✅ 已点击OK关闭弹窗")
                time.sleep(2)
                return True

            except TimeoutException:
                print(f"  ❌ 未检测到端口冲突弹窗（应该有弹窗）")
                return False

        except Exception as e:
            print(f"  ❌ 测试过程出错: {e}")
            return False

    def execute(self):
        """执行测试"""
        print("\n" + "=" * 80)
        print("开始执行ID21：串口1/2与防火墙跨页面端口冲突检测测试")
        print("=" * 80)

        print(f"\n📋 测试配置:")
        print(f"  测试端口: {self.TEST_PORT}")
        print(f"  测试场景: 防火墙FTP端口 vs Serial1/Serial2端口")
        print(f"\n  ⚠️  测试逻辑: 跨页面端口冲突检测应该生效")
        print(f"      - 有弹窗 = ✅ 测试通过（冲突检测生效）")
        print(f"      - 无弹窗 = ❌ 测试失败（冲突检测失效）\n")

        serial1_conflict = False
        serial2_conflict = False
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
        # 步骤2：测试Serial1端口冲突（遍历三种模式）
        # ====================================================================
        print("\n" + "=" * 80)
        print("步骤2：测试Serial1端口冲突检测（遍历三种模式）")
        print("=" * 80)

        serial1_results = {}

        try:
            # 2.1 跳转到Serial1页面
            print("\n2.1 跳转到Serial1页面...")
            self.router_client.navigate_to_page("#industrial/serialport/serial1")
            time.sleep(3)

            # F5强制刷新，防止空白页
            print("  F5强制刷新页面...")
            self.router_client.driver.refresh()
            time.sleep(3)
            print("  ✅ 页面已加载")

            # 2.2 启用Serial1
            # 注意：Serial1和Serial2都使用 //*[@id="1_enable"]
            print("\n2.2 启用Serial1...")
            enable_checkbox = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]'))
            )
            is_enabled = enable_checkbox.is_selected() or enable_checkbox.get_attribute("checked")
            if not is_enabled:
                enable_checkbox.click()
                time.sleep(1)
                print("  ✅ 已启用Serial1")
            else:
                print("  ℹ️  Serial1已启用")

            # 2.3 遍历测试三种工作模式
            print(f"\n2.3 遍历测试三种工作模式...")
            for mode_config in self.SERIAL_MODES:
                mode_name = mode_config["name"]
                result = self.test_serial_port_conflict(1, mode_config)
                serial1_results[mode_name] = result

        except Exception as e:
            print(f"\n❌ Serial1测试失败: {e}")
            # 如果完全失败，标记所有模式为失败
            for mode_config in self.SERIAL_MODES:
                if mode_config["name"] not in serial1_results:
                    serial1_results[mode_config["name"]] = False

        # ====================================================================
        # 步骤3：测试Serial2端口冲突（遍历三种模式）
        # ====================================================================
        print("\n" + "=" * 80)
        print("步骤3：测试Serial2端口冲突检测（遍历三种模式）")
        print("=" * 80)

        serial2_results = {}

        try:
            # 3.1 跳转到Serial2页面
            print("\n3.1 跳转到Serial2页面...")
            self.router_client.navigate_to_page("#industrial/serialport/serial2")
            time.sleep(3)

            # F5强制刷新，防止空白页
            print("  F5强制刷新页面...")
            self.router_client.driver.refresh()
            time.sleep(3)
            print("  ✅ 页面已加载")

            # 3.2 启用Serial2
            # 注意：Serial1和Serial2都使用 //*[@id="1_enable"]
            print("\n3.2 启用Serial2...")
            enable_checkbox = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="1_enable"]'))
            )
            is_enabled = enable_checkbox.is_selected() or enable_checkbox.get_attribute("checked")
            if not is_enabled:
                enable_checkbox.click()
                time.sleep(1)
                print("  ✅ 已启用Serial2")
            else:
                print("  ℹ️  Serial2已启用")

            # 3.3 遍历测试三种工作模式
            print(f"\n3.3 遍历测试三种工作模式...")
            for mode_config in self.SERIAL_MODES:
                mode_name = mode_config["name"]
                result = self.test_serial_port_conflict(2, mode_config)
                serial2_results[mode_name] = result

        except Exception as e:
            print(f"\n❌ Serial2测试失败: {e}")
            # 如果完全失败，标记所有模式为失败
            for mode_config in self.SERIAL_MODES:
                if mode_config["name"] not in serial2_results:
                    serial2_results[mode_config["name"]] = False

        # ====================================================================
        # 测试结果汇总
        # ====================================================================
        print("\n" + "=" * 80)
        print("ID21 测试结果总结")
        print("=" * 80)

        print(f"\n步骤1 - 防火墙FTP配置: {'✅ 成功' if firewall_success else '❌ 失败'}")

        print(f"\n步骤2 - Serial1冲突检测结果:")
        for mode_name, result in serial1_results.items():
            status = "✅ 检测到冲突" if result else "❌ 未检测到冲突"
            print(f"  [{mode_name:15s}] {status}")

        print(f"\n步骤3 - Serial2冲突检测结果:")
        for mode_name, result in serial2_results.items():
            status = "✅ 检测到冲突" if result else "❌ 未检测到冲突"
            print(f"  [{mode_name:15s}] {status}")

        # 计算总体通过情况
        all_serial1_pass = all(serial1_results.values())
        all_serial2_pass = all(serial2_results.values())
        all_pass = all_serial1_pass and all_serial2_pass

        print(f"\n{'='*60}")
        print(f"Serial1 所有模式: {'✅ 全部通过' if all_serial1_pass else '❌ 部分失败'}")
        print(f"Serial2 所有模式: {'✅ 全部通过' if all_serial2_pass else '❌ 部分失败'}")
        print(f"{'='*60}")
        print(f"总体测试结果: {'✅ 通过' if all_pass else '❌ 失败'}")

        if not all_pass:
            failed_modes = []
            for mode_name, result in serial1_results.items():
                if not result:
                    failed_modes.append(f"Serial1-{mode_name}")
            for mode_name, result in serial2_results.items():
                if not result:
                    failed_modes.append(f"Serial2-{mode_name}")

            print(f"\n❌ 测试失败！以下模式未检测到与防火墙FTP端口 {self.TEST_PORT} 的冲突:")
            for failed in failed_modes:
                print(f"   - {failed}")
            print("   跨页面端口冲突检测功能失效")
            raise Exception(f"跨页面端口冲突检测失败 - {len(failed_modes)}个模式未弹出冲突提示")
        else:
            print(f"\n✅ 测试通过！Serial1和Serial2的所有模式都成功检测到与防火墙FTP端口 {self.TEST_PORT} 的冲突")
            print(f"   共测试了 {len(self.SERIAL_MODES)} 种工作模式 × 2个串口 = {len(self.SERIAL_MODES)*2} 个测试点")
            print("   跨页面端口冲突检测功能正常")

        print("=" * 80)

    def verify(self):
        """验证测试结果"""
        print("\n=== 验证测试结果 ===")
        print("✅ Serial1/2与防火墙跨页面端口冲突检测功能正常")
        print(f"   已验证 {len(self.SERIAL_MODES)} 种工作模式 × 2个串口的冲突检测")
        print("   所有模式在跨页面配置相同端口时都能正确检测冲突并弹出提示")

    def cleanup(self):
        """测试清理"""
        print("\n=== 测试清理 ===")
        try:
            # 恢复Serial1配置
            if hasattr(self, 'serial1_config') and self.serial1_config:
                print("恢复Serial1配置...")
                if self.router_client.restore_serial_config(1, self.serial1_config):
                    print("✅ Serial1配置已恢复")
                else:
                    print("⚠️  Serial1配置恢复失败")

            # 恢复Serial2配置
            if hasattr(self, 'serial2_config') and self.serial2_config:
                print("恢复Serial2配置...")
                if self.router_client.restore_serial_config(2, self.serial2_config):
                    print("✅ Serial2配置已恢复")
                else:
                    print("⚠️  Serial2配置恢复失败")

            # 恢复防火墙配置
            if hasattr(self, 'firewall_config') and self.firewall_config:
                print("恢复防火墙Security配置...")
                if self.router_client.restore_firewall_security_config(self.firewall_config):
                    print("✅ 防火墙配置已恢复")
                else:
                    print("⚠️  防火墙配置恢复失败")

            if not (hasattr(self, 'firewall_config') and hasattr(self, 'serial1_config') and hasattr(self, 'serial2_config')):
                print("⚠️  没有备份配置，跳过恢复步骤")
                print("刷新页面清理测试状态...")
                self.router_client.driver.refresh()
                time.sleep(2)
        except Exception as e:
            print(f"⚠️  清理过程出错: {e}")

        super().cleanup()
        print("✅ 测试清理完成")
