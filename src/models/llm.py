import logging
import os
import httpx

log = logging.getLogger("pipeline.llm")

# Provider definitions — both use OpenAI-compatible chat completions format.
PROVIDERS = {
    "openrouter": {
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "model": "meta-llama/llama-3.1-70b-instruct",
        "env_key": "OPENROUTER_API_KEY",
    },
    "nvidia": {
        "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
        "model": "meta/llama-3.1-70b-instruct",
        "env_key": "NVIDIA_API_KEY",
    },
}

# Ordered fallback chain: try OpenRouter first, then NVIDIA.
FALLBACK_ORDER = ["openrouter", "nvidia"]

def _available_providers() -> list[dict]:
    """Return providers that have an API key configured, in fallback order."""
    available = []
    for name in FALLBACK_ORDER:
        info = PROVIDERS[name]
        key = os.getenv(info["env_key"])
        if key:
            available.append({
                "name": name,
                "endpoint": info["endpoint"],
                "model": info["model"],
                "key": key,
            })
    return available

def get_providers() -> list[dict]:
    """Return the list of usable providers. Raises if none are configured."""
    providers = _available_providers()
    if not providers:
        raise RuntimeError(
            "No LLM API key configured. "
            "Set OPENROUTER_API_KEY or NVIDIA_API_KEY in your .env file."
        )
    names = [p["name"] for p in providers]
    log.info("LLM providers available: %s (primary: %s)", names, names[0])
    return providers


async def call_llm(
    providers: list[dict],
    messages: list[dict],
    temperature: float = 0,
    timeout: float = 30,
) -> str:
    """Send a chat completion request, falling back across providers on failure.

    Tries each provider in order. If a request fails (rate limit, server error,
    timeout), logs the failure and moves to the next provider. Returns the
    assistant message content from the first successful response.
    """
    last_error: Exception | None = None

    async with httpx.AsyncClient() as client:
        for provider in providers:
            body = {
                "model": provider["model"],
                "temperature": temperature,
                "messages": messages,
            }
            headers = {
                "Authorization": f"Bearer {provider['key']}",
                "Content-Type": "application/json",
            }
            try:
                resp = await client.post(
                    provider["endpoint"],
                    json=body,
                    headers=headers,
                    timeout=timeout,
                )
                if resp.status_code != 200:
                    log.warning(
                        "%s returned %s: %s",
                        provider["name"], resp.status_code, resp.text[:200],
                    )
                    last_error = httpx.HTTPStatusError(
                        f"{resp.status_code}", request=resp.request, response=resp,
                    )
                    continue

                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                log.info("LLM response from %s (first 300 chars): %s", provider["name"], content[:300])
                return content

            except Exception as exc:
                log.warning("%s call failed: %s", provider["name"], exc)
                last_error = exc
                continue

    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")