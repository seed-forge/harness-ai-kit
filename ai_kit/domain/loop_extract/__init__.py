"""Session-to-Loop extraction engine.

Re-exports all public symbols from sub-modules so that existing
``from ai_kit.domain.loop_extract import ...`` imports work.
"""
from .scoring import Recommendation, ValueScore, ValueScorer, ValueSignal
from .field_mapper import LoopFieldMapper
from .extractors import RubricExtractor, StopConditionExtractor
from .asset_generator import LoopAssetGenerator, _normalize_action, _normalize_weights

__all__ = [
    "LoopAssetGenerator",
    "LoopFieldMapper",
    "Recommendation",
    "RubricExtractor",
    "StopConditionExtractor",
    "ValueScore",
    "ValueScorer",
    "ValueSignal",
    "_normalize_action",
    "_normalize_weights",
]
