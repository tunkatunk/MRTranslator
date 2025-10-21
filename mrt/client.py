"""OpenAI client helpers with rate limiting, retries, and streaming support."""

from __future__ import annotations

import json
import random
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
    from openai import APIConnectionError, RateLimitError, APITimeoutError, APIError
except Exception:  # pragma: no cover - fallback when openai is unavailable
    OpenAI = None  # type: ignore

    class APIError(Exception):
        pass

    class RateLimitError(APIError):
        pass

    class APIConnectionError(APIError):
        pass

    class APITimeoutError(APIError):
        pass


class RateLimiter:
    """A simple thread-safe token bucket style limiter."""

    def __init__(self, max_calls: int, period: float) -> None:
        self.max_calls = max_calls
        self.period = period
        self._timestamps: List[float] = []
        self._lock = threading.Condition()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            while len(self._timestamps) >= self.max_calls:
                earliest = self._timestamps[0]
                delta = now - earliest
                if delta >= self.period:
                    self._timestamps.pop(0)
                    continue
                timeout = self.period - delta
                self._lock.wait(timeout)
                now = time.monotonic()
            self._timestamps.append(now)

            # Clean up timestamps outside the window
            cutoff = now - self.period
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.pop(0)

            self._lock.notify_all()


@dataclass
class CompletionResult:
    """Structured response returned by :class:`OpenAITranslatorClient`."""

    text: str
    raw: Any
    parsed: Dict[str, Any]


class StreamHandle:
    """Iterator wrapper that accumulates streamed text and exposes helpers."""

    def __init__(self, iterator: Iterator[str]) -> None:
        self._iterator = iterator
        self._chunks: List[str] = []

    def __iter__(self) -> Iterator[str]:
        for chunk in self._iterator:
            if chunk:
                self._chunks.append(chunk)
                yield chunk

    @property
    def text(self) -> str:
        return "".join(self._chunks)

    @property
    def parsed(self) -> Dict[str, Any]:
        return parse_model_output(self.text)


class OpenAITranslatorClient:
    """Opinionated OpenAI client tailored for MRTranslator."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        use_responses_api: bool = True,
        temperature: float = 0.4,
        max_retries: int = 4,
        backoff_base: float = 2.0,
        rate_limit: int = 60,
        rate_period: float = 60.0,
        client: Optional[Any] = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.use_responses_api = use_responses_api
        self._limiter = RateLimiter(rate_limit, rate_period)
        self._client = client or (OpenAI(api_key=api_key) if OpenAI is not None else None)
        if self._client is None:
            raise RuntimeError(
                "The openai package is required to use OpenAITranslatorClient. Install the official openai client."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> CompletionResult | StreamHandle:
        """Send a prompt to the configured OpenAI model.

        Parameters
        ----------
        prompt:
            The fully rendered prompt string.
        system:
            Optional system prompt. Ignored when using the Responses API since
            the instructions are included directly in the prompt payload.
        stream:
            When ``True`` the method returns a :class:`StreamHandle` whose
            iterator yields text deltas as they arrive.
        kwargs:
            Extra keyword arguments forwarded to the underlying OpenAI API call.
        """

        payload = self._build_payload(prompt, system=system, **kwargs)

        if stream:
            iterator = self._call_with_retry(payload, stream=True)
            return StreamHandle(iterator)

        response = self._call_with_retry(payload, stream=False)
        text = self._extract_text(response)
        return CompletionResult(text=text, raw=response, parsed=parse_model_output(text))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _call_with_retry(self, payload: Dict[str, Any], *, stream: bool) -> Any:
        attempt = 0
        last_error: Optional[Exception] = None
        while attempt <= self.max_retries:
            self._limiter.acquire()
            try:
                if self.use_responses_api:
                    if stream:
                        return self._stream_responses(payload)
                    return self._client.responses.create(**payload)
                if stream:
                    return self._stream_chat_completions(payload)
                return self._client.chat.completions.create(**payload)
            except (RateLimitError, APITimeoutError, APIConnectionError, APIError) as exc:
                last_error = exc
                sleep_for = (self.backoff_base ** attempt) + random.uniform(0, 0.5)
                time.sleep(sleep_for)
                attempt += 1
        raise RuntimeError("OpenAI request failed after retries") from last_error

    # Payload builders -------------------------------------------------
    def _build_payload(self, prompt: str, *, system: str | None = None, **kwargs: Any) -> Dict[str, Any]:
        base_kwargs = {
            "model": self.model,
            "temperature": self.temperature,
        }
        base_kwargs.update(kwargs)

        if self.use_responses_api:
            return {
                **base_kwargs,
                "input": prompt,
            }

        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return {
            **base_kwargs,
            "messages": messages,
        }

    # Streaming --------------------------------------------------------
    def _stream_responses(self, payload: Dict[str, Any]) -> Iterator[str]:
        stream = self._client.responses.create(stream=True, **payload)
        return self._consume_stream(stream, mode="responses")

    def _stream_chat_completions(self, payload: Dict[str, Any]) -> Iterator[str]:
        stream = self._client.chat.completions.create(stream=True, **payload)
        return self._consume_stream(stream, mode="chat")

    def _consume_stream(self, stream: Iterable[Any], *, mode: str) -> Iterator[str]:
        def generator() -> Iterator[str]:
            for event in stream:
                data = _object_to_dict(event)
                chunk = _extract_stream_delta(data, mode=mode)
                if chunk:
                    yield chunk
        return generator()

    # Response parsing -------------------------------------------------
    def _extract_text(self, response: Any) -> str:
        data = _object_to_dict(response)
        if not data:
            return ""

        if self.use_responses_api:
            if "output_text" in data:
                if isinstance(data["output_text"], list):
                    return "".join(data["output_text"])
                return str(data["output_text"])
            outputs = data.get("output", [])
            for item in outputs or []:
                for content in item.get("content", []):
                    if content.get("type") in {"output_text", "text"}:
                        text = content.get("text")
                        if text:
                            return text
            if "text" in data:
                return str(data["text"])

        # Chat completions fallback
        choices = data.get("choices")
        if choices:
            choice0 = choices[0]
            message = choice0.get("message")
            if message:
                return message.get("content", "")
            if "text" in choice0:
                return str(choice0["text"])

        return str(response)


# ----------------------------------------------------------------------
# Output parsing helpers
# ----------------------------------------------------------------------

def _object_to_dict(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    for attr in ("model_dump", "to_dict", "dict"):
        method = getattr(obj, attr, None)
        if callable(method):
            try:
                return method()
            except Exception:  # pragma: no cover - best effort
                continue
    return {}


def _extract_stream_delta(event: Dict[str, Any], *, mode: str) -> str:
    if not event:
        return ""

    if mode == "chat":
        choices = event.get("choices")
        if choices:
            delta = choices[0].get("delta")
            if isinstance(delta, dict):
                return delta.get("content", "") or ""
            if isinstance(delta, str):
                return delta
        return ""

    # Responses API streaming events
    event_type = event.get("type")
    if event_type == "response.output_text.delta":
        return event.get("delta", "") or ""
    if event_type == "response.output_text":
        return event.get("text", "") or ""
    if "text" in event:
        return str(event["text"])
    return ""


# ----------------------------------------------------------------------
# Output parsing utilities
# ----------------------------------------------------------------------

import re


def parse_model_output(text: str) -> Dict[str, Any]:
    """Parse Markdown/JSON output generated by the model."""

    result: Dict[str, Any] = {
        "raw": text,
        "sections": _parse_markdown_sections(text),
    }

    json_payload = _extract_json_payload(text)
    if json_payload is not None:
        result["json"] = json_payload

    return result


def _extract_json_payload(text: str) -> Optional[Any]:
    fenced = _extract_fenced_json(text)
    candidates = [fenced, text.strip()]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _extract_fenced_json(text: str) -> Optional[str]:
    fence = re.search(r"```json\s*(.*?)```", text, flags=re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return None


def _parse_markdown_sections(text: str) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$", flags=re.MULTILINE)
    matches = list(heading_pattern.finditer(text))
    if not matches:
        return sections

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        title = match.group(2).strip()
        sections[title] = text[start:end].strip()
    return sections


__all__ = [
    "OpenAITranslatorClient",
    "CompletionResult",
    "StreamHandle",
    "parse_model_output",
    "RateLimiter",
]
