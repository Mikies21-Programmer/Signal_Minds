"""
Módulo de evaluación morfológica de Lengua de Señas Mexicana (LSM).
"""

from .evaluator import LSMEvaluator
from .classifier import AutomaticLSMClassifier

__all__ = ["LSMEvaluator", "AutomaticLSMClassifier"]
