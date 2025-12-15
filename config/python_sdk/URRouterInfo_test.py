# -*- coding:utf-8 -*-
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
