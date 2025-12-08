#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Boot密码验证工具
帮助确认密码是否正确
"""

import os

print("=" * 80)
print("Boot密码验证")
print("=" * 80)

# 从代码中读取密码
boot_password = "ys23#2ls29#4"

print(f"\n当前配置的Boot密码: '{boot_password}'")
print(f"密码长度: {len(boot_password)} 字符")
print(f"密码字符列表: {list(boot_password)}")

print("\n逐字符分析:")
for i, char in enumerate(boot_password):
    print(f"  [{i}] '{char}' - ASCII {ord(char):3d} (0x{ord(char):02x})")

print("\n检查特殊字符:")
special_chars = [c for c in boot_password if not c.isalnum()]
if special_chars:
    print(f"  特殊字符: {special_chars}")
    for char in special_chars:
        print(f"    '{char}' - 可能在某些环境需要转义")
else:
    print("  无特殊字符")

print("\n" + "=" * 80)
print("重要问题")
print("=" * 80)
print("""
1. 这个密码是从哪里获取的？
   - 设备文档？
   - 之前成功过的记录？
   - 其他来源？

2. 在CRT中手动输入时：
   - 看到 "please input password:" 后
   - 手动输入: y-s-2-3-#-2-l-s-2-9-#-4
   - 按回车
   - 结果如何？
     a) 密码被显示在 "Enter :" 后面？
     b) 直接 "command not found"？
     c) 其他响应？

3. 是否有其他Boot密码？
   - 默认密码？
   - 空密码（直接按回车）？

4. 设备是否有Boot密码功能？
   - 有些设备的Boot模式不需要密码
   - 或者密码功能被禁用了

5. User Menu中的选项：
   [h] Print user menu
   [f] Format Flash, Reset settings to factory default
   [b] Boot recovery system
   [d] Download firmware from TFTP
   [m] modify env: ipaddr, netmask, gatewayip, serverip
   [r] Reboot

   是否注意到：没有明确的 "进入Boot模式" 选项？
   'X' 命令可能是隐藏命令，但需要特定条件？

6. 尝试其他命令：
   - 输入 'b' (Boot recovery system) 会怎样？
   - 是否也要求密码？
""")

print("\n" + "=" * 80)
print("建议测试步骤")
print("=" * 80)
print("""
1. 在CRT中测试：
   a) Enter: 后输入 'X'，按回车
   b) 看到 "please input password:"
   c) 尝试直接按回车（测试空密码）
   d) 观察响应

2. 如果空密码不行，尝试：
   a) 输入简单的测试密码，如: 123456
   b) 观察是否也被显示出来

3. 尝试其他进入Boot的方法：
   a) Enter: 后输入 'b' (Boot recovery system)
   b) 看是否也要求密码
   c) 密码是否相同

4. 检查设备文档：
   - 查找 "Boot Mode Password" 或 "U-Boot Password"
   - 确认正确的密码
""")

print("\n" + "=" * 80)
print("密码可能性")
print("=" * 80)
print("""
常见的Boot密码模式：
1. 空密码（直接回车）
2. 简单密码：admin, 123456, password
3. 设备型号相关
4. MAC地址相关
5. 出厂默认密码

当前密码 'ys23#2ls29#4' 看起来像：
- 随机密码？
- 特定设备的密码？
- 是否确认这个密码之前成功过？
""")

# 创建密码测试文件
print("\n" + "=" * 80)
print("创建密码测试文件")
print("=" * 80)

with open("boot_password_test.txt", "w", encoding="utf-8") as f:
    f.write(boot_password)

print(f"✅ 已创建 'boot_password_test.txt'")
print(f"   可以从这个文件复制密码到CRT中测试")
print(f"   确保复制时没有额外的空格或换行")

# 十六进制表示
hex_repr = boot_password.encode('utf-8').hex()
print(f"\n密码的十六进制表示: {hex_repr}")
print(f"可以用这个验证发送的是否正确")

print("\n" + "=" * 80)
