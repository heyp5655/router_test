from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any


class TestMode(Enum):
    REGRESSION = "regression"
    ALL = "all"
    SPECIFIC = "specific"
    FULL = "full"  # 为了向后兼容


@dataclass
class RouterConfig:
    router_ip: str
    username: str
    password: str
    model: str
    module_type: str = "auto"  # 添加模组类型字段
    serial_port: str = "COM3"  # 本地系统串口配置
    serial_baudrate: int = 115200  # 串口波特率
    industrial_serial_port: str = "COM4"  # 本地工业串口485配置
    mqtt_broker: str = "192.168.50.36"  # MQTT服务器IP
    mqtt_port: int = 1883  # MQTT端口
    mqtt_username: str = "admin"  # MQTT用户名
    mqtt_password: str = "password"  # MQTT密码
    modbus_server_ip: str = "192.168.1.100"  # Modbus Server IP (PC IP，与路由器同网段)
    modbus_port: int = 5020  # Modbus端口


@dataclass
class TestConfig:
    router_config: RouterConfig
    test_mode: TestMode
    timeout: int = 300  # 添加超时字段
    restore_default: bool = True  # 添加恢复默认字段


@dataclass
class TestRequest:
    router_config: RouterConfig
    test_mode: TestMode
    selected_cases: List[str]
    timeout: int = 300  # 添加超时字段
    restore_default: bool = True  # 添加恢复默认字段


# 添加 TestResult 类
@dataclass
class TestResult:
    test_name: str
    status: str  # PASS, FAIL, ERROR
    message: str
    duration: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'test_name': self.test_name,
            'status': self.status,
            'message': self.message,
            'duration': self.duration
        }


# 添加 TestSummary 类
@dataclass
class TestSummary:
    total: int
    passed: int
    failed: int
    error: int
    duration: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total': self.total,
            'passed': self.passed,
            'failed': self.failed,
            'error': self.error,
            'duration': self.duration
        }