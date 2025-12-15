#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenVPN端口冲突检测测试用例
用例ID: 18
测试项: 功能用例/端口冲突检测
测试点: 设备OpenVPN界面端口冲突

⚠️ 测试逻辑：
- 有弹窗 = ✅ 测试通过（端口冲突检测生效）
- 无弹窗 = ❌ 测试失败（端口冲突检测失效）

测试内容：
跳转到OpenVPN服务器配置页面，测试端口字段
对每个保留端口进行测试，验证是否弹出端口冲突提示

测试范围：保留端口列表
保留端口配置: 从 config/reserved_ports.yaml 读取

测试流程：
1. 登录路由器Web界面
2. 跳转到OpenVPN服务器配置页面 (#network/vpn/server)
3. 启用OpenVPN服务器
4. 遍历保留端口：
   - 输入端口号 → 保存 → 检测是否有弹窗
   - 有弹窗 = 通过，无弹窗 = 失败
5. 输出详细的测试统计报告

参考实现：D:\\WK\\Milesight\\AUTO\\port_check.py 的 configure_vpn_server_ports()
"""

import time
import os
import yaml
from test_cases.base_test import BaseTest


class OpenVPNPortConflictTest(BaseTest):
    """OpenVPN端口冲突检测测试（ID18）"""

    # 保留端口列表从配置文件读取
    RESERVED_PORTS = None

    def __init__(self, config):
        super().__init__(config)
        # 从配置文件加载保留端口列表
        if OpenVPNPortConflictTest.RESERVED_PORTS is None:
            OpenVPNPortConflictTest.RESERVED_PORTS = self._load_reserved_ports()

    @staticmethod
    def _load_reserved_ports():
        """从配置文件加载保留端口列表"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config', 'reserved_ports.yaml'
        )
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                ports = config.get('reserved_ports', [])
                print(f"✅ 从配置文件加载保留端口: {ports}")
                return ports
        except Exception as e:
            print(f"⚠️  加载保留端口配置失败: {e}")
            print(f"⚠️  使用默认端口列表")
            # 默认端口列表（备用）
            return [53, 1701, 9001, 68, 500, 4500, 123, 1, 58, 7547, 9993, 520]

    @property
    def test_name(self) -> str:
        """测试用例名称"""
        return "OpenVPN端口冲突检测测试"

    @property
    def test_id(self) -> str:
        """测试用例ID"""
        return "ID18"

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

        # 备份当前配置
        self.original_config = self.router_client.backup_openvpn_config()
        if self.original_config:
            print("✅ 配置备份成功，测试完成后将恢复配置")
        else:
            print("⚠️  配置备份失败，测试完成后将无法恢复配置")

        print("✅ 前置条件完成")

    def execute(self):
        """执行测试"""
        print("\n=== 开始执行OpenVPN端口冲突检测测试 ===")

        # 调用router_client的configure_OpenVPN_ports方法
        print(f"\n测试配置:")
        print(f"  保留端口数量: {len(self.RESERVED_PORTS)}")
        print(f"  保留端口列表: {self.RESERVED_PORTS}")
        print(f"  测试路径: #network/vpn/server")

        # 执行端口冲突检测测试
        stats = self.router_client.configure_OpenVPN_ports(self.RESERVED_PORTS)

        # 验证结果
        print("\n=== 测试结果验证 ===")
        if not stats["success"]:
            failed_ports = stats.get("failed_details", [])
            error_msg = f"OpenVPN端口冲突检测失败！\n"
            error_msg += f"  总测试次数: {stats['total']}\n"
            error_msg += f"  通过: {stats['passed']}\n"
            error_msg += f"  失败: {stats['failed']}\n"
            if failed_ports:
                error_msg += f"  失败端口: {failed_ports}\n"
            raise Exception(error_msg)

        print(f"✅ OpenVPN端口冲突检测测试通过")
        print(f"  - 所有 {stats['total']} 个保留端口都正确触发了冲突检测")
        print(f"  - 通过率: 100%")

    def verify(self):
        """验证测试结果"""
        print("\n=== 验证测试结果 ===")
        print("✅ OpenVPN端口冲突检测功能正常")
        print("   所有保留端口都能正确检测冲突并弹出提示")

    def cleanup(self):
        """测试清理"""
        print("\n=== 测试清理 ===")
        try:
            # 恢复原始配置
            if hasattr(self, 'original_config') and self.original_config:
                print("恢复OpenVPN配置...")
                if self.router_client.restore_openvpn_config(self.original_config):
                    print("✅ 配置已恢复到测试前的状态")
                else:
                    print("⚠️  配置恢复失败，请手动检查配置")
            else:
                print("⚠️  没有备份配置，跳过恢复步骤")
                # 备用：刷新页面
                print("刷新页面清理测试状态...")
                self.router_client.driver.refresh()
                time.sleep(2)
        except Exception as e:
            print(f"⚠️  清理过程出错: {e}")

        super().cleanup()
        print("✅ 测试清理完成")
