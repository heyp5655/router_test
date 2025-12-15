"""
路由器页面自动分析工具 V2 - 增强版

改进点：
1. 智能识别多种类型的菜单结构（包括JavaScript控制的菜单）
2. 截图页面，辅助分析
3. 使用JavaScript获取页面详细信息
4. 支持动态加载的内容
5. 自动遍历所有可能的页面

使用方法：
python scripts/analyze_router_pages_v2.py --ip 192.168.3.1 --username admin --password admin1
"""

import sys
import os
import time
import argparse
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from core.router_client import RouterClient


class RouterPageAnalyzerV2:
    """路由器页面分析器 V2"""

    def __init__(self, router_ip: str, username: str, password: str, model: str = "UR35"):
        self.router_ip = router_ip
        self.username = username
        self.password = password
        self.model = model

        # 创建路由器客户端
        self.router_client = RouterClient(
            router_ip=router_ip,
            username=username,
            password=password,
            model=model
        )

        # 存储分析结果
        self.menu_items = []  # 菜单列表
        self.page_elements = []  # 页面元素列表

        # 创建截图目录
        self.screenshot_dir = r"E:\GIT\ROUTER_TEST\logs\screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def analyze(self):
        """执行完整的分析流程"""
        print("\n" + "=" * 70)
        print("路由器页面自动分析工具 V2（增强版）")
        print("=" * 70)
        print(f"路由器IP: {self.router_ip}")
        print(f"用户名: {self.username}")
        print(f"型号: {self.model}")
        print("=" * 70 + "\n")

        try:
            # 1. 登录路由器
            print("步骤1: 登录路由器...")
            if not self.router_client.login_web():
                raise Exception("登录失败")
            print("✅ 登录成功\n")

            # 2. 截图首页
            print("步骤2: 截图首页...")
            self._take_screenshot("home_page")
            print("✅ 截图已保存\n")

            # 3. 获取页面HTML并分析
            print("步骤3: 分析页面HTML结构...")
            self._analyze_page_html()
            print("✅ HTML分析完成\n")

            # 4. 智能识别菜单结构
            print("步骤4: 智能识别菜单结构...")
            self._smart_analyze_menu()
            print(f"✅ 发现 {len(self.menu_items)} 个菜单项\n")

            # 5. 遍历每个页面，分析表单元素
            if len(self.menu_items) > 0:
                print("步骤5: 分析页面元素...")
                self._analyze_page_elements()
                print(f"✅ 分析了 {len(self.page_elements)} 个表单元素\n")
            else:
                print("步骤5: 跳过（没有发现菜单项）\n")

            # 6. 生成Excel报告
            print("步骤6: 生成Excel报告...")
            output_file = self._generate_excel_report()
            print(f"✅ Excel报告已生成: {output_file}\n")

            print("=" * 70)
            print("分析完成！")
            print("=" * 70)

        except Exception as e:
            print(f"\n❌ 分析失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 关闭浏览器
            if self.router_client.driver:
                self.router_client.driver.quit()

    def _take_screenshot(self, name):
        """截图"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            self.router_client.driver.save_screenshot(filepath)
            print(f"  📸 截图保存: {filepath}")
        except Exception as e:
            print(f"  ⚠️  截图失败: {e}")

    def _analyze_page_html(self):
        """分析页面HTML结构"""
        driver = self.router_client.driver

        try:
            # 获取页面HTML
            html = driver.page_source

            # 保存HTML到文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = os.path.join(self.screenshot_dir, f"page_source_{timestamp}.html")
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"  📄 页面HTML已保存: {html_file}")

            # 分析HTML中的关键元素
            print("  🔍 分析关键元素...")

            # 查找所有可能的菜单容器
            menu_containers = [
                "nav", "aside", "sidebar", "menu", "navigation",
                "left-panel", "side-menu", "main-menu", "tree", "accordion"
            ]

            for container in menu_containers:
                # 通过id查找
                elements = driver.find_elements(By.XPATH, f"//*[contains(@id, '{container}')]")
                if elements:
                    print(f"    找到包含'{container}'的ID元素: {len(elements)}个")

                # 通过class查找
                elements = driver.find_elements(By.XPATH, f"//*[contains(@class, '{container}')]")
                if elements:
                    print(f"    找到包含'{container}'的Class元素: {len(elements)}个")

        except Exception as e:
            print(f"  ⚠️  HTML分析出错: {e}")

    def _smart_analyze_menu(self):
        """智能分析菜单结构"""
        driver = self.router_client.driver

        try:
            # 等待页面完全加载
            time.sleep(5)

            print("  🔍 尝试多种方法识别菜单...")

            # 方法1: 查找标准的<a>链接
            self._method_find_links()

            # 方法2: 查找可点击的列表项
            self._method_find_clickable_items()

            # 方法3: 执行JavaScript获取菜单信息
            self._method_javascript_analysis()

            # 方法4: 查找iframe中的菜单
            self._method_find_iframe_menus()

            # 去重
            self._deduplicate_menu_items()

        except Exception as e:
            print(f"  ⚠️  菜单识别出错: {e}")

    def _method_find_links(self):
        """方法1: 查找所有链接"""
        driver = self.router_client.driver

        print("    方法1: 查找<a>标签链接...")
        try:
            links = driver.find_elements(By.XPATH, "//a[@href]")
            count = 0

            for link in links:
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()

                    # 跳过空文本和无效链接
                    if not text or len(text) < 2:
                        continue

                    # 处理hash路由
                    if '#' in href:
                        hash_part = href.split('#')[-1]
                        if len(hash_part) > 0:
                            menu_item = {
                                'text': text,
                                'url': href,
                                'hash': hash_part,
                                'type': 'hash',
                                'method': 'link'
                            }
                            self.menu_items.append(menu_item)
                            count += 1
                            print(f"      ✓ {text} -> #{hash_part}")

                    # 处理普通URL
                    elif not href.startswith('javascript:'):
                        menu_item = {
                            'text': text,
                            'url': href,
                            'hash': '',
                            'type': 'url',
                            'method': 'link'
                        }
                        self.menu_items.append(menu_item)
                        count += 1
                        print(f"      ✓ {text} -> {href}")

                except:
                    continue

            print(f"    方法1完成: 找到 {count} 个链接")

        except Exception as e:
            print(f"    方法1失败: {e}")

    def _method_find_clickable_items(self):
        """方法2: 查找可点击的菜单项"""
        driver = self.router_client.driver

        print("    方法2: 查找可点击的菜单项...")
        try:
            # 查找常见的菜单结构
            selectors = [
                "//li[contains(@class, 'menu')]",
                "//div[contains(@class, 'menu-item')]",
                "//div[contains(@class, 'nav-item')]",
                "//span[contains(@class, 'menu')]",
                "//div[@onclick]",
                "//li[@onclick]",
            ]

            count = 0
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        if text and len(text) >= 2:
                            # 尝试获取onclick属性或data属性
                            onclick = elem.get_attribute('onclick') or ''
                            data_page = elem.get_attribute('data-page') or ''
                            data_route = elem.get_attribute('data-route') or ''

                            menu_item = {
                                'text': text,
                                'url': '',
                                'hash': data_page or data_route,
                                'type': 'clickable',
                                'method': 'clickable',
                                'onclick': onclick
                            }
                            self.menu_items.append(menu_item)
                            count += 1
                            print(f"      ✓ {text} (可点击)")
                except:
                    continue

            print(f"    方法2完成: 找到 {count} 个可点击项")

        except Exception as e:
            print(f"    方法2失败: {e}")

    def _method_javascript_analysis(self):
        """方法3: 使用JavaScript分析"""
        driver = self.router_client.driver

        print("    方法3: JavaScript深度分析...")
        try:
            # 执行JavaScript获取所有可能的菜单信息
            script = """
            var menuItems = [];

            // 查找所有包含常见菜单属性的元素
            var elements = document.querySelectorAll('a, li, div[onclick], span[onclick]');

            elements.forEach(function(elem) {
                var text = elem.textContent.trim();
                if (text && text.length >= 2 && text.length <= 50) {
                    var href = elem.getAttribute('href') || '';
                    var onclick = elem.getAttribute('onclick') || '';
                    var dataPage = elem.getAttribute('data-page') || '';

                    menuItems.push({
                        text: text,
                        href: href,
                        onclick: onclick,
                        dataPage: dataPage
                    });
                }
            });

            return menuItems;
            """

            result = driver.execute_script(script)

            if result:
                print(f"    JavaScript发现 {len(result)} 个潜在菜单项")
                # 这里可以进一步处理result

        except Exception as e:
            print(f"    方法3失败: {e}")

    def _method_find_iframe_menus(self):
        """方法4: 查找iframe中的菜单"""
        driver = self.router_client.driver

        print("    方法4: 查找iframe中的菜单...")
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")

            if len(iframes) > 0:
                print(f"    发现 {len(iframes)} 个iframe")

                for idx, iframe in enumerate(iframes):
                    try:
                        # 切换到iframe
                        driver.switch_to.frame(iframe)

                        # 在iframe中查找链接
                        links = driver.find_elements(By.XPATH, "//a[@href]")
                        print(f"      iframe {idx+1}: 找到 {len(links)} 个链接")

                        # 切换回主页面
                        driver.switch_to.default_content()
                    except:
                        driver.switch_to.default_content()
                        continue
            else:
                print("    未发现iframe")

        except Exception as e:
            print(f"    方法4失败: {e}")

    def _deduplicate_menu_items(self):
        """去除重复的菜单项"""
        seen = {}
        unique_items = []

        for item in self.menu_items:
            # 使用文本作为唯一键
            key = item['text']

            if key not in seen:
                seen[key] = True
                unique_items.append(item)

        original_count = len(self.menu_items)
        self.menu_items = unique_items

        if original_count > len(unique_items):
            print(f"  去重: {original_count} -> {len(unique_items)}")

    def _analyze_page_elements(self):
        """分析每个页面的表单元素"""
        driver = self.router_client.driver

        for idx, menu_item in enumerate(self.menu_items, 1):
            print(f"\n  [{idx}/{len(self.menu_items)}] 分析页面: {menu_item['text']}")

            try:
                # 导航到页面
                if menu_item['type'] == 'hash' and menu_item['hash']:
                    url = f"http://{self.router_ip}/#{menu_item['hash']}"
                    driver.get(url)
                elif menu_item['type'] == 'url' and menu_item['url']:
                    driver.get(menu_item['url'])
                else:
                    print(f"    ⚠️  无法导航，跳过")
                    continue

                time.sleep(2)  # 等待页面加载

                # 截图
                self._take_screenshot(f"page_{idx}_{menu_item['text'][:20]}")

                # 分析表单元素
                elements = self._extract_form_elements()

                # 保存元素信息
                for element in elements:
                    element['menu'] = menu_item['text']
                    element['page_hash'] = menu_item.get('hash', '')
                    self.page_elements.append(element)

                print(f"    ✅ 找到 {len(elements)} 个表单元素")

            except Exception as e:
                print(f"    ⚠️  页面分析出错: {e}")
                continue

    def _extract_form_elements(self):
        """提取页面中的表单元素"""
        driver = self.router_client.driver
        elements = []

        try:
            # 查找所有输入元素
            input_elements = driver.find_elements(By.XPATH, "//input | //select | //textarea")

            for elem in input_elements:
                try:
                    # 基本属性
                    elem_type = elem.get_attribute('type') or 'text'
                    elem_id = elem.get_attribute('id') or ''
                    elem_name = elem.get_attribute('name') or ''
                    elem_value = elem.get_attribute('value') or ''
                    elem_placeholder = elem.get_attribute('placeholder') or ''
                    elem_tag = elem.tag_name

                    # 跳过隐藏元素
                    if elem_type == 'hidden':
                        continue

                    # 获取XPath
                    xpath = self._get_element_xpath(driver, elem)

                    # 查找对应的label
                    label = self._find_label_for_element(driver, elem, elem_id, elem_name)

                    # 对于select元素，获取所有选项
                    options = []
                    if elem_tag == 'select':
                        option_elements = elem.find_elements(By.XPATH, ".//option")
                        options = [opt.text.strip() for opt in option_elements if opt.text.strip()]

                    # 保存元素信息
                    element_info = {
                        'label': label,
                        'tag': elem_tag,
                        'type': elem_type,
                        'id': elem_id,
                        'name': elem_name,
                        'xpath': xpath,
                        'default_value': elem_value,
                        'placeholder': elem_placeholder,
                        'options': ', '.join(options) if options else ''
                    }

                    elements.append(element_info)

                except Exception as e:
                    continue

        except Exception as e:
            print(f"      ⚠️  元素提取出错: {e}")

        return elements

    def _get_element_xpath(self, driver, element):
        """获取元素的XPath"""
        try:
            script = """
            function getXPath(element) {
                if (element.id !== '')
                    return '//*[@id="' + element.id + '"]';
                if (element === document.body)
                    return '/html/body';

                var ix = 0;
                var siblings = element.parentNode.childNodes;
                for (var i = 0; i < siblings.length; i++) {
                    var sibling = siblings[i];
                    if (sibling === element)
                        return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                    if (sibling.nodeType === 1 && sibling.tagName === element.tagName)
                        ix++;
                }
            }
            return getXPath(arguments[0]);
            """
            xpath = driver.execute_script(script, element)
            return xpath or ''
        except:
            return ''

    def _find_label_for_element(self, driver, element, elem_id, elem_name):
        """查找元素对应的label"""
        try:
            # 方法1: 通过for属性查找label
            if elem_id:
                try:
                    label = driver.find_element(By.XPATH, f"//label[@for='{elem_id}']")
                    return label.text.strip()
                except:
                    pass

            # 方法2: 查找父元素中的label
            try:
                parent = element.find_element(By.XPATH, "./..")
                label = parent.find_element(By.XPATH, ".//label")
                return label.text.strip()
            except:
                pass

            # 方法3: 查找前面的相邻label
            try:
                label = element.find_element(By.XPATH, "./preceding-sibling::label[1]")
                return label.text.strip()
            except:
                pass

            # 方法4: 使用name或placeholder作为label
            if elem_name:
                return elem_name

        except:
            pass

        return '(未找到label)'

    def _generate_excel_report(self):
        """生成Excel报告"""
        wb = Workbook()

        # 删除默认sheet
        if 'Sheet' in wb.sheetnames:
            del wb['Sheet']

        # Sheet1: 菜单导航
        ws_menu = wb.create_sheet("菜单导航", 0)
        self._create_menu_sheet(ws_menu)

        # Sheet2: 页面元素
        ws_elements = wb.create_sheet("页面元素明细", 1)
        self._create_elements_sheet(ws_elements)

        # Sheet3: 配置参数模板
        ws_config = wb.create_sheet("配置参数模板", 2)
        self._create_config_template_sheet(ws_config)

        # 保存文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = r"E:\GIT\ROUTER_TEST\config"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"router_pages_analysis_v2_{timestamp}.xlsx")
        wb.save(output_file)

        return output_file

    def _create_menu_sheet(self, ws):
        """创建菜单导航Sheet"""
        headers = ['序号', '菜单名称', 'URL', 'Hash路由', '类型', '识别方法']
        ws.append(headers)

        # 设置标题行样式
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # 填充数据
        for idx, item in enumerate(self.menu_items, 1):
            ws.append([
                idx,
                item['text'],
                item.get('url', ''),
                item.get('hash', ''),
                item.get('type', ''),
                item.get('method', '')
            ])

        # 设置列宽
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 50
        ws.column_dimensions['D'].width = 30
        ws.column_dimensions['E'].width = 12
        ws.column_dimensions['F'].width = 15

    def _create_elements_sheet(self, ws):
        """创建页面元素Sheet"""
        headers = ['菜单', '页面Hash', '字段标签', '元素标签', '元素类型', 'ID', 'Name',
                   'XPath', '默认值', '占位符', '选项列表']
        ws.append(headers)

        # 设置标题行样式
        header_fill = PatternFill(start_color='70AD47', end_color='70AD47', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # 填充数据
        for elem in self.page_elements:
            ws.append([
                elem['menu'],
                elem['page_hash'],
                elem['label'],
                elem['tag'],
                elem['type'],
                elem['id'],
                elem['name'],
                elem['xpath'],
                elem['default_value'],
                elem['placeholder'],
                elem['options']
            ])

        # 设置列宽
        for col, width in [('A', 20), ('B', 20), ('C', 25), ('D', 10), ('E', 12),
                          ('F', 20), ('G', 20), ('H', 50), ('I', 20), ('J', 20), ('K', 30)]:
            ws.column_dimensions[col].width = width

    def _create_config_template_sheet(self, ws):
        """创建配置参数模板Sheet"""
        ws.append(['路由器满配置参数模板'])
        ws.append(['说明: 请在"配置值"列填写实际要配置的参数值'])
        ws.append([''])

        headers = ['菜单', '字段标签', '元素类型', '默认值', '配置值', '是否启用', '备注']
        ws.append(headers)

        # 设置标题行样式
        header_row = 4
        header_fill = PatternFill(start_color='FFC000', end_color='FFC000', fill_type='solid')
        header_font = Font(bold=True, color='000000')
        for cell in ws[header_row]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # 按菜单分组填充数据
        current_menu = None
        for elem in self.page_elements:
            if elem['menu'] != current_menu:
                if current_menu is not None:
                    ws.append([''] * 7)
                current_menu = elem['menu']

            ws.append([
                elem['menu'],
                elem['label'],
                elem['type'],
                elem['default_value'],
                '',
                'Y',
                elem['options'] if elem['options'] else ''
            ])

        # 设置列宽
        for col, width in [('A', 20), ('B', 25), ('C', 15), ('D', 20),
                          ('E', 30), ('F', 10), ('G', 40)]:
            ws.column_dimensions[col].width = width

        # 合并说明单元格
        ws.merge_cells('A1:G1')
        ws.merge_cells('A2:G2')
        ws['A1'].font = Font(bold=True, size=14)
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='路由器页面自动分析工具 V2')
    parser.add_argument('--ip', required=True, help='路由器IP地址')
    parser.add_argument('--username', default='admin', help='登录用户名（默认: admin）')
    parser.add_argument('--password', default='password', help='登录密码（默认: password）')
    parser.add_argument('--model', default='UR35', help='路由器型号（默认: UR35）')

    args = parser.parse_args()

    analyzer = RouterPageAnalyzerV2(
        router_ip=args.ip,
        username=args.username,
        password=args.password,
        model=args.model
    )

    analyzer.analyze()


if __name__ == '__main__':
    main()
