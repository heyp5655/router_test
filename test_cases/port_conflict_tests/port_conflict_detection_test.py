#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
端口冲突检测测试用例
用例ID: 11
测试项: 功能用例/端口冲突检测
测试点: 验证研发提供端口冲突静态端口列表的完整性与准确性

测试范围: 1-65535 所有端口
保留端口配置: 从 config/reserved_ports.yaml 读取
已移除端口: 55832, 40404, 22

测试流程（完全优化，极致性能）:
1. 点击添加按钮（只点击一次）
2. 填写固定字段：源地址192.168.1.100/24, 目标IP 10.10.10.10, 目标端口222, 源端口1
3. 点击保存，检查弹窗，处理结果
4. 循环测试剩余端口 (2-65535):
   - 修改源端口输入框值 → 保存 → 检查弹窗
   - 有弹窗: 点击OK（表单保持打开）
   - 无弹窗: 什么都不做（表单保持打开）
   - 继续下一个端口

关键优化:
- 不刷新页面
- 不重新点击添加按钮
- 不重新填写固定字段
- 只修改源端口值
- 预计速度: ~2-3端口/秒，总耗时: ~6-9小时（相比原来的54小时，提升6-9倍！）
"""

import time
import os
import yaml
from test_cases.base_test import BaseTest
from selenium.webdriver.common.by import By


class PortConflictDetectionTest(BaseTest):
    """端口冲突检测测试"""

    # 保留端口列表从配置文件读取
    RESERVED_PORTS = None

    def __init__(self, config):
        super().__init__(config)
        # 从配置文件加载保留端口列表
        if PortConflictDetectionTest.RESERVED_PORTS is None:
            PortConflictDetectionTest.RESERVED_PORTS = self._load_reserved_ports()

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
        return "端口冲突检测测试（全端口扫描）"

    @property
    def test_id(self) -> str:
        """测试用例ID"""
        return "ID11"

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
        print("\n=== 开始执行端口冲突检测测试 ===")

        # 步骤1: 登录路由器并跳转到端口映射页面
        print("\n步骤1: 跳转到端口映射页面...")
        print("  路径: #network/firewall/portmapping")
        self.router_client.navigate_to_page(
            "#network/firewall/portmapping"
            # Port Mapping页面不需要点击子标签
        )
        time.sleep(2)
        print("  ✅ 页面跳转成功")

        # 步骤2: 点击添加按钮，填写固定字段
        print("\n步骤2: 点击添加按钮并填写固定字段...")
        print("  源地址: 192.168.1.100/24")
        print("  目标IP: 10.10.10.10")
        print("  目标端口: 222")

        if not self.router_client.add_port_mapping(
            src="192.168.1.100/24",
            dst_ip="10.10.10.10",
            dst_port="222",
            external_port="1",  # 初始值，后续会修改
            click_add=True  # 首次点击添加按钮
        ):
            raise Exception("填写表单失败")

        print("  ✅ 表单填写完成")

        # 测试统计
        tested_ports = 0
        passed_ports = 0
        failed_ports = 0

        # 保留端口测试结果
        reserved_correct = 0  # 保留端口正确弹窗
        reserved_missing = []  # 保留端口未弹窗（错误）

        # 非保留端口测试结果
        non_reserved_correct = 0  # 非保留端口未弹窗
        non_reserved_error = []  # 非保留端口弹窗（错误）

        # 测试配置
        total_ports = 65535

        print(f"\n步骤3: 开始端口冲突测试...")
        print(f"  📋 测试范围: 1-{total_ports} 所有端口")
        print(f"  🔒 保留端口列表 ({len(self.RESERVED_PORTS)}个): {sorted(self.RESERVED_PORTS)}")
        print(f"  ⚠️  预期行为:")
        print(f"      - 保留端口: 应该弹出冲突提示")
        print(f"      - 非保留端口: 不应该弹窗")
        print(f"\n  ⚡ 极致优化: 表单复用，只修改源端口值")
        print(f"  🚀 预计速度: 2-3端口/秒，总耗时约6-9小时")
        print(f"  💡 提示: 测试期间请勿操作浏览器\n")

        print("=" * 80)
        start_time = time.time()

        # 遍历测试所有端口 (1-65535)
        for test_port in range(1, total_ports + 1):
            tested_ports += 1
            is_reserved = test_port in self.RESERVED_PORTS

            # 每100个端口或遇到保留端口时输出进度
            if tested_ports % 100 == 0 or is_reserved:
                elapsed = time.time() - start_time
                speed = tested_ports / elapsed  # 端口/秒
                remaining = (total_ports - tested_ports) / speed if speed > 0 else 0  # 剩余秒数
                progress = (tested_ports / total_ports) * 100

                print(f"\n[{tested_ports}/{total_ports}] 进度: {progress:.2f}% | "
                      f"已测: {tested_ports} | 通过: {passed_ports} | 失败: {failed_ports}")
                print(f"  ⏱️  已用时: {elapsed/60:.1f}分 | 速度: {speed:.1f}端口/秒 | "
                      f"剩余: {remaining/60:.1f}分")

                if is_reserved:
                    print(f"  🔍 测试保留端口: {test_port}")

            try:
                # 测试当前端口
                result = self._test_single_port(test_port, is_first=(test_port == 1))

                if result:
                    passed_ports += 1
                    if is_reserved:
                        reserved_correct += 1
                    else:
                        non_reserved_correct += 1
                else:
                    failed_ports += 1
                    if is_reserved:
                        reserved_missing.append(test_port)
                        print(f"  ❌ 保留端口 {test_port} 未弹窗（应该弹窗）")
                    else:
                        non_reserved_error.append(test_port)
                        print(f"  ❌ 非保留端口 {test_port} 弹窗（不应该弹窗）")

            except Exception as e:
                failed_ports += 1
                print(f"  ❌ 端口 {test_port} 测试异常: {e}")
                # 异常时尝试恢复：等待页面稳定后继续
                print(f"  ⚠️  尝试恢复...")
                try:
                    # 等待页面稳定，不刷新不重新点击添加
                    time.sleep(2)
                    # 检查表单是否还在，如果不在则重新打开
                    try:
                        # 尝试定位源端口输入框
                        external_port_input = self.router_client.driver.find_element(
                            By.XPATH, '//input[contains(@id, "_dport") and not(contains(@id, "_to_dport"))]'
                        )
                        print(f"  ✅ 表单仍然打开，继续测试")
                    except:
                        # 表单已关闭，需要重新打开（但仍然只点击一次添加）
                        print(f"  ℹ️  表单已关闭，重新打开表单...")
                        self.router_client.add_port_mapping(
                            src="192.168.1.100/24",
                            dst_ip="10.10.10.10",
                            dst_port="222",
                            external_port=str(test_port),
                            click_add=True  # 只有在表单关闭时才重新点击添加
                        )
                    print(f"  ✅ 已恢复，继续测试")
                except Exception as recover_error:
                    print(f"  ❌ 恢复失败: {recover_error}")
                    raise Exception(f"测试在端口 {test_port} 处异常中断，无法恢复")

        # 输出测试总结
        total_time = time.time() - start_time
        print("\n" + "=" * 80)
        print("测试总结:")
        print("=" * 80)
        print(f"总测试端口数: {total_ports}")
        print(f"总耗时: {total_time/60:.1f} 分钟 ({total_time/3600:.2f} 小时)")
        print(f"平均速度: {total_ports/total_time:.1f} 端口/秒")
        print(f"\n测试结果:")
        print(f"  ✅ 通过: {passed_ports} ({passed_ports/tested_ports*100:.2f}%)")
        print(f"  ❌ 失败: {failed_ports} ({failed_ports/tested_ports*100:.2f}%)")

        print(f"\n保留端口测试 ({len(self.RESERVED_PORTS)}个):")
        print(f"  ✅ 正确弹窗: {reserved_correct}")
        print(f"  ❌ 未弹窗(错误): {len(reserved_missing)}")
        if reserved_missing:
            print(f"     缺失端口: {reserved_missing}")

        print(f"\n非保留端口测试 ({total_ports - len(self.RESERVED_PORTS)}个):")
        print(f"  ✅ 正确(未弹窗): {non_reserved_correct}")
        print(f"  ❌ 错误弹窗: {len(non_reserved_error)}")
        if non_reserved_error and len(non_reserved_error) <= 20:
            print(f"     错误端口: {non_reserved_error}")
        elif len(non_reserved_error) > 20:
            print(f"     错误端口: {non_reserved_error[:20]} ... (共{len(non_reserved_error)}个)")

        # 判断测试结果
        if failed_ports > 0:
            print("\n" + "=" * 80)
            print(f"❌ 测试失败！共有 {failed_ports} 个端口测试失败")
            print("=" * 80)

            # 详细错误分析
            if reserved_missing:
                print(f"\n⚠️  保留端口列表不完整！以下端口应该保留但未弹窗:")
                print(f"   {reserved_missing}")

            if non_reserved_error:
                print(f"\n⚠️  保留端口列表有误！以下端口不应该保留但弹窗了:")
                if len(non_reserved_error) <= 50:
                    print(f"   {non_reserved_error}")
                else:
                    print(f"   前50个: {non_reserved_error[:50]}")
                    print(f"   ... (共{len(non_reserved_error)}个)")

            raise Exception(f"端口冲突检测失败！")
        else:
            print("\n" + "=" * 80)
            print("✅ 测试通过！所有端口测试成功")
            print("=" * 80)
            print(f"\n✅ 保留端口列表完整且准确")
            print(f"   保留端口: {sorted(self.RESERVED_PORTS)}")

    def _test_single_port(self, test_port: int, is_first: bool = False) -> bool:
        """
        测试单个端口

        优化流程（完全不刷新页面，不重新点击添加）:
        1. 修改源端口输入框的值为当前测试端口
        2. 点击保存
        3. 检查是否弹窗
        4. 判断结果并处理:
           - 有弹窗: 点击OK关闭弹窗（表单保持打开，源端口输入框仍然可用）
           - 无弹窗: 规则已保存（表单仍然打开，源端口输入框仍然可用，不需要任何操作）
        5. 继续修改源端口值，测试下一个端口

        Args:
            test_port: 要测试的端口号
            is_first: 是否是第一个端口（第一个端口已经在execute中填写过表单）

        Returns:
            bool: True=测试通过, False=测试失败
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException

        is_reserved = test_port in self.RESERVED_PORTS

        try:
            # 定位源端口输入框（每次都需要）
            external_port_input = self.router_client.driver.find_element(
                By.XPATH, '//input[contains(@id, "_dport") and not(contains(@id, "_to_dport"))]'
            )

            # 清空并输入新端口号（第一个端口也需要清理！）
            external_port_input.clear()
            external_port_input.send_keys(str(test_port))

            # 点击保存按钮
            save_button = self.router_client.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="save"]'))
            )
            save_button.click()
            time.sleep(0.3)  # 减少等待时间：0.5→0.3秒

            # 检查是否有弹窗
            has_popup = False
            try:
                # 尝试定位弹窗的OK按钮（减少等待时间：1秒→0.5秒）
                ok_button = WebDriverWait(self.router_client.driver, 0.5).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "OK") or contains(text(), "确定")]'))
                )
                has_popup = True
                # 点击OK关闭弹窗
                ok_button.click()
                time.sleep(0.1)  # 减少等待时间：0.2→0.1秒
                # 🔍 调试日志
                if test_port <= 10 or is_reserved:
                    print(f"      [DEBUG] 端口{test_port}: 有弹窗，已点击OK，表单保持打开")
                # 弹窗关闭后，表单仍然打开，源端口输入框可以继续使用
                # ✅ 不需要任何额外操作，直接返回
            except TimeoutException:
                # 没有弹窗，规则已保存
                has_popup = False
                # 🔍 调试日志
                if test_port <= 10 or is_reserved:
                    print(f"      [DEBUG] 端口{test_port}: 无弹窗，规则已保存，表单保持打开")
                # 表单仍然打开，源端口输入框可以继续使用
                # ✅ 不需要重新点击添加，不需要重新填写字段，直接返回

            # 判断测试结果
            if is_reserved:
                # 保留端口：应该有弹窗
                return has_popup  # True=通过, False=失败
            else:
                # 非保留端口：不应该有弹窗
                return not has_popup  # True=通过, False=失败

        except Exception as e:
            # 异常情况，打印详细错误信息
            print(f"      [ERROR] 端口{test_port}测试异常: {e}")
            # 抛出异常，让上层处理
            raise e

    def cleanup(self):
        """测试清理"""
        print("\n=== 测试清理 ===")
        try:
            # 清理：刷新页面移除所有测试规则
            print("刷新页面清理测试规则...")
            self.router_client.driver.refresh()
            time.sleep(2)
        except Exception as e:
            print(f"⚠️  清理过程出错: {e}")

        super().cleanup()
        print("✅ 测试清理完成")
