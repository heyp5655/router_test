# 项目结构规范

本文档定义了 ROUTER_TEST 项目的目录结构和代码组织规范。所有开发者和AI助手必须遵循此规范。

## 目录结构总览

```
E:\GIT\ROUTER_TEST\
├── app.py                  # Flask Web应用主入口
├── main.py                 # 程序启动入口
├── start_admin.bat         # 管理员权限启动脚本
├── requirements.txt        # Python依赖包列表
├── CLAUDE.md              # 项目说明文档(供Claude参考)
├── PROJECT_STRUCTURE.md   # 本文档 - 项目结构规范
│
├── config/                # 配置文件目录
│   ├── default_config.yaml      # 默认配置
│   ├── router_models.yaml       # 路由器型号配置
│   └── __init__.py
│
├── core/                  # 核心模块目录
│   ├── config_loader.py         # 配置加载器
│   ├── result_manager.py        # 测试结果管理器
│   ├── router_client.py         # 路由器客户端(核心类)
│   ├── test_runner.py           # 测试运行器
│   └── __init__.py
│
├── test_cases/           # 测试用例目录(所有测试用例必须在此)
│   ├── base_test.py            # 测试基类
│   ├── __init__.py
│   │
│   ├── wan_tests/              # WAN功能测试
│   │   ├── pppoe_test.py
│   │   ├── static_ip.py
│   │   └── __init__.py
│   │
│   ├── cellular_tests/         # 蜂窝网络测试
│   │   ├── cellular_band_test.py
│   │   ├── cellular_netmask_test.py
│   │   ├── cellular_status_verification_test.py
│   │   ├── cellular_supported_network_standards.py
│   │   ├── pin_function_test.py
│   │   ├── SMS_Center_test.py
│   │   └── __init__.py
│   │
│   ├── mqtt_test/              # MQTT功能测试
│   │   ├── mqtt_router_command_reboot_test.py
│   │   ├── mqttx_automation.py      # MQTTX自动化辅助工具
│   │   ├── mqttx_controller.py      # MQTTX数据库控制器
│   │   ├── mqttx_ui_controller.py   # MQTTX UI控制器
│   │   └── __init__.py
│   │
│   ├── industrial_tests/       # 工业协议测试
│   │   └── __init__.py
│   │
│   └── app_tests/              # 应用程序测试(Python SDK等)
│       ├── python_sdk_normal_install_test.py
│       ├── python_sdk_abnormal_install_test.py
│       ├── python_sdk_stability_test.py
│       ├── python_module_check_test.py
│       ├── paho_mqtt_library_test.py
│       ├── pymodbus_library_test.py
│       ├── pyserial_library_test.py
│       └── __init__.py
│
├── utils/                # 工具类目录(所有通用工具必须在此)
│   ├── logger.py               # 日志工具
│   ├── network_utils.py        # PC网络工具(设置网卡IP、测试连通性等)
│   ├── mqtt_client.py          # MQTT测试客户端工具
│   ├── excel_exporter.py       # Excel导出工具
│   ├── report_generator.py     # 报告生成器
│   └── __init__.py
│
├── models/               # 数据模型目录
│   ├── test_config.py          # 测试配置模型
│   └── __init__.py
│
├── scripts/              # 独立脚本目录
│   ├── create_dmvpn_doc.py     # DMVPN文档生成脚本
│   └── read_excel.py           # Excel读取脚本
│
├── templates/            # Flask HTML模板
│   └── index.html
│
├── logs/                 # 测试日志目录
├── reports/              # 测试报告目录
└── results/              # 测试结果目录
```

## 代码组织规范

### 1. 测试用例放置规则 (test_cases/)

**规则**: 所有测试用例必须放在 `test_cases/` 目录下,按功能分类到子目录中。

**分类标准**:
- `wan_tests/` - WAN接口相关测试(PPPoE、静态IP、DHCP等)
- `cellular_tests/` - 蜂窝网络相关测试(PIN、网络制式、信号等)
- `mqtt_test/` - MQTT协议相关测试
- `industrial_tests/` - 其他工业协议测试(Modbus、OPC UA等)
- `app_tests/` - 应用程序测试(Python SDK、第三方库等)

**要求**:
- 所有测试类必须继承 `base_test.BaseTest`
- 测试文件命名格式: `功能描述_test.py`
- 每个子目录必须有 `__init__.py` 文件

### 2. 工具类放置规则 (utils/)

**规则**: 所有可复用的工具类、辅助函数必须放在 `utils/` 目录下。

**包含内容**:
- `logger.py` - 日志记录工具
- `network_utils.py` - PC网络操作工具(设置网卡、检测连通性)
- `mqtt_client.py` - MQTT测试客户端
- `excel_exporter.py` - Excel导出工具
- `report_generator.py` - 报告生成器

**要求**:
- 工具类必须是通用的、可复用的
- 不包含具体测试逻辑
- 提供清晰的文档字符串

### 3. 核心模块规则 (core/)

**规则**: 核心框架代码放在 `core/` 目录下。

**包含内容**:
- `router_client.py` - 路由器Web客户端,包含所有与路由器交互的方法:
  - Web登录和导航
  - WAN配置(PPPoE, 静态IP)
  - 蜂窝网络配置和状态检查
  - AT命令执行
  - Ping测试
  - UI元素操作(click, input, get_text等)
- `test_runner.py` - 测试执行器
- `config_loader.py` - 配置加载器
- `result_manager.py` - 结果管理器

**要求**:
- 不要随意添加新文件到 core/ 目录
- router_client.py 应包含所有路由器交互方法
- 保持核心模块的稳定性

### 4. 独立脚本规则 (scripts/)

**规则**: 独立运行的脚本文件放在 `scripts/` 目录下。

**包含内容**:
- 文档生成脚本
- 数据处理脚本
- 一次性运行的工具脚本

**不包含**:
- 测试用例(应放在 test_cases/)
- 可复用工具类(应放在 utils/)

## 导入路径规范

### 标准导入格式

```python
# 从test_cases导入
from test_cases.base_test import BaseTest

# 从utils导入工具类
from utils.network_utils import network_utils
from utils.mqtt_client import MQTTTestClient
from utils.logger import logger

# 从core导入核心类
from core.router_client import RouterClient
from core.config_loader import ConfigLoader

# 从models导入数据模型
from models.test_config import RouterConfig
```

### 相对导入规则

- **禁止使用**: `from . import xxx` 或 `from .. import xxx`
- **必须使用**: 从项目根目录的绝对导入

### 导入顺序

1. 标准库导入
2. 第三方库导入
3. 项目内部导入(按 models -> core -> utils -> test_cases 顺序)

## 文件命名规范

### 测试用例文件
- 格式: `功能描述_test.py`
- 示例: `pppoe_test.py`, `cellular_netmask_test.py`
- 类名: 使用大驼峰命名,示例: `PppoeTest`, `CellularNetmaskTest`

### 工具类文件
- 格式: `工具用途_工具类型.py`
- 示例: `network_utils.py`, `mqtt_client.py`
- 类名: 使用大驼峰命名,示例: `NetworkUtils`, `MQTTTestClient`

### 配置文件
- 格式: `功能_config.yaml`
- 示例: `default_config.yaml`, `router_models.yaml`

## 新增功能开发流程

### 添加新测试用例
1. 确定测试类型,选择对应的子目录
2. 创建测试文件,继承 `BaseTest`
3. 在对应子目录的 `__init__.py` 中导出测试类
4. 如需新的工具类,添加到 `utils/`
5. 如需路由器新操作,添加方法到 `core/router_client.py`

### 添加新工具类
1. 在 `utils/` 目录创建文件
2. 编写清晰的类文档和方法文档
3. 在 `utils/__init__.py` 中导出
4. 更新本文档的工具类列表

### 扩展 router_client 功能
1. 在 `core/router_client.py` 中添加新方法
2. 保持方法命名清晰、功能单一
3. 添加详细的文档字符串
4. 私有方法使用 `_` 前缀

## 注意事项

### 禁止操作
1. ❌ 不要在根目录创建测试用例文件
2. ❌ 不要在 test_cases/ 之外创建测试用例
3. ❌ 不要在 utils/ 之外创建工具类
4. ❌ 不要随意修改 core/ 目录结构
5. ❌ 不要使用相对导入

### 推荐做法
1. ✅ 所有测试用例放在 test_cases/ 对应子目录
2. ✅ 所有工具类放在 utils/
3. ✅ 路由器操作方法统一放在 router_client.py
4. ✅ 使用绝对导入路径
5. ✅ 添加清晰的文档字符串

## 维护说明

本文档应在以下情况更新:
- 添加新的目录分类
- 修改代码组织规范
- 添加重要的工具类或核心模块
- 发现规范遗漏或不清晰的地方

**最后更新**: 2025-11-25
**维护者**: 项目团队
