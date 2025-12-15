"""
路由器页面自动分析工具

功能：
1. 自动登录路由器
2. 遍历所有菜单项，记录URL和菜单名称
3. 分析每个页面的表单元素（input、select、checkbox等）
4. 提取XPath、元素类型、默认值、选项列表
5. 生成Excel配置表，方便后续实现满配置脚本

使用方法：
python scripts/analyze_router_pages.py --ip 192.168.50.17 --username admin --password password

输出文件：
E:\GIT\ROUTER_TEST\config\router_pages_analysis.xlsx
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
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from core.router_client import RouterClient
from models.test_config import RouterConfig


class RouterPageAnalyzer:
    """路由器页面分析器"""

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

    def analyze(self):
        """执行完整的分析流程"""
        print("\n" + "=" * 70)
        print("路由器页面自动分析工具")
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

            # 2. 分析菜单结构
            print("步骤2: 分析菜单结构...")
            self._analyze_menu_structure()
            print(f"✅ 发现 {len(self.menu_items)} 个菜单项\n")

            # 3. 遍历每个页面，分析表单元素
            print("步骤3: 分析页面元素...")
            self._analyze_page_elements()
            print(f"✅ 分析了 {len(self.page_elements)} 个表单元素\n")

            # 4. 生成Excel报告
            print("步骤4: 生成Excel报告...")
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

    def _analyze_menu_structure(self):
        """分析菜单结构"""
        driver = self.router_client.driver

        try:
            # 等待页面加载
            time.sleep(3)

            # 方法1: 查找左侧菜单（通常是 <li> 或 <a> 标签）
            # 根据实际页面结构调整选择器
            menu_selectors = [
                "//div[@id='menu']//a",  # 常见菜单结构1
                "//ul[@class='menu']//a",  # 常见菜单结构2
                "//nav//a",  # HTML5语义化标签
                "//aside//a",  # 侧边栏菜单
                "//div[contains(@class, 'sidebar')]//a",  # 包含sidebar类的div
                "//div[contains(@class, 'nav')]//a",  # 包含nav类的div
            ]

            menu_links = []
            for selector in menu_selectors:
                try:
                    links = driver.find_elements(By.XPATH, selector)
                    if links:
                        menu_links = links
                        print(f"  使用选择器找到菜单: {selector}")
                        break
                except:
                    continue

            if not menu_links:
                print("  ⚠️  未找到标准菜单结构，尝试分析整个页面的链接...")
                menu_links = driver.find_elements(By.XPATH, "//a[@href]")

            # 提取菜单信息
            for link in menu_links:
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()

                    # 过滤无效链接
                    if not href or not text:
                        continue
                    if href.startswith('javascript:'):
                        continue
                    if '#' in href and len(href.split('#')[-1]) > 0:
                        # 这是一个hash路由
                        hash_part = href.split('#')[-1]
                        menu_item = {
                            'text': text,
                            'url': href,
                            'hash': hash_part,
                            'type': 'hash'
                        }
                        self.menu_items.append(menu_item)
                        print(f"  📄 {text} -> #{hash_part}")

                except Exception as e:
                    continue

            # 去重
            seen = set()
            unique_items = []
            for item in self.menu_items:
                key = item['hash'] if item['type'] == 'hash' else item['url']
                if key not in seen:
                    seen.add(key)
                    unique_items.append(item)
            self.menu_items = unique_items

        except Exception as e:
            print(f"  ⚠️  菜单结构分析出错: {e}")

    def _analyze_page_elements(self):
        """分析每个页面的表单元素"""
        driver = self.router_client.driver

        for idx, menu_item in enumerate(self.menu_items, 1):
            print(f"\n  [{idx}/{len(self.menu_items)}] 分析页面: {menu_item['text']}")

            try:
                # 导航到页面
                if menu_item['type'] == 'hash':
                    # Hash路由，直接修改URL
                    url = f"http://{self.router_ip}/#{menu_item['hash']}"
                    driver.get(url)
                else:
                    driver.get(menu_item['url'])

                time.sleep(2)  # 等待页面加载

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
            # 使用JavaScript获取XPath
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
        output_file = os.path.join(output_dir, f"router_pages_analysis_{timestamp}.xlsx")
        wb.save(output_file)

        return output_file

    def _create_menu_sheet(self, ws):
        """创建菜单导航Sheet"""
        # 设置标题行
        headers = ['序号', '菜单名称', 'URL', 'Hash路由', '类型']
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
                item['url'],
                item.get('hash', ''),
                item['type']
            ])

        # 设置列宽
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 50
        ws.column_dimensions['D'].width = 30
        ws.column_dimensions['E'].width = 12

    def _create_elements_sheet(self, ws):
        """创建页面元素Sheet"""
        # 设置标题行
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
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 25
        ws.column_dimensions['D'].width = 10
        ws.column_dimensions['E'].width = 12
        ws.column_dimensions['F'].width = 20
        ws.column_dimensions['G'].width = 20
        ws.column_dimensions['H'].width = 50
        ws.column_dimensions['I'].width = 20
        ws.column_dimensions['J'].width = 20
        ws.column_dimensions['K'].width = 30

    def _create_config_template_sheet(self, ws):
        """创建配置参数模板Sheet"""
        # 设置说明
        ws.append(['路由器满配置参数模板'])
        ws.append(['说明: 请在"配置值"列填写实际要配置的参数值'])
        ws.append([''])

        # 设置标题行
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
            # 如果是新菜单，添加分隔行
            if elem['menu'] != current_menu:
                if current_menu is not None:
                    ws.append([''] * 7)  # 空行
                current_menu = elem['menu']

            # 填充数据行
            ws.append([
                elem['menu'],
                elem['label'],
                elem['type'],
                elem['default_value'],
                '',  # 配置值（留空，供用户填写）
                'Y',  # 是否启用（默认启用）
                elem['options'] if elem['options'] else ''  # 备注（对于select显示选项）
            ])

        # 设置列宽
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 20
        ws.column_dimensions['E'].width = 30
        ws.column_dimensions['F'].width = 10
        ws.column_dimensions['G'].width = 40

        # 合并说明单元格
        ws.merge_cells('A1:G1')
        ws.merge_cells('A2:G2')
        ws['A1'].font = Font(bold=True, size=14)
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='路由器页面自动分析工具')
    parser.add_argument('--ip', required=True, help='路由器IP地址')
    parser.add_argument('--username', default='admin', help='登录用户名（默认: admin）')
    parser.add_argument('--password', default='password', help='登录密码（默认: password）')
    parser.add_argument('--model', default='UR35', help='路由器型号（默认: UR35）')

    args = parser.parse_args()

    # 创建分析器并执行
    analyzer = RouterPageAnalyzer(
        router_ip=args.ip,
        username=args.username,
        password=args.password,
        model=args.model
    )

    analyzer.analyze()


if __name__ == '__main__':
    main()
