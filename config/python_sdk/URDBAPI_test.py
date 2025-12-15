# -*- coding:utf-8 -*-
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
