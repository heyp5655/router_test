"""
清理旧版本分析文件

功能：
1. 删除旧版本的Excel分析文件（V1、V2、V3）
2. 删除旧版本的Python分析脚本（V1、V2、V3）
3. 只保留最新的V4版本
4. 可选：清理旧的截图文件

使用方法：
python scripts/cleanup_old_files.py
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class FileCleanup:
    """文件清理工具"""

    def __init__(self):
        self.project_root = r"E:\GIT\ROUTER_TEST"
        self.config_dir = os.path.join(self.project_root, "config")
        self.scripts_dir = os.path.join(self.project_root, "scripts")
        self.screenshots_dir = os.path.join(self.project_root, "logs", "screenshots")

        # 要删除的文件列表
        self.files_to_delete = []
        self.backup_dir = None

    def analyze(self):
        """分析需要删除的文件"""
        print("\n" + "=" * 80)
        print("文件清理分析工具")
        print("=" * 80 + "\n")

        # 1. 分析Excel文件
        print("📊 分析Excel文件...")
        excel_files = self._find_old_excel_files()
        print(f"   发现 {len(excel_files)} 个旧Excel文件\n")

        # 2. 分析Python脚本
        print("🐍 分析Python脚本...")
        python_files = self._find_old_python_scripts()
        print(f"   发现 {len(python_files)} 个旧Python脚本\n")

        # 3. 显示将要删除的文件
        total = len(excel_files) + len(python_files)
        if total == 0:
            print("✅ 没有需要清理的文件！")
            return False

        print(f"📋 将要删除的文件 (共{total}个):")
        print("\n旧Excel文件:")
        for f in excel_files:
            size = os.path.getsize(f) / 1024  # KB
            print(f"   ❌ {os.path.basename(f)} ({size:.1f} KB)")
            self.files_to_delete.append(f)

        print("\n旧Python脚本:")
        for f in python_files:
            size = os.path.getsize(f) / 1024  # KB
            print(f"   ❌ {os.path.basename(f)} ({size:.1f} KB)")
            self.files_to_delete.append(f)

        print("\n保留的文件:")
        print("   ✅ router_full_analysis_v4_*.xlsx (最新最完整)")
        print("   ✅ analyze_router_pages_v4.py (最新脚本)")
        print("   ✅ apply_full_config.py (满配置脚本)")

        return True

    def _find_old_excel_files(self):
        """查找旧版本Excel文件"""
        old_files = []

        # 要删除的Excel文件模式
        patterns = [
            "router_pages_analysis_202512*.xlsx",  # V1版本（不含v2/v3/v4）
            "router_pages_analysis_v2_*.xlsx",     # V2版本
            "router_pages_analysis_v3_*.xlsx",     # V3版本
        ]

        for pattern in patterns:
            import glob
            full_pattern = os.path.join(self.config_dir, pattern)
            files = glob.glob(full_pattern)
            old_files.extend(files)

        return old_files

    def _find_old_python_scripts(self):
        """查找旧版本Python脚本"""
        old_scripts = []

        # 要删除的脚本（不含v2/v3/v4后缀的原始版本，以及v2和v3）
        script_names = [
            "analyze_router_pages.py",      # V1
            "analyze_router_pages_v2.py",   # V2
            "analyze_router_pages_v3.py",   # V3
        ]

        for script_name in script_names:
            script_path = os.path.join(self.scripts_dir, script_name)
            if os.path.exists(script_path):
                old_scripts.append(script_path)

        return old_scripts

    def create_backup(self):
        """创建备份目录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = os.path.join(self.project_root, "backup", f"cleanup_{timestamp}")
        os.makedirs(self.backup_dir, exist_ok=True)
        print(f"\n📦 创建备份目录: {self.backup_dir}")
        return self.backup_dir

    def backup_and_delete(self):
        """备份并删除文件"""
        if not self.files_to_delete:
            print("\n✅ 没有文件需要删除")
            return

        # 创建备份
        backup_dir = self.create_backup()

        print("\n开始清理...")
        success_count = 0
        fail_count = 0

        for file_path in self.files_to_delete:
            try:
                # 备份文件
                file_name = os.path.basename(file_path)
                backup_path = os.path.join(backup_dir, file_name)

                import shutil
                shutil.copy2(file_path, backup_path)

                # 删除原文件
                os.remove(file_path)

                print(f"   ✅ 已删除: {file_name}")
                success_count += 1

            except Exception as e:
                print(f"   ❌ 删除失败: {file_name} - {e}")
                fail_count += 1

        print("\n" + "=" * 80)
        print(f"清理完成！")
        print(f"成功删除: {success_count} 个文件")
        if fail_count > 0:
            print(f"删除失败: {fail_count} 个文件")
        print(f"备份位置: {backup_dir}")
        print("=" * 80)

    def cleanup_screenshots(self):
        """清理截图目录（可选）"""
        print("\n📸 分析截图目录...")

        if not os.path.exists(self.screenshots_dir):
            print("   截图目录不存在")
            return

        # 统计截图文件
        screenshot_files = []
        for file in os.listdir(self.screenshots_dir):
            if file.endswith('.png'):
                file_path = os.path.join(self.screenshots_dir, file)
                screenshot_files.append(file_path)

        if not screenshot_files:
            print("   没有截图文件")
            return

        total_size = sum(os.path.getsize(f) for f in screenshot_files) / (1024 * 1024)  # MB
        print(f"   发现 {len(screenshot_files)} 个截图文件")
        print(f"   总大小: {total_size:.1f} MB")

        # 询问是否删除旧截图
        print("\n   截图文件说明:")
        print("   - V4版本的截图命名格式: page_X_MenuName_timestamp.png")
        print("   - 旧版本的截图: home_page_timestamp.png, page_source_timestamp.html")
        print("\n   是否清理旧截图？")
        print("   注意: 这不会删除V4版本的截图（page_X_开头的）")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("⚠️  文件清理工具")
    print("=" * 80)
    print("\n此工具将删除以下旧版本文件:")
    print("  • router_pages_analysis_*.xlsx (V1/V2/V3)")
    print("  • analyze_router_pages.py, v2.py, v3.py")
    print("\n保留:")
    print("  • router_full_analysis_v4_*.xlsx (最完整)")
    print("  • analyze_router_pages_v4.py (最新)")
    print("  • apply_full_config.py (满配置)")
    print("\n所有删除的文件都会先备份到 backup/ 目录")
    print("=" * 80)

    # 询问确认
    confirm = input("\n是否继续？(y/n): ").strip().lower()
    if confirm != 'y':
        print("\n❌ 已取消清理")
        return

    # 执行清理
    cleanup = FileCleanup()

    # 分析文件
    has_files = cleanup.analyze()

    if not has_files:
        return

    # 再次确认
    print("\n" + "=" * 80)
    confirm2 = input("确认删除以上文件？(y/n): ").strip().lower()
    if confirm2 != 'y':
        print("\n❌ 已取消清理")
        return

    # 执行删除
    cleanup.backup_and_delete()

    # 询问是否清理截图
    print("\n" + "=" * 80)
    cleanup_ss = input("是否也分析截图目录？(y/n): ").strip().lower()
    if cleanup_ss == 'y':
        cleanup.cleanup_screenshots()

    print("\n✅ 全部完成！")


if __name__ == '__main__':
    main()
