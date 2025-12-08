#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试 Serial2 页面元素结构
检查启用按钮的实际 ID
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# 路由器信息
ROUTER_IP = "192.168.1.1"
USERNAME = "admin"
PASSWORD = "admin1"

print("=" * 80)
print("Serial2 页面元素结构调试")
print("=" * 80)

# 初始化浏览器
print("\n1. 初始化浏览器...")
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option('excludeSwitches', ['enable-automation'])
options.add_experimental_option('useAutomationExtension', False)

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 10)

try:
    # 登录
    print(f"\n2. 登录路由器: {ROUTER_IP}")
    driver.get(f"http://{ROUTER_IP}")
    time.sleep(2)

    username_input = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="username"]')))
    password_input = driver.find_element(By.XPATH, '//*[@id="password"]')
    login_button = driver.find_element(By.XPATH, '//*[@id="login-button"]')

    username_input.clear()
    username_input.send_keys(USERNAME)
    password_input.clear()
    password_input.send_keys(PASSWORD)
    login_button.click()

    print("  等待登录...")
    time.sleep(5)
    print("  ✅ 登录成功")

    # 跳转到 Serial2 页面
    print("\n3. 跳转到 Serial2 页面...")
    driver.get(f"http://{ROUTER_IP}/#industrial/serialport/serial2")
    time.sleep(5)
    print("  ✅ 页面加载完成")

    # 查找所有包含 "enable" 的元素
    print("\n4. 查找所有包含 'enable' 的元素...")
    script = """
    var elements = document.querySelectorAll('[id*="enable"]');
    var result = [];
    elements.forEach(function(el) {
        result.push({
            id: el.id,
            tag: el.tagName,
            type: el.type,
            checked: el.checked,
            value: el.value,
            innerHTML: el.innerHTML.substring(0, 100)
        });
    });
    return result;
    """

    elements = driver.execute_script(script)

    if elements:
        print(f"\n  找到 {len(elements)} 个包含 'enable' 的元素:")
        for idx, el in enumerate(elements, 1):
            print(f"\n  元素 {idx}:")
            print(f"    ID: {el['id']}")
            print(f"    标签: {el['tag']}")
            print(f"    类型: {el['type']}")
            print(f"    选中: {el['checked']}")
            print(f"    值: {el['value']}")
            if el['innerHTML']:
                print(f"    内容: {el['innerHTML'][:50]}...")
    else:
        print("  ⚠️ 未找到包含 'enable' 的元素")

    # 查找所有包含 "2_" 开头的ID元素
    print("\n5. 查找所有 ID 以 '2_' 开头的元素...")
    script2 = """
    var elements = document.querySelectorAll('[id^="2_"]');
    var result = [];
    elements.forEach(function(el) {
        result.push({
            id: el.id,
            tag: el.tagName,
            type: el.type
        });
    });
    return result;
    """

    elements2 = driver.execute_script(script2)

    if elements2:
        print(f"\n  找到 {len(elements2)} 个 ID 以 '2_' 开头的元素:")
        for el in elements2:
            print(f"    ID={el['id']}, 标签={el['tag']}, 类型={el['type']}")
    else:
        print("  ⚠️ 未找到 ID 以 '2_' 开头的元素")

    # 尝试查找 Serial2 相关的 checkbox/switch 元素
    print("\n6. 查找所有 checkbox 和 switch 元素...")
    script3 = """
    var checkboxes = document.querySelectorAll('input[type="checkbox"]');
    var result = [];
    checkboxes.forEach(function(el) {
        // 获取父元素的文本，看看是否与Serial2相关
        var parent = el.parentElement;
        var parentText = parent ? parent.textContent : '';
        result.push({
            id: el.id,
            name: el.name,
            parentText: parentText.substring(0, 50)
        });
    });
    return result;
    """

    checkboxes = driver.execute_script(script3)

    if checkboxes:
        print(f"\n  找到 {len(checkboxes)} 个 checkbox 元素:")
        for cb in checkboxes:
            print(f"    ID={cb['id']}, name={cb['name']}, 父元素文本={cb['parentText'][:30]}...")
    else:
        print("  ⚠️ 未找到 checkbox 元素")

    # 等待用户查看
    print("\n" + "=" * 80)
    print("调试完成！浏览器将在 10 秒后关闭...")
    print("=" * 80)
    time.sleep(10)

except Exception as e:
    print(f"\n❌ 发生错误: {e}")
    import traceback
    traceback.print_exc()

finally:
    print("\n关闭浏览器...")
    driver.quit()
    print("✅ 完成")
