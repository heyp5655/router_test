from .test_config import (
    TestConfig,
    TestRequest,
    TestMode,
    RouterConfig,
)

# 检查 TestResult 是否存在，如果不存在则定义它
try:
    from .test_config import TestResult
except ImportError:
    # 如果 TestResult 不存在，创建一个简单的实现
    from dataclasses import dataclass
    from typing import Dict, Any


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

# 检查 TestSummary 是否存在，如果不存在则定义它
try:
    from .test_config import TestSummary
except ImportError:
    # 如果 TestSummary 不存在，创建一个简单的实现
    from dataclasses import dataclass
    from typing import Dict, Any


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

__all__ = [
    'TestMode',
    'RouterConfig',
    'TestRequest',
    'TestConfig',
    'TestResult',
    'TestSummary'
]