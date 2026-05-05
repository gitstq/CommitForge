"""
AI-powered commit message generation for CommitForge.

Supports multiple LLM backends: OpenAI, Anthropic, DeepSeek, Ollama (local),
and Google Gemini. Uses urllib.request for HTTP requests (no external deps).
"""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

from .conventional import ConventionalCommit, parse_commit, STANDARD_TYPES
from .git_analyzer import ChangeAnalysis, FileChange


# ─── Constants ────────────────────────────────────────────────────────────────

# Default system prompt for commit message generation
DEFAULT_SYSTEM_PROMPT_EN = """You are an expert at writing Git commit messages following the Conventional Commits specification (https://www.conventionalcommits.org/).

Your task is to generate a concise, clear, and well-structured commit message based on the provided git diff and change analysis.

Rules:
1. Use the format: type(scope): description
2. Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
3. Description should be lowercase, imperative mood, no period at end
4. Keep subject line under 72 characters
5. Add a body paragraph explaining WHAT and WHY if the change is non-trivial
6. Use BREAKING CHANGE: in footer if there are breaking changes
7. Be specific and descriptive, avoid vague messages like "update code"
8. Focus on the intent of the change, not the mechanics

Respond with ONLY the commit message, no explanation or markdown formatting."""

DEFAULT_SYSTEM_PROMPT_ZH = """你是一位 Git 提交消息编写专家，遵循 Conventional Commits 规范 (https://www.conventionalcommits.org/)。

你的任务是根据提供的 git diff 和变更分析，生成简洁、清晰、结构良好的提交消息。

规则：
1. 使用格式：type(scope): description
2. 类型：feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
3. 描述使用小写，祈使语气，末尾不加句号
4. 主题行控制在 72 字符以内
5. 如果变更较复杂，添加正文段落解释变更内容和原因
6. 如果有破坏性变更，在页脚使用 BREAKING CHANGE:
7. 要具体和描述性，避免"更新代码"这类模糊消息
8. 关注变更的意图，而非实现细节

只输出提交消息本身，不要包含任何解释或 markdown 格式。"""

# Timeout for API requests (seconds)
REQUEST_TIMEOUT = 30

# Maximum diff content length to send (characters)
MAX_DIFF_LENGTH = 15000


# ─── HTTP Utilities ───────────────────────────────────────────────────────────

def _make_request(url: str, data: Optional[bytes] = None,
                  headers: Optional[Dict[str, str]] = None,
                  method: str = "POST", timeout: int = REQUEST_TIMEOUT) -> Tuple[int, str]:
    """Make an HTTP request using urllib.

    Args:
        url: The URL to request.
        data: Optional request body bytes.
        headers: Optional request headers.
        method: HTTP method.
        timeout: Request timeout in seconds.

    Returns:
        Tuple of (status_code, response_body_string).

    Raises:
        urllib.error.URLError: On network errors.
        ValueError: On non-2xx responses.
    """
    if headers is None:
        headers = {}

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, body
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        return e.code, body


def _make_streaming_request(url: str, data: Optional[bytes] = None,
                             headers: Optional[Dict[str, str]] = None,
                             method: str = "POST",
                             timeout: int = REQUEST_TIMEOUT) -> Generator[str, None, None]:
    """Make a streaming HTTP request, yielding chunks of the response.

    Args:
        url: The URL to request.
        data: Optional request body bytes.
        headers: Optional request headers.
        method: HTTP method.
        timeout: Request timeout in seconds.

    Yields:
        Chunks of response text.
    """
    if headers is None:
        headers = {}

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            buffer = ""
            while True:
                chunk = response.read(1)
                if not chunk:
                    break
                char = chunk.decode("utf-8", errors="replace")
                buffer += char
                # Yield complete lines
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    yield line
            if buffer:
                yield buffer
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        yield f"ERROR: HTTP {e.code} - {error_body}"


def _retry_request(request_fn: Callable, max_retries: int = 3,
                    delay: float = 1.0) -> Any:
    """Execute a request with retry logic.

    Args:
        request_fn: Function that performs the request.
        max_retries: Maximum number of retry attempts.
        delay: Delay between retries in seconds (exponential backoff).

    Returns:
        The result of the request function.

    Raises:
        Exception: If all retries are exhausted.
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return request_fn()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                ConnectionError, OSError) as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt)
                time.sleep(wait_time)

    raise last_error  # type: ignore


# ─── Diff Context Builder ─────────────────────────────────────────────────────

def build_diff_context(analysis: ChangeAnalysis, lang: str = "en") -> str:
    """Build a context string from change analysis for AI prompt.

    Args:
        analysis: The change analysis result.
        lang: Language ('en' or 'zh').

    Returns:
        Formatted context string for the AI prompt.
    """
    lines: List[str] = []

    if lang == "zh":
        lines.append("## 变更分析")
        lines.append(f"- 文件数量: {analysis.total_files}")
        lines.append(f"- 插入行数: +{analysis.total_insertions}")
        lines.append(f"- 删除行数: -{analysis.total_deletions}")
        lines.append(f"- 推断类型: {analysis.commit_type}")
        if analysis.scope:
            lines.append(f"- 推断范围: {analysis.scope}")
        if analysis.has_breaking_change:
            lines.append("- 可能包含破坏性变更")
        lines.append("")
        lines.append("## 变更文件")
    else:
        lines.append("## Change Analysis")
        lines.append(f"- Files changed: {analysis.total_files}")
        lines.append(f"- Insertions: +{analysis.total_insertions}")
        lines.append(f"- Deletions: -{analysis.total_deletions}")
        lines.append(f"- Detected type: {analysis.commit_type}")
        if analysis.scope:
            lines.append(f"- Detected scope: {analysis.scope}")
        if analysis.has_breaking_change:
            lines.append("- Potential breaking changes detected")
        lines.append("")
        lines.append("## Changed Files")

    for f in analysis.files:
        status = f.status.upper()
        lines.append(f"- [{status}] {f.path} (+{f.added_lines}/-{f.removed_lines})")

    lines.append("")

    # Add diff content (truncated if needed)
    if lang == "zh":
        lines.append("## Diff 内容")
    else:
        lines.append("## Diff Content")

    for f in analysis.files:
        if f.is_binary:
            continue
        if f.diff_content:
            # Truncate individual file diffs
            diff_lines = f.diff_content.split("\n")
            if len(diff_lines) > 200:
                diff_lines = diff_lines[:100] + ["... (truncated) ..."] + diff_lines[-50:]
            lines.append(f"\n--- {f.path} ---")
            lines.extend(diff_lines)

    result = "\n".join(lines)

    # Truncate overall if too long
    if len(result) > MAX_DIFF_LENGTH:
        result = result[:MAX_DIFF_LENGTH] + "\n... (diff truncated due to length) ..."

    return result


def build_user_prompt(analysis: ChangeAnalysis, lang: str = "en",
                      force_type: Optional[str] = None,
                      force_scope: Optional[str] = None,
                      custom_prompt: Optional[str] = None) -> str:
    """Build the user prompt for AI commit message generation.

    Args:
        analysis: The change analysis result.
        lang: Language ('en' or 'zh').
        force_type: Optional forced commit type.
        force_scope: Optional forced commit scope.
        custom_prompt: Optional custom user prompt.

    Returns:
        User prompt string.
    """
    if custom_prompt:
        return custom_prompt

    context = build_diff_context(analysis, lang)

    if lang == "zh":
        prompt = f"""请根据以下 git 变更生成一个 Conventional Commits 格式的提交消息。

{context}

"""
        if force_type:
            prompt += f"请使用类型: {force_type}\n"
        if force_scope:
            prompt += f"请使用范围: {force_scope}\n"

        prompt += "\n请只输出提交消息本身："
    else:
        prompt = f"""Generate a Conventional Commits formatted commit message for the following git changes.

{context}

"""
        if force_type:
            prompt += f"Use commit type: {force_type}\n"
        if force_scope:
            prompt += f"Use scope: {force_scope}\n"

        prompt += "\nOutput ONLY the commit message:"

    return prompt


# ─── Base AI Backend ──────────────────────────────────────────────────────────

class AIBackend:
    """Base class for AI backends."""

    name: str = "base"

    def __init__(self, api_key: str = "", base_url: str = "",
                 model: str = "", temperature: float = 0.7,
                 max_tokens: int = 512, system_prompt: str = "",
                 retry_count: int = 3, retry_delay: float = 1.0):
        """Initialize the AI backend.

        Args:
            api_key: API key for authentication.
            base_url: Base URL for the API.
            model: Model name to use.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            system_prompt: Custom system prompt.
            retry_count: Number of retry attempts.
            retry_delay: Delay between retries.
        """
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._system_prompt = system_prompt
        self._retry_count = retry_count
        self._retry_delay = retry_delay

    def generate(self, prompt: str) -> str:
        """Generate a commit message from a prompt.

        Args:
            prompt: The user prompt.

        Returns:
            Generated commit message string.
        """
        raise NotImplementedError("Subclasses must implement generate()")

    def generate_streaming(self, prompt: str) -> Generator[str, None, None]:
        """Generate a commit message with streaming output.

        Args:
            prompt: The user prompt.

        Yields:
            Chunks of generated text.
        """
        raise NotImplementedError("Subclasses must implement generate_streaming()")

    def validate_config(self) -> Tuple[bool, str]:
        """Validate the backend configuration.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not self._base_url:
            return False, "Base URL is not configured"
        return True, ""


# ─── OpenAI Backend ───────────────────────────────────────────────────────────

class OpenAIBackend(AIBackend):
    """OpenAI API backend (also compatible with OpenAI-compatible APIs)."""

    name = "openai"

    def generate(self, prompt: str) -> str:
        """Generate commit message using OpenAI API.

        Args:
            prompt: The user prompt.

        Returns:
            Generated commit message string.
        """
        url = f"{self._base_url}/chat/completions"

        system_prompt = self._system_prompt or DEFAULT_SYSTEM_PROMPT_EN

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        data = json.dumps(payload).encode("utf-8")

        def request_fn():
            status, body = _make_request(url, data=data, headers=headers)
            if status != 200:
                raise ValueError(f"OpenAI API error: {status} - {body}")
            return json.loads(body)

        response = _retry_request(request_fn, self._retry_count, self._retry_delay)

        try:
            message = response["choices"][0]["message"]["content"]
            return message.strip()
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid OpenAI response format: {e}")

    def generate_streaming(self, prompt: str) -> Generator[str, None, None]:
        """Generate commit message with streaming from OpenAI API.

        Args:
            prompt: The user prompt.

        Yields:
            Chunks of generated text.
        """
        url = f"{self._base_url}/chat/completions"

        system_prompt = self._system_prompt or DEFAULT_SYSTEM_PROMPT_EN

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": True,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        data = json.dumps(payload).encode("utf-8")

        for line in _make_streaming_request(url, data=data, headers=headers):
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue

    def validate_config(self) -> Tuple[bool, str]:
        """Validate OpenAI configuration.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not self._api_key:
            return False, "OpenAI API key is not configured. Set COMMITFORGE_OPENAI_API_KEY or configure in .commitforge.toml"
        if not self._base_url:
            return False, "OpenAI base URL is not configured"
        if not self._model:
            return False, "OpenAI model is not configured"
        return True, ""


# ─── Anthropic Backend ────────────────────────────────────────────────────────

class AnthropicBackend(AIBackend):
    """Anthropic Claude API backend."""

    name = "anthropic"

    def generate(self, prompt: str) -> str:
        """Generate commit message using Anthropic API.

        Args:
            prompt: The user prompt.

        Returns:
            Generated commit message string.
        """
        url = f"{self._base_url}/v1/messages"

        system_prompt = self._system_prompt or DEFAULT_SYSTEM_PROMPT_EN

        payload = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": self._temperature,
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
        }

        data = json.dumps(payload).encode("utf-8")

        def request_fn():
            status, body = _make_request(url, data=data, headers=headers)
            if status != 200:
                raise ValueError(f"Anthropic API error: {status} - {body}")
            return json.loads(body)

        response = _retry_request(request_fn, self._retry_count, self._retry_delay)

        try:
            content_blocks = response["content"]
            text_parts = [block["text"] for block in content_blocks if block.get("type") == "text"]
            return "\n".join(text_parts).strip()
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid Anthropic response format: {e}")

    def generate_streaming(self, prompt: str) -> Generator[str, None, None]:
        """Generate commit message with streaming from Anthropic API.

        Args:
            prompt: The user prompt.

        Yields:
            Chunks of generated text.
        """
        url = f"{self._base_url}/v1/messages"

        system_prompt = self._system_prompt or DEFAULT_SYSTEM_PROMPT_EN

        payload = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": self._temperature,
            "stream": True,
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
        }

        data = json.dumps(payload).encode("utf-8")

        for line in _make_streaming_request(url, data=data, headers=headers):
            if line.startswith("data: "):
                data_str = line[6:]
                try:
                    chunk = json.loads(data_str)
                    if chunk.get("type") == "content_block_delta":
                        delta = chunk.get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            yield text
                except json.JSONDecodeError:
                    continue

    def validate_config(self) -> Tuple[bool, str]:
        """Validate Anthropic configuration.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not self._api_key:
            return False, "Anthropic API key is not configured. Set COMMITFORGE_ANTHROPIC_API_KEY or configure in .commitforge.toml"
        if not self._base_url:
            return False, "Anthropic base URL is not configured"
        if not self._model:
            return False, "Anthropic model is not configured"
        return True, ""


# ─── DeepSeek Backend ─────────────────────────────────────────────────────────

class DeepSeekBackend(AIBackend):
    """DeepSeek API backend (OpenAI-compatible)."""

    name = "deepseek"

    def generate(self, prompt: str) -> str:
        """Generate commit message using DeepSeek API.

        Args:
            prompt: The user prompt.

        Returns:
            Generated commit message string.
        """
        url = f"{self._base_url}/chat/completions"

        system_prompt = self._system_prompt or DEFAULT_SYSTEM_PROMPT_EN

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        data = json.dumps(payload).encode("utf-8")

        def request_fn():
            status, body = _make_request(url, data=data, headers=headers)
            if status != 200:
                raise ValueError(f"DeepSeek API error: {status} - {body}")
            return json.loads(body)

        response = _retry_request(request_fn, self._retry_count, self._retry_delay)

        try:
            message = response["choices"][0]["message"]["content"]
            return message.strip()
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid DeepSeek response format: {e}")

    def generate_streaming(self, prompt: str) -> Generator[str, None, None]:
        """Generate commit message with streaming from DeepSeek API.

        Args:
            prompt: The user prompt.

        Yields:
            Chunks of generated text.
        """
        # DeepSeek uses OpenAI-compatible streaming
        url = f"{self._base_url}/chat/completions"

        system_prompt = self._system_prompt or DEFAULT_SYSTEM_PROMPT_EN

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": True,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        data = json.dumps(payload).encode("utf-8")

        for line in _make_streaming_request(url, data=data, headers=headers):
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue

    def validate_config(self) -> Tuple[bool, str]:
        """Validate DeepSeek configuration.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not self._api_key:
            return False, "DeepSeek API key is not configured. Set COMMITFORGE_DEEPSEEK_API_KEY or configure in .commitforge.toml"
        if not self._base_url:
            return False, "DeepSeek base URL is not configured"
        if not self._model:
            return False, "DeepSeek model is not configured"
        return True, ""


# ─── Ollama Backend (Local) ──────────────────────────────────────────────────

class OllamaBackend(AIBackend):
    """Ollama local LLM backend."""

    name = "ollama"

    def generate(self, prompt: str) -> str:
        """Generate commit message using Ollama API.

        Args:
            prompt: The user prompt.

        Returns:
            Generated commit message string.
        """
        url = f"{self._base_url}/api/chat"

        system_prompt = self._system_prompt or DEFAULT_SYSTEM_PROMPT_EN

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": self._temperature,
                "num_predict": self._max_tokens,
            },
        }

        headers = {
            "Content-Type": "application/json",
        }

        data = json.dumps(payload).encode("utf-8")

        def request_fn():
            status, body = _make_request(url, data=data, headers=headers)
            if status != 200:
                raise ValueError(f"Ollama API error: {status} - {body}")
            return json.loads(body)

        response = _retry_request(request_fn, self._retry_count, self._retry_delay)

        try:
            message = response["message"]["content"]
            return message.strip()
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid Ollama response format: {e}")

    def generate_streaming(self, prompt: str) -> Generator[str, None, None]:
        """Generate commit message with streaming from Ollama API.

        Args:
            prompt: The user prompt.

        Yields:
            Chunks of generated text.
        """
        url = f"{self._base_url}/api/chat"

        system_prompt = self._system_prompt or DEFAULT_SYSTEM_PROMPT_EN

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": True,
            "options": {
                "temperature": self._temperature,
                "num_predict": self._max_tokens,
            },
        }

        headers = {
            "Content-Type": "application/json",
        }

        data = json.dumps(payload).encode("utf-8")

        for line in _make_streaming_request(url, data=data, headers=headers):
            try:
                chunk = json.loads(line)
                message = chunk.get("message", {})
                content = message.get("content", "")
                if content:
                    yield content
                if chunk.get("done", False):
                    break
            except json.JSONDecodeError:
                continue

    def validate_config(self) -> Tuple[bool, str]:
        """Validate Ollama configuration.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not self._base_url:
            return False, "Ollama base URL is not configured"
        if not self._model:
            return False, "Ollama model is not configured"
        return True, ""


# ─── Google Gemini Backend ────────────────────────────────────────────────────

class GeminiBackend(AIBackend):
    """Google Gemini API backend."""

    name = "gemini"

    def generate(self, prompt: str) -> str:
        """Generate commit message using Google Gemini API.

        Args:
            prompt: The user prompt.

        Returns:
            Generated commit message string.
        """
        system_prompt = self._system_prompt or DEFAULT_SYSTEM_PROMPT_EN

        url = (
            f"{self._base_url}/v1beta/models/{self._model}:generateContent"
            f"?key={self._api_key}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_prompt + "\n\n" + prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self._temperature,
                "maxOutputTokens": self._max_tokens,
            },
        }

        headers = {
            "Content-Type": "application/json",
        }

        data = json.dumps(payload).encode("utf-8")

        def request_fn():
            status, body = _make_request(url, data=data, headers=headers)
            if status != 200:
                raise ValueError(f"Gemini API error: {status} - {body}")
            return json.loads(body)

        response = _retry_request(request_fn, self._retry_count, self._retry_delay)

        try:
            candidates = response.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in Gemini response")
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            text_parts = [p["text"] for p in parts if "text" in p]
            return "\n".join(text_parts).strip()
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid Gemini response format: {e}")

    def generate_streaming(self, prompt: str) -> Generator[str, None, None]:
        """Generate commit message with streaming from Gemini API.

        Args:
            prompt: The user prompt.

        Yields:
            Chunks of generated text.
        """
        system_prompt = self._system_prompt or DEFAULT_SYSTEM_PROMPT_EN

        url = (
            f"{self._base_url}/v1beta/models/{self._model}:streamGenerateContent"
            f"?key={self._api_key}&alt=sse"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_prompt + "\n\n" + prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self._temperature,
                "maxOutputTokens": self._max_tokens,
            },
        }

        headers = {
            "Content-Type": "application/json",
        }

        data = json.dumps(payload).encode("utf-8")

        for line in _make_streaming_request(url, data=data, headers=headers):
            if line.startswith("data: "):
                data_str = line[6:]
                try:
                    chunk = json.loads(data_str)
                    candidates = chunk.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for p in parts:
                            if "text" in p:
                                yield p["text"]
                except json.JSONDecodeError:
                    continue

    def validate_config(self) -> Tuple[bool, str]:
        """Validate Gemini configuration.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not self._api_key:
            return False, "Gemini API key is not configured. Set COMMITFORGE_GEMINI_API_KEY or configure in .commitforge.toml"
        if not self._model:
            return False, "Gemini model is not configured"
        return True, ""


# ─── Backend Factory ──────────────────────────────────────────────────────────

BACKEND_REGISTRY: Dict[str, type] = {
    "openai": OpenAIBackend,
    "anthropic": AnthropicBackend,
    "deepseek": DeepSeekBackend,
    "ollama": OllamaBackend,
    "gemini": GeminiBackend,
}


def create_backend(backend_name: str, config: Dict[str, Any],
                   system_prompt: str = "") -> AIBackend:
    """Create an AI backend instance from configuration.

    Args:
        backend_name: Name of the backend ('openai', 'anthropic', etc.).
        config: Configuration dictionary for the backend.
        system_prompt: Optional custom system prompt.

    Returns:
        An AIBackend instance.

    Raises:
        ValueError: If the backend name is unknown.
    """
    backend_cls = BACKEND_REGISTRY.get(backend_name)
    if backend_cls is None:
        raise ValueError(f"Unknown AI backend: {backend_name}. Available: {', '.join(BACKEND_REGISTRY.keys())}")

    return backend_cls(
        api_key=config.get("api_key", ""),
        base_url=config.get("base_url", ""),
        model=config.get("model", ""),
        temperature=config.get("temperature", 0.7),
        max_tokens=config.get("max_tokens", 512),
        system_prompt=system_prompt,
        retry_count=config.get("retry_count", 3),
        retry_delay=config.get("retry_delay", 1.0),
    )


def generate_commit_message(
    analysis: ChangeAnalysis,
    backend_name: str,
    backend_config: Dict[str, Any],
    lang: str = "en",
    force_type: Optional[str] = None,
    force_scope: Optional[str] = None,
    system_prompt: str = "",
    streaming: bool = False,
) -> str:
    """Generate a commit message using the specified AI backend.

    This is the main entry point for AI-based commit message generation.

    Args:
        analysis: The change analysis result.
        backend_name: Name of the AI backend to use.
        backend_config: Configuration for the backend.
        lang: Output language ('en' or 'zh').
        force_type: Optional forced commit type.
        force_scope: Optional forced commit scope.
        system_prompt: Optional custom system prompt.
        streaming: Whether to use streaming output.

    Returns:
        Generated commit message string.
    """
    # Create the backend
    backend = create_backend(backend_name, backend_config, system_prompt)

    # Validate configuration
    is_valid, error_msg = backend.validate_config()
    if not is_valid:
        raise ValueError(error_msg)

    # Build the prompt
    prompt = build_user_prompt(analysis, lang, force_type, force_scope)

    # Generate
    if streaming:
        full_message = ""
        for chunk in backend.generate_streaming(prompt):
            print(chunk, end="", flush=True)
            full_message += chunk
        print()  # Newline after streaming
        return full_message.strip()
    else:
        return backend.generate(prompt)


def parse_ai_response(response_text: str) -> ConventionalCommit:
    """Parse AI response into a ConventionalCommit object.

    Cleans up the AI response and attempts to parse it as a
    conventional commit message.

    Args:
        response_text: The raw AI response text.

    Returns:
        Parsed ConventionalCommit, or a fallback commit.
    """
    # Clean up the response
    cleaned = response_text.strip()

    # Remove markdown code blocks if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last lines (code block markers)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    # Remove any leading/trailing quotes
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]
    if cleaned.startswith("'") and cleaned.endswith("'"):
        cleaned = cleaned[1:-1]

    # Try to parse as conventional commit
    parsed = parse_commit(cleaned)
    if parsed:
        return parsed

    # If parsing fails, create a fallback commit with the raw text as description
    # Try to extract a reasonable subject line
    first_line = cleaned.split("\n")[0].strip()
    if len(first_line) > 100:
        first_line = first_line[:97] + "..."

    return ConventionalCommit(
        type="chore",
        description=first_line,
        body="\n".join(cleaned.split("\n")[1:]).strip() or None,
        raw=cleaned,
    )
