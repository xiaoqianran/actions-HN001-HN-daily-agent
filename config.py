"""
配置模块
负责环境变量加载和网络配置初始化
"""
import os
from typing import Dict, Optional
from dotenv import load_dotenv

# 模块导入时自动加载环境变量
load_dotenv()

# 禁用代理的常量配置
_NO_PROXY: Dict[str, Optional[str]] = {"http": None, "https": None}


def get_deepseek_key() -> str:
    """获取 DeepSeek API Key"""
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("环境变量 DEEPSEEK_API_KEY 未设置")
    return key


def get_pushplus_token() -> str:
    """获取 PushPlus Token"""
    token = os.getenv("PUSHPLUS_TOKEN")
    if not token:
        raise ValueError("环境变量 PUSHPLUS_TOKEN 未设置")
    return token


def get_no_proxy() -> Dict[str, Optional[str]]:
    """获取 NO_PROXY 配置字典，用于禁用代理"""
    return _NO_PROXY
