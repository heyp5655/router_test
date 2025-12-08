"""
调试脚本：登录路由器并查找PLMN ID的正确获取方法
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.router_client import RouterClient
from selenium.webdriver.common.by import By
import time

def debug_plmn_id():
    """调试PLMN ID获取"""
    client = None
    try:
        # 创建路由器客户端
        print("创建路由器客户端...")
        client = RouterClient(
            router_ip="192.168.1.1",
            username="admin",
            password="admin1"
        )

        # 登录
        print("登录路由器...")
        if not client.login_web():
            print("登录失败！")
            return

        print("登录成功！")

        # 导航到cellular detail页面
        print("\n导航到 #status/cellular 页面...")
        client.driver.get('http://192.168.1.1/#status/cellular')
        time.sleep(3)
        client.driver.refresh()
        time.sleep(3)

        print("\n" + "="*80)
        print("开始查找PLMN ID元素...")
        print("="*80)

        # 方法1: 查找所有包含'plmn'的元素（不区分大小写）
        print("\n[方法1] 查找所有ID包含'plmn'的元素:")
        try:
            elements = client.driver.find_elements(By.XPATH, '//*[contains(translate(@id, "PLMN", "plmn"), "plmn")]')
            for i, elem in enumerate(elements):
                elem_id = elem.get_attribute("id")
                elem_tag = elem.tag_name
                elem_text = elem.text[:100] if elem.text else ""
                elem_value = elem.get_attribute("value") or ""
                elem_class = elem.get_attribute("class") or ""
                print(f"\n  元素 {i+1}:")
                print(f"    ID: {elem_id}")
                print(f"    Tag: {elem_tag}")
                print(f"    Class: {elem_class}")
                print(f"    Text: '{elem_text}'")
                print(f"    Value: '{elem_value}'")
        except Exception as e:
            print(f"  失败: {e}")

        # 方法2: 查找文本包含'PLMN'的元素
        print("\n[方法2] 查找文本包含'PLMN'的元素:")
        try:
            elements = client.driver.find_elements(By.XPATH, '//*[contains(text(), "PLMN")]')
            for i, elem in enumerate(elements):
                elem_id = elem.get_attribute("id") or ""
                elem_tag = elem.tag_name
                elem_text = elem.text[:100] if elem.text else ""
                print(f"\n  元素 {i+1}:")
                print(f"    ID: {elem_id}")
                print(f"    Tag: {elem_tag}")
                print(f"    Text: '{elem_text}'")

                # 查找同级或子级元素
                try:
                    # 查找下一个兄弟div
                    next_div = elem.find_element(By.XPATH, './following-sibling::div[1]')
                    print(f"    Next Sibling Div Text: '{next_div.text}'")
                    print(f"    Next Sibling Div HTML: {next_div.get_attribute('outerHTML')[:200]}")

                    # 查找label
                    labels = next_div.find_elements(By.TAG_NAME, 'label')
                    if labels:
                        for j, label in enumerate(labels):
                            print(f"      Label {j+1}: ID='{label.get_attribute('id')}', Text='{label.text}'")
                except Exception as e2:
                    print(f"    查找兄弟元素失败: {e2}")
        except Exception as e:
            print(f"  失败: {e}")

        # 方法3: 尝试常见的ID模式
        print("\n[方法3] 尝试常见的ID模式:")
        test_xpaths = [
            ('//*[@id="0_plmnid"]', 'text'),
            ('//*[@id="0_plmnid"]', 'value'),
            ('//*[@id="0_plmnid"]', 'innerHTML'),
            ('//label[@id="0_plmnid"]', 'text'),
            ('//span[@id="0_plmnid"]', 'text'),
            ('//input[@id="0_plmnid"]', 'value'),
            ('//*[@id="plmnid"]', 'text'),
            ('//*[@id="plmnid"]', 'value'),
            ('//div[contains(text(), "PLMN ID")]/following-sibling::div[1]/label', 'text'),
            ('//div[contains(text(), "PLMN ID")]/following-sibling::div[1]//label', 'text'),
            ('//div[contains(text(), "PLMN ID")]/following-sibling::div[1]/span', 'text'),
            ('//div[contains(text(), "PLMN ID")]/..//label[not(contains(text(), "PLMN"))]', 'text'),
        ]

        for xpath, attr in test_xpaths:
            try:
                elem = client.driver.find_element(By.XPATH, xpath)
                if attr == 'text':
                    value = elem.text.strip()
                elif attr == 'innerHTML':
                    value = elem.get_attribute('innerHTML')
                else:
                    value = elem.get_attribute(attr) or ""

                print(f"\n  XPath: {xpath}")
                print(f"  属性: {attr}")
                print(f"  值: '{value}'")
                print(f"  标签: {elem.tag_name}")
                print(f"  ID: {elem.get_attribute('id')}")

                # 如果找到值为46011，高亮显示
                if '46011' in str(value):
                    print(f"  *** 找到了！值包含 46011 ***")
                    print(f"  完整HTML: {elem.get_attribute('outerHTML')[:300]}")

            except Exception as e:
                pass  # 静默失败

        # 方法4: 获取整个cellular页面的HTML，手动查找46011
        print("\n[方法4] 在页面HTML中搜索'46011':")
        try:
            page_source = client.driver.page_source
            if '46011' in page_source:
                print("  页面HTML中找到了 '46011'")

                # 找到46011附近的HTML片段
                index = page_source.find('46011')
                start = max(0, index - 200)
                end = min(len(page_source), index + 200)
                snippet = page_source[start:end]

                print("\n  46011 附近的HTML片段:")
                print("  " + "="*76)
                print("  " + snippet)
                print("  " + "="*76)
            else:
                print("  页面HTML中没有找到 '46011'")
                print("  可能PLMN ID的值不是46011，或者页面还没有加载完成")
        except Exception as e:
            print(f"  失败: {e}")

        # 方法5: 使用JavaScript获取
        print("\n[方法5] 使用JavaScript查找:")
        try:
            # 查找所有包含46011的元素
            js_script = """
            var elements = [];
            var allElements = document.querySelectorAll('*');
            for (var i = 0; i < allElements.length; i++) {
                var elem = allElements[i];
                if (elem.textContent && elem.textContent.includes('46011')) {
                    elements.push({
                        tag: elem.tagName,
                        id: elem.id,
                        class: elem.className,
                        text: elem.textContent.trim().substring(0, 100)
                    });
                }
            }
            return elements;
            """
            results = client.driver.execute_script(js_script)
            if results:
                print(f"  找到 {len(results)} 个包含'46011'的元素:")
                for i, result in enumerate(results):
                    print(f"\n  元素 {i+1}:")
                    print(f"    Tag: {result['tag']}")
                    print(f"    ID: {result['id']}")
                    print(f"    Class: {result['class']}")
                    print(f"    Text: {result['text']}")
            else:
                print("  没有找到包含'46011'的元素")
        except Exception as e:
            print(f"  失败: {e}")

        # 等待，让我们可以手动检查浏览器
        print("\n" + "="*80)
        print("浏览器将在30秒后关闭，您可以手动检查页面...")
        print("="*80)
        time.sleep(30)

    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if client and client.driver:
            print("\n关闭浏览器...")
            client.driver.quit()

if __name__ == "__main__":
    debug_plmn_id()

