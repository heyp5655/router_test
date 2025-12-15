# -*- coding:utf-8 -*-
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
