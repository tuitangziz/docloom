"""Small replaceable transports. Credentials are never written or logged here."""
from dataclasses import dataclass, field
import ipaddress
import json
from typing import Protocol
from urllib.parse import urlsplit

import httpx

MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class ProviderError(ValueError):
    pass


class ChatProvider(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


def validate_url(value: str, *, local_only: bool = False) -> str:
    value = value.strip().rstrip("/")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ProviderError("服务地址格式不正确。") from exc
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ProviderError("地址不能包含密钥、用户名、查询参数或片段。")
    try:
        loopback = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        loopback = parsed.hostname == "localhost"
    if local_only and not loopback:
        raise ProviderError("Ollama 适配器只允许本机回环地址。")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
        raise ProviderError("远程 API 必须使用 HTTPS；HTTP 仅允许本机地址。")
    if port == 0:
        raise ProviderError("端口不能为 0。")
    # Avoid resolving localhost through an unexpected proxy/DNS configuration.
    if parsed.hostname == "localhost":
        value = value.replace("localhost", "127.0.0.1", 1)
    return value


def _request(url: str, payload: dict, headers: dict, transport=None) -> dict:
    try:
        # No environment proxy, redirects, automatic retries, cookies or file logging.
        with httpx.Client(timeout=httpx.Timeout(120, connect=10), trust_env=False, follow_redirects=False, transport=transport) as client:
            with client.stream("POST", url, json=payload, headers=headers) as response:
                if not 200 <= response.status_code < 300:
                    explanations = {401: "密钥无效或未授权", 403: "服务拒绝访问", 404: "地址或模型不存在", 429: "额度不足或请求过于频繁"}
                    detail = explanations.get(response.status_code, "请检查服务状态与配置")
                    raise ProviderError(f"API 返回 HTTP {response.status_code}：{detail}。")
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise ProviderError("API 响应过大，已停止读取。")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ProviderError("API 返回格式不正确。")
        return result
    except ProviderError:
        raise
    except httpx.TimeoutException as exc:
        raise ProviderError("API 请求超时。可减少检索片段或检查服务状态。") from exc
    except (httpx.HTTPError, ValueError) as exc:
        # Do not display response bodies/URLs: some services echo prompts or secrets.
        raise ProviderError("无法连接服务或读取响应，请检查网络和配置。") from exc


@dataclass
class CompatibleAPI:
    base_url: str
    model: str
    api_key: str = field(repr=False)
    transport: object = field(default=None, repr=False)
    modern_parameters: bool = False

    def __post_init__(self):
        self.base_url = validate_url(self.base_url)
        self.model = self.model.strip()
        if not self.model or len(self.model) > 180 or not self.api_key.strip():
            raise ProviderError("请填写模型名和 API 密钥。")

    def complete(self, messages: list[dict[str, str]]) -> str:
        if self.modern_parameters:
            messages = [{**message, "role": "developer" if message["role"] == "system" else message["role"]} for message in messages]
        limit_key = "max_completion_tokens" if self.modern_parameters else "max_tokens"
        result = _request(self.base_url + "/chat/completions", {"model": self.model, "messages": messages, "stream": False, limit_key: 1200}, {"Authorization": "Bearer " + self.api_key}, self.transport)
        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("此服务没有返回兼容的聊天响应。") from exc
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("模型未返回文本。请使用支持文本聊天的模型。")
        return content


@dataclass
class OllamaProvider:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen3.5:4b"
    transport: object = field(default=None, repr=False)

    def __post_init__(self):
        self.base_url = validate_url(self.base_url, local_only=True)
        if not self.model.strip() or "cloud" in self.model.lower():
            raise ProviderError("请使用已下载的本地模型，不能选择 cloud 模型。")

    def _check_local(self):
        info = _request(self.base_url + "/api/show", {"model": self.model}, {}, self.transport)
        if info.get("remote_host") or info.get("remote_model"):
            raise ProviderError("检测到远程模型配置；请切换为本地模型。")

    def complete(self, messages: list[dict[str, str]]) -> str:
        self._check_local()
        result = _request(self.base_url + "/api/chat", {"model": self.model, "messages": messages, "stream": False, "format": "json", "think": False, "options": {"num_ctx": 8192, "num_predict": 1200, "temperature": 0.1}, "keep_alive": "5m"}, {}, self.transport)
        message = result.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("本地模型没有返回文本。")
        return content

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._check_local()
        result = _request(self.base_url + "/api/embed", {"model": self.model, "input": texts, "truncate": False}, {}, self.transport)
        vectors = result.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise ProviderError("嵌入模型返回的向量数量不正确。")
        return vectors
