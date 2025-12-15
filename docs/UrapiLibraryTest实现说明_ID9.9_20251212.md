# Urapi库适配测试 (ID 9.9) 实现说明

## 文档信息
- **测试ID**: 9.9
- **测试名称**: 新Urapi库在新SDK上面的适配测试
- **实现日期**: 2025-12-12
- **文件位置**: `test_cases/app_tests/urapi_library_test.py`

## 测试概述
验证新Urapi库在新Python SDK上的适配性，测试三个核心模块：
1. **urdbapi** - 数据库API功能
2. **urinterface** - 网络接口控制功能
3. **urrouterinfo** - 路由器信息获取功能

## 测试实现

### 1. 测试架构
```
UrapiLibraryTest (继承自 BaseTest)
├── 前置条件检查
│   ├── Python SDK安装检查
│   └── SSH服务启用检查
├── 测试执行
│   ├── URDBAPI测试脚本上传和执行
│   ├── URInterface测试脚本上传和执行
│   └── URRouterInfo测试脚本上传和执行
└── 测试清理
    └── 删除临时测试脚本
```

### 2. 测试脚本内容

#### 2.1 URDBAPI_test.py (数据库API测试)
**测试功能**:
- 数据库文件管理（创建、删除）
- 键值对操作（添加、更新、删除、查询）
- 数据列表获取

**关键API**:
```python
urdbapi.addValue(key, value)
urdbapi.showValue(key)
urdbapi.getList()
urdbapi.updateValue(key, new_value)
urdbapi.delValue(key)
```

**预期输出**:
```
Using db file: /tmp/urdbapi_test.db
rmDBFile (cleanup) -> None
addValue(alpha, foo) -> None
addValue(alpha, {'n': 1}) -> None
addValue(beta, 123) -> None
showValue(alpha) -> None
showValue(beta) -> None
getList() -> None
updateValue(alpha, 'updated') -> None
showValue(alpha) -> None
delValue(beta) -> None
getList() -> None
rmDBFile (final cleanup) -> None
✅ URDBAPI测试完成
```

#### 2.2 URInterface_test.py (接口控制测试)
**测试功能**:
- 接口启用/禁用
- IP地址配置（IPv4）
- MTU和MAC地址设置
- 静态路由管理
- 默认路由管理
- AT命令发送

**关键API**:
```python
urinterface.down(iface)
urinterface.up(iface)
urinterface.set_ipv4(iface, ip, netmask)
urinterface.set_mtu(iface, mtu)
urinterface.set_mac(iface, mac)
urinterface.add_static_route(iface, route)
urinterface.add_default_route(iface, gateway)
urinterface.del_static_route(iface, route)
urinterface.del_default_route(iface, gateway)
urinterface.send_at_cmd(cmd)
```

**预期输出**:
```
down(FE0) -> True
up(FE0) -> True
set_ipv4(FE0, 192.0.2.10, 255.255.255.0) -> True
set_mtu(FE0, 1500) -> True
set_mac(FE0, 00:11:22:33:44:55) -> True
add_static_route(FE0, 198.51.100.0/24) -> True
add_default_route(FE0, 192.0.2.1) -> True
del_static_route(FE0, 198.51.100.0/24) -> True
del_default_route(FE0, 192.0.2.1) -> True
send_at_cmd(ATI) -> [AT命令响应]
✅ URInterface测试完成 - 全部通过
```

#### 2.3 URRouterInfo_test.py (路由器信息获取测试)
**测试功能**:
- 以太网端口信息
- 固件信息
- 蜂窝网络状态
- WAN状态
- Bridge状态
- 串口信息
- DI状态

**关键API**:
```python
urrouterinfo.get_eth_portList()
urrouterinfo.get_firmware_info()
urrouterinfo.get_cellular_status()
urrouterinfo.get_wan_status()
urrouterinfo.get_bridge_status()
urrouterinfo.get_serial_info()
urrouterinfo.get_di_status()
```

**预期输出**:
```
get_eth_portList -> [端口列表...]
get_firmware_info -> {固件信息...}
get_cellular_status -> {蜂窝状态...}
get_wan_status -> {WAN状态...}
get_bridge_status -> {Bridge状态...}
get_serial_info -> {串口信息...}
get_di_status -> {DI状态...}
✅ URRouterInfo测试完成 - 全部通过
```

### 3. 实现方法

#### 3.1 脚本上传
使用SFTP通过SSH上传测试脚本到路由器的 `/tmp` 目录：
```python
ssh = paramiko.SSHClient()
ssh.connect(router_ip, username='root', password='...')
sftp = ssh.open_sftp()
sftp.file(script_path, 'w').write(script_content)
```

#### 3.2 脚本执行
通过SSH执行脚本，设置正确的环境变量：
```bash
export LD_LIBRARY_PATH=/usr/python/lib:$LD_LIBRARY_PATH
/usr/python/bin/python3.9 /tmp/test_script.py
```

#### 3.3 结果验证
- 检查脚本退出码（期望为0）
- 检查输出中是否包含"测试完成"关键字
- 验证所有API调用没有抛出异常

### 4. 测试流程

```
1. 前置条件检查
   ├── 检查Python SDK是否安装
   │   └── 如果未安装，自动安装
   └── 检查SSH服务是否启用
       └── 如果未启用，自动启用

2. URDBAPI测试
   ├── 上传urdbapi_test.py到/tmp
   ├── 执行脚本
   ├── 验证输出和退出码
   └── 删除临时脚本

3. URInterface测试
   ├── 上传urinterface_test.py到/tmp
   ├── 执行脚本
   ├── 验证输出和退出码
   └── 删除临时脚本

4. URRouterInfo测试
   ├── 上传urrouterinfo_test.py到/tmp
   ├── 执行脚本
   ├── 验证输出和退出码
   └── 删除临时脚本

5. 测试清理
   └── 确保所有临时文件已删除
```

### 5. 关键特性

#### 5.1 自动化程度高
- 自动检查和安装Python SDK
- 自动启用SSH服务
- 自动上传和执行测试脚本
- 自动清理临时文件

#### 5.2 错误处理完善
- 所有SSH/SFTP操作都有异常处理
- 超时保护机制
- 详细的错误日志输出

#### 5.3 输出清晰
- 每个步骤都有明确的进度提示
- 测试结果统计
- 详细的脚本输出展示

### 6. 使用方法

#### 6.1 通过Web界面运行
1. 访问测试平台首页 http://localhost:5000
2. 在测试用例列表中找到"新Urapi库在新SDK上面的适配测试"
3. 点击"运行测试"按钮
4. 等待测试完成，查看结果

#### 6.2 通过命令行运行
```python
from test_cases.app_tests.urapi_library_test import UrapiLibraryTest
from models.test_config import TestConfig, RouterConfig

# 创建配置
router_config = RouterConfig(router_ip="192.168.1.1", ...)
test_config = TestConfig(router_config=router_config)

# 创建测试实例
test = UrapiLibraryTest(test_config)

# 运行测试
test.setup()
result = test.execute()
test.cleanup()
```

## 与参考用例的对比

### 参考用例: pymodbus_library_test.py
- **相似点**:
  - 都使用SFTP上传测试脚本
  - 都通过SSH执行脚本
  - 都有详细的输出验证
  - 都有自动清理机制

- **差异点**:
  - pymodbus测试需要PC端运行Modbus Server进行交互
  - urapi测试是独立运行，不需要外部依赖
  - pymodbus测试使用串口登录，urapi测试使用SSH执行
  - pymodbus测试需要实时读取串口输出，urapi测试直接获取SSH命令输出

## 测试配置要求

### 必需配置
- 路由器IP地址
- SSH凭据（root用户）
- Python SDK文件路径

### 可选配置
- SSH超时时间（默认10秒）
- 脚本执行超时时间（默认30秒）

## 故障排查

### 常见问题

#### 1. Python SDK未安装
**症状**: 提示"Python SDK未安装且自动安装失败"
**解决**:
- 检查config/python_sdk目录下是否有SDK文件
- 手动通过Web界面安装SDK
- 检查FTP服务是否正常

#### 2. SSH连接失败
**症状**: SSH连接超时或认证失败
**解决**:
- 检查路由器IP是否正确
- 检查SSH服务是否启用
- 检查SSH凭据是否正确

#### 3. 脚本执行失败
**症状**: 脚本退出码非0或输出包含错误
**解决**:
- 检查urapi库是否正确安装
- 检查Python环境变量是否正确
- 查看详细的脚本输出日志

#### 4. 模块导入失败
**症状**: 脚本输出"urapi模块导入失败"
**解决**:
- 确认Python SDK版本是否支持urapi库
- 检查LD_LIBRARY_PATH环境变量
- 重新安装Python SDK

## 维护说明

### 更新测试脚本
如果需要更新测试脚本内容，直接修改类中的脚本字符串常量：
- `URDBAPI_TEST_SCRIPT`
- `URINTERFACE_TEST_SCRIPT`
- `URROUTERINFO_TEST_SCRIPT`

### 添加新的测试项
1. 在对应的测试脚本中添加新的测试代码
2. 更新测试结果验证逻辑
3. 更新文档说明

### 调整超时时间
根据实际情况调整SSH和脚本执行的超时参数。

## 总结
本测试用例成功实现了ID 9.9的需求，提供了完整的Urapi库适配测试功能。测试覆盖了三个核心模块的主要API，具有高度自动化、良好的错误处理和清晰的输出展示。

---
**最后更新**: 2025-12-12
**维护者**: Claude Code
