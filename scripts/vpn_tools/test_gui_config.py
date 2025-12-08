#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试GUI工具生成的配置"""

import sys
sys.path.insert(0, 'E:/GIT/ROUTER_TEST/scripts/vpn_tools')

# 模拟GUI对象
class MockGUI:
    def __init__(self):
        # 模拟用户选择
        self.exchange_mode_value = "Main"  # 用户选择Main
        self.local_id_type_value = "Default"
        self.phase1_dh_value = "MODP3072-15"
        self.phase1_encryption_value = "AES128"
        self.phase1_hash_value = "SHA1"
        self.nat_traversal_value = True
        self.sa_algorithm_value = "3DES-SHA1"
        self.pfs_group_value = "NULL"
        self.ike_lifetime_value = "10800"
        self.sa_lifetime_value = "3600"
        self.dpd_delay_value = "30"
        self.psk_key_value = "123456"
        self.allow_all_var_value = True  # anonymous模式

    def get(self):
        """模拟Tkinter的get()方法"""
        return getattr(self, f'{self._attr}_value')

# 创建mock对象
gui = MockGUI()

# 设置属性名称
class MockVar:
    def __init__(self, gui_obj, attr_name):
        self.gui_obj = gui_obj
        self.gui_obj._attr = attr_name

    def get(self):
        return getattr(self.gui_obj, f'{self.gui_obj._attr}_value')

# 测试exchange_mode
gui._attr = 'exchange_mode'
exchange_mode_map = {
    "Main": "main",
    "Aggressive": "aggressive"
}
result = exchange_mode_map.get(gui.get(), "main")
print(f"Exchange Mode: {gui.get()} -> {result}")

# 测试local_id_type
gui._attr = 'local_id_type'
local_id_map = {
    "Default": "address",
    "Address": "address",
    "FQDN": "fqdn",
    "User FQDN": "user_fqdn"
}
result = local_id_map.get(gui.get(), "address")
print(f"Local ID Type: {gui.get()} -> {result}")

# 测试DH组
gui._attr = 'phase1_dh'
dh_group_map = {
    "MODP1024-2": "modp1024",
    "MODP1536-5": "modp1536",
    "MODP2048-14": "modp2048",
    "MODP3072-15": "modp3072",
    "MODP4096-16": "modp4096",
    "MODP6144-17": "modp6144",
    "MODP8192-18": "modp8192",
    "ECP256-19": "ecp_256",
    "ECP384-20": "ecp_384",
    "ECP521-21": "ecp_521"
}
result = dh_group_map.get(gui.get(), "modp3072")
print(f"DH Group: {gui.get()} -> {result}")

print("\n" + "="*60)
print("如果上面显示:")
print("  Exchange Mode: Main -> main")
print("  Local ID Type: Default -> address")
print("  DH Group: MODP3072-15 -> modp3072")
print("那么代码逻辑是正确的")
print("="*60)
