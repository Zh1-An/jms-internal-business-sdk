# -*- coding: utf-8 -*-
"""JMS-Internal-Business 内部业务域接入 SDK。

Copyright (c) 2021-2026 JMS-Internal-Business Platform Team. All rights reserved.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

__version__ = "0.9.4"

SDK_NAME = "jms_internal_business"
SERVICE_ID = "JMS-Internal-Business"
API_VERSION = "v2"
REGISTRY_KEY = "jms-internal-business"
DEFAULT_GATEWAY = "https://gw.jms-internal.example.com"
SIGN_ALGO = "HMAC-SHA256"
ENV_SECRET = "JMS_APP_SECRET"


@dataclass
class RetryPolicy:
    """指数退避重试策略。"""

    max_attempts: int = 3
    backoff_ms: int = 200
    max_backoff_ms: int = 3000

    def delay(self, attempt: int) -> float:
        step = self.backoff_ms * (2 ** max(attempt - 1, 0))
        return min(step, self.max_backoff_ms) / 1000.0


@dataclass
class ClientConfig:
    """客户端配置。``app_secret`` 缺省时从环境变量读取。"""

    app_id: str
    app_secret: str = ""
    gateway: str = DEFAULT_GATEWAY
    timeout_ms: int = 1500
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.app_secret:
            self.app_secret = os.environ.get(ENV_SECRET, "")
        if not self.gateway.startswith("https://"):
            raise ValueError("gateway 必须使用 https")


def canonical_body(payload: Optional[Dict[str, Any]]) -> str:
    if payload is None:
        return ""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sign(app_secret: str, method: str, path: str, body: str, ts: int) -> str:
    """按 HMAC-SHA256 计算请求签名，结果写入 ``X-Jms-Sign`` 头。"""
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    payload = "\n".join([method.upper(), path, str(ts), digest])
    return hmac.new(
        app_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def build_headers(cfg: ClientConfig, method: str, path: str, body: str) -> Dict[str, str]:
    ts = int(time.time())
    headers = {
        "X-Jms-App": cfg.app_id,
        "X-Jms-Service": SERVICE_ID,
        "X-Jms-Ts": str(ts),
        "X-Jms-Sign-Version": API_VERSION,
        "X-Jms-Sign": sign(cfg.app_secret, method, path, body, ts),
        "Content-Type": "application/json",
    }
    for key, value in cfg.tags.items():
        headers["X-Jms-Tag-" + key] = str(value)
    return headers


class JmsInternalBusinessClient:
    """JMS-Internal-Business 统一客户端。

    调用链为「业务服务 -> 内部网关 -> 业务域实例」，网关按 ``REGISTRY_KEY`` 做灰度分流。
    """

    def __init__(self, config: ClientConfig, transport: Optional[Any] = None) -> None:
        self.config = config
        self.transport = transport

    def call(
        self,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        method: str = "POST",
    ) -> Dict[str, Any]:
        if self.transport is None:
            raise NotImplementedError("transport 未注入，生产环境由 service-boot 装配")
        body = canonical_body(payload)
        headers = build_headers(self.config, method, path, body)
        attempt = 0
        while True:
            attempt += 1
            try:
                return self.transport.request(
                    method,
                    self.config.gateway + path,
                    body=body,
                    headers=headers,
                    timeout=self.config.timeout_ms / 1000.0,
                )
            except (ConnectionError, TimeoutError):
                if attempt >= self.config.retry.max_attempts:
                    raise
                time.sleep(self.config.retry.delay(attempt))

    def health(self) -> Dict[str, Any]:
        return self.call("/healthz", None, method="GET")
