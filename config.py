"""配置管理模块 - 从 .env 文件加载并验证所有配置"""

import os
import logging
from typing import List, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """集中配置管理，从 .env 文件读取并验证"""

    # OpenAI API 配置
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"

    # 模型配置
    BIG_MODEL: str = "gpt-4.1"
    SMALL_MODEL: str = "gpt-4.1-mini"
    MAX_TOKENS: int = 65535

    # 模型路由
    BIG_PREFIXES: List[str] = []
    SMALL_PREFIXES: List[str] = []

    # 服务配置
    BASE_URL: Optional[str] = None
    PORT: int = 8082
    LOG_LEVEL: str = "WARNING"

    # 支持的 OpenAI 模型列表
    OPENAI_MODELS: List[str] = [
        "o3-mini",
        "o1",
        "o1-mini",
        "o1-pro",
        "gpt-4.5-preview",
        "gpt-4o",
        "gpt-4o-audio-preview",
        "chatgpt-4o-latest",
        "gpt-4o-mini",
        "gpt-4o-mini-audio-preview",
        "gpt-4.1",
        "gpt-4.1-mini",
    ]

    @classmethod
    def load(cls):
        """从环境变量加载配置"""
        # OpenAI API 配置
        cls.OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
        cls.OPENAI_API_BASE = os.environ.get(
            "OPENAI_API_BASE", "https://api.openai.com/v1"
        )

        # 模型配置
        cls.BIG_MODEL = os.environ.get("BIG_MODEL", "gpt-4.1")
        cls.SMALL_MODEL = os.environ.get("SMALL_MODEL", "gpt-4.1-mini")

        try:
            cls.MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "65535"))
        except ValueError:
            logger.warning(f"Invalid MAX_TOKENS, using default: 65535")
            cls.MAX_TOKENS = 65535

        # 模型路由配置
        cls.BIG_PREFIXES = [
            p.strip().lower()
            for p in os.environ.get("BIG_PREFIXES", "opus,sonnet").split(",")
            if p.strip()
        ]
        cls.SMALL_PREFIXES = [
            p.strip().lower()
            for p in os.environ.get("SMALL_PREFIXES", "haiku").split(",")
            if p.strip()
        ]

        # 服务配置
        cls._load_base_url()
        cls.PORT = int(os.environ.get("PORT", "8082"))
        cls.LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING")

    @classmethod
    def _load_base_url(cls):
        """加载并验证 BASE_URL"""
        base_url = os.environ.get("BASE_URL")
        if not base_url:
            cls.BASE_URL = None
            return

        parsed = urlparse(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            logger.warning(f"Invalid BASE_URL ignored: {base_url}")
            cls.BASE_URL = None
        else:
            cls.BASE_URL = base_url.rstrip("/")
            logger.info(f"Using BASE_URL: {cls.BASE_URL}")

    @classmethod
    def validate(cls) -> bool:
        """验证必需的配置项"""
        errors = []

        if not cls.OPENAI_API_BASE:
            errors.append("OPENAI_API_BASE is required")

        if not cls.BIG_MODEL:
            errors.append("BIG_MODEL is required")

        if not cls.SMALL_MODEL:
            errors.append("SMALL_MODEL is required")

        if cls.MAX_TOKENS <= 0:
            errors.append("MAX_TOKENS must be positive")

        if errors:
            for error in errors:
                logger.error(f"Config validation failed: {error}")
            return False

        return True

    @classmethod
    def print_config(cls):
        """打印当前配置（隐藏敏感信息）"""
        api_key_display = (
            f"{cls.OPENAI_API_KEY[:8]}..." if cls.OPENAI_API_KEY else "(empty)"
        )
        logger.info("=" * 50)
        logger.info("Configuration loaded:")
        logger.info(f"  OPENAI_API_BASE: {cls.OPENAI_API_BASE}")
        logger.info(f"  OPENAI_API_KEY:  {api_key_display}")
        logger.info(f"  BIG_MODEL:       {cls.BIG_MODEL}")
        logger.info(f"  SMALL_MODEL:     {cls.SMALL_MODEL}")
        logger.info(f"  MAX_TOKENS:      {cls.MAX_TOKENS}")
        logger.info(f"  BIG_PREFIXES:    {cls.BIG_PREFIXES}")
        logger.info(f"  SMALL_PREFIXES:  {cls.SMALL_PREFIXES}")
        logger.info(f"  BASE_URL:        {cls.BASE_URL or '(not set)'}")
        logger.info(f"  PORT:            {cls.PORT}")
        logger.info(f"  LOG_LEVEL:       {cls.LOG_LEVEL}")
        logger.info("=" * 50)

    @classmethod
    def set_litellm_api_key(cls, api_key: str):
        os.environ['OPENAI_API_KEY'] = api_key

    @classmethod
    def map_model(cls, model_name: str) -> str:
        """根据模型名称映射到实际使用的模型"""
        original_model = model_name
        clean = model_name

        if clean.startswith("anthropic/"):
            clean = clean[10:]
        elif clean.startswith("openai/"):
            clean = clean[7:]

        lower_clean = clean.lower()

        # 根据前缀路由
        if any(lower_clean.startswith(p) for p in cls.SMALL_PREFIXES):
            return f"openai/{cls.SMALL_MODEL}"

        if any(lower_clean.startswith(p) for p in cls.BIG_PREFIXES):
            return f"openai/{cls.BIG_MODEL}"

        # 已知 OpenAI 模型
        if clean in cls.OPENAI_MODELS and not model_name.startswith("openai/"):
            return f"openai/{clean}"

        # 透传
        if not model_name.startswith(("openai/", "anthropic/")):
            logger.debug(f"Model passthru: '{original_model}'")

        return model_name
