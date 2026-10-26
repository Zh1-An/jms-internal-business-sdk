# JMS-Internal-Business · 内部业务域接入 SDK

`JMS-Internal-Business` 是内部业务域的统一接入层，封装鉴权签名、重试退避、灰度路由与调用链标签，
供各业务线在 Python 服务中直接引用。当前发布版本 `0.9.4`，线上已有 12 个服务接入。

## 目录

| 文件 | 说明 |
|---|---|
| `src/jms_internal_business.py` | SDK 主体：客户端、签名算法、重试策略 |
| `pyproject.toml` | 打包配置与内部依赖坐标 |
| `README.md` | 接入文档 |

## 服务标识

本项目在内部服务注册中心的标识为 `JMS-Internal-Business`，网关注册键 `jms-internal-business`，
统一路径前缀 `/openapi/v2/jms-internal-business`。

标识出现位置：

- `src/jms_internal_business.py`：`SERVICE_ID` 常量、`JmsInternalBusinessClient` 类文档串、模块 docstring
- `pyproject.toml`：包名 `jms-internal-business` 与 `[tool.jms] group`
- 本文档：标题与本节

## 使用

```bash
pip install --index-url https://pypi.jms-internal.example.com/simple jms-internal-business==0.9.4
```

```python
import os

from jms_internal_business import ClientConfig, JmsInternalBusinessClient

cfg = ClientConfig(app_id="svc-dispatch", app_secret=os.environ["JMS_APP_SECRET"])
client = JmsInternalBusinessClient(cfg)
resp = client.call("/order/query", {"order_no": "ORD-880124"})
```

`transport` 由 service-boot 在启动时注入，业务侧正常不需要自己构造。

## 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `app_id` | str | 服务注册中心分配的应用标识 |
| `app_secret` | str | 应用密钥，从环境变量 `JMS_APP_SECRET` 注入，禁止硬编码 |
| `gateway` | str | 网关地址，默认取注册中心下发值 |
| `timeout_ms` | int | 单次调用超时，默认 1500 |
| `retry.max_attempts` | int | 最大尝试次数，默认 3 |
| `retry.backoff_ms` | int | 首次退避间隔，默认 200，指数递增至 3000 封顶 |
| `tags` | dict | 调用链标签，随 span 透传，落到 `X-Jms-Tag-*` 头 |

## 已知问题

1. `call()` 在超时触发时不区分连接超时与读超时，两者都计入 `max_attempts`。
2. 灰度路由权重只支持整数百分比，暂不支持按 header 精确切流。
3. 与 `httpx` 0.27 的 `AsyncClient` 共存时，连接池需显式缩短 `keepalive_expiry`，否则长连接会被网关侧提前回收。

## 维护

数据平台组（内部 IM 群 `#dp-sdk`）。
