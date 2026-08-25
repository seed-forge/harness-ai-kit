from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness_ai_kit.domain.policies import (
    SOURCE_GIT_REPO,
    SOURCE_PUBLIC_REGISTRY,
    SOURCE_REGISTRY,
    SOURCE_REPO,
    SourcePolicy,
    consumer_source_order,
    selectable_install_source,
    source_order_for_selector,
)


class PublicSourcePolicyTests(unittest.TestCase):
    def test_default_policy_has_distinct_public_sources(self) -> None:
        policy = SourcePolicy()

        self.assertEqual(
            policy.preferred,
            [SOURCE_REPO, SOURCE_PUBLIC_REGISTRY, SOURCE_REGISTRY, SOURCE_GIT_REPO],
        )
        self.assertEqual(len(policy.preferred), len(set(policy.preferred)))

    def test_consumer_falls_back_from_public_to_configured_registry(self) -> None:
        self.assertEqual(
            consumer_source_order(),
            [SOURCE_PUBLIC_REGISTRY, SOURCE_REGISTRY],
        )

    def test_public_selectors_reject_retired_private_names(self) -> None:
        self.assertEqual(selectable_install_source("repo"), SOURCE_REPO)
        self.assertEqual(selectable_install_source("registry"), SOURCE_REGISTRY)
        self.assertEqual(selectable_install_source("public-registry"), SOURCE_PUBLIC_REGISTRY)
        self.assertEqual(source_order_for_selector("public-registry"), [SOURCE_PUBLIC_REGISTRY])
        with self.assertRaisesRegex(ValueError, "Unsupported install source selector"):
            selectable_install_source("internal-registry")
        with self.assertRaisesRegex(ValueError, "Unsupported install source selector"):
            selectable_install_source("workspace-repo")


if __name__ == "__main__":
    unittest.main()
