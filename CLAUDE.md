# ROUTER_TEST - 路由器自动化测试框架

## ⚠️ 重要提示
**请先阅读 `PROJECT_STRUCTURE.md` 文档了解项目结构规范!**

该文档定义了代码组织规范、文件放置规则、导入路径规范等重要内容。

## 项目概述
基于 Flask 的路由器自动化测试平台，支持 WAN、蜂窝网络、MQTT等功能测试，通过 Web 界面控制测试流程。

## 技术栈
- Python 3.14
- Flask 2.3.3 (Web界面)
- Selenium (浏览器自动化)
- PySerial (串口通信)
- paho-mqtt (MQTT通信)
- PyYAML (配置管理)
- PowerShell (网卡IP获取)

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

## 运行命令
```bash
# 安装依赖
pip install -r requirements.txt

# 运行 (推荐使用bat脚本自动获取管理员权限)
start_admin.bat

# 或手动以管理员身份运行
python app.py
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

### MQTT测试
- **MQTT路由器命令测试** (`mqtt_test/mqtt_router_command_reboot_test.py`)

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
**测试名称**: MQTT下发命令指令给路由器及设备回复

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
**最后整理时间**: 2025-11-25

**整理内容**:
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

---
**最后更新**: 2025-11-25
