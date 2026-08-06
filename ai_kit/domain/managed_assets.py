from __future__ import annotations

from typing import Any, Mapping

from ai_kit.domain.identity import canonical_package_id
from ai_kit.domain.versions import spec_matches_version


def select_managed_asset_record_for_spec(inventory: Mapping[str, Any], asset_type: str, spec: Any) -> Any:
    record = inventory.get(spec.id)
    if record is None:
        available = ", ".join(sorted(inventory))
        raise KeyError(f"Unknown {asset_type} ID: {spec.id}. Available {asset_type}s: {available}")
    if spec.namespace is not None:
        raise ValueError(
            f"{asset_type.title()} namespaces are not supported yet for project declarations: {canonical_package_id(spec.id, spec.namespace)}"
        )
    if not spec_matches_version(spec.version, record.version):
        raise ValueError(
            f"{asset_type.title()} {spec.id} pinned to {spec.version} but the available version is {record.version}. Publish or select a matching version first."
        )
    return record
