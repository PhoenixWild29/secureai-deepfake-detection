"""Central configuration for the SecureAI deepfake training pipeline.

Everything tunable lives here as a dataclass so the rest of the pipeline can be
driven by a single object. Every field can be overridden by an environment
variable (handy on Modal, where you set them via the launch command or a
Modal Secret) — see ``Config.from_env``.

Design goals encoded here:
  * CROSS-DATASET generalization is the target — so the dataset registry has a
    distinct ``train_datasets`` and ``test_datasets`` selection, defaulting to
    the canonical FF++ -> Celeb-DF/DFDC protocol.
  * The default backbone is EfficientNet-B4 (``tf_efficientnet_b4_ns``) at
    380px, which is the standard strong-generalization backbone (and the size
    SBI papers use). ConvNeXt-Base is provided as an alternative.
  * Model selection is by VAL AUC, never accuracy.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Environment-variable helpers
# ---------------------------------------------------------------------------
def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw not in (None, "") else default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return float(raw) if raw not in (None, "") else default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "y", "on")


def _env_list(name: str, default: List[str]) -> List[str]:
    raw = os.environ.get(name)
    if raw in (None, ""):
        return list(default)
    return [p.strip() for p in raw.split(",") if p.strip()]


# ---------------------------------------------------------------------------
# Dataset registry
# ---------------------------------------------------------------------------
@dataclass
class DatasetSpec:
    """Where a single dataset lives and how to read it.

    ``s3_prefix`` is relative to the data bucket. The expected on-disk / on-S3
    layout after acquisition + extraction is:

        datasets/<name>/{real,fake}/<identity>/<clip>/<frame>.png   (face crops)
        videos/<name>/{real,fake}/...                                (raw videos)

    ``kind`` is "video" (raw videos that need face extraction) or "frames"
    (already-extracted frames/face crops).
    """

    name: str
    s3_prefix: str                 # e.g. "datasets/celeb_df_v2"
    kind: str = "video"            # "video" | "frames"
    gated: bool = False            # requires manual access request
    note: str = ""


# Canonical registry. Prefixes follow the layout data_acquire.py enforces.
DEFAULT_DATASET_REGISTRY: Dict[str, DatasetSpec] = {
    "faceforensics": DatasetSpec(
        name="faceforensics",
        s3_prefix="datasets/faceforensics",
        kind="video",
        gated=True,
        note="FF++ c23 — request access via ondyari/FaceForensics form.",
    ),
    "celeb_df_v2": DatasetSpec(
        name="celeb_df_v2",
        s3_prefix="datasets/celeb_df_v2",
        kind="video",
        gated=True,
        note="Celeb-DF v2 — request via Google form.",
    ),
    "dfdc": DatasetSpec(
        name="dfdc",
        s3_prefix="datasets/dfdc",
        kind="video",
        gated=True,
        note="DFDC — Kaggle competition rules acceptance or AWS open-data.",
    ),
    "diffusion": DatasetSpec(
        name="diffusion",
        s3_prefix="datasets/diffusion",
        kind="frames",
        gated=False,
        note="Diffusion-generated faces (e.g. DiFF) for 2025+ synthetic coverage.",
    ),
}


# ---------------------------------------------------------------------------
# Main config
# ---------------------------------------------------------------------------
@dataclass
class Config:
    # --- Backbone / model ------------------------------------------------
    backbone: str = "tf_efficientnet_b4_ns"   # timm name; alt: "convnext_base"
    image_size: int = 380                      # 380 for b4; use 224/256 for convnext
    pretrained: bool = True
    num_classes: int = 1                       # single logit -> BCEWithLogits

    # --- Optimisation ----------------------------------------------------
    batch_size: int = 24
    epochs: int = 30
    lr: float = 3e-4
    weight_decay: float = 1e-2
    optimizer: str = "adamw"                   # "adamw" | "sgd"
    scheduler: str = "cosine_warmup"           # "cosine_warmup" | "cosine" | "none"
    warmup_epochs: int = 2
    grad_clip: float = 1.0
    label_smoothing: float = 0.0
    mixed_precision: bool = True
    early_stop_patience: int = 6               # epochs w/o val-AUC improvement

    # --- Data / sampling -------------------------------------------------
    num_workers: int = 8
    frames_per_video: int = 16                 # evenly sampled frames per clip
    face_margin: float = 0.30                  # 30% margin around detected face
    val_fraction: float = 0.15                 # identity-disjoint holdout of train
    balance_classes: bool = True               # WeightedRandomSampler

    # --- Augmentation toggles -------------------------------------------
    compression_aug: bool = True               # JPEG/H264/downscale/noise/blur
    sbi: bool = True                           # Self-Blended Images on real faces
    sbi_prob: float = 0.5                      # prob a real image becomes an SBI fake
    hflip: bool = True

    # --- Dataset selection (CROSS-DATASET protocol) ---------------------
    # Train on these, evaluate (cross-dataset) on those. The default is the
    # classic generalization benchmark: train FF++, test Celeb-DF + DFDC.
    train_datasets: List[str] = field(default_factory=lambda: ["faceforensics"])
    test_datasets: List[str] = field(default_factory=lambda: ["celeb_df_v2", "dfdc"])
    dataset_registry: Dict[str, DatasetSpec] = field(
        default_factory=lambda: dict(DEFAULT_DATASET_REGISTRY)
    )

    # --- Storage (AWS S3, us-east-2) ------------------------------------
    aws_region: str = "us-east-2"
    data_bucket: str = "secureai-deepfake-videos"
    results_bucket: str = "secureai-deepfake-results"
    output_prefix: str = "training_runs"       # results_bucket/<output_prefix>/<run_id>

    # --- Local working dirs (on the Modal worker / volume) --------------
    data_root: str = "/data"                   # CloudBucketMount of data bucket
    outputs_root: str = "/outputs"             # CloudBucketMount of results bucket
    work_dir: str = "/cache"                   # Modal Volume for checkpoints/crops
    crops_subdir: str = "face_crops"           # under work_dir
    checkpoint_subdir: str = "checkpoints"     # under work_dir

    # --- Ensemble refit --------------------------------------------------
    ensemble_C: float = 0.03                   # matches repo's existing refit
    # Detector order must match the repo's ensemble_weights.json, with the new
    # backbone appended as an extra column.
    ensemble_detectors: List[str] = field(
        default_factory=lambda: ["clip", "laa", "resnet50", "convnext", "fft", "new_backbone"]
    )

    # --- Run identity ----------------------------------------------------
    run_id: str = ""                           # filled at runtime if empty
    seed: int = 1337

    # -- derived helpers --------------------------------------------------
    @property
    def crops_dir(self) -> str:
        return os.path.join(self.work_dir, self.crops_subdir)

    @property
    def checkpoint_dir(self) -> str:
        return os.path.join(self.work_dir, self.checkpoint_subdir)

    def spec(self, name: str) -> DatasetSpec:
        if name not in self.dataset_registry:
            raise KeyError(f"Unknown dataset '{name}'. Known: {list(self.dataset_registry)}")
        return self.dataset_registry[name]

    def to_dict(self) -> dict:
        d = asdict(self)
        # DatasetSpec instances -> plain dicts (asdict already handles nested dataclasses)
        return d

    # -- construction from environment -----------------------------------
    @classmethod
    def from_env(cls, **overrides) -> "Config":
        """Build a Config, taking env-var overrides then explicit kwargs.

        Explicit kwargs win over env vars, which win over defaults. This makes
        the pipeline scriptable from the Modal launch command without editing
        code (e.g. ``SECUREAI_BACKBONE=convnext_base``).
        """
        cfg = cls(
            backbone=_env_str("SECUREAI_BACKBONE", cls.backbone),
            image_size=_env_int("SECUREAI_IMAGE_SIZE", cls.image_size),
            pretrained=_env_bool("SECUREAI_PRETRAINED", cls.pretrained),
            batch_size=_env_int("SECUREAI_BATCH_SIZE", cls.batch_size),
            epochs=_env_int("SECUREAI_EPOCHS", cls.epochs),
            lr=_env_float("SECUREAI_LR", cls.lr),
            weight_decay=_env_float("SECUREAI_WEIGHT_DECAY", cls.weight_decay),
            optimizer=_env_str("SECUREAI_OPTIMIZER", cls.optimizer),
            scheduler=_env_str("SECUREAI_SCHEDULER", cls.scheduler),
            warmup_epochs=_env_int("SECUREAI_WARMUP_EPOCHS", cls.warmup_epochs),
            mixed_precision=_env_bool("SECUREAI_AMP", cls.mixed_precision),
            early_stop_patience=_env_int("SECUREAI_EARLY_STOP", cls.early_stop_patience),
            num_workers=_env_int("SECUREAI_NUM_WORKERS", cls.num_workers),
            frames_per_video=_env_int("SECUREAI_FRAMES_PER_VIDEO", cls.frames_per_video),
            face_margin=_env_float("SECUREAI_FACE_MARGIN", cls.face_margin),
            val_fraction=_env_float("SECUREAI_VAL_FRACTION", cls.val_fraction),
            balance_classes=_env_bool("SECUREAI_BALANCE", cls.balance_classes),
            compression_aug=_env_bool("SECUREAI_COMPRESSION_AUG", cls.compression_aug),
            sbi=_env_bool("SECUREAI_SBI", cls.sbi),
            sbi_prob=_env_float("SECUREAI_SBI_PROB", cls.sbi_prob),
            hflip=_env_bool("SECUREAI_HFLIP", cls.hflip),
            train_datasets=_env_list("SECUREAI_TRAIN_DATASETS", cls().train_datasets),
            test_datasets=_env_list("SECUREAI_TEST_DATASETS", cls().test_datasets),
            aws_region=_env_str("AWS_REGION", cls.aws_region),
            data_bucket=_env_str("SECUREAI_DATA_BUCKET", cls.data_bucket),
            results_bucket=_env_str("SECUREAI_RESULTS_BUCKET", cls.results_bucket),
            output_prefix=_env_str("SECUREAI_OUTPUT_PREFIX", cls.output_prefix),
            data_root=_env_str("SECUREAI_DATA_ROOT", cls.data_root),
            outputs_root=_env_str("SECUREAI_OUTPUTS_ROOT", cls.outputs_root),
            work_dir=_env_str("SECUREAI_WORK_DIR", cls.work_dir),
            ensemble_C=_env_float("SECUREAI_ENSEMBLE_C", cls.ensemble_C),
            run_id=_env_str("SECUREAI_RUN_ID", cls.run_id),
            seed=_env_int("SECUREAI_SEED", cls.seed),
        )
        for k, v in overrides.items():
            if v is not None and hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg


def default_config(**overrides) -> Config:
    """Convenience: env-aware config with optional explicit overrides."""
    return Config.from_env(**overrides)
