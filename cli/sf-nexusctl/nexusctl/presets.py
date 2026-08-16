"""Built-in proxy repository presets for common upstream registries."""
from __future__ import annotations

PRESETS: dict[str, dict] = {
    "pypi-org-proxy": {
        "name": "pypi-org-proxy",
        "format": "pypi",
        "remote_url": "https://pypi.org/",
        "blob_store": None,
        "content_max_age": 1440,
        "metadata_max_age": 1440,
        "negative_cache_enabled": True,
        "negative_cache_ttl": 1440,
        "description": "PyPI 官方上游代理",
    },
    "npm-registry-proxy": {
        "name": "npm-registry-proxy",
        "format": "npm",
        "remote_url": "https://registry.npmjs.org/",
        "blob_store": None,
        "content_max_age": 1440,
        "metadata_max_age": 1440,
        "negative_cache_enabled": True,
        "negative_cache_ttl": 1440,
        "description": "npmjs.org 官方上游代理",
    },
    "maven-central-proxy": {
        "name": "maven-central-proxy",
        "format": "maven",
        "remote_url": "https://repo1.maven.org/maven2/",
        "blob_store": None,
        "content_max_age": 1440,
        "metadata_max_age": 1440,
        "negative_cache_enabled": True,
        "negative_cache_ttl": 1440,
        "description": "Maven Central 官方上游代理",
    },
    "docker-hub-proxy": {
        "name": "docker-hub-proxy",
        "format": "docker",
        "remote_url": "https://registry-1.docker.io/",
        "blob_store": None,
        "content_max_age": 1440,
        "metadata_max_age": 1440,
        "negative_cache_enabled": True,
        "negative_cache_ttl": 1440,
        "description": "Docker Hub 官方上游代理",
    },
    "goproxy-cn": {
        "name": "goproxy-cn-proxy",
        "format": "go",
        "remote_url": "https://goproxy.cn/",
        "blob_store": None,
        "content_max_age": 1440,
        "metadata_max_age": 1440,
        "negative_cache_enabled": True,
        "negative_cache_ttl": 1440,
        "description": "goproxy.cn 国内 Go 模块代理",
    },
    "goproxy-io": {
        "name": "goproxy-io-proxy",
        "format": "go",
        "remote_url": "https://proxy.golang.org/",
        "blob_store": None,
        "content_max_age": 1440,
        "metadata_max_age": 1440,
        "negative_cache_enabled": True,
        "negative_cache_ttl": 1440,
        "description": "Go 官方上游代理 (proxy.golang.org)",
    },
    "rubygems-proxy": {
        "name": "rubygems-proxy",
        "format": "rubygems",
        "remote_url": "https://rubygems.org/",
        "blob_store": None,
        "content_max_age": 1440,
        "metadata_max_age": 1440,
        "negative_cache_enabled": True,
        "negative_cache_ttl": 1440,
        "description": "RubyGems 官方上游代理",
    },
    "nuget-org-proxy": {
        "name": "nuget-org-proxy",
        "format": "nuget",
        "remote_url": "https://api.nuget.org/v3/index.json",
        "blob_store": None,
        "content_max_age": 1440,
        "metadata_max_age": 1440,
        "negative_cache_enabled": True,
        "negative_cache_ttl": 1440,
        "description": "NuGet.org 官方上游代理",
    },
}


def get_preset(name: str) -> dict | None:
    """Return preset by name, or None if not found."""
    return PRESETS.get(name)


def list_presets() -> list[dict]:
    """Return all presets as a list of dicts (for display)."""
    return [
        {"id": k, **v}
        for k, v in PRESETS.items()
    ]
