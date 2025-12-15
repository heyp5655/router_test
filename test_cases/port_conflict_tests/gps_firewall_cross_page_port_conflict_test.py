#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GPS与防火墙跨页面端口冲突检测测试用例
用例ID: 24
测试项: 功能用例/端口冲突检测
测试点: GPS与防火墙自定义端口冲突检测
"""

import time
from test_cases.base_test import BaseTest


class GPSFirewallCrossPagePortConflictTest(BaseTest):
    """GPS与防火墙跨页面端口冲突检测测试（ID24）"""

    TEST_PORT = 1111

    @property
    def test_name(self) -> str:
        return "GPS与防火墙跨页面端口冲突检测"

    @property
    def test_id(self) -> str:
        return "ID24"

    @property
    def category(self) -> str:
        return "功能用例/端口冲突检测"

    def setup(self):
        print("\n=== 测试前置条件 ===")
        if not self.router_client.login_web():
            raise Exception("无法登录路由器Web界面")

        # 备份防火墙Security配置
        self.firewall_config = self.router_client.backup_firewall_security_config()
        if self.firewall_config:
            print("✅ 防火墙配置备份成功")
        else:
            print("⚠️  防火墙配置备份失败")

        # 备份GPS配置
        self.gps_config = self.router_client.backup_gps_config()
        if self.gps_config:
            print("✅ GPS配置备份成功")
        else:
            print("⚠️  GPS配置备份失败")

        print("✅ 前置条件完成")

    def execute(self):
        print("\n=== 开始执行ID24：GPS与防火墙跨页面端口冲突检测测试 ===")
        result = self.router_client.test_cross_page_port_conflict_gps_firewall(self.TEST_PORT)

        print(f"\n{'='*80}")
        print(f"防火墙FTP配置: {'✅ 成功' if result['firewall_config'] else '❌ 失败'}")
        print(f"GPS冲突检测: {'✅ 检测到冲突' if result['conflict_detected'] else '❌ 未检测到冲突'}")
        print(f"测试结果: {'✅ 通过' if result['success'] else '❌ 失败'}")
        print(f"{result['message']}")
        print(f"{'='*80}")

        if not result['success']:
            raise Exception(f"ID24测试失败！\n{result['message']}")

    def cleanup(self):
        """测试清理"""
        print("\n=== 测试清理 ===")
        try:
            # 恢复GPS配置
            if hasattr(self, 'gps_config') and self.gps_config:
                print("恢复GPS配置...")
                if self.router_client.restore_gps_config(self.gps_config):
                    print("✅ GPS配置已恢复")
                else:
                    print("⚠️  GPS配置恢复失败")

            # 恢复防火墙配置
            if hasattr(self, 'firewall_config') and self.firewall_config:
                print("恢复防火墙Security配置...")
                if self.router_client.restore_firewall_security_config(self.firewall_config):
                    print("✅ 防火墙配置已恢复")
                else:
                    print("⚠️  防火墙配置恢复失败")

            if not (hasattr(self, 'firewall_config') and hasattr(self, 'gps_config')):
                print("⚠️  没有备份配置，跳过恢复步骤")
                print("刷新页面清理测试状态...")
                self.router_client.driver.refresh()
                time.sleep(2)
        except Exception as e:
            print(f"⚠️  清理过程出错: {e}")

        super().cleanup()
        print("✅ 测试清理完成")
