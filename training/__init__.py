"""
Training package - re-exports training-related scripts for modular layout.
This package wraps existing scripts under `scripts/` to provide a stable import path.
"""
from training.train_model import MultimodalFeatureExtractor, RecommendationTrainer  # noqa: F401
from training.run_training_pipeline import TrainingPipeline  # noqa: F401
from training.train_manager import TrainManager  # noqa: F401
from training.training_coordinator import training_coordinator, get_coordinator  # noqa: F401
from training.gpu_monitor import GPUManager  # noqa: F401

__all__ = [
    "MultimodalFeatureExtractor",
    "RecommendationTrainer",
    "TrainingPipeline",
    "TrainManager",
    "training_coordinator",
    "get_coordinator",
    "GPUManager",
]


