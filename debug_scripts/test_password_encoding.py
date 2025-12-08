#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试Boot密码的编码格式
检查不同编码方式的字节表示
"""

import sys

# 从配置文件读取密码
password = "ys23#2ls29#4"

print("=" * 80)
print("Boot密码编码分析")
print("=" * 80)
print(f"\n密码字符串: '{password}'")
print(f"密码长度: {len(password)} 字符")
print(f"Python字符串类型: {type(password)}")
print(f"Python版本: {sys.version}")

print("\n" + "=" * 80)
print("不同编码方式的字节表示")
print("=" * 80)

# UTF-8编码（当前使用）
utf8_bytes = password.encode('utf-8')
print(f"\n1. UTF-8编码:")
print(f"   字节: {utf8_bytes}")
print(f"   十六进制: {utf8_bytes.hex()}")
print(f"   长度: {len(utf8_bytes)} 字节")
print(f"   每个字符:")
for i, char in enumerate(password):
    char_bytes = char.encode('utf-8')
    print(f"      '{char}' -> {char_bytes} (0x{char_bytes.hex()})")

# ASCII编码
try:
    ascii_bytes = password.encode('ascii')
    print(f"\n2. ASCII编码:")
    print(f"   字节: {ascii_bytes}")
    print(f"   十六进制: {ascii_bytes.hex()}")
    print(f"   长度: {len(ascii_bytes)} 字节")
except UnicodeEncodeError as e:
    print(f"\n2. ASCII编码: ❌ 失败 - {e}")

# Latin-1编码
latin1_bytes = password.encode('latin-1')
print(f"\n3. Latin-1编码:")
print(f"   字节: {latin1_bytes}")
print(f"   十六进制: {latin1_bytes.hex()}")
print(f"   长度: {len(latin1_bytes)} 字节")

# GBK编码（中文环境可能）
try:
    gbk_bytes = password.encode('gbk')
    print(f"\n4. GBK编码:")
    print(f"   字节: {gbk_bytes}")
    print(f"   十六进制: {gbk_bytes.hex()}")
    print(f"   长度: {len(gbk_bytes)} 字节")
except UnicodeEncodeError as e:
    print(f"\n4. GBK编码: ❌ 失败 - {e}")

print("\n" + "=" * 80)
print("编码对比")
print("=" * 80)
if utf8_bytes == ascii_bytes:
    print("✅ UTF-8 和 ASCII 编码结果相同（纯ASCII字符）")
else:
    print("⚠️ UTF-8 和 ASCII 编码结果不同")

if utf8_bytes == latin1_bytes:
    print("✅ UTF-8 和 Latin-1 编码结果相同")
else:
    print("⚠️ UTF-8 和 Latin-1 编码结果不同")

print("\n" + "=" * 80)
print("CRT工具可能使用的编码")
print("=" * 80)
print("""
常见串口工具的默认编码:
- SecureCRT: ASCII / UTF-8 / Latin-1（可在会话选项中设置）
- PuTTY: UTF-8（默认）
- Tera Term: UTF-8 / Shift-JIS
- MobaXterm: UTF-8（默认）

建议检查:
1. 打开SecureCRT -> 选项 -> 会话选项 -> 终端 -> 外观
2. 查看"字符编码"设置
3. 常见选项: UTF-8, ASCII, Latin-1, GBK
""")

print("\n" + "=" * 80)
print("特殊字符分析")
print("=" * 80)
special_chars = ['#', '2', 'l', 's', '9']
print("\n密码中的特殊字符:")
for char in password:
    if not char.isalnum():
        print(f"  '{char}' (ASCII {ord(char)}, 0x{ord(char):02x})")

print("\n可能的问题字符:")
print("  '#' (ASCII 35, 0x23) - 井号，在某些环境可能被转义")
print("  其他都是普通字母数字，应该没问题")

print("\n" + "=" * 80)
print("测试建议")
print("=" * 80)
print("""
1. 检查CRT的字符编码设置
2. 尝试不同编码方式:
   - self.serial.write(password.encode('ascii'))
   - self.serial.write(password.encode('latin-1'))
   - self.serial.write(password.encode('utf-8'))  # 当前

3. 检查是否有隐藏字符:
   - BOM (Byte Order Mark)
   - 回车换行符的差异 (\\r\\n vs \\n)

4. 使用十六进制查看实际发送的字节
5. 对比CRT发送的字节和Python发送的字节
""")

print("\n" + "=" * 80)
print("PySerial编码测试")
print("=" * 80)

# 测试PySerial可能的发送方式
print("\n可能的发送方式:")
print(f"1. password.encode('utf-8')  : {password.encode('utf-8')}")
print(f"2. password.encode('ascii')  : {password.encode('ascii')}")
print(f"3. password.encode('latin-1'): {password.encode('latin-1')}")
print(f"4. password.encode()         : {password.encode()}  (默认UTF-8)")

# 测试是否有不可见字符
print("\n检查不可见字符:")
if any(ord(c) < 32 or ord(c) > 126 for c in password):
    print("⚠️ 密码包含不可见字符!")
    for i, char in enumerate(password):
        if ord(char) < 32 or ord(char) > 126:
            print(f"   位置{i}: '{char}' (ASCII {ord(char)})")
else:
    print("✅ 密码只包含可见ASCII字符 (32-126)")

print("\n" + "=" * 80)
