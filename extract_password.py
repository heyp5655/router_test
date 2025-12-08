"""从桌面工作笔记.txt提取密码"""
import os
import re

# 查找桌面路径
desktop_paths = [
    r'C:\Users\Administrator\Desktop\工作笔记.txt',
    os.path.join(os.path.expanduser('~'), 'Desktop', '工作笔记.txt'),
]

for txt_path in desktop_paths:
    if os.path.exists(txt_path):
        print(f"找到文件: {txt_path}")

        # 尝试多种编码
        for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'cp936']:
            try:
                with open(txt_path, 'r', encoding=encoding) as f:
                    content = f.read()
                print(f"✅ 成功使用编码: {encoding}")

                # 查找密码相关行
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'ys23' in line.lower() or 'uboot' in line.lower():
                        print(f"\n第{i+1}行: {line}")

                # 提取密码
                match = re.search(r'密码[:：\s]*(ys23[^\s，。；\n]+)', content)
                if match:
                    password = match.group(1)
                else:
                    # 直接查找
                    match = re.search(r'(ys23#2ls29#4)', content)
                    password = match.group(1) if match else None

                if password:
                    print(f"\n提取的密码: '{password}'")
                    print(f"密码长度: {len(password)}")
                    print(f"字符列表: {[c for c in password]}")
                    print(f"十六进制: {password.encode('utf-8').hex()}")
                    print(f"ASCII码: {[ord(c) for c in password]}")

                    # 对比代码中的密码
                    code_password = "ys23#2ls29#4"
                    print(f"\n代码中的密码: '{code_password}'")
                    print(f"代码密码长度: {len(code_password)}")
                    print(f"代码十六进制: {code_password.encode('utf-8').hex()}")

                    if password == code_password:
                        print("\n✅ 密码完全相同")
                    else:
                        print("\n❌ 密码不同！")
                        print("差异分析:")
                        for i, (c1, c2) in enumerate(zip(password, code_password)):
                            if c1 != c2:
                                print(f"  位置{i}: TXT='{c1}'(0x{ord(c1):02x}) vs 代码='{c2}'(0x{ord(c2):02x})")
                break
            except Exception as e:
                continue
        break
else:
    print("❌ 未找到工作笔记.txt文件")
    print("请检查文件是否在桌面")
