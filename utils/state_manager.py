# -*- coding: utf-8 -*-
"""
测试状态管理器
负责保存和恢复测试前后的PC网卡状态和路由器配置状态
"""
import subprocess
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class NetworkAdapterState:
    """PC网卡状态"""
    adapter_name: str
    dhcp_enabled: bool
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    default_gateway: Optional[str] = None
    dns_servers: list = None

    def __post_init__(self):
        if self.dns_servers is None:
            self.dns_servers = []


@dataclass
class RouterState:
    """路由器配置状态（可扩展）"""
    router_ip: str
    # 这里可以添加需要保存的路由器配置项
    # 例如：wan_config, cellular_config, mqtt_config等
    config_snapshot: Dict[str, Any] = None

    def __post_init__(self):
        if self.config_snapshot is None:
            self.config_snapshot = {}


class StateManager:
    """测试状态管理器"""

    def __init__(self):
        """初始化状态管理器"""
        self.pc_adapter_state: Optional[NetworkAdapterState] = None
        self.router_state: Optional[RouterState] = None

    # ==================== PC网卡状态管理 ====================

    def save_pc_adapter_state(self, adapter_name: str = "TEST") -> bool:
        """
        保存PC网卡当前状态

        Args:
            adapter_name: 网卡名称

        Returns:
            bool: 保存是否成功
        """
        print(f"\n{'='*70}")
        print(f"保存PC网卡状态: {adapter_name}")
        print(f"{'='*70}")

        try:
            # 使用PowerShell获取网卡详细信息
            ps_cmd = f'''
            $adapter = Get-NetIPConfiguration -InterfaceAlias "{adapter_name}" -ErrorAction SilentlyContinue
            if ($adapter) {{
                $ipv4 = $adapter.IPv4Address
                $ipv4DefaultGateway = $adapter.IPv4DefaultGateway
                $dnsServer = $adapter.DNSServer | Where-Object {{$_.AddressFamily -eq 2}}

                # 检查是否启用DHCP
                $dhcpEnabled = (Get-NetIPInterface -InterfaceAlias "{adapter_name}" -AddressFamily IPv4).Dhcp

                # 构造JSON输出
                $state = @{{
                    "dhcp_enabled" = $dhcpEnabled
                    "ip_address" = if ($ipv4) {{ $ipv4.IPAddress }} else {{ $null }}
                    "subnet_mask" = if ($ipv4) {{ $ipv4.PrefixLength }} else {{ $null }}
                    "default_gateway" = if ($ipv4DefaultGateway) {{ $ipv4DefaultGateway.NextHop }} else {{ $null }}
                    "dns_servers" = if ($dnsServer) {{ $dnsServer.ServerAddresses }} else {{ @() }}
                }}

                $state | ConvertTo-Json -Compress
            }}
            '''

            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0 and result.stdout.strip():
                state_data = json.loads(result.stdout.strip())

                # 转换子网掩码（从前缀长度到点分十进制）
                prefix_length = state_data.get('subnet_mask')
                if prefix_length:
                    subnet_mask = self._prefix_to_netmask(int(prefix_length))
                else:
                    subnet_mask = None

                self.pc_adapter_state = NetworkAdapterState(
                    adapter_name=adapter_name,
                    dhcp_enabled=state_data.get('dhcp_enabled', 'Enabled') == 'Enabled',
                    ip_address=state_data.get('ip_address'),
                    subnet_mask=subnet_mask,
                    default_gateway=state_data.get('default_gateway'),
                    dns_servers=state_data.get('dns_servers', [])
                )

                print(f"  网卡名称: {adapter_name}")
                print(f"  DHCP状态: {'启用' if self.pc_adapter_state.dhcp_enabled else '禁用'}")
                print(f"  IP地址: {self.pc_adapter_state.ip_address or '未配置'}")
                print(f"  子网掩码: {self.pc_adapter_state.subnet_mask or '未配置'}")
                print(f"  默认网关: {self.pc_adapter_state.default_gateway or '未配置'}")
                print(f"  DNS服务器: {', '.join(self.pc_adapter_state.dns_servers) if self.pc_adapter_state.dns_servers else '未配置'}")
                print(f"✅ PC网卡状态保存成功\n")

                return True
            else:
                print(f"❌ 获取网卡信息失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 保存PC网卡状态失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def restore_pc_adapter_state(self) -> bool:
        """
        恢复PC网卡到之前保存的状态

        Returns:
            bool: 恢复是否成功
        """
        if not self.pc_adapter_state:
            print("⚠️  没有保存的PC网卡状态，跳过恢复")
            return True

        print(f"\n{'='*70}")
        print(f"恢复PC网卡状态: {self.pc_adapter_state.adapter_name}")
        print(f"{'='*70}")

        try:
            adapter_name = self.pc_adapter_state.adapter_name

            if self.pc_adapter_state.dhcp_enabled:
                # 恢复为DHCP模式
                print(f"  恢复网卡为DHCP模式...")

                # 设置IP为DHCP
                result = subprocess.run(
                    ["netsh", "interface", "ip", "set", "address",
                     f"name={adapter_name}", "source=dhcp"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                    if "已在此接口上启用 DHCP" not in error_msg:
                        print(f"  ⚠️  设置DHCP时出现警告: {error_msg}")

                # 设置DNS为DHCP
                subprocess.run(
                    ["netsh", "interface", "ip", "set", "dns",
                     f"name={adapter_name}", "source=dhcp"],
                    capture_output=True,
                    timeout=10
                )

                print(f"  ✅ 已恢复为DHCP模式")

            else:
                # 恢复为静态IP模式
                print(f"  恢复网卡为静态IP模式...")

                if self.pc_adapter_state.ip_address:
                    ip = self.pc_adapter_state.ip_address
                    subnet = self.pc_adapter_state.subnet_mask or "255.255.255.0"
                    gateway = self.pc_adapter_state.default_gateway

                    if gateway:
                        cmd = f'netsh interface ip set address name="{adapter_name}" static {ip} {subnet} {gateway}'
                    else:
                        cmd = f'netsh interface ip set address name="{adapter_name}" static {ip} {subnet}'

                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

                    if result.returncode == 0:
                        print(f"  ✅ 已恢复静态IP: {ip}")
                    else:
                        print(f"  ⚠️  恢复静态IP时出现警告: {result.stderr}")

                    # 恢复DNS
                    if self.pc_adapter_state.dns_servers:
                        for i, dns in enumerate(self.pc_adapter_state.dns_servers):
                            if i == 0:
                                # 设置首选DNS
                                subprocess.run(
                                    ["netsh", "interface", "ip", "set", "dns",
                                     f"name={adapter_name}", "static", dns],
                                    capture_output=True,
                                    timeout=10
                                )
                            else:
                                # 添加备用DNS
                                subprocess.run(
                                    ["netsh", "interface", "ip", "add", "dns",
                                     f"name={adapter_name}", dns, f"index={i+1}"],
                                    capture_output=True,
                                    timeout=10
                                )
                        print(f"  ✅ 已恢复DNS服务器")
                else:
                    print(f"  ⚠️  没有保存的IP地址信息，无法恢复静态IP")

            # 等待网络配置生效
            time.sleep(2)

            print(f"✅ PC网卡状态恢复完成\n")
            return True

        except Exception as e:
            print(f"❌ 恢复PC网卡状态失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    # ==================== 路由器状态管理 ====================

    def save_router_state(self, router_ip: str, router_client=None) -> bool:
        """
        保存路由器配置状态

        Args:
            router_ip: 路由器IP地址
            router_client: 路由器客户端对象（可选，用于获取详细配置）

        Returns:
            bool: 保存是否成功
        """
        print(f"\n{'='*70}")
        print(f"保存路由器配置状态: {router_ip}")
        print(f"{'='*70}")

        try:
            self.router_state = RouterState(router_ip=router_ip)

            # TODO: 这里可以通过router_client获取路由器的详细配置
            # 例如：
            # - WAN配置
            # - Cellular配置
            # - MQTT配置
            # - 防火墙规则
            # 等等

            # 目前先标记为已保存
            print(f"  路由器IP: {router_ip}")
            print(f"  ⚠️  路由器配置快照功能待实现")
            print(f"✅ 路由器状态保存完成（基础信息）\n")

            return True

        except Exception as e:
            print(f"❌ 保存路由器状态失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def restore_router_state(self, router_client=None) -> bool:
        """
        恢复路由器到之前保存的状态

        Args:
            router_client: 路由器客户端对象（可选，用于恢复详细配置）

        Returns:
            bool: 恢复是否成功
        """
        if not self.router_state:
            print("⚠️  没有保存的路由器状态，跳过恢复")
            return True

        print(f"\n{'='*70}")
        print(f"恢复路由器配置状态: {self.router_state.router_ip}")
        print(f"{'='*70}")

        try:
            # TODO: 这里可以通过router_client恢复路由器的详细配置
            # 目前先标记为已恢复

            print(f"  路由器IP: {self.router_state.router_ip}")
            print(f"  ⚠️  路由器配置恢复功能待实现")
            print(f"✅ 路由器状态恢复完成（基础信息）\n")

            return True

        except Exception as e:
            print(f"❌ 恢复路由器状态失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    # ==================== 工具方法 ====================

    def _prefix_to_netmask(self, prefix_length: int) -> str:
        """
        将CIDR前缀长度转换为点分十进制子网掩码

        Args:
            prefix_length: CIDR前缀长度（如24）

        Returns:
            str: 点分十进制子网掩码（如"255.255.255.0"）
        """
        mask = (0xffffffff >> (32 - prefix_length)) << (32 - prefix_length)
        return '.'.join([str((mask >> (8 * i)) & 0xff) for i in range(3, -1, -1)])

    def get_saved_states_summary(self) -> str:
        """
        获取已保存状态的摘要信息

        Returns:
            str: 摘要信息
        """
        summary = []

        if self.pc_adapter_state:
            summary.append(f"PC网卡: {self.pc_adapter_state.adapter_name} "
                         f"({'DHCP' if self.pc_adapter_state.dhcp_enabled else f'静态IP {self.pc_adapter_state.ip_address}'})")
        else:
            summary.append("PC网卡: 未保存")

        if self.router_state:
            summary.append(f"路由器: {self.router_state.router_ip}")
        else:
            summary.append("路由器: 未保存")

        return " | ".join(summary)


# 创建全局单例
state_manager = StateManager()
