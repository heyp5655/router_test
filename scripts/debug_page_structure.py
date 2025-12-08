#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试页面结构 - 查看实际的HTML元素
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.router_client import RouterClient
from selenium.webdriver.common.by import By
import time

def save_page_source(client, filename):
    """保存页面源代码"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(client.driver.page_source)
        print(f"[OK] 页面源代码已保存到: {filename}")
    except Exception as e:
        print(f"[ERROR] 保存失败: {e}")

def find_element_with_strategies(client, label_text):
    """尝试多种策略查找标签对应的值"""
    print(f"\n{'='*70}")
    print(f"查找标签 '{label_text}' 对应的值")
    print(f"{'='*70}")

    strategies = []

    # 策略1: 通过following-sibling查找
    try:
        xpath = f'//*[contains(text(), "{label_text}")]/following-sibling::*[1]'
        element = client.driver.find_element(By.XPATH, xpath)
        value = element.text.strip()
        print(f"[策略1-following-sibling] 找到值: '{value}'")
        print(f"  元素标签: {element.tag_name}")
        print(f"  元素ID: {element.get_attribute('id')}")
        print(f"  元素Class: {element.get_attribute('class')}")
        strategies.append(('following-sibling', xpath, value))
    except Exception as e:
        print(f"[策略1] 失败: {e}")

    # 策略2: 通过父元素的下一个子元素查找
    try:
        xpath = f'//*[contains(text(), "{label_text}")]/../*[2]'
        element = client.driver.find_element(By.XPATH, xpath)
        value = element.text.strip()
        print(f"[策略2-parent-child] 找到值: '{value}'")
        print(f"  元素标签: {element.tag_name}")
        strategies.append(('parent-child', xpath, value))
    except Exception as e:
        print(f"[策略2] 失败: {e}")

    # 策略3: 通过td标签查找 (表格结构)
    try:
        xpath = f'//td[contains(text(), "{label_text}")]/following-sibling::td[1]'
        element = client.driver.find_element(By.XPATH, xpath)
        value = element.text.strip()
        print(f"[策略3-table-td] 找到值: '{value}'")
        strategies.append(('table-td', xpath, value))
    except Exception as e:
        print(f"[策略3] 失败: {e}")

    # 策略4: 通过dt/dd标签查找
    try:
        xpath = f'//dt[contains(text(), "{label_text}")]/following-sibling::dd[1]'
        element = client.driver.find_element(By.XPATH, xpath)
        value = element.text.strip()
        print(f"[策略4-dt-dd] 找到值: '{value}'")
        strategies.append(('dt-dd', xpath, value))
    except Exception as e:
        print(f"[策略4] 失败: {e}")

    # 策略5: 查找父元素的HTML结构
    try:
        label_element = client.driver.find_element(By.XPATH, f'//*[contains(text(), "{label_text}")]')
        parent = label_element.find_element(By.XPATH, '..')
        print(f"\n[结构分析]")
        print(f"  标签元素: <{label_element.tag_name}> text='{label_element.text}'")
        print(f"  父元素: <{parent.tag_name}> class='{parent.get_attribute('class')}'")
        print(f"  父元素HTML (前400字符):")
        print(f"  {parent.get_attribute('outerHTML')[:400]}")
    except Exception as e:
        print(f"[结构分析] 失败: {e}")

    return strategies

def debug_summary_page(client):
    """调试summary页面结构"""
    print("\n" + "="*70)
    print("调试 Summary 页面 (#status/summary)")
    print("="*70)

    client.driver.get(f"http://{client.router_ip}/#status/summary")
    client.driver.refresh()
    time.sleep(3)

    # 保存页面源代码
    save_page_source(client, "E:\\GIT\\ROUTER_TEST\\logs\\summary_page_source.html")

    # 测试不同的标签
    test_labels = ["Status", "Current Cellular Link", "IPv4", "Connection Duration"]

    all_strategies = {}
    for label in test_labels:
        strategies = find_element_with_strategies(client, label)
        if strategies:
            all_strategies[label] = strategies[0]  # 保存第一个成功的策略

    print(f"\n{'='*70}")
    print("Summary页面成功策略汇总:")
    print(f"{'='*70}")
    for label, (strategy_name, xpath, value) in all_strategies.items():
        print(f"{label}: 策略={strategy_name}, 值='{value}'")

def debug_cellular_page(client):
    """调试cellular详细页面结构"""
    print("\n" + "="*70)
    print("调试 Cellular 详细页面 (#status/cellular)")
    print("="*70)

    client.driver.get(f"http://{client.router_ip}/#status/cellular")
    client.driver.refresh()
    time.sleep(3)

    # 保存页面源代码
    save_page_source(client, "E:\\GIT\\ROUTER_TEST\\logs\\cellular_page_source.html")

    # 测试不同的标签
    test_labels = ["Model", "Version", "Current SIM", "Signal Level", "IMEI", "RSRP"]

    all_strategies = {}
    for label in test_labels:
        strategies = find_element_with_strategies(client, label)
        if strategies:
            all_strategies[label] = strategies[0]

    print(f"\n{'='*70}")
    print("Cellular页面成功策略汇总:")
    print(f"{'='*70}")
    for label, (strategy_name, xpath, value) in all_strategies.items():
        print(f"{label}: 策略={strategy_name}, 值='{value}'")

def main():
    ROUTER_IP = "192.168.1.1"
    USERNAME = "admin"
    PASSWORD = "admin1"
    MODEL = "UR32"

    print("="*70)
    print("  页面结构调试工具")
    print("="*70)

    client = RouterClient(
        router_ip=ROUTER_IP,
        username=USERNAME,
        password=PASSWORD,
        model=MODEL
    )

    try:
        print("\n登录路由器...")
        if not client.login_web():
            print("[ERROR] 登录失败")
            return

        print("[OK] 登录成功\n")

        # 调试summary页面
        debug_summary_page(client)

        print("\n" + "="*70)
        print("Summary页面调试完成，准备调试Cellular页面")
        print("="*70)
        time.sleep(2)

        # 调试cellular详细页面
        debug_cellular_page(client)

        print("\n" + "="*70)
        print("所有调试完成！")
        print("="*70)
        print("\n提示: 页面源代码已保存到 logs/ 目录")

    finally:
        if client.driver:
            time.sleep(2)
            client.driver.quit()

if __name__ == "__main__":
    main()
