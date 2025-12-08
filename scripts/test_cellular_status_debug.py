"""
测试蜂窝状态读取函数
直接输出原始返回数据，不做格式化
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.router_client import RouterClient
import json

def test_cellular_status_functions():
    """测试两个蜂窝状态读取函数"""

    # 读取配置
    router_ip = "192.168.1.1"
    username = "admin"
    password = "admin1"

    print("="*80)
    print("开始测试蜂窝状态读取函数")
    print("="*80)

    # 创建路由器客户端（使用关键字参数）
    client = RouterClient(router_ip=router_ip, username=username, password=password)

    try:
        # 登录
        print("\n[1] 登录路由器...")
        if not client.login_web():
            print("[ERROR] 登录失败")
            return
        print("[OK] 登录成功\n")

        # 测试函数1: check_cellular_summary_status
        print("\n" + "="*80)
        print("测试函数1: check_cellular_summary_status()")
        print("="*80)

        result1 = client.check_cellular_summary_status(timeout=30)

        print("\n" + "-"*80)
        print("函数返回的原始字典:")
        print("-"*80)
        print(json.dumps(result1, indent=2, ensure_ascii=False))

        # 测试函数2: check_cellular_detail_status
        print("\n\n" + "="*80)
        print("测试函数2: check_cellular_detail_status()")
        print("="*80)

        result2 = client.check_cellular_detail_status(timeout=30)

        print("\n" + "-"*80)
        print("函数返回的原始字典:")
        print("-"*80)
        print(json.dumps(result2, indent=2, ensure_ascii=False))

        print("\n" + "="*80)
        print("测试完成")
        print("="*80)

    except Exception as e:
        print(f"\n[ERROR] 测试过程出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 关闭浏览器
        print("\n关闭浏览器...")
        client.close()

if __name__ == "__main__":
    test_cellular_status_functions()
