"""
路由器页面自动分析工具 V3 - 最终版

特性：
1. 支持data-target属性的菜单导航
2. 自动识别主菜单和子菜单
3. 点击式导航，完全模拟用户操作
4. 智能等待页面加载完成
5. 自动截图每个页面
6. 提取所有表单元素

使用方法：
python scripts/analyze_router_pages_v3.py --ip 192.168.3.1 --username admin --password admin1
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from core.router_client import RouterClient


class RouterPageAnalyzerV3:
    """路由器页面分析器 V3 - 最终版"""

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
        print("路由器页面自动分析工具 V3（最终版）")
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

            # 2. 识别所有菜单项
            print("步骤2: 识别菜单结构...")
            self._collect_all_menu_items()
            print(f"✅ 发现 {len(self.menu_items)} 个页面\n")

            # 3. 遍历每个页面，分析表单元素
            if len(self.menu_items) > 0:
                print("步骤3: 分析页面元素...")
                self._analyze_all_pages()
                print(f"✅ 分析了 {len(self.page_elements)} 个表单元素\n")
            else:
                print("步骤3: 跳过（没有发现菜单项）\n")

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

    def _collect_all_menu_items(self):
        """收集所有菜单项"""
        driver = self.router_client.driver

        try:
            # 等待主菜单加载
            time.sleep(3)

            # 查找主菜单容器
            try:
                main_menu = driver.find_element(By.ID, "mainmenu")
            except:
                print("  ❌ 未找到主菜单容器 #mainmenu")
                return

            # 查找所有主菜单项（li.dropdown）
            main_menu_items = main_menu.find_elements(By.XPATH, ".//li[contains(@class, 'dropdown')]")
            print(f"  发现 {len(main_menu_items)} 个主菜单项")

            for idx, main_item in enumerate(main_menu_items, 1):
                try:
                    # 获取主菜单名称
                    main_link = main_item.find_element(By.XPATH, "./a")
                    main_text = main_link.text.strip()
                    main_target = main_link.get_attribute('data-target')

                    print(f"\n  [{idx}] 主菜单: {main_text}")

                    # 如果主菜单本身有data-target，直接添加
                    if main_target:
                        menu_info = {
                            'main_menu': main_text,
                            'sub_menu': '',
                            'text': main_text,
                            'target': main_target
                        }
                        self.menu_items.append(menu_info)
                        print(f"      ✓ {main_text} -> {main_target}")

                    # 检查是否有子菜单
                    try:
                        # 点击主菜单展开
                        if 'dropdown-toggle' in main_link.get_attribute('class'):
                            try:
                                main_link.click()
                                time.sleep(0.5)  # 等待下拉菜单展开
                            except:
                                pass

                        # 查找子菜单
                        sub_menu = main_item.find_element(By.XPATH, ".//ul[contains(@class, 'dropdown-menu')]")
                        sub_items = sub_menu.find_elements(By.XPATH, ".//li/a")

                        print(f"      子菜单数量: {len(sub_items)}")

                        for sub_item in sub_items:
                            try:
                                sub_text = sub_item.text.strip()
                                sub_target = sub_item.get_attribute('data-target')

                                if sub_text and sub_target:
                                    menu_info = {
                                        'main_menu': main_text,
                                        'sub_menu': sub_text,
                                        'text': f"{main_text} > {sub_text}",
                                        'target': sub_target
                                    }
                                    self.menu_items.append(menu_info)
                                    print(f"        ✓ {sub_text} -> {sub_target}")

                            except Exception as e:
                                continue

                    except NoSuchElementException:
                        # 没有子菜单
                        pass

                except Exception as e:
                    print(f"      ⚠️  主菜单项解析出错: {e}")
                    continue

        except Exception as e:
            print(f"  ❌ 菜单收集失败: {e}")
            import traceback
            traceback.print_exc()

    def _analyze_all_pages(self):
        """分析所有页面"""
        driver = self.router_client.driver
        total = len(self.menu_items)

        for idx, menu_item in enumerate(self.menu_items, 1):
            print(f"\n  [{idx}/{total}] 分析页面: {menu_item['text']}")

            try:
                # 导航到页面（通过点击对应的链接）
                success = self._navigate_to_page(menu_item['target'])

                if not success:
                    print(f"      ⚠️  导航失败，跳过")
                    continue

                # 等待页面加载
                time.sleep(2)

                # 截图
                safe_filename = menu_item['text'].replace('>', '_').replace('/', '_')[:50]
                self._take_screenshot(f"page_{idx}_{safe_filename}")

                # 分析表单元素
                elements = self._extract_form_elements()

                # 保存元素信息
                for element in elements:
                    element['main_menu'] = menu_item['main_menu']
                    element['sub_menu'] = menu_item['sub_menu']
                    element['target'] = menu_item['target']
                    self.page_elements.append(element)

                print(f"      ✅ 找到 {len(elements)} 个表单元素")

            except Exception as e:
                print(f"      ⚠️  页面分析出错: {e}")
                continue

    def _navigate_to_page(self, target):
        """导航到指定页面（通过URL hash）"""
        driver = self.router_client.driver

        try:
            # 直接通过URL hash导航（更简单可靠）
            url = f"http://{self.router_ip}/#{target}"
            driver.get(url)
            time.sleep(2)  # 等待页面加载

            return True

        except Exception as e:
            print(f"        导航错误: {e}")
            return False

    def _take_screenshot(self, name):
        """截图"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            self.router_client.driver.save_screenshot(filepath)
        except Exception as e:
            pass

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

                    # 跳过不可见元素
                    if not elem.is_displayed():
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

                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    continue

        except Exception as e:
            pass

        return elements

    def _get_element_xpath(self, driver, element):
        """获取元素的XPath"""
        try:
            elem_id = element.get_attribute('id')
            if elem_id:
                return f'//*[@id="{elem_id}"]'
            return ''
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

            # 方法2: 查找同一行的label（常见布局）
            try:
                # 向上找到包含该元素的row
                row = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'row')][1]")
                # 在row中查找label
                label = row.find_element(By.XPATH, ".//div[contains(@class, 'ys-label')]/text() | .//label")
                return label.text.strip()
            except:
                pass

            # 方法3: 查找父元素中的label
            try:
                parent = element.find_element(By.XPATH, "./..")
                label = parent.find_element(By.XPATH, ".//label")
                return label.text.strip()
            except:
                pass

            # 方法4: 查找前面的相邻div（包含ys-label类）
            try:
                label_div = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'ys-field')]/preceding-sibling::div[contains(@class, 'ys-label')][1]")
                return label_div.text.strip()
            except:
                pass

        except:
            pass

        return elem_name if elem_name else '(未找到label)'

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
        output_file = os.path.join(output_dir, f"router_pages_analysis_v3_{timestamp}.xlsx")
        wb.save(output_file)

        return output_file

    def _create_menu_sheet(self, ws):
        """创建菜单导航Sheet"""
        headers = ['序号', '主菜单', '子菜单', '完整路径', 'data-target']
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
                item['main_menu'],
                item['sub_menu'],
                item['text'],
                item['target']
            ])

        # 设置列宽
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 30
        ws.column_dimensions['D'].width = 40
        ws.column_dimensions['E'].width = 40

    def _create_elements_sheet(self, ws):
        """创建页面元素Sheet"""
        headers = ['主菜单', '子菜单', 'data-target', '字段标签', '元素标签', '元素类型',
                   'ID', 'Name', 'XPath', '默认值', '占位符', '选项列表']
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
                elem['main_menu'],
                elem['sub_menu'],
                elem['target'],
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
        for col, width in [('A', 15), ('B', 25), ('C', 30), ('D', 25), ('E', 10), ('F', 12),
                          ('G', 20), ('H', 20), ('I', 40), ('J', 20), ('K', 20), ('L', 30)]:
            ws.column_dimensions[col].width = width

    def _create_config_template_sheet(self, ws):
        """创建配置参数模板Sheet"""
        ws.append(['路由器满配置参数模板'])
        ws.append(['说明: 请在"配置值"列填写实际要配置的参数值'])
        ws.append([''])

        headers = ['主菜单', '子菜单', 'data-target', '字段标签', '元素类型', '默认值', '配置值', '是否启用', '备注']
        ws.append(headers)

        # 设置标题行样式
        header_row = 4
        header_fill = PatternFill(start_color='FFC000', end_color='FFC000', fill_type='solid')
        header_font = Font(bold=True, color='000000')
        for cell in ws[header_row]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # 按主菜单和子菜单分组填充数据
        current_main = None
        current_sub = None

        for elem in self.page_elements:
            # 如果是新的主菜单，添加分隔行
            if elem['main_menu'] != current_main:
                if current_main is not None:
                    ws.append([''] * 9)
                current_main = elem['main_menu']
                current_sub = None

            # 如果是新的子菜单，添加小分隔
            if elem['sub_menu'] != current_sub:
                current_sub = elem['sub_menu']

            ws.append([
                elem['main_menu'],
                elem['sub_menu'],
                elem['target'],
                elem['label'],
                elem['type'],
                elem['default_value'],
                '',  # 配置值
                'Y',  # 是否启用
                elem['options'] if elem['options'] else ''
            ])

        # 设置列宽
        for col, width in [('A', 15), ('B', 25), ('C', 30), ('D', 25), ('E', 15),
                          ('F', 20), ('G', 30), ('H', 10), ('I', 40)]:
            ws.column_dimensions[col].width = width

        # 合并说明单元格
        ws.merge_cells('A1:I1')
        ws.merge_cells('A2:I2')
        ws['A1'].font = Font(bold=True, size=14)
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='路由器页面自动分析工具 V3')
    parser.add_argument('--ip', required=True, help='路由器IP地址')
    parser.add_argument('--username', default='admin', help='登录用户名（默认: admin）')
    parser.add_argument('--password', default='password', help='登录密码（默认: password）')
    parser.add_argument('--model', default='UR35', help='路由器型号（默认: UR35）')

    args = parser.parse_args()

    analyzer = RouterPageAnalyzerV3(
        router_ip=args.ip,
        username=args.username,
        password=args.password,
        model=args.model
    )

    analyzer.analyze()


if __name__ == '__main__':
    main()
