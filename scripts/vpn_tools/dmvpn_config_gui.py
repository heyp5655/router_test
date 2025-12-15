#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMVPN服务器配置工具 - 图形界面版本 v2.2

v2.2 更新 (2025-11-28):
- ✅ 添加配置预览功能，确认无误后再应用
- ✅ 添加配置对比功能，对比新旧配置差异
- ✅ 添加参数验证，防止错误配置
- ✅ 添加二次确认机制，避免误操作
- ✅ 应用按钮初始禁用，预览后才能应用
- ✅ 支持复制配置到剪贴板

v2.1 更新 (2025-11-27):
- 添加滚动框架支持，解决内容过多无法显示的问题
- 支持鼠标滚轮滚动
- 窗口大小自适应
- 所有区域（包括日志）都可通过滚动访问
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import paramiko
import threading
from typing import Optional

class DMVPNServerConfigGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DMVPN服务器配置工具 v2.2")
        self.root.geometry("900x700")
        self.root.resizable(True, True)

        # SSH连接对象
        self.ssh_client: Optional[paramiko.SSHClient] = None

        # 创建主容器和滚动条
        self.create_scrollable_frame()

        # 创建界面
        self.create_widgets()

    def create_scrollable_frame(self):
        """创建可滚动的主框架"""
        # 创建Canvas和滚动条
        self.main_canvas = tk.Canvas(self.root, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)

        # 创建内部容器Frame
        self.scrollable_frame = ttk.Frame(self.main_canvas)

        # 记录上次的canvas宽度，避免重复更新
        self._last_canvas_width = 0

        # 配置Canvas滚动区域
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )

        self.canvas_frame = self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)

        # 布局Canvas和滚动条
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 绑定鼠标滚轮事件
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # 绑定Canvas大小调整事件
        self.main_canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_canvas_configure(self, event):
        """Canvas大小改变时调整内部Frame宽度"""
        # 防抖动：只在宽度实际改变时更新
        if abs(event.width - self._last_canvas_width) > 5:  # 5像素容差
            self._last_canvas_width = event.width
            self.main_canvas.itemconfig(self.canvas_frame, width=event.width)

    def create_widgets(self):
        """创建所有界面组件"""

        # ===== SSH连接配置区域 =====
        ssh_frame = ttk.LabelFrame(self.scrollable_frame, text="服务器SSH连接", padding=10)
        ssh_frame.pack(fill=tk.X, padx=10, pady=5)

        # SSH IP
        ttk.Label(ssh_frame, text="服务器IP:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.ssh_ip = ttk.Entry(ssh_frame, width=30)
        self.ssh_ip.insert(0, "192.168.50.48")
        self.ssh_ip.grid(row=0, column=1, padx=5, pady=5)

        # SSH端口
        ttk.Label(ssh_frame, text="SSH端口:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.ssh_port = ttk.Entry(ssh_frame, width=15)
        self.ssh_port.insert(0, "22")
        self.ssh_port.grid(row=0, column=3, padx=5, pady=5)

        # SSH用户名
        ttk.Label(ssh_frame, text="用户名:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.ssh_user = ttk.Entry(ssh_frame, width=30)
        self.ssh_user.insert(0, "yuxy")
        self.ssh_user.grid(row=1, column=1, padx=5, pady=5)

        # SSH密码
        ttk.Label(ssh_frame, text="密码:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.ssh_password = ttk.Entry(ssh_frame, width=30, show="*")
        self.ssh_password.insert(0, "milesight123")
        self.ssh_password.grid(row=1, column=3, padx=5, pady=5)

        # 测试连接按钮
        self.test_btn = ttk.Button(ssh_frame, text="测试连接", command=self.test_connection)
        self.test_btn.grid(row=2, column=0, columnspan=4, pady=10)

        # ===== 允许的路由器IP配置区域 =====
        router_frame = ttk.LabelFrame(self.scrollable_frame, text="允许连接的路由器IP (服务器端)", padding=10)
        router_frame.pack(fill=tk.X, padx=10, pady=5)

        # 路由器IP列表
        ttk.Label(router_frame, text="路由器WAN IP:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        # IP输入框和列表框的容器
        ip_container = ttk.Frame(router_frame)
        ip_container.grid(row=0, column=1, columnspan=3, sticky=tk.EW, padx=5, pady=5)

        # IP输入框
        self.router_ip_input = ttk.Entry(ip_container, width=30)
        self.router_ip_input.pack(side=tk.LEFT, padx=(0, 5))

        # 添加IP按钮
        ttk.Button(ip_container, text="添加", command=self.add_router_ip, width=10).pack(side=tk.LEFT, padx=2)

        # 删除IP按钮
        ttk.Button(ip_container, text="删除选中", command=self.remove_router_ip, width=10).pack(side=tk.LEFT, padx=2)

        # 允许所有IP按钮
        self.allow_all_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ip_container, text="允许任意IP (推荐)", variable=self.allow_all_var,
                       command=self.toggle_ip_list).pack(side=tk.LEFT, padx=10)

        # IP列表框
        list_container = ttk.Frame(router_frame)
        list_container.grid(row=1, column=0, columnspan=4, sticky=tk.EW, padx=5, pady=5)

        ttk.Label(list_container, text="已添加的路由器IP:").pack(anchor=tk.W, pady=(0, 5))

        # 创建列表框和滚动条
        list_frame = ttk.Frame(list_container)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.router_ip_listbox = tk.Listbox(list_frame, height=4, yscrollcommand=scrollbar.set)
        self.router_ip_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.router_ip_listbox.yview)

        # 默认添加一些IP
        default_ips = ["192.168.50.16", "192.168.40.207", "10.33.126.188"]
        for ip in default_ips:
            self.router_ip_listbox.insert(tk.END, ip)

        # 提示信息
        ttk.Label(router_frame,
                 text="提示: 路由器的WAN口IP。如果是4G路由器，填写公网IP。建议勾选'允许任意IP'",
                 foreground="gray").grid(row=2, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)

        # 初始化时禁用列表（因为默认允许所有IP）
        self.toggle_ip_list()

        # ===== GRE服务器配置区域 =====
        gre_frame = ttk.LabelFrame(self.scrollable_frame, text="GRE隧道配置 (服务器端)", padding=10)
        gre_frame.pack(fill=tk.X, padx=10, pady=5)

        # 服务器GRE IP
        ttk.Label(gre_frame, text="服务器GRE IP:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.gre_server_ip = ttk.Entry(gre_frame, width=30)
        self.gre_server_ip.insert(0, "10.0.0.1")
        self.gre_server_ip.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(gre_frame, text="提示: 服务器作为Hub，通常使用网段的第一个IP",
                 foreground="gray").grid(row=0, column=2, columnspan=2, sticky=tk.W, padx=5, pady=5)

        # GRE子网掩码
        ttk.Label(gre_frame, text="子网掩码:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.gre_netmask = ttk.Entry(gre_frame, width=30)
        self.gre_netmask.insert(0, "255.255.255.0")
        self.gre_netmask.grid(row=1, column=1, padx=5, pady=5)

        # GRE密钥
        ttk.Label(gre_frame, text="GRE密钥:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.gre_key = ttk.Entry(gre_frame, width=30)
        self.gre_key.insert(0, "123456")
        self.gre_key.grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(gre_frame, text="提示: 路由器端需要配置相同的GRE密钥",
                 foreground="gray").grid(row=2, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)

        # ===== IPSec Phase 1配置区域 =====
        phase1_frame = ttk.LabelFrame(self.scrollable_frame, text="IPSec Phase 1配置 (服务器端)", padding=10)
        phase1_frame.pack(fill=tk.X, padx=10, pady=5)

        # 协商模式
        ttk.Label(phase1_frame, text="协商模式:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.exchange_mode = ttk.Combobox(phase1_frame, width=27, state="readonly")
        self.exchange_mode.configure(values=["Main", "Aggressive"])
        self.exchange_mode.current(0)  # 默认Main
        self.exchange_mode.grid(row=0, column=1, padx=5, pady=5)

        # 本地ID类型
        ttk.Label(phase1_frame, text="本地ID类型:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.local_id_type = ttk.Combobox(phase1_frame, width=27, state="readonly")
        self.local_id_type.configure(values=["Default", "Address", "FQDN", "User FQDN"])
        self.local_id_type.current(0)  # 默认Default
        self.local_id_type.grid(row=0, column=3, padx=5, pady=5)

        # 加密算法
        ttk.Label(phase1_frame, text="加密算法:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.phase1_encryption = ttk.Combobox(phase1_frame, width=27, state="readonly")
        self.phase1_encryption.configure(values=[
            "AES256", "AES192", "AES128", "3DES", "DES", "BLOWFISH"
        ])
        self.phase1_encryption.current(0)
        self.phase1_encryption.grid(row=1, column=1, padx=5, pady=5)

        # 认证算法
        ttk.Label(phase1_frame, text="认证算法:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.phase1_hash = ttk.Combobox(phase1_frame, width=27, state="readonly")
        self.phase1_hash.configure(values=[
            "SHA2-256", "SHA2-384", "SHA2-512", "SHA1", "MD5"
        ])
        self.phase1_hash.current(0)
        self.phase1_hash.grid(row=1, column=3, padx=5, pady=5)

        # DH组
        ttk.Label(phase1_frame, text="DH组:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.phase1_dh = ttk.Combobox(phase1_frame, width=27, state="readonly")
        self.phase1_dh.configure(values=[
            "MODP2048-14", "MODP3072-15", "MODP4096-16",
            "MODP6144-17", "MODP8192-18", "MODP1536-5",
            "MODP1024-2", "ECP256-19", "ECP384-20", "ECP521-21"
        ])
        self.phase1_dh.current(1)  # 默认MODP3072-15
        self.phase1_dh.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(phase1_frame, text="提示: 路由器端需配置相同的协商模式、加密算法、认证算法和DH组",
                 foreground="gray").grid(row=3, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)

        # ===== IPSec Phase 2配置区域 =====
        phase2_frame = ttk.LabelFrame(self.scrollable_frame, text="IPSec Phase 2配置 (服务器端)", padding=10)
        phase2_frame.pack(fill=tk.X, padx=10, pady=5)

        # PSK密钥
        ttk.Label(phase2_frame, text="PSK密钥:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.psk_key = ttk.Entry(phase2_frame, width=30, show="*")
        self.psk_key.insert(0, "123456")
        self.psk_key.grid(row=0, column=1, padx=5, pady=5)

        # 显示密码按钮
        self.show_psk = tk.BooleanVar(value=False)
        ttk.Checkbutton(phase2_frame, text="显示密钥", variable=self.show_psk,
                       command=self.toggle_psk_visibility).grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)

        ttk.Label(phase2_frame, text="提示: 路由器端需配置相同的PSK密钥",
                 foreground="gray").grid(row=1, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)

        # SA算法
        ttk.Label(phase2_frame, text="SA算法:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.sa_algorithm = ttk.Combobox(phase2_frame, width=27, state="readonly")
        self.sa_algorithm.configure(values=[
            "AES256-SHA2-256", "AES256-SHA2-384", "AES256-SHA1",
            "AES192-SHA2-256", "AES192-SHA2-384", "AES192-SHA1",
            "AES128-SHA2-256", "AES128-SHA2-384", "AES128-SHA1",
            "3DES-SHA2-256", "3DES-SHA2-384", "3DES-SHA1"
        ])
        self.sa_algorithm.current(0)  # 默认AES256-SHA2-256
        self.sa_algorithm.grid(row=2, column=1, padx=5, pady=5)

        # PFS组
        ttk.Label(phase2_frame, text="PFS组:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)
        self.pfs_group = ttk.Combobox(phase2_frame, width=27, state="readonly")
        self.pfs_group.configure(values=[
            "NULL", "MODP1024-2", "MODP1536-5", "MODP2048-14",
            "MODP3072-15", "MODP4096-16", "ECP256-19", "ECP384-20"
        ])
        self.pfs_group.current(0)
        self.pfs_group.grid(row=2, column=3, padx=5, pady=5)

        # ===== 高级配置区域 =====
        advanced_frame = ttk.LabelFrame(self.scrollable_frame, text="高级配置 (服务器端)", padding=10)
        advanced_frame.pack(fill=tk.X, padx=10, pady=5)

        # NAT穿透
        self.nat_traversal = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="启用NAT穿透 (NAT-T) - 如果服务器在NAT后面，必须启用",
                       variable=self.nat_traversal).grid(row=0, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)

        # IKE生存时间
        ttk.Label(advanced_frame, text="IKE生存时间(秒):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.ike_lifetime = ttk.Entry(advanced_frame, width=20)
        self.ike_lifetime.insert(0, "10800")
        self.ike_lifetime.grid(row=1, column=1, padx=5, pady=5)

        # SA生存时间
        ttk.Label(advanced_frame, text="SA生存时间(秒):").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.sa_lifetime = ttk.Entry(advanced_frame, width=20)
        self.sa_lifetime.insert(0, "3600")
        self.sa_lifetime.grid(row=1, column=3, padx=5, pady=5)

        # DPD配置
        ttk.Label(advanced_frame, text="DPD间隔(秒):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.dpd_delay = ttk.Entry(advanced_frame, width=20)
        self.dpd_delay.insert(0, "30")
        self.dpd_delay.grid(row=2, column=1, padx=5, pady=5)

        # ===== 操作按钮区域 =====
        button_frame = ttk.Frame(self.scrollable_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # 第一行按钮
        button_row1 = ttk.Frame(button_frame)
        button_row1.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(button_row1, text="1. 生成并预览配置",
                  command=self.preview_config, width=25).pack(side=tk.LEFT, padx=5)

        self.apply_btn = ttk.Button(button_row1, text="2. 应用到服务器",
                                    command=self.apply_config, width=20, state='disabled')
        self.apply_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_row1, text="重启DMVPN服务",
                  command=self.restart_racoon, width=18).pack(side=tk.LEFT, padx=5)

        # 第二行按钮
        button_row2 = ttk.Frame(button_frame)
        button_row2.pack(fill=tk.X)

        ttk.Button(button_row2, text="查看当前服务器配置",
                  command=self.view_config, width=22).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_row2, text="对比配置差异",
                  command=self.compare_config, width=18).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_row2, text="清空日志",
                  command=self.clear_log, width=15).pack(side=tk.LEFT, padx=5)

        # 存储预览的配置
        self.preview_config_content = None

        # ===== 日志输出区域 =====
        log_frame = ttk.LabelFrame(self.scrollable_frame, text="操作日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置日志颜色标签
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("info", foreground="black")

        # 初始提示
        self.log("欢迎使用DMVPN服务器配置工具 v2.2")
        self.log("提示: 本工具仅配置服务器端，路由器端请在路由器Web界面配置", "WARNING")
        self.log("=" * 60)

    def toggle_psk_visibility(self):
        """切换PSK密钥显示/隐藏"""
        if self.show_psk.get():
            self.psk_key.config(show="")
        else:
            self.psk_key.config(show="*")

    def toggle_ip_list(self):
        """切换IP列表的启用/禁用状态"""
        if self.allow_all_var.get():
            # 允许所有IP，禁用列表
            self.router_ip_input.config(state='disabled')
            self.router_ip_listbox.config(state='disabled')
        else:
            # 限制特定IP，启用列表
            self.router_ip_input.config(state='normal')
            self.router_ip_listbox.config(state='normal')

    def add_router_ip(self):
        """添加路由器IP到列表"""
        ip = self.router_ip_input.get().strip()
        if not ip:
            messagebox.showwarning("警告", "请输入IP地址")
            return

        # 简单的IP格式验证
        import re
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            messagebox.showerror("错误", "IP地址格式不正确")
            return

        # 检查是否已存在
        existing_ips = self.router_ip_listbox.get(0, tk.END)
        if ip in existing_ips:
            messagebox.showwarning("警告", "该IP已存在")
            return

        # 添加到列表
        self.router_ip_listbox.insert(tk.END, ip)
        self.router_ip_input.delete(0, tk.END)
        self.log(f"添加路由器IP: {ip}", "SUCCESS")

    def remove_router_ip(self):
        """从列表中删除选中的IP"""
        selection = self.router_ip_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的IP")
            return

        ip = self.router_ip_listbox.get(selection[0])
        self.router_ip_listbox.delete(selection[0])
        self.log(f"删除路由器IP: {ip}", "INFO")

    def get_router_ips(self):
        """获取所有路由器IP列表"""
        if self.allow_all_var.get():
            return []  # 空列表表示允许所有IP
        else:
            return list(self.router_ip_listbox.get(0, tk.END))

    def log(self, message: str, level: str = "INFO"):
        """输出日志到界面"""
        self.log_text.configure(state='normal')
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")

        # 根据级别设置颜色
        if level == "ERROR":
            tag = "error"
            prefix = "❌"
        elif level == "SUCCESS":
            tag = "success"
            prefix = "✅"
        elif level == "WARNING":
            tag = "warning"
            prefix = "⚠️"
        else:
            tag = "info"
            prefix = "ℹ️"

        self.log_text.insert(tk.END, f"[{timestamp}] {prefix} {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
        self.root.update()

    def clear_log(self):
        """清空日志"""
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        self.log("日志已清空")

    def test_connection(self):
        """测试SSH连接"""
        def _test():
            try:
                self.log("正在测试SSH连接...")
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                ssh.connect(
                    hostname=self.ssh_ip.get(),
                    port=int(self.ssh_port.get()),
                    username=self.ssh_user.get(),
                    password=self.ssh_password.get(),
                    timeout=10
                )

                self.log("SSH连接成功！", "SUCCESS")
                ssh.close()
                messagebox.showinfo("成功", "SSH连接测试成功！")

            except Exception as e:
                self.log(f"SSH连接失败: {str(e)}", "ERROR")
                messagebox.showerror("错误", f"SSH连接失败:\n{str(e)}")

        threading.Thread(target=_test, daemon=True).start()

    def connect_ssh(self) -> bool:
        """连接SSH服务器"""
        try:
            if self.ssh_client:
                self.ssh_client.close()

            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.ssh_client.connect(
                hostname=self.ssh_ip.get(),
                port=int(self.ssh_port.get()),
                username=self.ssh_user.get(),
                password=self.ssh_password.get(),
                timeout=10
            )

            self.log("SSH连接成功", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"SSH连接失败: {str(e)}", "ERROR")
            return False

    def run_ssh_command(self, command: str, use_sudo: bool = True, timeout: int = 30) -> tuple:
        """执行SSH命令

        Args:
            command: 要执行的命令
            use_sudo: 是否使用sudo
            timeout: 命令超时时间（秒）

        Returns:
            (stdout, stderr, exit_code) 元组
        """
        try:
            if use_sudo:
                # 使用stdin传递密码更安全
                full_command = f"sudo -S {command}"
            else:
                full_command = command

            # 🔧 修复关键：使用get_pty=True为命令分配伪终端
            # 这对于init.d服务脚本和某些系统命令是必需的
            stdin, stdout, stderr = self.ssh_client.exec_command(
                full_command,
                get_pty=True,  # ✅ 分配伪终端
                timeout=timeout  # ✅ 设置超时
            )

            if use_sudo:
                stdin.write(self.ssh_password.get() + '\n')
                stdin.flush()

            # 等待命令完成并读取输出
            out = stdout.read().decode('utf-8', errors='ignore')
            err = stderr.read().decode('utf-8', errors='ignore')

            # 获取退出码
            exit_code = stdout.channel.recv_exit_status()

            # 记录命令执行结果
            if exit_code != 0:
                self.log(f"命令退出码: {exit_code}", "WARNING")

            # 如果有错误输出，记录到日志（排除sudo提示和伪终端输出）
            if err:
                err_lines = [line for line in err.split('\n')
                           if line.strip() and not line.startswith('[sudo]')]
                if err_lines:
                    self.log(f"命令错误输出: {' '.join(err_lines)}", "WARNING")

            return out, err, exit_code

        except Exception as e:
            self.log(f"命令执行异常: {str(e)}", "ERROR")
            return "", str(e), -1

    def generate_racoon_config(self) -> str:
        """生成Racoon配置文件内容"""

        # 协商模式
        exchange_mode_map = {
            "Main": "main",
            "Aggressive": "aggressive"
        }
        exchange_mode = exchange_mode_map.get(self.exchange_mode.get(), "main")

        # 本地ID类型
        local_id_map = {
            "Default": "address",
            "Address": "address",
            "FQDN": "fqdn",
            "User FQDN": "user_fqdn"
        }
        local_id_type = local_id_map.get(self.local_id_type.get(), "address")

        # 解析DH组
        dh_group_raw = self.phase1_dh.get()

        # DH组映射表 (UI显示 -> Racoon配置)
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
        dh_group = dh_group_map.get(dh_group_raw, "modp3072")

        # 解析加密算法
        encryption_map = {
            "AES256": "aes 256",
            "AES192": "aes 192",
            "AES128": "aes 128",
            "3DES": "3des",
            "DES": "des",
            "BLOWFISH": "blowfish 448"
        }
        encryption = encryption_map.get(self.phase1_encryption.get(), "aes 256")

        # 解析认证算法
        hash_map = {
            "SHA2-256": "sha256",
            "SHA2-384": "sha384",
            "SHA2-512": "sha512",
            "SHA1": "sha1",
            "MD5": "md5"
        }
        hash_alg = hash_map.get(self.phase1_hash.get(), "sha256")

        # 解析Phase 2 SA算法
        sa_alg = self.sa_algorithm.get()
        if "AES256" in sa_alg:
            phase2_enc = "aes 256"
        elif "AES192" in sa_alg:
            phase2_enc = "aes 192"
        elif "AES128" in sa_alg:
            phase2_enc = "aes 128"
        else:
            phase2_enc = "3des"

        if "SHA2-256" in sa_alg:
            phase2_hash = "hmac_sha256"
        elif "SHA2-384" in sa_alg:
            phase2_hash = "hmac_sha384"
        else:
            phase2_hash = "hmac_sha1"

        # NAT穿透配置
        nat_t = "on" if self.nat_traversal.get() else "off"

        # PFS组配置
        pfs_val = self.pfs_group.get()
        if pfs_val == "NULL":
            pfs_config = None  # 不配置PFS
        else:
            # PFS组也使用相同的映射表
            pfs_group_map = {
                "MODP1024-2": "modp1024",
                "MODP1536-5": "modp1536",
                "MODP2048-14": "modp2048",
                "MODP3072-15": "modp3072",
                "MODP4096-16": "modp4096",
                "ECP256-19": "ecp_256",
                "ECP384-20": "ecp_384",
                "ECP521-21": "ecp_521"
            }
            pfs_config = pfs_group_map.get(pfs_val, pfs_val.split('-')[0].lower())

        # 获取路由器IP列表
        router_ips = self.get_router_ips()

        # 生成配置文件头部
        config = f"""# Racoon configuration for DMVPN Server
# Generated by DMVPN Server Config Tool v2.1
# Date: {__import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

path pre_shared_key "/etc/racoon/psk.txt";
path certificate "/etc/racoon/certs";

log info;

# Note: listen block removed - Racoon will auto-listen on all interfaces
# This fixes the port binding issue

"""

        # 根据是否限制IP生成不同的remote配置
        if not router_ips:
            # 允许所有IP - anonymous模式
            config += f"""# Accept connections from any router (anonymous mode)
remote anonymous {{
    exchange_mode {exchange_mode};
    my_identifier {local_id_type};
    peers_identifier address;

    nat_traversal {nat_t};

    proposal {{
        encryption_algorithm {encryption};
        hash_algorithm {hash_alg};
        authentication_method pre_shared_key;
        dh_group {dh_group};
        lifetime time {self.ike_lifetime.get()} sec;
    }}

    dpd_delay {self.dpd_delay.get()};
    dpd_retry 5;
    dpd_maxfail 5;
}}
"""
        else:
            # 限制特定IP
            for router_ip in router_ips:
                config += f"""# Router: {router_ip}
remote {router_ip} {{
    exchange_mode {exchange_mode};
    my_identifier {local_id_type};
    peers_identifier address;

    nat_traversal {nat_t};

    proposal {{
        encryption_algorithm {encryption};
        hash_algorithm {hash_alg};
        authentication_method pre_shared_key;
        dh_group {dh_group};
        lifetime time {self.ike_lifetime.get()} sec;
    }}

    dpd_delay {self.dpd_delay.get()};
    dpd_retry 5;
    dpd_maxfail 5;
}}

"""

        # 添加sainfo配置
        pfs_line = f"    pfs_group {pfs_config};" if pfs_config else "    # pfs_group disabled"

        config += f"""sainfo anonymous {{
{pfs_line}
    lifetime time {self.sa_lifetime.get()} sec;

    encryption_algorithm {phase2_enc};
    authentication_algorithm {phase2_hash};
    compression_algorithm deflate;
}}
"""
        return config

    def apply_config(self):
        """应用配置到服务器"""
        def _apply():
            try:
                # 检查是否已生成预览配置
                if not self.preview_config_content:
                    self.log("请先点击 '1. 生成并预览配置'", "ERROR")
                    messagebox.showerror("错误", "请先生成并预览配置！\n\n点击 '1. 生成并预览配置' 按钮，确认无误后再应用。")
                    return

                # 二次确认
                result = messagebox.askyesno(
                    "确认应用配置",
                    "即将应用配置到服务器，这将：\n\n"
                    "1. 备份现有配置\n"
                    "2. 写入新配置文件\n"
                    "3. 更新PSK密钥\n"
                    "4. 配置GRE隧道\n"
                    "5. 重启DMVPN服务(dmvpn.sh)\n\n"
                    "确认要继续吗？",
                    icon='warning'
                )

                if not result:
                    self.log("用户取消操作", "WARNING")
                    return

                self.log("=" * 60)
                self.log("开始应用DMVPN服务器配置...")

                # 连接SSH
                if not self.connect_ssh():
                    return

                # 1. 备份现有配置
                self.log("备份现有配置...")
                timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
                self.run_ssh_command(f"cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.bak.{timestamp}")
                self.run_ssh_command(f"cp /etc/racoon/psk.txt /etc/racoon/psk.txt.bak.{timestamp}")
                self.log(f"配置备份完成: racoon.conf.bak.{timestamp}", "SUCCESS")

                # 2. 使用预览的配置
                self.log("使用预览的配置...")
                racoon_config = self.preview_config_content

                # 3. 写入配置文件
                self.log("写入Racoon配置文件...")
                config_escaped = racoon_config.replace("'", "'\\''")
                self.run_ssh_command(f"echo '{config_escaped}' > /tmp/racoon.conf")
                self.run_ssh_command("cp /tmp/racoon.conf /etc/racoon/racoon.conf")
                self.run_ssh_command("chown root:root /etc/racoon/racoon.conf")
                self.run_ssh_command("chmod 644 /etc/racoon/racoon.conf")

                # 4. 更新PSK密钥
                self.log("更新PSK密钥...")
                psk_content = f"* {self.psk_key.get()}\n"
                self.run_ssh_command(f"echo '{psk_content}' > /tmp/psk.txt")
                self.run_ssh_command("cp /tmp/psk.txt /etc/racoon/psk.txt")
                self.run_ssh_command("chown root:root /etc/racoon/psk.txt")
                self.run_ssh_command("chmod 600 /etc/racoon/psk.txt")

                # 5. 配置GRE隧道
                self.log("配置GRE隧道...")
                server_ip = self.ssh_ip.get()
                gre_commands = f"""
                ip tunnel del gre1 2>/dev/null || true
                ip tunnel add gre1 mode gre remote any local {server_ip} key {self.gre_key.get()}
                ip addr flush dev gre1
                ip addr add {self.gre_server_ip.get()}/24 dev gre1
                ip link set gre1 up
                """
                self.run_ssh_command(gre_commands)

                # 6. 重启DMVPN服务（Racoon + dmvpn.sh）
                self.log("重启DMVPN服务（完整启动流程）...")

                # 先停止所有服务
                self.log("  - 停止 Racoon 服务", "INFO")
                self.run_ssh_command("/etc/init.d/racoon stop")
                __import__('time').sleep(2)

                self.log("  - 停止 DMVPN 服务（清空IPsec策略）", "INFO")
                self.run_ssh_command("cd /home && sh dmvpn.sh stop")
                __import__('time').sleep(2)

                # 启动所有服务
                self.log("  - 启动 Racoon 服务", "INFO")
                self.run_ssh_command("/etc/init.d/racoon start")
                __import__('time').sleep(2)

                self.log("  - 启动 DMVPN 服务（加载IPsec策略 + GRE + NHRP）", "INFO")
                self.run_ssh_command("cd /home && sh dmvpn.sh start")
                __import__('time').sleep(3)

                # 7. 验证配置
                self.log("验证配置...")

                # 检查Racoon进程
                out, _ = self.run_ssh_command("ps aux | grep '[r]acoon -f'", use_sudo=False)
                if "racoon -f" in out:
                    self.log("  ✓ Racoon进程运行正常", "SUCCESS")
                else:
                    self.log("  ✗ Racoon进程未运行", "ERROR")

                # 检查GRE隧道
                out, _ = self.run_ssh_command("ip addr show gre1", use_sudo=False)
                if "10.0.0.1" in out and "UP" in out:
                    self.log("  ✓ GRE隧道配置正确", "SUCCESS")
                else:
                    self.log("  ✗ GRE隧道配置异常", "ERROR")

                # 检查OpenNHRP
                out, _ = self.run_ssh_command("ps aux | grep '[o]pennhrp'", use_sudo=False)
                if "opennhrp" in out:
                    self.log("  ✓ OpenNHRP运行正常", "SUCCESS")
                else:
                    self.log("  ✗ OpenNHRP未运行", "ERROR")

                # 检查IPsec策略（最关键）
                out, _ = self.run_ssh_command("setkey -DP", use_sudo=False)
                if "esp/transport" in out and "0.0.0.0/0 0.0.0.0/0 gre" in out:
                    self.log("  ✓ IPsec策略已加载（GRE流量加密）", "SUCCESS")
                else:
                    self.log("  ✗ IPsec策略未加载！", "ERROR")
                    self.log("    这是导致连接失败的最常见原因", "WARNING")

                __import__('time').sleep(3)
                out, err = self.run_ssh_command("systemctl status racoon", use_sudo=False)
                if "active (running)" in out:
                    self.log("Racoon服务运行正常 ✓", "SUCCESS")
                else:
                    self.log("警告: Racoon服务状态异常", "WARNING")
                    self.log("服务状态:", "INFO")
                    for line in out.split('\n')[:15]:
                        if line.strip():
                            self.log(f"  {line}", "INFO")

                    # 检查配置文件语法
                    self.log("-" * 60, "INFO")
                    self.log("正在检查配置文件语法...", "INFO")
                    out, err = self.run_ssh_command("racoon -C -f /etc/racoon/racoon.conf")
                    if err:
                        self.log("配置文件语法检查结果:", "ERROR")
                        for line in err.split('\n')[:10]:
                            if line.strip():
                                self.log(f"  {line}", "ERROR")
                    else:
                        self.log("配置文件语法检查通过", "SUCCESS")

                    # 查看系统日志
                    self.log("-" * 60, "INFO")
                    self.log("正在查看系统日志...", "INFO")
                    out, err = self.run_ssh_command("journalctl -u racoon -n 20 --no-pager")
                    if out:
                        self.log("最近的Racoon日志:", "INFO")
                        for line in out.split('\n')[-15:]:
                            if line.strip():
                                self.log(f"  {line}", "INFO")

                # 8. 显示GRE状态
                out, _ = self.run_ssh_command("ip addr show gre1", use_sudo=False)
                if "gre1" in out:
                    self.log("GRE隧道配置成功", "SUCCESS")

                self.log("=" * 60)
                self.log("配置应用完成！", "SUCCESS")
                self.log("", "INFO")
                self.log("下一步: 在路由器Web界面配置DMVPN参数 (必须与服务器端匹配):", "WARNING")
                self.log(f"  - Hub地址: {server_ip}", "INFO")
                self.log(f"  - GRE密钥: {self.gre_key.get()}", "INFO")
                self.log(f"  - 协商模式: {self.exchange_mode.get()}", "INFO")
                self.log(f"  - 本地ID类型: {self.local_id_type.get()}", "INFO")
                self.log(f"  - 加密算法: {self.phase1_encryption.get()}", "INFO")
                self.log(f"  - 认证算法: {self.phase1_hash.get()}", "INFO")
                self.log(f"  - DH组: {self.phase1_dh.get()}", "INFO")
                self.log(f"  - PSK密钥: {'*' * len(self.psk_key.get())}", "INFO")

                # 显示路由器IP配置信息
                router_ips = self.get_router_ips()
                if not router_ips:
                    self.log("  - 允许连接的路由器: 任意IP (anonymous模式)", "INFO")
                else:
                    self.log(f"  - 允许连接的路由器: {len(router_ips)}个IP地址", "INFO")
                    for ip in router_ips:
                        self.log(f"    • {ip}", "INFO")

                messagebox.showinfo("成功", "DMVPN服务器配置已成功应用！\n\n请在路由器Web界面配置相同的参数。")

            except Exception as e:
                self.log(f"配置应用失败: {str(e)}", "ERROR")
                messagebox.showerror("错误", f"配置应用失败:\n{str(e)}")

            finally:
                if self.ssh_client:
                    self.ssh_client.close()
                    self.ssh_client = None

        threading.Thread(target=_apply, daemon=True).start()

    def restart_racoon(self):
        """重启DMVPN服务"""
        def _restart():
            try:
                self.log("=" * 60)
                self.log("正在重启DMVPN服务...")

                if not self.connect_ssh():
                    self.log("SSH连接失败，无法重启服务", "ERROR")
                    messagebox.showerror("错误", "SSH连接失败，请检查连接配置")
                    return

                # Stop DMVPN
                self.log("停止DMVPN服务（包括清空IPsec策略）...")
                self.run_ssh_command("cd /home && sh dmvpn.sh stop")

                __import__('time').sleep(2)

                # Start DMVPN
                self.log("启动DMVPN服务（包括加载IPsec策略）...")
                self.run_ssh_command("cd /home && sh dmvpn.sh start")

                self.log("等待服务启动...")
                __import__('time').sleep(3)

                # 检查服务状态（增强验证）
                self.log("\n检查服务组件状态:")

                # 1. Racoon
                out, _ = self.run_ssh_command("ps aux | grep '[r]acoon -f'", use_sudo=False)
                if "racoon -f" in out:
                    self.log("  ✓ Racoon进程运行正常", "SUCCESS")
                else:
                    self.log("  ✗ Racoon进程未运行", "ERROR")

                # 2. GRE隧道
                out, _ = self.run_ssh_command("ip addr show gre1 2>&1", use_sudo=False)
                if "10.0.0.1" in out:
                    self.log("  ✓ GRE隧道已创建 (10.0.0.1)", "SUCCESS")
                else:
                    self.log("  ✗ GRE隧道未创建", "ERROR")

                # 3. OpenNHRP
                out, _ = self.run_ssh_command("ps aux | grep '[o]pennhrp'", use_sudo=False)
                if "opennhrp" in out:
                    self.log("  ✓ OpenNHRP运行正常", "SUCCESS")
                else:
                    self.log("  ✗ OpenNHRP未运行", "ERROR")

                # 4. IPsec策略（最关键！）
                out, _ = self.run_ssh_command("setkey -DP 2>&1", use_sudo=False)
                if "esp/transport" in out and "gre" in out:
                    self.log("  ✓ IPsec策略已加载（GRE流量将被加密）", "SUCCESS")
                    self.log("    这是DMVPN工作的关键！", "INFO")
                else:
                    self.log("  ✗ IPsec策略未加载！", "ERROR")
                    self.log("    警告: 没有IPsec策略，路由器无法连接", "WARNING")

                __import__('time').sleep(2)

                # 检查服务状态
                out, err = self.run_ssh_command("systemctl status racoon", use_sudo=False)

                if "active (running)" in out:
                    self.log("Racoon服务重启成功 ✓", "SUCCESS")
                    self.log("=" * 60)
                    messagebox.showinfo("成功", "Racoon服务已成功重启")
                else:
                    self.log("Racoon服务状态异常", "ERROR")
                    self.log("服务状态输出:", "INFO")
                    # 输出前15行状态信息
                    for line in out.split('\n')[:15]:
                        if line.strip():
                            self.log(f"  {line}", "INFO")

                    # 检查配置文件语法
                    self.log("-" * 60, "INFO")
                    self.log("正在检查配置文件语法...", "INFO")
                    out, err = self.run_ssh_command("racoon -C -f /etc/racoon/racoon.conf")
                    if err:
                        self.log("配置文件语法检查结果:", "ERROR")
                        for line in err.split('\n')[:10]:
                            if line.strip():
                                self.log(f"  {line}", "ERROR")
                    else:
                        self.log("配置文件语法检查通过", "SUCCESS")

                    # 查看系统日志中的racoon错误
                    self.log("-" * 60, "INFO")
                    self.log("正在查看系统日志...", "INFO")
                    out, err = self.run_ssh_command("journalctl -u racoon -n 20 --no-pager")
                    if out:
                        self.log("最近的Racoon日志:", "INFO")
                        for line in out.split('\n')[-15:]:
                            if line.strip():
                                self.log(f"  {line}", "INFO")

                    self.log("=" * 60)
                    messagebox.showerror("错误", "Racoon服务重启失败\n请查看日志了解详情")

            except Exception as e:
                self.log(f"重启过程异常: {str(e)}", "ERROR")
                self.log("=" * 60)
                messagebox.showerror("错误", f"重启失败:\n{str(e)}")

            finally:
                if self.ssh_client:
                    self.ssh_client.close()
                    self.ssh_client = None

        threading.Thread(target=_restart, daemon=True).start()

    def preview_config(self):
        """生成并预览配置"""
        try:
            self.log("=" * 60)
            self.log("正在生成配置预览...")

            # 验证必填参数
            if not self.gre_server_ip.get().strip():
                messagebox.showerror("错误", "请输入GRE服务器IP")
                return

            if not self.gre_key.get().strip():
                messagebox.showerror("错误", "请输入GRE密钥")
                return

            if not self.psk_key.get().strip():
                messagebox.showerror("错误", "请输入PSK密钥")
                return

            # 如果不是anonymous模式，检查路由器IP列表
            if not self.allow_all_var.get():
                router_ips = self.get_router_ips()
                if not router_ips:
                    messagebox.showwarning("警告", "未添加路由器IP，将使用anonymous模式（允许任意IP连接）")

            # 生成配置
            config_content = self.generate_racoon_config()

            # 保存配置内容
            self.preview_config_content = config_content

            # 创建新窗口显示配置
            preview_window = tk.Toplevel(self.root)
            preview_window.title("配置预览")
            preview_window.geometry("900x650")

            # 添加说明标签
            info_frame = ttk.Frame(preview_window)
            info_frame.pack(fill=tk.X, padx=10, pady=10)

            ttk.Label(info_frame, text="请仔细检查以下配置，确认无误后点击主窗口的 '2. 应用到服务器' 按钮",
                     foreground="blue", font=("", 10, "bold")).pack()

            # 配置内容显示区域
            text_frame = ttk.Frame(preview_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

            text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Courier New", 9))
            text.pack(fill=tk.BOTH, expand=True)
            text.insert(1.0, config_content)
            text.configure(state='disabled')

            # 按钮区域
            btn_frame = ttk.Frame(preview_window)
            btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

            def copy_to_clipboard():
                preview_window.clipboard_clear()
                preview_window.clipboard_append(config_content)
                messagebox.showinfo("提示", "配置已复制到剪贴板")

            ttk.Button(btn_frame, text="复制到剪贴板", command=copy_to_clipboard).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="关闭", command=preview_window.destroy).pack(side=tk.LEFT, padx=5)

            # 启用应用按钮
            self.apply_btn.config(state='normal')

            self.log("配置预览生成完成", "SUCCESS")
            self.log("提示: 配置已生成，您可以点击 '2. 应用到服务器' 按钮应用配置", "INFO")
            self.log("=" * 60)

        except Exception as e:
            self.log(f"生成配置失败: {str(e)}", "ERROR")
            messagebox.showerror("错误", f"生成配置失败:\n{str(e)}")

    def compare_config(self):
        """对比新旧配置差异"""
        def _compare():
            try:
                self.log("=" * 60)
                self.log("正在对比配置差异...")

                # 先生成新配置
                if not self.preview_config_content:
                    self.log("请先点击 '1. 生成并预览配置'", "WARNING")
                    messagebox.showwarning("警告", "请先生成新配置！")
                    return

                # 连接SSH读取当前配置
                if not self.connect_ssh():
                    return

                self.log("正在读取服务器当前配置...")
                old_config, _ = self.run_ssh_command("cat /etc/racoon/racoon.conf", use_sudo=False)

                if not old_config.strip():
                    self.log("警告: 服务器上没有找到配置文件", "WARNING")
                    old_config = "# 服务器上没有配置文件\n"

                # 创建对比窗口
                compare_window = tk.Toplevel(self.root)
                compare_window.title("配置差异对比")
                compare_window.geometry("1200x700")

                # 创建左右分栏
                main_frame = ttk.Frame(compare_window)
                main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

                # 左侧：当前配置
                left_frame = ttk.LabelFrame(main_frame, text="服务器当前配置", padding=5)
                left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

                left_text = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, font=("Courier New", 9))
                left_text.pack(fill=tk.BOTH, expand=True)
                left_text.insert(1.0, old_config)
                left_text.configure(state='disabled')

                # 右侧：新配置
                right_frame = ttk.LabelFrame(main_frame, text="新生成的配置", padding=5)
                right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

                right_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, font=("Courier New", 9))
                right_text.pack(fill=tk.BOTH, expand=True)
                right_text.insert(1.0, self.preview_config_content)
                right_text.configure(state='disabled')

                # 底部提示
                tip_frame = ttk.Frame(compare_window)
                tip_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

                ttk.Label(tip_frame, text="提示: 左侧为服务器当前配置，右侧为新生成的配置。请仔细对比差异。",
                         foreground="blue").pack()

                ttk.Button(tip_frame, text="关闭", command=compare_window.destroy).pack(pady=5)

                self.log("配置对比完成", "SUCCESS")
                self.log("=" * 60)

            except Exception as e:
                self.log(f"对比配置失败: {str(e)}", "ERROR")
                messagebox.showerror("错误", f"对比失败:\n{str(e)}")

            finally:
                if self.ssh_client:
                    self.ssh_client.close()
                    self.ssh_client = None

        threading.Thread(target=_compare, daemon=True).start()

    def view_config(self):
        """查看当前配置"""
        def _view():
            try:
                self.log("正在读取当前配置...")

                if not self.connect_ssh():
                    return

                # 读取Racoon配置
                out, _ = self.run_ssh_command("cat /etc/racoon/racoon.conf", use_sudo=False)

                # 创建新窗口显示配置
                config_window = tk.Toplevel(self.root)
                config_window.title("当前Racoon配置")
                config_window.geometry("800x600")

                text = scrolledtext.ScrolledText(config_window, wrap=tk.WORD)
                text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                text.insert(1.0, out)
                text.configure(state='disabled')

                self.log("配置读取成功", "SUCCESS")

            except Exception as e:
                self.log(f"读取配置失败: {str(e)}", "ERROR")

            finally:
                if self.ssh_client:
                    self.ssh_client.close()
                    self.ssh_client = None

        threading.Thread(target=_view, daemon=True).start()


def main():
    """主函数"""
    root = tk.Tk()
    app = DMVPNServerConfigGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
