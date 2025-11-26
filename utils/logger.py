import logging
import os
from datetime import datetime


def get_logger(router_model: str, test_case_name: str) -> logging.Logger:
    """获取指定路由器型号和测试用例的日志器"""

    # 创建日志目录
    log_dir = f"logs/{router_model}"
    os.makedirs(log_dir, exist_ok=True)

    # 日志文件名
    log_file = f"{log_dir}/{test_case_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # 创建logger
    logger = logging.getLogger(f"{router_model}.{test_case_name}")
    logger.setLevel(logging.INFO)

    # 避免重复添加handler
    if not logger.handlers:
        # 文件handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)

        # 控制台handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger