from __future__ import annotations

PUBLIC_NAMESPACE = "public"


def normalize_namespace(namespace: str | None) -> str | None:
    if namespace is None:
        return None
    value = str(namespace).strip()
    return value or None


def namespace_label(namespace: str | None) -> str:
    normalized = normalize_namespace(namespace)
    return normalized or PUBLIC_NAMESPACE


def canonical_package_id(package_id: str, namespace: str | None = None) -> str:
    namespace = normalize_namespace(namespace)
    return f"{namespace}/{package_id}" if namespace else package_id


def namespaced_asset_id(namespace: str | None, asset_id: str) -> str:
    normalized = normalize_namespace(namespace)
    return f"{normalized}/{asset_id}" if normalized else asset_id


def split_canonical_id(value: str) -> tuple[str | None, str]:
    text = str(value).strip()
    if "/" not in text:
        return None, text
    namespace, package_id = text.split("/", 1)
    return normalize_namespace(namespace), package_id


def package_key_for(dep_type: str, package_id: str, namespace: str | None = None) -> str:
    return f"{dep_type}:{canonical_package_id(package_id, namespace)}"


def package_key(dep_type: str, package_id: str) -> str:
    namespace, base_id = split_canonical_id(package_id)
    return package_key_for(dep_type, base_id, namespace)
