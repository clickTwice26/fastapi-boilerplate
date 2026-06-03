from hashlib import sha256


def stable_cache_key(namespace: str, value: str) -> str:
    digest = sha256(value.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"
