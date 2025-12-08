#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的蜂窝状态检查函数
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.router_client import RouterClient
import json

def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_cellular_summary_status():
    """测试 summary 页面蜂窝状态检查"""
    print_section("测试 1: status/summary 页面蜂窝状态检查")

    # 创建路由器客户端
    router_client = RouterClient(
        router_ip="192.168.50.16",  # 替换为你的路由器IP
        username="admin",
        password="password",
        model="UR32"
    )

    try:
        # 登录路由器
        print("\n1. 登录路由器...")
        if not router_client.login_web():
            print("[ERROR] 登录失败")
            return False

        # 检查 summary 页面状态
        print("\n2. 检查 summary 页面蜂窝状态...")
        result = router_client.check_cellular_summary_status(timeout=60)

        # 打印结果
        print("\n3. 检查结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 验证结果
        if result['success']:
            print("\n[OK] Summary页面检查成功!")
            print(f"  - 链路状态: {result['link_status']}")
            print(f"  - 状态: {result['status']}")
            print(f"  - 当前网络: {result['current_network']}")
            print(f"  - IPv4: {result['ipv4']}")
            print(f"  - IPv6: {result['ipv6']}")
            print(f"  - 连接时长: {result['connection_time']}")
            print(f"  - 数据用量: {result['data_usage']}")
            return True
        else:
            print(f"\n[ERROR] Summary页面检查失败: {result['error']}")
            return False

    except Exception as e:
        print(f"\n[ERROR] 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 关闭浏览器
        if router_client.driver:
            router_client.driver.quit()

def test_cellular_detail_status():
    """测试 cellular 页面详细状态检查"""
    print_section("测试 2: status/cellular 页面详细状态检查")

    # 创建路由器客户端
    router_client = RouterClient(
        router_ip="192.168.50.16",  # 替换为你的路由器IP
        username="admin",
        password="password",
        model="UR32"
    )

    try:
        # 登录路由器
        print("\n1. 登录路由器...")
        if not router_client.login_web():
            print("[ERROR] 登录失败")
            return False

        # 检查 cellular 页面详细状态
        print("\n2. 检查 cellular 页面详细状态...")
        result = router_client.check_cellular_detail_status(timeout=60)

        # 打印结果
        print("\n3. 检查结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 验证结果
        if result['success']:
            print("\n[OK] Cellular页面检查成功!")
            print(f"\n蜂窝运行状态:")
            print(f"  - 模块型号: {result['module_type']}")
            print(f"  - 版本: {result['firmware']}")
            print(f"  - 当前SIM卡: {result['current_sim']}")
            print(f"  - 信号强度: {result['signal_strength']}")
            print(f"  - 注册状态: {result['registration_status']}")
            print(f"  - IMEI: {result['imei']}")
            print(f"  - 运营商: {result['carrier']}")
            print(f"  - 网络类型: {result['network_type']}")
            print(f"  - 频段: {result['frequency_band']}")
            print(f"  - RSRP: {result['rsrp']}")
            print(f"  - RSRQ: {result['rsrq']}")
            print(f"  - SINR: {result['sinr']}")

            if result['monthly_stats']:
                print(f"\n月度数据统计:")
                for sim, stats in result['monthly_stats'].items():
                    print(f"  - {sim}: {stats}")

            if result['sim_apn_info']:
                print(f"\nSIM卡APN信息:")
                for apn in result['sim_apn_info']:
                    print(f"\n  {apn['name']}:")
                    print(f"    状态: {apn['status']}")
                    print(f"    IPv4: {apn['ipv4']}")
                    print(f"    IPv4网关: {apn['ipv4_gateway']}")
                    print(f"    连接时长: {apn['connection_time']}")

            return True
        else:
            print(f"\n[ERROR] Cellular页面检查失败: {result['error']}")
            return False

    except Exception as e:
        print(f"\n[ERROR] 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 关闭浏览器
        if router_client.driver:
            router_client.driver.quit()

def test_compatibility_method():
    """测试兼容性方法"""
    print_section("测试 3: 兼容性方法 check_cellular_status()")

    # 创建路由器客户端
    router_client = RouterClient(
        router_ip="192.168.50.16",  # 替换为你的路由器IP
        username="admin",
        password="password",
        model="UR32"
    )

    try:
        # 登录路由器
        print("\n1. 登录路由器...")
        if not router_client.login_web():
            print("[ERROR] 登录失败")
            return False

        # 使用兼容性方法检查
        print("\n2. 使用兼容性方法检查蜂窝状态...")
        result = router_client.check_cellular_status()

        # 验证结果
        if result:
            print("\n[OK] 兼容性方法检查成功!")
            return True
        else:
            print("\n[ERROR] 兼容性方法检查失败")
            return False

    except Exception as e:
        print(f"\n[ERROR] 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 关闭浏览器
        if router_client.driver:
            router_client.driver.quit()

def main():
    """主测试函数"""
    print("=" * 70)
    print("  蜂窝状态检查函数测试")
    print("=" * 70)
    print("\n注意: 请先确保:")
    print("  1. 路由器IP、用户名、密码正确")
    print("  2. 路由器已连接蜂窝网络")
    print("  3. Chrome浏览器驱动已安装")

    results = {
        'summary': False,
        'detail': False,
        'compatibility': False
    }

    # 测试 1: Summary 页面
    results['summary'] = test_cellular_summary_status()

    # 测试 2: Detail 页面
    results['detail'] = test_cellular_detail_status()

    # 测试 3: 兼容性方法
    results['compatibility'] = test_compatibility_method()

    # 打印总结
    print_section("测试总结")
    print(f"\n测试1 - Summary页面: {'✅ 通过' if results['summary'] else '❌ 失败'}")
    print(f"测试2 - Detail页面: {'✅ 通过' if results['detail'] else '❌ 失败'}")
    print(f"测试3 - 兼容性方法: {'✅ 通过' if results['compatibility'] else '❌ 失败'}")

    all_passed = all(results.values())
    print(f"\n{'='*70}")
    if all_passed:
        print("  ✅ 所有测试通过!")
    else:
        print("  ❌ 部分测试失败")
    print("=" * 70)

    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试过程中发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
