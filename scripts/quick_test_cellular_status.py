#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
蜂窝状态检查函数快速测试脚本
用于验证函数是否能正确获取路由器状态
"""

import sys
import os
import time
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.router_client import RouterClient

def print_separator(char="=", length=70):
    """打印分隔线"""
    print(char * length)

def print_header(title):
    """打印标题"""
    print("\n")
    print_separator()
    print(f"  {title}")
    print_separator()

def print_dict(data, indent=0):
    """递归打印字典"""
    indent_str = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{indent_str}{key}:")
            print_dict(value, indent + 1)
        elif isinstance(value, list):
            print(f"{indent_str}{key}:")
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    print(f"{indent_str}  [{i}]:")
                    print_dict(item, indent + 2)
                else:
                    print(f"{indent_str}  [{i}]: {item}")
        else:
            print(f"{indent_str}{key}: {value}")

def test_summary_status(client):
    """测试 summary 页面状态获取"""
    print_header("测试 1: status/summary 页面蜂窝状态")

    start_time = time.time()
    result = client.check_cellular_summary_status(timeout=60)
    elapsed = time.time() - start_time

    print(f"\n耗时: {elapsed:.2f} 秒")
    print(f"成功: {result['success']}")

    if result['success']:
        print("\n[OK] 获取成功！详细信息：")
        print_separator("-")
        print(f"链路状态: {result['Current Cellular Link']}")
        print(f"状态: {result['Status']}")
        print(f"IPv4: {result['IPv4']}")
        print(f"IPv6: {result['IPv6']}")
        print(f"连接时长: {result['Connection Duration']}")
        print(f"数据用量: {result['SIM Data Usage Monthly']}")
        print_separator("-")
    else:
        print(f"\n[ERROR] 获取失败: {result['error']}")

    return result['success']

def test_detail_status(client):
    """测试 cellular 页面详细状态获取"""
    print_header("测试 2: status/cellular 页面详细状态")

    start_time = time.time()
    result = client.check_cellular_detail_status(timeout=60)
    elapsed = time.time() - start_time

    print(f"\n耗时: {elapsed:.2f} 秒")
    print(f"成功: {result['success']}")

    if result['success']:
        print("\n[OK] 获取成功！详细信息：")

        # 蜂窝运行状态
        print("\n" + "="*70)
        print("【蜂窝运行状态】")
        print("="*70)
        print(f"模块型号: {result['Model']}")
        print(f"版本: {result['Version']}")
        print(f"当前SIM卡: {result['Current SIM']}")
        print(f"信号强度: {result['Signal Level']}")
        print(f"注册状态: {result['Register Status']}")
        print(f"IMEI: {result['IMEI']}")
        print(f"IMSI: {result['IMSI']}")
        print(f"ICCID: {result['ICCID']}")
        print(f"运营商: {result['ISP']}")
        print(f"网络类型: {result['Network Type']}")
        print(f"频段: {result['Cellular Frequency Band']}")
        print(f"PLMN ID: {result['PLMN ID']}")
        print(f"位置区码: {result['LAC']}")
        print(f"Cell ID: {result['Cell ID']}")
        print(f"RSRP: {result['RSRP']}")
        print(f"RSRQ: {result['RSRQ']}")
        print(f"SINR: {result['SINR']}")

        # 月度统计
        print("\n" + "="*70)
        print("【月度数据统计】")
        print("="*70)
        print(f"SIM-1: {result['SIM-1 Monthly']}")
        print(f"SIM-2: {result['SIM-2 Monthly']}")

        # APN信息
        if result['SIM APN Profile']:
            print("\n" + "="*70)
            print("【SIM卡APN信息】")
            print("="*70)
            for i, apn in enumerate(result['SIM APN Profile'], 1):
                print(f"\n{apn['Name']}:")
                print(f"  状态: {apn['Status']}")
                print(f"  IPv4地址: {apn['IPv4']}")
                print(f"  IPv4网关: {apn['IPv4 Gateway']}")
                print(f"  IPv4 DNS: {apn['IPv4 DNS']}")
                print(f"  IPv6地址: {apn['IPv6']}")
                print(f"  IPv6网关: {apn['IPv6 Gateway']}")
                print(f"  IPv6 DNS: {apn['IPv6 DNS']}")
                print(f"  连接时长: {apn['Connection Duration']}")

        print("\n" + "="*70)
    else:
        print(f"\n[ERROR] 获取失败: {result['error']}")

    return result['success']

def test_compatibility_method(client):
    """测试兼容性方法"""
    print_header("测试 3: 兼容性方法 check_cellular_status()")

    start_time = time.time()
    result = client.check_cellular_status()
    elapsed = time.time() - start_time

    print(f"\n耗时: {elapsed:.2f} 秒")
    print(f"结果: {result}")

    if result:
        print("\n[OK] 兼容性方法检查通过")
    else:
        print("\n[ERROR] 兼容性方法检查失败")

    return result

def main():
    """主函数"""
    print_separator("=")
    print("  蜂窝状态检查函数 - 快速测试")
    print_separator("=")
    print(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator("=")

    # 配置信息 - 请根据实际情况修改
    ROUTER_IP = "192.168.1.1"  # 修改为你的路由器IP
    USERNAME = "admin"
    PASSWORD = "admin1"  # 修改为你的路由器密码
    MODEL = "UR32"

    print(f"\n路由器配置:")
    print(f"  IP: {ROUTER_IP}")
    print(f"  用户名: {USERNAME}")
    print(f"  型号: {MODEL}")

    # 创建路由器客户端
    print("\n" + "="*70)
    print("初始化路由器客户端...")
    print("="*70)

    client = RouterClient(
        router_ip=ROUTER_IP,
        username=USERNAME,
        password=PASSWORD,
        model=MODEL
    )

    try:
        # 登录
        print("\n正在登录路由器...")
        login_start = time.time()
        if not client.login_web():
            print("[ERROR] 登录失败，退出测试")
            return False
        login_time = time.time() - login_start
        print(f"[OK] 登录成功 (耗时: {login_time:.2f}秒)")

        # 等待用户准备
        print("\n" + "="*70)
        print("  准备开始测试")
        print("="*70)
        print("\n提示: 开始自动测试...")
        # input("按 Enter 键开始测试...")  # 跳过交互提示，自动运行

        # 测试统计
        results = {
            'summary': False,
            'detail': False,
            'compatibility': False
        }

        # 测试1: Summary页面
        try:
            results['summary'] = test_summary_status(client)
        except Exception as e:
            print(f"\n[ERROR] 测试1异常: {e}")
            import traceback
            traceback.print_exc()

        # 询问是否继续
        print("\n" + "="*70)
        print("继续测试详细状态页面...")
        # response = input("继续测试详细状态页面? (y/n, 默认y): ").strip().lower()
        # if response and response != 'y':
        #     print("测试已中止")
        #     return True

        # 测试2: Detail页面
        try:
            results['detail'] = test_detail_status(client)
        except Exception as e:
            print(f"\n[ERROR] 测试2异常: {e}")
            import traceback
            traceback.print_exc()

        # 询问是否继续
        print("\n" + "="*70)
        print("继续测试兼容性方法...")
        # response = input("继续测试兼容性方法? (y/n, 默认y): ").strip().lower()
        # if response and response != 'y':
        #     print("测试已中止")
        #     return True

        # 测试3: 兼容性方法
        try:
            results['compatibility'] = test_compatibility_method(client)
        except Exception as e:
            print(f"\n[ERROR] 测试3异常: {e}")
            import traceback
            traceback.print_exc()

        # 测试总结
        print("\n" + "="*70)
        print("  测试总结")
        print("="*70)
        print(f"测试1 - Summary页面: {'[OK] 通过' if results['summary'] else '[ERROR] 失败'}")
        print(f"测试2 - Detail页面: {'[OK] 通过' if results['detail'] else '[ERROR] 失败'}")
        print(f"测试3 - 兼容性方法: {'[OK] 通过' if results['compatibility'] else '[ERROR] 失败'}")
        print("="*70)

        # 总体结果
        all_passed = all(results.values())
        if all_passed:
            print("\n[SUCCESS] 所有测试通过!")
        else:
            passed_count = sum(results.values())
            print(f"\n[WARN]  部分测试失败 ({passed_count}/3 通过)")

        return all_passed

    except KeyboardInterrupt:
        print("\n\n[WARN]  测试被用户中断")
        return False
    except Exception as e:
        print(f"\n[ERROR] 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理
        print("\n正在清理资源...")
        if client.driver:
            try:
                client.driver.quit()
                print("[OK] 浏览器已关闭")
            except:
                pass

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  启动测试脚本")
    print("="*70)

    try:
        success = main()

        print("\n" + "="*70)
        if success:
            print("  测试完成 - 成功")
        else:
            print("  测试完成 - 失败")
        print("="*70)

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n[ERROR] 脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
