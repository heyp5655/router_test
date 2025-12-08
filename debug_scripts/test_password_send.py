"""
测试Boot密码的不同发送方式
"""
import time

password = "ys23#2ls29#4"

print("=" * 60)
print("Boot密码发送方式对比测试")
print("=" * 60)

# 方式1: 只发送密码（当前代码）
print("\n方式1: 只发送密码字符")
print(f"  发送内容: {password}")
print(f"  字节: {password.encode('utf-8')}")
print(f"  十六进制: {password.encode('utf-8').hex()}")
print(f"  长度: {len(password)} 字符")

# 方式2: 密码 + \r
print("\n方式2: 密码 + \\r (回车)")
data2 = password + "\r"
print(f"  发送内容: {repr(data2)}")
print(f"  字节: {data2.encode('utf-8')}")
print(f"  十六进制: {data2.encode('utf-8').hex()}")
print(f"  长度: {len(data2)} 字符")

# 方式3: 密码 + \n
print("\n方式3: 密码 + \\n (换行)")
data3 = password + "\n"
print(f"  发送内容: {repr(data3)}")
print(f"  字节: {data3.encode('utf-8')}")
print(f"  十六进制: {data3.encode('utf-8').hex()}")
print(f"  长度: {len(data3)} 字符")

# 方式4: 密码 + \r\n
print("\n方式4: 密码 + \\r\\n (回车换行)")
data4 = password + "\r\n"
print(f"  发送内容: {repr(data4)}")
print(f"  字节: {data4.encode('utf-8')}")
print(f"  十六进制: {data4.encode('utf-8').hex()}")
print(f"  长度: {len(data4)} 字符")

print("\n" + "=" * 60)
print("对比总结:")
print("=" * 60)
print(f"纯密码:        {password.encode('utf-8').hex()}")
print(f"密码+\\r:        {(password + '\\r').encode('utf-8').hex()}")
print(f"密码+\\n:        {(password + '\\n').encode('utf-8').hex()}")
print(f"密码+\\r\\n:      {(password + '\\r\\n').encode('utf-8').hex()}")

# 十六进制对照表
print("\n" + "=" * 60)
print("ASCII码对照:")
print("=" * 60)
print("\\r (回车)   = 0d")
print("\\n (换行)   = 0a")
print("\\r\\n (回车换行) = 0d 0a")
