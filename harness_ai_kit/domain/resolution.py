from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness_ai_kit.domain.dependencies import DependencySpec
from harness_ai_kit.domain.lockfile import LockNode, Lockfile, RootRequest
from harness_ai_kit.domain.manifest import SkillManifest


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class PackageCandidate:
    dep_type: str
    namespace: str | None
    package_id: str
    version: str
    source: str
    manifest: SkillManifest | None = None
    dependency_spec: DependencySpec | None = None
    path: Path | None = None
    artifact_url: str | None = None
    metadata_url: str | None = None
    source_ref: str | None = None
    source_url: str | None = None
    source_commit: str | None = None
    ref: str | None = None
    subpath: str | None = None
    checksum: str | None = None
    source_checksum: str | None = None
    materialized_checksum: str | None = None


@dataclass(frozen=True)
class DependencyRequirement:
    dep_type: str
    namespace: str | None
    package_id: str
    specifier: str
    scope: str = "required"
    feature: str | None = None
    source_ref: str | None = None
    ref: str | None = None
    subpath: str | None = None
    source_url: str | None = None
    extra_metadata: dict[str, Any] | None = None


@dataclass
class ResolutionPlan:
    roots: list[str]
    features: list[str]
    runtime: str
    install_scope: str
    nodes: list[LockNode]
    manifest_map: dict[str, SkillManifest]
    candidate_map: dict[str, PackageCandidate]
    dependency_edges: dict[str, list[str]]
    root_requests: list[RootRequest] | None = None

    def to_lockfile(self) -> Lockfile:
        return Lockfile(
            generated_at=utc_now_iso(),
            runtime=self.runtime,
            install_scope=self.install_scope,
            roots=self.roots,
            features=self.features,
            root_requests=list(self.root_requests or []),
            nodes=self.nodes,
        )
