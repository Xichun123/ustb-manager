"""自定义异常类"""


class BYYTSessionExpired(Exception):
    """BYYT系统会话已过期，需要重新登录"""
    pass
