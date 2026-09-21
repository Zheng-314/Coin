# ==============================================================================
# 统一日志配置
# ==============================================================================
import logging
import sys


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    创建带格式化的logger实例

    Args:
        name: logger名称，通常用模块名
        level: 日志级别，默认INFO

    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # 控制台handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # 格式：时间 | 级别 | 模块名 | 消息
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-7s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
