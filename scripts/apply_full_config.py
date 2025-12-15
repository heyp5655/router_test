"""
路由器满配置自动应用工具

功能：
1. 读取Excel配置文件（由analyze_router_pages.py生成）
2. 自动登录路由器
3. 按菜单页面遍历，自动填写所有配置项
4. 保存并应用配置
5. 生成配置执行报告

使用方法：
python scripts/apply_full_config.py --ip 192.168.50.17 --config config/router_pages_analysis_20251211_142132.xlsx

输出报告：
E:\GIT\ROUTER_TEST\reports\full_config_report_<timestamp>.xlsx
"""

import sys
import os
import time
import argparse
from datetime import datetime
from collections import defaultdict

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from core.router_client import RouterClient


class FullConfigApplier:
    """路由器满配置应用器"""

    def __init__(self, router_ip: str, username: str, password: str, config_file: str, model: str = "UR35"):
        self.router_ip = router_ip
        self.username = username
        self.password = password
        self.config_file = config_file
        self.model = model

        # 创建路由器客户端
        self.router_client = RouterClient(
            router_ip=router_ip,
            username=username,
            password=password,
            model=model
        )

        # 配置项列表（从Excel读取）
        self.config_items = []

        # 执行结果记录
        self.results = []

        # 统计信息
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

    def apply_config(self):
        """执行完整的配置应用流程"""
        print("\n" + "=" * 70)
        print("路由器满配置自动应用工具")
        print("=" * 70)
        print(f"路由器IP: {self.router_ip}")
        print(f"用户名: {self.username}")
        print(f"型号: {self.model}")
        print(f"配置文件: {self.config_file}")
        print("=" * 70 + "\n")

        try:
            # 1. 读取配置文件
            print("步骤1: 读取配置文件...")
            if not self._load_config_from_excel():
                raise Exception("配置文件读取失败")
            print(f"✅ 成功加载 {len(self.config_items)} 个配置项\n")

            # 2. 登录路由器
            print("步骤2: 登录路由器...")
            if not self.router_client.login_web():
                raise Exception("登录失败")
            print("✅ 登录成功\n")

            # 3. 按菜单分组配置项
            print("步骤3: 分组配置项...")
            grouped_configs = self._group_configs_by_menu()
            print(f"✅ 配置项分为 {len(grouped_configs)} 个菜单页面\n")

            # 4. 遍历每个菜单页面，应用配置
            print("步骤4: 应用配置...")
            self._apply_configs_by_menu(grouped_configs)
            print(f"\n✅ 配置应用完成\n")

            # 5. 生成执行报告
            print("步骤5: 生成执行报告...")
            report_file = self._generate_report()
            print(f"✅ 执行报告已生成: {report_file}\n")

            # 6. 显示统计信息
            self._print_statistics()

            print("=" * 70)
            print("配置应用完成！")
            print("=" * 70)

        except Exception as e:
            print(f"\n❌ 配置应用失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 关闭浏览器
            if self.router_client.driver:
                self.router_client.driver.quit()

    def _load_config_from_excel(self):
        """从Excel文件加载配置"""
        try:
            if not os.path.exists(self.config_file):
                print(f"  ❌ 配置文件不存在: {self.config_file}")
                return False

            wb = load_workbook(self.config_file)

            # 读取"配置参数模板"Sheet
            if "配置参数模板" not in wb.sheetnames:
                print(f"  ❌ 配置文件中没有找到'配置参数模板'工作表")
                return False

            ws = wb["配置参数模板"]

            # 跳过前3行（标题和说明）
            # 第4行是表头: 菜单、字段标签、元素类型、默认值、配置值、是否启用、备注
            header_row = 4

            # 读取所有配置项
            for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
                # 跳过空行
                if not any(row):
                    continue

                menu = row[0] if len(row) > 0 else ''
                label = row[1] if len(row) > 1 else ''
                elem_type = row[2] if len(row) > 2 else ''
                default_value = row[3] if len(row) > 3 else ''
                config_value = row[4] if len(row) > 4 else ''
                enabled = row[5] if len(row) > 5 else 'Y'
                remark = row[6] if len(row) > 6 else ''

                # 只处理启用的配置项
                if str(enabled).upper() != 'Y':
                    continue

                # 只处理填写了配置值的项
                if not config_value or str(config_value).strip() == '':
                    continue

                config_item = {
                    'menu': menu,
                    'label': label,
                    'type': elem_type,
                    'default_value': default_value,
                    'config_value': config_value,
                    'remark': remark
                }

                self.config_items.append(config_item)
                self.stats['total'] += 1

            wb.close()
            return True

        except Exception as e:
            print(f"  ❌ 读取配置文件出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _group_configs_by_menu(self):
        """按菜单分组配置项"""
        grouped = defaultdict(list)
        for item in self.config_items:
            menu = item['menu']
            grouped[menu].append(item)
        return grouped

    def _apply_configs_by_menu(self, grouped_configs):
        """按菜单逐个应用配置"""
        total_menus = len(grouped_configs)

        for idx, (menu, configs) in enumerate(grouped_configs.items(), 1):
            print(f"\n  [{idx}/{total_menus}] 配置菜单: {menu}")
            print(f"    配置项数量: {len(configs)}")

            try:
                # 导航到菜单页面
                # 注意: 需要知道菜单对应的hash路由
                # 这里暂时跳过导航，实际使用时需要从"菜单导航"Sheet读取
                print(f"    ⚠️  暂时跳过页面导航，需要完善菜单映射")

                # 应用该页面的所有配置
                for config in configs:
                    self._apply_single_config(config)

                # 保存配置
                # 注意: 这里需要调用保存按钮，实际实现时需要知道保存按钮的定位方式
                print(f"    ⚠️  暂时跳过保存操作，需要完善保存逻辑")

            except Exception as e:
                print(f"    ❌ 菜单配置失败: {e}")
                continue

    def _apply_single_config(self, config):
        """应用单个配置项"""
        label = config['label']
        elem_type = config['type']
        config_value = config['config_value']

        try:
            # 根据元素类型选择不同的填写方法
            if elem_type == 'text' or elem_type == 'number':
                success = self._fill_text_input(label, config_value)
            elif elem_type == 'checkbox':
                success = self._fill_checkbox(label, config_value)
            elif elem_type == 'radio':
                success = self._fill_radio(label, config_value)
            elif elem_type == 'select':
                success = self._fill_select(label, config_value)
            else:
                print(f"      ⚠️  不支持的元素类型: {elem_type} ({label})")
                success = False
                self.stats['skipped'] += 1

            # 记录结果
            result = {
                'menu': config['menu'],
                'label': label,
                'type': elem_type,
                'config_value': config_value,
                'status': '成功' if success else '失败',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.results.append(result)

            if success:
                self.stats['success'] += 1
                print(f"      ✅ {label}: {config_value}")
            else:
                self.stats['failed'] += 1
                print(f"      ❌ {label}: 配置失败")

        except Exception as e:
            self.stats['failed'] += 1
            print(f"      ❌ {label}: {e}")

            result = {
                'menu': config['menu'],
                'label': label,
                'type': elem_type,
                'config_value': config_value,
                'status': f'失败: {e}',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.results.append(result)

    def _fill_text_input(self, label, value):
        """填写文本输入框"""
        # 这里需要根据label找到对应的input元素
        # 实际实现时需要更复杂的定位逻辑
        # 暂时返回False表示未实现
        return False

    def _fill_checkbox(self, label, value):
        """填写复选框"""
        # 实现复选框填写逻辑
        return False

    def _fill_radio(self, label, value):
        """填写单选框"""
        # 实现单选框填写逻辑
        return False

    def _fill_select(self, label, value):
        """填写下拉选择框"""
        # 实现下拉框填写逻辑
        return False

    def _generate_report(self):
        """生成执行报告"""
        wb = Workbook()

        # 删除默认sheet
        if 'Sheet' in wb.sheetnames:
            del wb['Sheet']

        # Sheet1: 执行摘要
        ws_summary = wb.create_sheet("执行摘要", 0)
        self._create_summary_sheet(ws_summary)

        # Sheet2: 详细结果
        ws_details = wb.create_sheet("详细结果", 1)
        self._create_details_sheet(ws_details)

        # 保存文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = r"E:\GIT\ROUTER_TEST\reports"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"full_config_report_{timestamp}.xlsx")
        wb.save(output_file)

        return output_file

    def _create_summary_sheet(self, ws):
        """创建执行摘要Sheet"""
        # 标题
        ws.append(['路由器满配置执行报告'])
        ws.append([''])
        ws.append(['执行时间', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        ws.append(['路由器IP', self.router_ip])
        ws.append(['配置文件', self.config_file])
        ws.append([''])

        # 统计信息
        ws.append(['统计信息'])
        ws.append(['总配置项', self.stats['total']])
        ws.append(['成功', self.stats['success']])
        ws.append(['失败', self.stats['failed']])
        ws.append(['跳过', self.stats['skipped']])

        # 计算成功率
        if self.stats['total'] > 0:
            success_rate = (self.stats['success'] / self.stats['total']) * 100
            ws.append(['成功率', f"{success_rate:.2f}%"])

        # 设置样式
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:B1')

        # 设置列宽
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 40

    def _create_details_sheet(self, ws):
        """创建详细结果Sheet"""
        # 设置标题行
        headers = ['菜单', '字段标签', '元素类型', '配置值', '状态', '执行时间']
        ws.append(headers)

        # 设置标题行样式
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # 填充数据
        for result in self.results:
            row = [
                result['menu'],
                result['label'],
                result['type'],
                result['config_value'],
                result['status'],
                result['timestamp']
            ]
            ws.append(row)

            # 根据状态设置行颜色
            row_idx = ws.max_row
            if '成功' in result['status']:
                fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
            elif '失败' in result['status']:
                fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
            else:
                fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')

            for cell in ws[row_idx]:
                cell.fill = fill

        # 设置列宽
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 30
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 20

    def _print_statistics(self):
        """打印统计信息"""
        print("\n" + "=" * 70)
        print("执行统计")
        print("=" * 70)
        print(f"总配置项: {self.stats['total']}")
        print(f"成功: {self.stats['success']} ({self.stats['success']/self.stats['total']*100:.2f}%)" if self.stats['total'] > 0 else "成功: 0")
        print(f"失败: {self.stats['failed']}")
        print(f"跳过: {self.stats['skipped']}")
        print("=" * 70)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='路由器满配置自动应用工具')
    parser.add_argument('--ip', required=True, help='路由器IP地址')
    parser.add_argument('--config', required=True, help='配置文件路径（Excel）')
    parser.add_argument('--username', default='admin', help='登录用户名（默认: admin）')
    parser.add_argument('--password', default='password', help='登录密码（默认: password）')
    parser.add_argument('--model', default='UR35', help='路由器型号（默认: UR35）')

    args = parser.parse_args()

    # 创建应用器并执行
    applier = FullConfigApplier(
        router_ip=args.ip,
        config_file=args.config,
        username=args.username,
        password=args.password,
        model=args.model
    )

    applier.apply_config()


if __name__ == '__main__':
    main()
