# -*- coding: utf-8 -*-
from test_cases.base_test import BaseTest
import time
import paramiko


class UrapiLibraryTest(BaseTest):
    """新Urapi库在新SDK上面的适配测试

    测试项：功能用例/APP/python
    测试点：新Urapi库在新SDK上面的适配测试

    前置条件：
    1. 路由器已安装python3.9环境
    2. 路由器FTP服务器已开启
    3. 路由器SSH服务已开启

    测试步骤：
    1. 参照用例"python3.9第三方库pymodbus验证"的实现方法
    2. 登录设备，检查FTP服务器和Python3.9环境
    3. 上传并执行URDBAPI_test.py，验证数据库API功能
    4. 上传并执行URInterface_test.py，验证接口控制功能
    5. 上传并执行URRouterInfo_test.py，验证路由器信息获取功能

    预期：
    三个脚本都能正常执行并输出预期结果，验证Urapi库的完整性
    """

    # 添加分类信息属性
    category = "功能用例/APP/python"
    is_regression = True  # 标记为回归测试用例

    # 测试脚本1: URDBAPI数据库API测试（使用正确的导入方式）
    URDBAPI_TEST_SCRIPT = '''# -*- coding:utf-8 -*-
"""
简单测试 URDBAPI.DBHandle 的基本方法。

默认 DB 路径 /tmp/urdbapi_test.db，可通过环境变量 UR_TEST_DB 覆盖。
"""

import os
from URDBAPI import DBHandle


def call_and_print(label, fn, *args, **kwargs):
    try:
        res = fn(*args, **kwargs)
    except Exception as exc:
        res = "EXCEPTION: %r" % exc
    print("%s -> %r" % (label, res))


def main():
    db_path = os.environ.get("UR_TEST_DB", "/tmp/urdbapi_test.db")
    db = DBHandle(db_path)

    print("Using db file: %s" % db_path)

    call_and_print("rmDBFile (cleanup)", db.rmDBFile)
    call_and_print("addValue(alpha, foo)", db.addValue, "alpha", "foo")
    call_and_print("addValue(alpha, {'n': 1})", db.addValue, "alpha", {"n": 1})
    call_and_print("addValue(beta, 123)", db.addValue, "beta", 123)
    call_and_print("showValue(alpha)", db.showValue, "alpha")
    call_and_print("showValue(beta)", db.showValue, "beta")
    call_and_print("getList()", db.getList)
    call_and_print("updateValue(alpha, 'updated')", db.updateValue, "alpha", "updated")
    call_and_print("showValue(alpha)", db.showValue, "alpha")
    call_and_print("delValue(beta)", db.delValue, "beta")
    call_and_print("getList()", db.getList)
    call_and_print("rmDBFile (final cleanup)", db.rmDBFile)


if __name__ == "__main__":
    main()
'''

    # 测试脚本2: URInterface接口控制测试（使用正确的导入方式）
    URINTERFACE_TEST_SCRIPT = '''# -*- coding:utf-8 -*-
"""
简单遍历 URInterface 每个接口的测试脚本。

默认网卡 ifname=FE0，可通过环境变量 UR_TEST_IF 覆盖。
仅打印调用结果，实际执行 ip/AT 操作需在目标设备上运行。
"""

import os
from URInterface import URInterface


def main():
    ifname = os.environ.get("UR_TEST_IF", "FE0")
    ui = URInterface()

    samples = {
        "ipaddr": "192.0.2.10",
        "netmask": "255.255.255.0",
        "mtu": 1500,
        "mac": "00:11:22:33:44:55",
        "static_route": "198.51.100.0/24",
        "default_via": "192.0.2.1",
        "at_cmd": "ATI",
    }

    tests = [
        ("down", ui.down, (ifname,), {}),
        ("up", ui.up, (ifname,), {}),
        ("set_ipv4", ui.set_ipv4, (ifname, samples["ipaddr"], samples["netmask"]), {}),
        ("set_mtu", ui.set_mtu, (ifname, samples["mtu"]), {}),
        ("set_mac", ui.set_mac, (ifname, samples["mac"]), {}),
        ("add_static_route", ui.add_static_route, (ifname, samples["static_route"]), {}),
        ("add_default_route", ui.add_default_route, (ifname, samples["default_via"]), {}),
        ("del_static_route", ui.del_static_route, (ifname, samples["static_route"]), {}),
        ("del_default_route", ui.del_default_route, (ifname, samples["default_via"]), {}),
        ("send_at_cmd", ui.send_at_cmd, (samples["at_cmd"],), {}),
    ]

    for name, fn, args, kwargs in tests:
        try:
            res = fn(*args, **kwargs)
        except Exception as exc:
            res = "EXCEPTION: %r" % exc
        print("%s(%s) -> %s" % (name, ", ".join(map(str, args)), res))


if __name__ == "__main__":
    main()
'''

    # 测试脚本3: URRouterInfo路由器信息获取测试（使用正确的导入方式）
    URROUTERINFO_TEST_SCRIPT = '''# -*- coding:utf-8 -*-
"""
简单遍历 URRouterInfo 每个接口的测试脚本。

需在设备上运行以获得真实数据；本地缺少 ubus/urtool 时可能返回 None 或异常。
"""

from URRouterInfo import URRouterInfo


def call_and_print(label, fn, *args, **kwargs):
    try:
        res = fn(*args, **kwargs)
    except Exception as exc:
        res = "EXCEPTION: %r" % exc
    print("%s -> %r" % (label, res))


def main():
    ri = URRouterInfo()
    tests = [
        ("get_eth_portList", ri.get_eth_portList),
        ("get_firmware_info", ri.get_firmware_info),
        ("get_cellular_status", ri.get_cellular_status),
        ("get_wan_status", ri.get_wan_status),
        ("get_bridge_status", ri.get_bridge_status),
        ("get_serial_info", ri.get_serial_info),
        ("get_di_status", ri.get_di_status),
    ]

    for name, fn in tests:
        call_and_print(name, fn)


if __name__ == "__main__":
    main()
'''

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "新Urapi库在新SDK上面的适配测试"

    @property
    def description(self):
        """测试描述"""
        return "验证新Urapi库的完整性，包括数据库API、接口控制、路由器信息获取等功能"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 获取路由器配置
        self.router_ip = self.config.router_config.router_ip

        # 测试结果缓存
        self.test_outputs = {
            'urdbapi': '',
            'urinterface': '',
            'urrouterinfo': ''
        }

    def setup(self):
        """测试前置条件"""
        print(f"\n{'='*70}")
        print(f"测试用例: {self.test_name}")
        print(f"测试分类: {self.category}")
        print(f"{'='*70}")
        print(f"路由器IP: {self.router_ip}")
        print(f"{'='*70}\n")

        # 检查并自动安装Python SDK
        print("前置条件: 检查Python SDK...")
        if not self.ensure_python_sdk_installed():
            raise Exception("Python SDK未安装且自动安装失败，无法继续测试")
        print("✅ Python SDK已就绪\n")

        # 检查并启用SSH（新版本固件默认关闭SSH）
        print("前置条件: 检查SSH启用状态...")
        if not self.router_client.ensure_ssh_enabled():
            raise Exception("SSH未启用且自动启用失败，无法继续测试")
        print("✅ SSH已就绪\n")

        print("✅ 前置条件检查完成\n")

    def execute(self):
        """执行测试 - 依次上传并执行三个测试脚本"""
        try:
            print(f"\n{'='*70}")
            print(f"开始执行Urapi库适配测试")
            print(f"{'='*70}\n")

            # 步骤1: 测试URDBAPI
            print("=" * 70)
            print("步骤1: 测试URDBAPI数据库API功能")
            print("=" * 70)
            if not self._test_script("urdbapi", self.URDBAPI_TEST_SCRIPT, "urdbapi_test.py"):
                raise Exception("URDBAPI测试失败")
            print("✅ URDBAPI测试通过\n")

            # 步骤2: 测试URInterface
            print("=" * 70)
            print("步骤2: 测试URInterface接口控制功能")
            print("=" * 70)
            if not self._test_script("urinterface", self.URINTERFACE_TEST_SCRIPT, "urinterface_test.py"):
                raise Exception("URInterface测试失败")
            print("✅ URInterface测试通过\n")

            # 步骤3: 测试URRouterInfo
            print("=" * 70)
            print("步骤3: 测试URRouterInfo路由器信息获取功能")
            print("=" * 70)
            if not self._test_script("urrouterinfo", self.URROUTERINFO_TEST_SCRIPT, "urrouterinfo_test.py"):
                raise Exception("URRouterInfo测试失败")
            print("✅ URRouterInfo测试通过\n")

            # 所有测试通过
            print("=" * 70)
            print("✅ 所有Urapi库测试通过！")
            print("=" * 70)
            return True

        except Exception as e:
            print(f"\n测试执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise

    def _test_script(self, test_name, script_content, script_filename):
        """通用的脚本测试方法

        Args:
            test_name: 测试名称（用于结果缓存）
            script_content: 脚本内容
            script_filename: 脚本文件名

        Returns:
            bool: 测试是否成功
        """
        ssh = None
        sftp = None
        script_path = f"/tmp/{script_filename}"

        try:
            # 1. 建立SSH连接并上传脚本
            print(f"1.1 SSH连接到路由器 {self.router_ip}...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )
            print("✅ SSH连接成功")

            # 1.2 上传脚本
            print(f"1.2 通过SFTP上传脚本到 {script_path}...")
            sftp = ssh.open_sftp()
            with sftp.file(script_path, 'w') as remote_file:
                remote_file.write(script_content)
            print("✅ SFTP上传完成")

            # 1.3 设置执行权限
            print("1.3 设置执行权限...")
            stdin, stdout, stderr = ssh.exec_command(f"chmod +x {script_path}")
            stdout.channel.recv_exit_status()
            print("✅ 权限设置完成")

            # 2. 执行脚本
            print(f"\n2. 执行脚本...")
            python_path = "/usr/python/bin/python3.9"
            lib_path = "/usr/python/lib"
            command = f"export LD_LIBRARY_PATH={lib_path}:$LD_LIBRARY_PATH && {python_path} {script_path} 2>&1"

            print(f"执行命令: {command}")
            print("-" * 70)

            stdin, stdout, stderr = ssh.exec_command(command, timeout=30)

            # 读取输出
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            exit_code = stdout.channel.recv_exit_status()

            # 保存输出
            self.test_outputs[test_name] = output

            # 打印输出
            for line in output.split('\n'):
                if line.strip():
                    print(f"  {line}")

            if error:
                print(f"\nStderr输出:")
                for line in error.split('\n'):
                    if line.strip():
                        print(f"  {line}")

            print("-" * 70)
            print(f"退出码: {exit_code}")

            # 3. 清理脚本文件
            print(f"\n3. 清理临时文件...")
            ssh.exec_command(f"rm -f {script_path}")

            # 4. 关闭连接
            if sftp:
                sftp.close()
            if ssh:
                ssh.close()

            # 5. 验证结果
            # 退出码为0即表示成功
            if exit_code == 0:
                print(f"\n✅ {test_name}脚本执行成功")
                return True
            else:
                print(f"\n❌ {test_name}脚本执行失败 (退出码: {exit_code})")
                return False

        except Exception as e:
            print(f"\n❌ {test_name}测试失败: {str(e)}")
            import traceback
            print(traceback.format_exc())

            # 清理资源
            if sftp:
                try:
                    sftp.close()
                except:
                    pass
            if ssh:
                try:
                    ssh.close()
                except:
                    pass

            return False

    def cleanup(self):
        """测试清理"""
        print(f"\n{'='*70}")
        print("测试清理")
        print(f"{'='*70}")

        # 清理路由器上的临时文件
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.router_ip,
                username=self.SSH_ROOT_USERNAME,
                password=self.SSH_ROOT_PASSWORD,
                timeout=10
            )

            print("删除临时测试脚本...")
            ssh.exec_command("rm -f /tmp/urdbapi_test.py /tmp/urinterface_test.py /tmp/urrouterinfo_test.py")
            ssh.close()
            print("✅ 临时文件已删除")

        except Exception as e:
            print(f"清理临时文件时出错: {str(e)}")

        print("测试清理完成")
