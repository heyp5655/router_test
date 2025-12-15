# ROUTER_TEST - 路由器自动化测试框架

## ⚠️ 重要提示
**请先阅读 `PROJECT_STRUCTURE.md` 文档了解项目结构规范!**

该文档定义了代码组织规范、文件放置规则、导入路径规范等重要内容。

## 项目概述
基于 Flask 的路由器自动化测试平台，支持 WAN、蜂窝网络、MQTT等功能测试，通过 Web 界面控制测试流程。

## 技术栈
- Python 3.12
- Flask 2.3.3 (Web界面)
- Selenium 4.12.0 (浏览器自动化)
- PySerial 3.5 (串口通信)
- paho-mqtt 2.0+ (MQTT通信)
- PyYAML 5.4.1+ (配置管理)
- paramiko 2.7+ (SSH客户端)
- openpyxl 3.0+ (Excel处理)
- webdriver-manager 4.0.1 (浏览器驱动管理)

## 目录结构
```
├── app.py                  # Flask应用主入口
├── main.py                 # 程序入口点
├── start_admin.bat         # 管理员权限启动脚本
├── PROJECT_STRUCTURE.md    # 项目结构规范文档(必读!)
├── CLAUDE.md              # 本文档
│
├── config/                # 配置文件
│   ├── default_config.yaml
│   └── router_models.yaml
│
├── core/                  # 核心模块
│   ├── config_loader.py
│   ├── result_manager.py
│   ├── router_client.py    # 路由器客户端(所有路由器操作方法)
│   └── test_runner.py
│
├── test_cases/            # 测试用例(所有测试用例必须在此)
│   ├── base_test.py       # 测试基类
│   ├── wan_tests/         # WAN测试
│   ├── cellular_tests/    # 蜂窝网络测试
│   ├── mqtt_test/         # MQTT测试(已整理)
│   ├── industrial_tests/  # 工业协议测试
│   └── app_tests/         # 应用测试
│
├── utils/                 # 工具类(所有通用工具必须在此)
│   ├── logger.py
│   ├── network_utils.py   # PC网络工具(重要)
│   ├── mqtt_client.py     # MQTT测试客户端
│   ├── excel_exporter.py
│   └── report_generator.py
│
├── scripts/               # 独立脚本
│   ├── create_dmvpn_doc.py
│   └── read_excel.py
│
├── models/                # 数据模型
├── templates/             # HTML模板
├── logs/                  # 测试日志
├── reports/               # 测试报告
└── results/               # 测试结果
```

## 关键文件
- `PROJECT_STRUCTURE.md` - **项目结构规范(必读)**
- `app.py` - Flask应用，包含API端点和管理员权限检测
- `core/router_client.py` - 路由器客户端,包含所有与路由器交互的方法
- `core/test_runner.py` - 测试执行器
- `test_cases/base_test.py` - 测试用例基类
- `utils/network_utils.py` - PC网络工具类(设置网卡、测试连通性)
- `utils/mqtt_client.py` - MQTT测试客户端工具

## 快速开始

### 新电脑首次安装
```
1. 运行 "完整安装_含GitHub.bat"（以管理员身份）
2. 按提示输入 Git 用户信息
3. 等待自动完成（约 10 分钟）
4. 浏览器访问 http://localhost:5000
```

详见：**`安装使用指南.md`**

### 日常运行
```bash
# 推荐：使用启动脚本（自动管理员权限）
start_admin.bat

# 或手动以管理员身份运行
python app.py
```

### 依赖问题修复
```
运行 "修复依赖安装.bat"（以管理员身份）
```

## network_utils.py 使用说明
PC网络连通性检测统一使用 `utils/network_utils.py`：

```python
from utils.network_utils import network_utils

# DHCP模式检测（设置DHCP → 获取IP → 测外网）
network_utils.check_pc_internet_via_adapter(adapter_name="TEST", timeout=10)

# 静态IP模式检测（设置静态IP → 测外网）
network_utils.check_pc_internet_via_static_ip(
    adapter_name="TEST",
    static_ip="192.168.1.100",
    subnet="255.255.255.0",
    timeout=30
)

# 仅测试外网连通性（不设置网卡）
network_utils.check_internet_connectivity(timeout=10)

# 单独设置网卡
network_utils.set_adapter_dhcp(adapter_name="TEST")
network_utils.set_adapter_static_ip(adapter_name="TEST", ip="192.168.1.100")
network_utils.get_adapter_ip(adapter_name="TEST")  # 返回 (ip, gateway)
```

## 网络检测规则
1. **路由器自身网络检测** - 通过路由器Web页面执行ping命令
2. **PC通过路由器上网检测** - 使用 `network_utils.py` 的方法

## 注意事项
- Windows 平台需要管理员权限运行（修改网络配置）
- Web 服务默认端口 5000
- 测试用例在 `用例步骤.xlsx` 中定义
- 测试网卡名称默认为 `TEST`
- 修改代码后需要重启 Flask 服务才能生效
- 使用 PowerShell 的 `Get-NetIPAddress` 获取网卡IP（比 ipconfig 更可靠）

## 已实现的测试用例
### WAN测试
- PPPoE连接测试 (`wan_tests/pppoe_test.py`)
- 静态IP测试 (`wan_tests/static_ip.py`)

### 蜂窝网络测试
- PIN功能测试 (`cellular_tests/pin_function_test.py`)
- 蜂窝网络制式测试 (`cellular_tests/cellular_supported_network_standards.py`)
- 蜂窝子网掩码测试 (`cellular_tests/cellular_netmask_test.py`)
- 蜂窝频段测试 (`cellular_tests/cellular_band_test.py`)
- SMS中心测试 (`cellular_tests/SMS_Center_test.py`)

### 端口冲突检测
- 端口冲突检测测试 (`port_conflict_tests/port_conflict_detection_test.py`)
  - 测试ID: 11
  - 验证静态保留端口列表的完整性与准确性
  - **保留端口配置**: 从 `config/reserved_ports.yaml` 文件读取
  - 保留端口列表: 53, 1701, 9001, 68, 500, 4500, 123, 1, 58, 7547, 9993, 520 (12个)
  - 已移除端口: 55832, 40404, 22, 7574→7547
  - 测试范围: 1-65535所有端口
  - 预期行为: 保留端口应弹出冲突提示，非保留端口可正常添加

- 防火墙Security端口冲突检测 (`port_conflict_tests/firewall_security_port_conflict_test.py`)
  - 测试ID: 12
  - 测试防火墙Security页面5个端口字段的冲突检测
  - 测试字段: HTTP、HTTPS、TELNET、SSH、FTP

- Serial1端口冲突检测 (`port_conflict_tests/serial1_port_conflict_test.py`)
  - 测试ID: 13
  - 测试Serial1页面端口冲突检测

- Serial2端口冲突检测 (`port_conflict_tests/serial2_port_conflict_test.py`)
  - 测试ID: 14
  - 测试Serial2页面端口冲突检测

- Modbus TCP端口冲突检测 (`port_conflict_tests/modbus_tcp_port_conflict_test.py`)
  - 测试ID: 15
  - 测试Modbus TCP页面端口冲突检测

- SNMP端口冲突检测 (`port_conflict_tests/snmp_port_conflict_test.py`)
  - 测试ID: 16
  - 测试SNMP页面端口冲突检测

- GPS端口冲突检测 (`port_conflict_tests/gps_port_conflict_test.py`) 🆕
  - 测试ID: 17
  - 测试GPS IP Forwarding页面端口冲突检测
  - 测试流程:
    1. 启用GPS功能 (#industrial/gps/gps)
    2. 启用IP Forwarding，类型选择server (#industrial/gps/ipforwarding)
    3. 测试本地端口字段的冲突检测
  - **保留端口配置**: 从 `config/reserved_ports.yaml` 文件读取
  - 保留端口: 53, 1701, 9001, 68, 500, 4500, 123, 1, 58, 7547, 9993, 520 (12个)

- OpenVPN端口冲突检测 (`port_conflict_tests/openvpn_port_conflict_test.py`)
  - 测试ID: 18
  - 测试OpenVPN服务器页面端口冲突检测
  - 测试流程:
    1. 启用OpenVPN服务器 (#vpn/openvpn/server)
    2. 测试端口字段的冲突检测
  - **保留端口配置**: 从 `config/reserved_ports.yaml` 文件读取
  - 保留端口: 53, 1701, 9001, 68, 500, 4500, 123, 1, 58, 7547, 9993, 520 (12个)

- OpenVPN与防火墙跨页面端口冲突检测 (`port_conflict_tests/openvpn_firewall_cross_page_port_conflict_test.py`) 🆕
  - 测试ID: 19
  - 测试OpenVPN Server与防火墙FTP端口的跨页面端口冲突检测
  - 测试流程:
    1. 跳转到防火墙Security页面配置FTP端口为1111并启用
    2. 保存并应用配置
    3. 跳转到OpenVPN服务器页面配置端口为1111
    4. 验证是否弹出端口冲突提醒
  - 测试端口: 1111（可配置）
  - **测试意义**: 验证路由器的全局端口管理能力，确保不同功能页面之间能够共享端口占用信息
  - 详细文档: `docs/ID19_OpenVPN与防火墙跨页面端口冲突检测_20251210.md`

- 端口映射与防火墙跨页面端口冲突检测 (`port_conflict_tests/portmapping_firewall_cross_page_port_conflict_test.py`) 🆕
  - 测试ID: 20
  - 测试端口映射与防火墙FTP端口的跨页面端口冲突检测

- 串口1/2与防火墙跨页面端口冲突检测 (`port_conflict_tests/serial_firewall_cross_page_port_conflict_test.py`) 🆕
  - 测试ID: 21
  - 测试Serial1和Serial2与防火墙FTP端口的跨页面端口冲突检测

- Modbus TCP与防火墙跨页面端口冲突检测 (`port_conflict_tests/modbus_firewall_cross_page_port_conflict_test.py`) 🆕
  - 测试ID: 22
  - 测试Modbus TCP与防火墙FTP端口的跨页面端口冲突检测

- SNMP与防火墙跨页面端口冲突检测 (`port_conflict_tests/snmp_firewall_cross_page_port_conflict_test.py`) 🆕
  - 测试ID: 23
  - 测试SNMP与防火墙FTP端口的跨页面端口冲突检测

- GPS与防火墙跨页面端口冲突检测 (`port_conflict_tests/gps_firewall_cross_page_port_conflict_test.py`) 🆕
  - 测试ID: 24
  - 测试GPS IP Forwarding与防火墙FTP端口的跨页面端口冲突检测

**注**: ID20-24都使用统一的测试端口1111，所有测试都验证跨页面端口冲突检测功能的有效性

#### 端口冲突检测的配置恢复机制 ✨新增 (2025-12-10) ⚠️更新 (2025-12-11)

**设计目标**: 确保所有端口冲突检测测试完成后，路由器配置能够自动恢复到测试前的初始状态。

**⚠️ 重要安全限制**:
- **HTTP和HTTPS端口绝对不备份不恢复**: 如果修改这两个端口，会导致无法通过Web界面访问路由器，从而无法进行恢复操作
- **防火墙Security配置**: 只备份和恢复FTP端口（跨页面测试只会用到FTP端口）
- **ID12测试**: 不需要备份恢复（该测试只检测冲突弹窗，不会真正保存配置到路由器）

**安全原则**:
```
┌─────────────────────────────────────────────────────────────┐
│ 端口冲突检测测试的安全原则                                     │
├─────────────────────────────────────────────────────────────┤
│ ✅ 可以测试的端口：                                            │
│   - FTP (21)      - 跨页面测试会修改                          │
│   - TELNET (23)   - 单页面测试，只触发弹窗                     │
│   - SSH (22)      - 单页面测试，只触发弹窗                     │
│   - Serial端口     - 会修改，需要备份恢复                      │
│   - OpenVPN端口    - 会修改，需要备份恢复                      │
│   - GPS端口        - 会修改，需要备份恢复                      │
│   - Modbus端口     - 会修改，需要备份恢复                      │
│   - SNMP端口       - 会修改，需要备份恢复                      │
│                                                               │
│ ❌ 绝对不能修改的端口：                                        │
│   - HTTP (80)     - 修改后无法访问Web界面                     │
│   - HTTPS (443)   - 修改后无法访问Web界面                     │
│                                                               │
│ ℹ️  测试逻辑：                                                 │
│   - ID12: 只检测冲突弹窗，点击OK后不保存，无风险              │
│   - ID19-24: 会修改并保存FTP端口，需要备份恢复                │
└─────────────────────────────────────────────────────────────┘
```

**实现方式**:
1. **在`router_client.py`中添加配置备份/恢复方法**:
   - `backup_firewall_security_config()` / `restore_firewall_security_config()` - 防火墙Security配置（**仅FTP端口**）
   - `backup_serial_config(serial_num)` / `restore_serial_config(serial_num, config)` - Serial1/2配置
   - `backup_openvpn_config()` / `restore_openvpn_config()` - OpenVPN配置
   - `backup_gps_config()` / `restore_gps_config()` - GPS配置
   - `backup_modbus_config()` / `restore_modbus_config()` - Modbus TCP配置
   - `backup_snmp_config()` / `restore_snmp_config()` - SNMP配置

2. **在每个测试用例中集成配置管理**:
   ```python
   def setup(self):
       """测试前置条件"""
       # ... 登录路由器 ...

       # 备份当前配置
       self.original_config = self.router_client.backup_xxx_config()
       if self.original_config:
           print("✅ 配置备份成功，测试完成后将恢复配置")
       else:
           print("⚠️  配置备份失败，测试完成后将无法恢复配置")

   def cleanup(self):
       """测试清理"""
       try:
           # 恢复原始配置
           if hasattr(self, 'original_config') and self.original_config:
               if self.router_client.restore_xxx_config(self.original_config):
                   print("✅ 配置已恢复到测试前的状态")
               else:
                   print("⚠️  配置恢复失败，请手动检查配置")
           else:
               # 备用：刷新页面
               self.router_client.driver.refresh()
       except Exception as e:
           print(f"⚠️  清理过程出错: {e}")
   ```

3. **跨页面测试的特殊处理**:
   - 跨页面测试（ID19-24）需要备份两个页面的配置
   - 恢复顺序：先恢复功能页面配置，再恢复防火墙配置
   - 例如ID19（OpenVPN与防火墙）:
     ```python
     def setup(self):
         self.firewall_config = self.router_client.backup_firewall_security_config()
         self.openvpn_config = self.router_client.backup_openvpn_config()

     def cleanup(self):
         self.router_client.restore_openvpn_config(self.openvpn_config)  # 先恢复
         self.router_client.restore_firewall_security_config(self.firewall_config)  # 后恢复
     ```

4. **配置恢复的优势**:
   - ✅ 测试完成后自动恢复到初始状态，无需手动清理
   - ✅ 多次运行测试不会累积配置变更
   - ✅ 容错机制：如果备份失败，降级使用页面刷新
   - ✅ 详细的日志输出，便于调试和跟踪

5. **已优化的测试用例**:
   - ID11: port_conflict_detection_test.py - 不需要恢复（测试规则不保存到路由器）
   - ID12: firewall_security_port_conflict_test.py - 不需要备份恢复（只测试冲突检测弹窗，不保存配置）
   - ID13: serial1_port_conflict_test.py ✅
   - ID14: serial2_port_conflict_test.py ✅
   - ID15: modbus_tcp_port_conflict_test.py ✅
   - ID16: snmp_port_conflict_test.py ✅
   - ID17: gps_port_conflict_test.py ✅
   - ID18: openvpn_port_conflict_test.py ✅
   - ID19: openvpn_firewall_cross_page_port_conflict_test.py ✅（只恢复FTP端口）
   - ID20: portmapping_firewall_cross_page_port_conflict_test.py ✅（只恢复FTP端口）
   - ID21: serial_firewall_cross_page_port_conflict_test.py ✅（只恢复FTP端口）
   - ID22: modbus_firewall_cross_page_port_conflict_test.py ✅（只恢复FTP端口）
   - ID23: snmp_firewall_cross_page_port_conflict_test.py ✅（只恢复FTP端口）
   - ID24: gps_firewall_cross_page_port_conflict_test.py ✅（只恢复FTP端口）

### MQTT测试
- **MQTT下发路由器重启指令发出以及设备回复** (`mqtt_test/mqtt_router_command_reboot_test.py`)

### Python SDK测试
- Python SDK正常安装测试 (`app_tests/python_sdk_normal_install_test.py`)
- Python SDK异常安装测试 (`app_tests/python_sdk_abnormal_install_test.py`)
- Python SDK稳定性测试 (`app_tests/python_sdk_stability_test.py`)

## MQTT测试功能说明
项目已完成MQTT功能整理，相关文件已移动到规范目录。

### MQTT测试用例位置
所有MQTT测试相关文件位于: `test_cases/mqtt_test/`

### MQTT工具类
- `utils/mqtt_client.py` - MQTT测试客户端(用于测试用例中)
- `test_cases/mqtt_test/mqttx_controller.py` - MQTTX数据库控制器
- `test_cases/mqtt_test/mqttx_automation.py` - MQTTX自动化工具
- `test_cases/mqtt_test/mqttx_ui_controller.py` - MQTTX UI控制器

### 使用示例
```python
# 在测试用例中使用MQTT客户端
from utils.mqtt_client import MQTTTestClient

client = MQTTTestClient(
    broker="192.168.50.36",
    port=1883,
    username="admin",
    password="password"
)

# 连接并订阅
if client.connect():
    client.subscribe("mqtt/system/response")
    client.publish("mqtt/system/request", {"id": "1", "status": "reboot"})
    response = client.wait_for_message("mqtt/system/response", timeout=10)
    client.disconnect()
```

### MQTT测试配置
- **服务器**: 192.168.50.36:1883
- **用户名**: admin
- **密码**: password
- **TLS**: 关闭
- **MQTT版本**: 5.0
- **Request主题**: `mqtt/system/request` - 向路由器发送命令
- **Response主题**: `mqtt/system/response` - 接收路由器响应

### MQTT测试用例说明
**测试名称**: MQTT下发路由器重启指令发出以及设备回复

**测试步骤**:
1. 登录路由器Web，配置MQTT客户端连接
2. 配置request和response主题
3. PC端MQTT客户端订阅主题
4. 发送reboot命令: `{"id":"1", "status":"reboot"}`
5. 验证路由器响应格式
6. 验证路由器实际重启

**响应格式**:
```json
{
  "id": "1",
  "code": "2",
  "time": "2023-05-11T03:09:30Z",
  "status": "reboot",
  "data": {"type": 0}
}
```

**文件位置**: `test_cases/mqtt_test/mqtt_router_command_reboot_test.py`

## 项目维护说明

### 添加新测试用例
1. 确定测试类型,在 `test_cases/` 下选择对应子目录
2. 创建测试文件,继承 `BaseTest`
3. 如需新工具类,添加到 `utils/`
4. 如需路由器新操作,添加方法到 `core/router_client.py`
5. **严格遵循 `PROJECT_STRUCTURE.md` 中的规范**

### 项目整理记录
**最后整理时间**: 2025-11-26

**最新整理内容**:
1. ✅ 整合安装脚本 - 统一使用 `完整安装_含GitHub.bat`
2. ✅ 创建统一文档 - `安装使用指南.md`
3. ✅ 清理冗余文件 - 删除重复的安装脚本和文档
4. ✅ 更新依赖列表 - 添加 `paramiko>=2.7.0`（SSH支持）
5. ✅ 修复依赖问题 - 解决 PyYAML 和 paramiko 安装问题

**保留的安装文件**:
- `完整安装_含GitHub.bat` - 主安装脚本（含Python、Git、GitHub Desktop）
- `修复依赖安装.bat` - 依赖问题快速修复工具
- `安装使用指南.md` - 完整的安装和使用文档

**之前的整理** (2025-11-25):
1. ✅ 创建 `PROJECT_STRUCTURE.md` 项目结构规范文档
2. ✅ 创建 `scripts/` 目录,移动独立脚本
3. ✅ 将 `mqtt_client.py` 移动到 `utils/` 目录
4. ✅ 将 MQTT测试相关文件整理到 `test_cases/mqtt_test/`
5. ✅ 更新所有导入路径
6. ✅ 更新 `CLAUDE.md` 文档
7. ✅ 修复 `test_runner.py` 添加 `test_cases.mqtt_test` 到扫描列表

**功能改进**:
- ✅ 优化MQTT连接状态检测机制
  - 支持中英文状态检测（已连接/Connected）
  - 检查间隔优化为5秒，每3次检查才刷新一次页面
  - 添加异常容错机制，检查失败时继续重试
  - 统一到 `router_client.wait_for_mqtt_connection()` 方法
  - 输出详细的检查进度和状态信息

- ✅ 完善MQTT Reboot测试用例
  - 新增步骤8: 通过SSH验证系统日志中的重启记录
    - 检查 `/etc/urlog/system.log` 中的 "Restarting system"
  - 新增步骤9: 等待路由器重启后重新连接MQTT
  - 新增步骤10-11: 验证路由器第二次响应(重启完成通知)
    - 消息格式: `{"code":"2", "id":"1", "status":"reboot", "result":1, "resultmsg":"Reboot system success"}`
  - 区分两次响应: 第一次确认收到命令，第二次通知重启完成
  - 详见: `docs/MQTT_Reboot测试更新说明.md`

**修复问题**:
- 修复了MQTT测试用例在Web页面不显示的问题
- 原因: `core/test_runner.py` 的 `test_packages` 列表中缺少 `test_cases.mqtt_test`
- 解决: 已添加到扫描列表,现在可以正常发现MQTT测试用例

- 修复了MQTT连接状态检测效率低的问题
- 原因: 每次检查都刷新页面,等待3秒,只检测中文状态
- 解决: 优化检查频率,支持中英文,添加容错机制

**当前项目状态**:
- 目录结构规范清晰
- 测试用例统一放在 `test_cases/` 分类子目录
- 工具类统一放在 `utils/`
- 路由器操作方法统一在 `core/router_client.py`
- 导入路径统一使用绝对路径

**最新修复** (2025-11-27):
1. ✅ 修复PLMN ID获取问题 **（重要bug修复）**
   - **根本原因**: 页面HTML有两个`id="0_plmnid"`的label元素
     - 第一个: `<label id="0_plmnid">4G(B1)</label>` (频段信息，错误)
     - 第二个: `<label id="0_plmnid">46011</label>` (PLMN ID，正确)
   - **原方法**: `//*[@id="0_plmnid"]` 总是返回第一个元素（错误值）
   - **修复方案**: 通过"PLMN ID"文本定位，精确获取第二个label
     - 优先XPath: `//div[contains(text(), "PLMN ID")]/following-sibling::div[1]/label`
     - 备用方案: 获取所有`id="0_plmnid"`元素，取最后一个
   - **效果**: 能正确获取值 `46011`
   - 文件: `core/router_client.py` (约1803-1846行)
   - 调试脚本: `scripts/debug_plmn_id.py`

2. ✅ 修复SINR值不一致问题
   - **根本原因**: 获取页面数据时刷新页面导致信号值变化
   - **修复方案**:
     - 调整执行顺序：先获取页面数据并锁定 → 再发送MQTT请求
     - 添加`skip_navigation`参数控制是否刷新页面
     - 获取完数据后导航回cellular页面但不刷新
   - **效果**: 数据一致性从50-70%提升到95%+
   - **关键**: 页面数据锁定后不再刷新，确保MQTT响应值 = 页面锁定值
   - 详见: `docs/ID15_PLMN_ID与SINR值修复_20251127.md`

3. ✅ 优化ID15字段对比策略 **（新增）**
   - **移除不稳定字段**: 去掉RSRP、RSRQ、SINR三个实时变化的信号值
     - 原因: 这些值每秒都在变化，即使页面锁定也会导致测试不稳定
     - 效果: 提高测试稳定性和成功率
   - **增加完整性验证**: 新增APN字段对比
     - 新增字段: IPv6 DNS (`dnsv6`), Connection Duration (`time`)
     - 每个APN: 6个字段 → 8个字段
     - 3个APN总计: 18个字段 → 24个字段
   - **字段统计**:
     - Modem: 18 → 15 (-3, 移除信号值)
     - Network: 18 → 24 (+6, 每个APN增加2个字段)
     - Statistics: 2 (不变)
     - 总计: 38 → 41 (+3)
   - 详见: `docs/ID15_字段对比优化_20251127.md`
   - 文件: `test_cases/mqtt_test/mqtt_cellular_status_report_test.py`

**DMVPN服务器配置完成** (2025-11-27):
4. ✅ 配置DMVPN服务器支持路由器连接 **（新功能）**
   - **服务器**: 192.168.50.48 (yuxy/milesight123)
   - **服务器GRE IP**: 10.0.0.1/24
   - **GRE密钥**: 123456

   **IPSec配置 (已完成并测试)**:
   - **Phase 1**: Main Mode, AES256, SHA256, modp3072 (DH Group 15)
   - **Phase 2**: AES256/AES192/AES128, HMAC-SHA256 (已测试全部成功)
   - **PSK密钥**: 123456
   - **支持的路由器IP**:
     - 192.168.40.207, 192.168.40.210, 192.168.40.237
     - 192.168.50.16, 192.168.50.40, 192.168.50.123
     - 192.168.40.242
     - **10.33.126.188** (新添加)

   **测试结果**:
   - ✅ IPSec SA建立成功 (modp3072 + AES256/192/128)
   - ✅ GRE隧道配置正确
   - ✅ 服务器端配置100%完成
   - ⚠️ 待路由器端DMVPN启动后完成连接测试

   **配置文件位置**:
   - Racoon配置: `/etc/racoon/racoon.conf`
   - PSK密钥: `/etc/racoon/psk.txt`
   - GRE隧道: `gre1` (remote any, local 192.168.50.48, key 123456)

   **VPN工具位置**:
   - 所有VPN相关工具已整理到 `scripts/vpn_tools/` 目录
   - 详细工具列表和使用说明见 `scripts/vpn_tools/README.md`

5. ✅ DMVPN NAT端口映射配置 **（新增）** (2025-11-27 18:30)
   - **场景**: 服务器192.168.50.48在私网，通过NAT公网IP 112.48.19.183提供服务
   - **问题**: 用户配置了非标准端口映射 (11025→500, 11026→4500)
   - **根本原因**: Racoon只能监听标准端口500/4500，无法配置自定义端口

   **解决方案**:
   - ✅ 创建NAT配置指南文档
   - ✅ 创建自动配置脚本 `configure_dmvpn_nat.py`
   - ✅ 配置Racoon为NAT-T force模式
   - ✅ 支持anonymous模式（接受任何公网IP的路由器连接）

   **关键配置**:
   - NAT端口映射必须使用标准端口: 500→500, 4500→4500
   - Racoon配置: `nat_traversal force;` (强制NAT-T模式)
   - 路由器Hub地址: 112.48.19.183 (公网IP)
   - 所有IPSec/GRE流量通过UDP 4500封装

   **VPN文档位置**:
   - 所有VPN相关文档已整理到 `docs/vpn/` 目录
   - 包括: DMVPN配置、NAT映射、GRE隧道、网络拓扑等

   **待验证**:
   - ⏳ NAT网关端口映射修改为标准端口
   - ⏳ 路由器配置Hub为公网IP
   - ⏳ 测试公网环境下的DMVPN连接

---
nn- **项目结构**: \ - 代码组织规范 (必读\!)n- **安装指南**: \ - 详细的安装和配置说明n---n**文档优化**: 已拆分为多个文件，主文档减少80%体积 🎉

## 📚 扩展文档

- **快速开始**: `QUICKSTART.md` - 5分钟快速上手指南
- **项目结构**: `PROJECT_STRUCTURE.md` - 代码组织规范 (必读!)
- **更新历史**: `CHANGELOG.md` - 完整的历史修改记录 (1794行)
- **安装指南**: `安装使用指南.md` - 详细的安装和配置说明

---
**最后更新**: 2025-12-11
**文档优化**: 已拆分为多个文件，主文档减少80%体积 🎉

## 🆕 路由器满配置功能 (2025-12-11)

**功能目标**: 自动识别路由器所有配置页面元素，生成Excel配置模板，实现批量配置

**开发状态**: 🚧 进行中（详见 `ROUTER_FULL_CONFIG_STATUS.md`）

**已完成**:
- ✅ 页面分析工具V4 - 成功识别3040个元素（32个页面）
- ✅ 文件清理工具 - 清理旧版本文件
- ✅ 满配置应用框架 - 基础框架完成

**当前问题**:
- V4数据结构平铺，缺少功能区域分组，用户难以填写配置值
- V5尝试结构化组织，但元素识别失败

**相关文件**:
- `scripts/analyze_router_pages_v4.py` - 可用的分析工具
- `scripts/analyze_router_pages_v5.py` - 结构化版本（待改进）
- `scripts/apply_full_config.py` - 满配置应用脚本（待完善）
- `config/router_full_analysis_v4_*.xlsx` - 完整元素数据
- `ROUTER_FULL_CONFIG_STATUS.md` - 详细状态文档

---
