import subprocess
import requests
import time
import re
from typing import List, Tuple, Optional


class NetworkUtils:
    """网络工具类，提供网络连通性检查等功能"""

    def __init__(self):
        # 不再使用 logger
        pass

    def get_adapter_ip(self, adapter_name: str = "TEST", max_retry: int = 6, retry_interval: int = 5) -> Tuple[Optional[str], Optional[str]]:
        """
        获取指定网卡的IPv4地址和网关

        Args:
            adapter_name: 网卡名称，默认为"TEST"
            max_retry: 最大重试次数
            retry_interval: 重试间隔（秒）

        Returns:
            Tuple[Optional[str], Optional[str]]: (IP地址, 网关地址)，获取失败返回(None, None)
        """
        test_adapter_ip = None
        test_adapter_gateway = None

        for attempt in range(1, max_retry + 1):
            print(f"  第{attempt}次尝试获取网卡{adapter_name}的IP...")

            try:
                # 使用PowerShell直接获取网卡IP
                ps_cmd = f'''
                $adapter = Get-NetIPAddress -InterfaceAlias "{adapter_name}" -AddressFamily IPv4 -ErrorAction SilentlyContinue
                if ($adapter) {{
                    $adapter.IPAddress
                }}
                '''
                result = subprocess.run(
                    ["powershell", "-Command", ps_cmd],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                ip_output = result.stdout.strip()
                print(f"  [PowerShell] 获取到的IP: '{ip_output}'")

                if ip_output:
                    ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', ip_output)
                    if ip_match:
                        test_adapter_ip = ip_match.group(1)
                        # 排除169.254开头的自动配置IP
                        if not test_adapter_ip.startswith('169.254'):
                            print(f"  ✅ IPv4地址: {test_adapter_ip}")

                            # 获取网关
                            gw_cmd = f'''
                            $route = Get-NetRoute -InterfaceAlias "{adapter_name}" -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue
                            if ($route) {{ $route.NextHop }}
                            '''
                            gw_result = subprocess.run(
                                ["powershell", "-Command", gw_cmd],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            gw_output = gw_result.stdout.strip()
                            if gw_output:
                                gw_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', gw_output)
                                if gw_match:
                                    test_adapter_gateway = gw_match.group(1)
                                    print(f"  ✅ 默认网关: {test_adapter_gateway}")

                            return test_adapter_ip, test_adapter_gateway
                        else:
                            print(f"  ⚠️  获取到自动配置IP {test_adapter_ip}，DHCP可能未成功")
                            test_adapter_ip = None

                if not test_adapter_ip:
                    print(f"  ⚠️  第{attempt}次尝试未获取到有效IPv4地址")
                    if attempt < max_retry:
                        print(f"  等待{retry_interval}秒后重试...")
                        time.sleep(retry_interval)

            except Exception as e:
                print(f"  ❌ 第{attempt}次获取网卡IP时出错: {str(e)}")
                if attempt < max_retry:
                    print(f"  等待{retry_interval}秒后重试...")
                    time.sleep(retry_interval)

        print("  ❌ 已达到最大重试次数，仍未获取到有效的IPv4地址")
        return None, None

    def set_adapter_dhcp(self, adapter_name: str = "TEST") -> bool:
        """
        设置指定网卡为DHCP模式

        Args:
            adapter_name: 网卡名称

        Returns:
            bool: 设置是否成功
        """
        try:
            # 设置IP为DHCP
            result = subprocess.run(
                ["netsh", "interface", "ip", "set", "address", f"name={adapter_name}", "source=dhcp"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print(f"  ✅ 网卡{adapter_name}已设置为DHCP模式")
            else:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                if "已在此接口上启用 DHCP" in error_msg or "DHCP is already enabled" in error_msg:
                    print(f"  ✅ 网卡{adapter_name}已经是DHCP模式，无需重复设置")
                elif "需要提升" in error_msg or "请求的操作需要提升" in error_msg:
                    print(f"  ❌ 设置DHCP失败: 需要管理员权限")
                    return False
                else:
                    print(f"  ⚠️  设置DHCP时出现警告: {error_msg}")

            # 设置DNS为DHCP
            subprocess.run(
                ["netsh", "interface", "ip", "set", "dns", f"name={adapter_name}", "source=dhcp"],
                capture_output=True,
                timeout=10
            )

            return True

        except Exception as e:
            print(f"  ❌ 设置网卡DHCP时出错: {str(e)}")
            return False

    def check_pc_internet_via_adapter(self, adapter_name: str = "TEST", timeout: int = 10) -> bool:
        """
        通过指定网卡检查PC的外网连通性（完整流程）

        步骤：
        1. 设置网卡为DHCP模式
        2. 等待获取IP地址
        3. 检查外网连通性

        Args:
            adapter_name: 网卡名称
            timeout: 连通性检查超时时间

        Returns:
            bool: 是否能通过该网卡访问外网
        """
        print(f"\n  === 通过网卡{adapter_name}检查外网连通性 ===")

        # 步骤1：设置DHCP
        print(f"  步骤1：设置网卡{adapter_name}为DHCP模式...")
        if not self.set_adapter_dhcp(adapter_name):
            print("  ⚠️  由于DHCP设置失败，无法验证网络连通性")
            return False

        # 步骤2：等待获取IP
        print(f"\n  步骤2：等待DHCP分配IP地址...")
        ip, gateway = self.get_adapter_ip(adapter_name)
        if not ip:
            print("  ❌ 未能获取到有效IP地址")
            return False

        # 步骤3：检查外网连通性
        print(f"\n  步骤3：检查外网连通性...")
        print(f"  本地IP: {ip}")
        print(f"  网关: {gateway}")

        connectivity_ok = self.check_internet_connectivity(timeout=timeout)

        if connectivity_ok:
            print(f"\n  ✅ 网络连通性测试通过")
            print(f"  ✅ 本地IP {ip} 可以通过网关 {gateway} 访问外网")
        else:
            print(f"\n  ❌ 网络连通性测试失败")

        return connectivity_ok

    def set_adapter_static_ip(self, adapter_name: str, ip: str, subnet: str = "255.255.255.0", gateway: str = None) -> bool:
        """
        设置网卡为静态IP

        Args:
            adapter_name: 网卡名称
            ip: 静态IP地址
            subnet: 子网掩码
            gateway: 网关地址（可选）

        Returns:
            bool: 设置是否成功
        """
        try:
            if gateway:
                cmd = f'netsh interface ip set address name="{adapter_name}" static {ip} {subnet} {gateway}'
            else:
                cmd = f'netsh interface ip set address name="{adapter_name}" static {ip} {subnet}'

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print(f"  ✅ 网卡{adapter_name}已设置为静态IP: {ip}")
                return True
            else:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                print(f"  ⚠️  设置静态IP时出现警告: {error_msg}")
                return True  # 可能已经设置好了

        except Exception as e:
            print(f"  ❌ 设置静态IP时出错: {str(e)}")
            return False

    def check_pc_internet_via_static_ip(self, adapter_name: str = "TEST", static_ip: str = "192.168.1.100",
                                         subnet: str = "255.255.255.0", gateway: str = None, timeout: int = 10) -> bool:
        """
        设置静态IP后检查PC的外网连通性

        Args:
            adapter_name: 网卡名称
            static_ip: 静态IP地址
            subnet: 子网掩码
            gateway: 网关地址（可选）
            timeout: 连通性检查超时时间

        Returns:
            bool: 是否能通过该网卡访问外网
        """
        print(f"\n  === 通过网卡{adapter_name}（静态IP: {static_ip}）检查外网连通性 ===")

        # 步骤1：设置静态IP
        print(f"  步骤1：设置网卡{adapter_name}为静态IP {static_ip}...")
        if not self.set_adapter_static_ip(adapter_name, static_ip, subnet, gateway):
            print("  ⚠️  设置静态IP可能失败，继续尝试...")

        time.sleep(3)  # 等待网络设置生效

        # 步骤2：检查外网连通性
        print(f"\n  步骤2：检查外网连通性...")
        connectivity_ok = self.check_internet_connectivity(timeout=timeout)

        if connectivity_ok:
            print(f"\n  ✅ 网络连通性测试通过")
            print(f"  ✅ 静态IP {static_ip} 可以访问外网")
        else:
            print(f"\n  ❌ 网络连通性测试失败")

        return connectivity_ok

    def restore_adapter_auto_config(self, adapter_name: str = "TEST") -> bool:
        """
        恢复网卡为自动配置（DHCP + 自动DNS）
        用于测试cleanup，避免影响后续访问路由器

        Args:
            adapter_name: 网卡名称

        Returns:
            bool: 恢复是否成功
        """
        try:
            print(f"  恢复网卡{adapter_name}为自动配置...")

            # 设置为DHCP
            result1 = subprocess.run(
                f'netsh interface ip set address name="{adapter_name}" source=dhcp',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            # 设置DNS为自动
            result2 = subprocess.run(
                f'netsh interface ip set dns name="{adapter_name}" source=dhcp',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result1.returncode == 0 or "已在此接口上启用 DHCP" in result1.stdout:
                print(f"  ✅ 网卡{adapter_name}已恢复为自动配置")
                return True
            else:
                print(f"  ⚠️  恢复网卡配置时出现警告")
                return True  # 继续执行

        except Exception as e:
            print(f"  ⚠️  恢复网卡配置时出错: {str(e)}")
            return False

    def check_internet_connectivity(self, timeout: int = 10) -> bool:
        """
        检查互联网连通性

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 是否能够访问互联网
        """
        # 测试目标列表，按优先级排序
        test_targets = [
            ("ping", "8.8.8.8"),  # Google DNS
            ("ping", "114.114.114.114"),  # 国内DNS
            ("http", "http://www.baidu.com"),  # 百度
            ("http", "http://www.qq.com"),  # 腾讯
            ("ping", "www.baidu.com"),  # 百度域名
        ]

        for test_type, target in test_targets:
            try:
                if test_type == "ping":
                    if self._ping_test(target, timeout=5):
                        print(f"✅ 网络连通性检查通过 - ping {target} 成功")
                        return True
                elif test_type == "http":
                    if self._http_test(target, timeout=5):
                        print(f"✅ 网络连通性检查通过 - HTTP访问 {target} 成功")
                        return True
            except Exception as e:
                print(f"检查 {target} 失败: {str(e)}")
                continue

        print("❌ 网络连通性检查失败 - 所有测试目标均无法访问")
        return False

    def _ping_test(self, target: str, count: int = 2, timeout: int = 5) -> bool:
        """
        执行ping测试

        Args:
            target: ping目标地址
            count: ping次数
            timeout: 超时时间

        Returns:
            bool: ping是否成功
        """
        try:
            # Windows和Linux/macOS的ping参数略有不同
            import platform
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), target]
            else:
                cmd = ["ping", "-c", str(count), "-W", str(timeout), target]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 2
            )

            success = result.returncode == 0
            if not success:
                print(f"ping {target} 失败: {result.stderr}")

            return success

        except subprocess.TimeoutExpired:
            print(f"ping {target} 超时")
            return False
        except Exception as e:
            print(f"ping {target} 异常: {str(e)}")
            return False

    def _http_test(self, url: str, timeout: int = 10) -> bool:
        """
        执行HTTP访问测试

        Args:
            url: 测试URL
            timeout: 超时时间

        Returns:
            bool: HTTP访问是否成功
        """
        try:
            response = requests.get(url, timeout=timeout, verify=False)
            success = response.status_code == 200

            if not success:
                print(f"HTTP访问 {url} 失败，状态码: {response.status_code}")

            return success

        except requests.exceptions.RequestException as e:
            print(f"HTTP访问 {url} 异常: {str(e)}")
            return False
        except Exception as e:
            print(f"HTTP访问 {url} 未知异常: {str(e)}")
            return False

    def check_specific_service(self, host: str, port: int, timeout: int = 5) -> bool:
        """
        检查特定服务的端口连通性

        Args:
            host: 主机地址
            port: 端口号
            timeout: 超时时间

        Returns:
            bool: 端口是否可连接
        """
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()

            success = result == 0
            if not success:
                print(f"服务检查 {host}:{port} 失败，错误码: {result}")

            return success

        except Exception as e:
            print(f"服务检查 {host}:{port} 异常: {str(e)}")
            return False

    def get_network_latency(self, target: str = "8.8.8.8", count: int = 4) -> float:
        """
        获取网络延迟

        Args:
            target: 测试目标
            count: ping次数

        Returns:
            float: 平均延迟（毫秒），失败返回-1
        """
        try:
            import platform
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", str(count), target]
            else:
                cmd = ["ping", "-c", str(count), target]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode != 0:
                return -1

            # 解析ping结果获取平均延迟
            output = result.stdout
            if "平均" in output:  # Windows中文版
                latency_line = [line for line in output.split('\n') if "平均" in line][0]
                latency = latency_line.split('=')[1].split('ms')[0].strip()
            elif "avg" in output:  # Linux/macOS
                latency_line = [line for line in output.split('\n') if "avg" in line][0]
                latency = latency_line.split('=')[1].split('/')[1].strip()
            else:
                return -1

            return float(latency)

        except Exception as e:
            print(f"获取网络延迟失败: {str(e)}")
            return -1


# 创建全局实例
network_utils = NetworkUtils()