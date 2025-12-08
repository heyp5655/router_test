#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Modbus TCP端口冲突检测测试用例
用例ID: 15
测试项: 功能用例/端口冲突检测
测试点: 设备去Modbus TCP端口冲突

⚠️ 测试逻辑：
- 有弹窗 = ✅ 测试通过（端口冲突检测生效）
- 无弹窗 = ❌ 测试失败（端口冲突检测失效）

测试内容：
跳转到Modbus TCP配置页面，测试Local Port字段
对每个保留端口进行测试，验证是否弹出端口冲突提示

测试范围：保留端口列表
保留端口配置: 从 config/reserved_ports.yaml 读取

测试流程：
1. 登录路由器Web界面
2. 跳转到Modbus TCP配置页面 (#industrial/modbus/modbustcp)
3. 启用Modbus TCP
4. 遍历保留端口：
   - 输入端口号 → 保存 → 检测是否有弹窗
   - 有弹窗 = 通过，无弹窗 = 失败
5. 输出详细的测试统计报告

参考实现：D:\\WK\\Milesight\\AUTO\\port_check.py 的 configure_Modbus_TCP_ports()
"""

import time
import os
import yaml
from test_cases.base_test import BaseTest


class ModbusTCPPortConflictTest(BaseTest):
    """Modbus TCP端口冲突检测测试（ID15）"""

    # 保留端口列表从配置文件读取
    RESERVED_PORTS = None

    def __init__(self, config):
        super().__init__(config)
        # 从配置文件加载保留端口列表
        if ModbusTCPPortConflictTest.RESERVED_PORTS is None:
            ModbusTCPPortConflictTest.RESERVED_PORTS = self._load_reserved_ports()

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
        return "设备去Modbus TCP端口冲突"

    @property
    def test_id(self) -> str:
        """测试用例ID"""
        return "ID15"

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

        print("✅ 前置条件完成")

    def execute(self):
        """执行测试"""
        print("\n=== 开始执行ID15：Modbus TCP端口冲突检测测试 ===")

        print(f"\n📋 测试配置:")
        print(f"  保留端口: {self.RESERVED_PORTS}")
        print(f"  端口数量: {len(self.RESERVED_PORTS)}")
        print(f"  测试字段: Local Port (1个)")
        print(f"  总测试次数: {len(self.RESERVED_PORTS)}")
        print(f"\n  ⚠️  测试逻辑: 所有保留端口都应该弹出冲突提示")
        print(f"      - 有弹窗 = ✅ 测试通过（端口冲突检测生效）")
        print(f"      - 无弹窗 = ❌ 测试失败（端口冲突检测失效）\n")

        # 调用RouterClient的测试方法
        stats = self.router_client.configure_Modbus_TCP_ports(self.RESERVED_PORTS)

        # 输出测试结果
        print("\n" + "=" * 80)
        print("ID15 测试结果总结:")
        print("=" * 80)
        print(f"总测试次数: {stats['total']}")

        if stats['total'] > 0:
            print(f"✅ 通过: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
            print(f"❌ 失败: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")
        else:
            print(f"✅ 通过: {stats['passed']}")
            print(f"❌ 失败: {stats['failed']}")
            print("⚠️  警告: 未执行任何测试，可能在初始化阶段失败")

        if stats['failed'] > 0:
            print(f"\n失败的端口详情 (共{stats['failed']}个):")
            for port in stats['failed_details']:
                print(f"  - 端口 {port} 未弹出冲突提示")

        # 判断测试是否通过
        if not stats['success']:
            failed_ports_str = ", ".join(map(str, stats['failed_details']))
            raise Exception(
                f"ID15测试失败！\n"
                f"有 {stats['failed']} 个端口未触发冲突检测弹窗\n"
                f"失败的端口: {failed_ports_str}\n"
                f"测试的端口应该都触发冲突提示，但实际有部分端口未触发"
            )

        print("\n✅ ID15测试通过！所有保留端口都正确触发了冲突检测弹窗")
        print("=" * 80)

    def cleanup(self):
        """测试清理"""
        print("\n=== 测试清理 ===")
        try:
            # 清理：刷新页面
            print("刷新页面清理测试状态...")
            self.router_client.driver.refresh()
            time.sleep(2)
        except Exception as e:
            print(f"⚠️  清理过程出错: {e}")

        super().cleanup()
        print("✅ 测试清理完成")
