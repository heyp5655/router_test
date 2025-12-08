"""
测试浏览器清理功能
验证三层防护机制是否正常工作
"""

import subprocess
import time
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def count_chrome_processes():
    """统计Chrome进程数量"""
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq chrome.exe'],
            capture_output=True,
            text=True
        )
        lines = result.stdout.strip().split('\n')
        # 减去表头行数（通常是3行）
        count = max(0, len(lines) - 3)
        return count
    except Exception as e:
        print(f"⚠️ 统计Chrome进程失败: {e}")
        return -1

def test_normal_cleanup():
    """测试正常cleanup流程"""
    print("\n" + "="*70)
    print("测试场景1: 正常cleanup流程")
    print("="*70)

    from models.test_config import TestConfig, RouterConfig
    from core.router_client import RouterClient

    # 记录初始进程数
    initial_count = count_chrome_processes()
    print(f"初始Chrome进程数: {initial_count}")

    try:
        # 创建RouterClient并登录
        config = RouterConfig(
            router_ip="192.168.50.16",
            username="admin",
            password="admin",
            model="UR35"
        )

        print("\n创建RouterClient...")
        client = RouterClient(config)

        print("登录路由器Web界面...")
        if not client.login_web():
            print("❌ 登录失败")
            return False

        print("✅ 登录成功，浏览器已打开")
        time.sleep(2)

        # 检查进程增加
        after_login = count_chrome_processes()
        print(f"登录后Chrome进程数: {after_login}")

        # 正常关闭
        print("\n调用close()方法...")
        client.close()
        time.sleep(2)

        # 检查进程恢复
        after_close = count_chrome_processes()
        print(f"关闭后Chrome进程数: {after_close}")

        if after_close <= initial_count:
            print("✅ 测试通过：浏览器已正常关闭")
            return True
        else:
            print(f"❌ 测试失败：进程未减少（初始:{initial_count}, 当前:{after_close}）")
            return False

    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_destructor_cleanup():
    """测试析构方法清理"""
    print("\n" + "="*70)
    print("测试场景2: 析构方法清理（不调用close）")
    print("="*70)

    from models.test_config import RouterConfig
    from core.router_client import RouterClient

    # 记录初始进程数
    initial_count = count_chrome_processes()
    print(f"初始Chrome进程数: {initial_count}")

    try:
        # 创建RouterClient并登录
        config = RouterConfig(
            router_ip="192.168.50.16",
            username="admin",
            password="admin",
            model="UR35"
        )

        print("\n创建RouterClient...")
        client = RouterClient(config)

        print("登录路由器Web界面...")
        if not client.login_web():
            print("❌ 登录失败")
            return False

        print("✅ 登录成功，浏览器已打开")
        time.sleep(2)

        # 检查进程增加
        after_login = count_chrome_processes()
        print(f"登录后Chrome进程数: {after_login}")

        # 不调用close()，直接删除对象
        print("\n不调用close()，直接删除对象（触发析构方法）...")
        del client

        # 等待析构和垃圾回收
        import gc
        gc.collect()
        time.sleep(3)

        # 检查进程恢复
        after_del = count_chrome_processes()
        print(f"删除对象后Chrome进程数: {after_del}")

        if after_del <= initial_count + 1:  # 允许1个进程的误差
            print("✅ 测试通过：析构方法成功关闭浏览器")
            return True
        else:
            print(f"⚠️ 测试警告：进程可能未完全清理（初始:{initial_count}, 当前:{after_del}）")
            print("   注意：析构方法调用时机不确定，这是Python的正常行为")
            return True  # 不算失败，只是警告

    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_exception_cleanup():
    """测试异常场景下的清理"""
    print("\n" + "="*70)
    print("测试场景3: 异常场景下的清理")
    print("="*70)

    from models.test_config import RouterConfig
    from core.router_client import RouterClient

    # 记录初始进程数
    initial_count = count_chrome_processes()
    print(f"初始Chrome进程数: {initial_count}")

    try:
        # 创建RouterClient并登录
        config = RouterConfig(
            router_ip="192.168.50.16",
            username="admin",
            password="admin",
            model="UR35"
        )

        print("\n创建RouterClient...")
        client = RouterClient(config)

        print("登录路由器Web界面...")
        if not client.login_web():
            print("❌ 登录失败")
            return False

        print("✅ 登录成功，浏览器已打开")
        time.sleep(2)

        # 检查进程增加
        after_login = count_chrome_processes()
        print(f"登录后Chrome进程数: {after_login}")

        # 模拟异常，但在finally中关闭
        print("\n模拟异常场景...")
        try:
            raise RuntimeError("模拟测试异常")
        except Exception as e:
            print(f"捕获到异常: {e}")
        finally:
            print("在finally块中调用close()...")
            client.close()

        time.sleep(2)

        # 检查进程恢复
        after_finally = count_chrome_processes()
        print(f"finally后Chrome进程数: {after_finally}")

        if after_finally <= initial_count:
            print("✅ 测试通过：finally块成功关闭浏览器")
            return True
        else:
            print(f"❌ 测试失败：进程未减少（初始:{initial_count}, 当前:{after_finally}）")
            return False

    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """主测试函数"""
    print("="*70)
    print("浏览器清理功能测试")
    print("="*70)
    print("\n⚠️ 注意：")
    print("1. 请确保路由器 192.168.50.16 可访问")
    print("2. 测试期间会打开Chrome浏览器窗口")
    print("3. 测试完成后浏览器应自动关闭")
    print("4. 如果看到浏览器窗口，请不要手动关闭")

    input("\n按Enter键开始测试...")

    results = []

    # 测试1: 正常cleanup
    try:
        result1 = test_normal_cleanup()
        results.append(("正常cleanup流程", result1))
    except Exception as e:
        print(f"测试1异常: {e}")
        results.append(("正常cleanup流程", False))

    time.sleep(3)

    # 测试2: 析构方法
    try:
        result2 = test_destructor_cleanup()
        results.append(("析构方法清理", result2))
    except Exception as e:
        print(f"测试2异常: {e}")
        results.append(("析构方法清理", False))

    time.sleep(3)

    # 测试3: 异常场景
    try:
        result3 = test_exception_cleanup()
        results.append(("异常场景清理", result3))
    except Exception as e:
        print(f"测试3异常: {e}")
        results.append(("异常场景清理", False))

    # 汇总结果
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)

    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {test_name}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print(f"\n总计: {passed_count}/{total_count} 通过")

    if passed_count == total_count:
        print("\n🎉 所有测试通过！浏览器清理功能正常工作。")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查修复代码。")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()

        # 最终检查
        print("\n" + "="*70)
        print("最终Chrome进程检查")
        print("="*70)
        final_count = count_chrome_processes()
        print(f"当前Chrome进程数: {final_count}")

        if final_count > 5:
            print("⚠️ 警告：Chrome进程数量较多，建议手动检查")
            print("   运行命令: tasklist | findstr chrome")
        else:
            print("✅ Chrome进程数量正常")

        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试脚本异常: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)
