"""Torch Dataset over extracted aligned face crops.

Critical correctness requirement (MODEL_IMPROVEMENT_PLAN.md section 5):
IDENTITY-DISJOINT train/val splits. No subject's frames may appear in both
train and val — that leakage is exactly what produced the fake "100%" model
that was removed. We parse identity from the directory layout written by
face_extract.extract_dataset:

    <crops_root>/<dataset>/{real,fake}/<identity>/<clip>/frame_*.png

and split by ``(dataset, label, identity)`` so an identity is wholly in train
or wholly in val.

Augmentation:
  * COMPRESSION / ROBUSTNESS aug (P1.2) via albumentations: random JPEG quality,
    downscale-upscale, gaussian noise/blur, h264-like degradation. Gated by
    ``config.compression_aug``.
  * SBI on-the-fly for real images (P1.1), gated by ``config.sbi``.
  * ImageNet normalisation always.

All heavy imports are local so the module imports without torch/albumentations.
"""

from __future__ import annotations

import os
import glob
import random
from typing import Dict, List, Optional, Tuple

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


# ---------------------------------------------------------------------------
# Sample indexing
# ---------------------------------------------------------------------------
class Sample:
    """A single training sample: a face-crop path plus its label/identity."""

    __slots__ = ("path", "label", "identity", "dataset")

    def __init__(self, path: str, label: int, identity: str, dataset: str):
        self.path = path
        self.label = label
        self.identity = identity
        self.dataset = dataset


def index_crops(crops_root: str, datasets: List[str]) -> List[Sample]:
    """Scan ``<crops_root>/<dataset>/{real,fake}/<identity>/<clip>/frame_*.png``.

    Returns a flat list of Sample objects. ``real`` -> label 0, ``fake`` -> 1.
    """
    samples: List[Sample] = []
    for ds in datasets:
        ds_root = os.path.join(crops_root, ds)
        if not os.path.isdir(ds_root):
            continue
        for label_name, label in (("real", 0), ("fake", 1)):
            label_root = os.path.join(ds_root, label_name)
            if not os.path.isdir(label_root):
                continue
            for identity in os.listdir(label_root):
                ident_dir = os.path.join(label_root, identity)
                if not os.path.isdir(ident_dir):
                    continue
                # frames may be nested under clip dirs or flat
                pngs = glob.glob(os.path.join(ident_dir, "**", "frame_*.png"),
                                 recursive=True)
                for p in pngs:
                    samples.append(Sample(p, label, identity, ds))
    return samples


def identity_disjoint_split(
    samples: List[Sample], val_fraction: float, seed: int = 1337
) -> Tuple[List[Sample], List[Sample]]:
    """Split samples so each (dataset, identity) lands entirely in train OR val.

    We key on (dataset, identity) and shuffle the *identities*, not the frames,
    guaranteeing no identity straddles the split. Stratification is approximate:
    identities are drawn so val_fraction of identities go to val.
    """
    rng = random.Random(seed)
    # group identities, remember the dominant label per identity for balance
    by_ident: Dict[Tuple[str, str], List[Sample]] = {}
    for s in samples:
        by_ident.setdefault((s.dataset, s.identity), []).append(s)

    # separate identities by majority label so val keeps both classes
    real_idents, fake_idents = [], []
    for key, items in by_ident.items():
        frac_fake = sum(i.label for i in items) / max(1, len(items))
        (fake_idents if frac_fake >= 0.5 else real_idents).append(key)

    rng.shuffle(real_idents)
    rng.shuffle(fake_idents)

    def take_val(idents: List[Tuple[str, str]]):
        n_val = max(1, int(round(len(idents) * val_fraction))) if idents else 0
        return set(idents[:n_val])

    val_keys = take_val(real_idents) | take_val(fake_idents)

    train, val = [], []
    for key, items in by_ident.items():
        (val if key in val_keys else train).extend(items)

    # sanity: no identity overlap
    train_keys = {(s.dataset, s.identity) for s in train}
    overlap = train_keys & val_keys
    assert not overlap, f"identity leakage between train/val: {overlap}"
    return train, val


# ---------------------------------------------------------------------------
# Albumentations pipelines
# ---------------------------------------------------------------------------
def build_train_transform(image_size: int, compression_aug: bool, hflip: bool):
    """Training augmentation. Compression/robustness aug gated by config."""
    import albumentations as A
    from albumentations.pytorch import ToTensorV2

    aug: List = []
    if hflip:
        aug.append(A.HorizontalFlip(p=0.5))

    if compression_aug:
        # P1.2 — survive social-media re-compression. Each op has its own prob.
        aug.extend([
            A.ImageCompression(quality_lower=40, quality_upper=100, p=0.5),
            A.OneOf([
                A.Downscale(scale_min=0.5, scale_max=0.9, p=1.0),
                A.GaussianBlur(blur_limit=(3, 7), p=1.0),
                A.MotionBlur(blur_limit=7, p=1.0),
            ], p=0.4),
            A.GaussNoise(var_limit=(5.0, 40.0), p=0.3),
            A.RandomBrightnessContrast(0.15, 0.15, p=0.4),
            A.HueSaturationValue(10, 15, 10, p=0.3),
        ])

    aug.extend([
        A.Resize(image_size, image_size),
        A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ToTensorV2(),
    ])
    return A.Compose(aug)


def build_eval_transform(image_size: int):
    """Deterministic eval transform: resize + normalise only."""
    import albumentations as A
    from albumentations.pytorch import ToTensorV2

    return A.Compose([
        A.Resize(image_size, image_size),
        A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ToTensorV2(),
    ])


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------
class FaceCropDataset:
    """Training dataset over face crops, with optional on-the-fly SBI.

    Subclasses torch.utils.data.Dataset lazily (so this file imports without
    torch). Construct via build_dataloaders or directly inside a GPU function.
    """

    def __init__(
        self,
        samples: List[Sample],
        image_size: int,
        train: bool = True,
        compression_aug: bool = True,
        hflip: bool = True,
        sbi_prob: float = 0.0,
    ):
        self.samples = samples
        self.image_size = image_size
        self.train = train
        self._transform = (
            build_train_transform(image_size, compression_aug, hflip)
            if train else build_eval_transform(image_size)
        )
        # SBI only makes sense at train time and on real images.
        self._sbi = None
        if train and sbi_prob > 0.0:
            from .sbi import SBITransform  # local import
            self._sbi = SBITransform(prob=sbi_prob)

    def __len__(self) -> int:
        return len(self.samples)

    def labels(self) -> List[int]:
        """Static labels (pre-SBI) — used for the WeightedRandomSampler."""
        return [s.label for s in self.samples]

    def _read_rgb(self, path: str):
        import cv2
        bgr = cv2.imread(path)
        if bgr is None:
            # return a black image rather than crashing the whole epoch
            import numpy as np
            return np.zeros((self.image_size, self.image_size, 3), dtype="uint8")
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def __getitem__(self, idx: int):
        import torch

        s = self.samples[idx]
        img = self._read_rgb(s.path)
        label = s.label

        # On-the-fly SBI: may convert a real crop into a pseudo-fake (label 1).
        if self._sbi is not None:
            img, label = self._sbi(img, label)

        out = self._transform(image=img)["image"]
        return out, torch.tensor(float(label), dtype=torch.float32)


class EvalFaceCropDataset(FaceCropDataset):
    """Eval dataset: no augmentation, no SBI. Returns (tensor, label, path)."""

    def __init__(self, samples: List[Sample], image_size: int):
        super().__init__(samples, image_size, train=False,
                         compression_aug=False, hflip=False, sbi_prob=0.0)

    def __getitem__(self, idx: int):
        import torch
        s = self.samples[idx]
        img = self._read_rgb(s.path)
        out = self._transform(image=img)["image"]
        return out, torch.tensor(float(s.label), dtype=torch.float32), s.path


def _as_torch_dataset(ds: FaceCropDataset):
    """Wrap our plain class as a real torch Dataset (lazy import)."""
    from torch.utils.data import Dataset as _TorchDataset

    class _Wrapped(_TorchDataset):
        def __len__(_self):
            return len(ds)

        def __getitem__(_self, i):
            return ds[i]

    return _Wrapped()


# ---------------------------------------------------------------------------
# Dataloader builder
# ---------------------------------------------------------------------------
def build_dataloaders(config) -> Dict[str, object]:
    """Build train/val dataloaders from the config's crops dir + train datasets.

    Returns dict with keys: ``train`` (DataLoader), ``val`` (DataLoader),
    ``train_size``, ``val_size``, ``pos_weight`` (for class-balanced BCE).
    Uses identity-disjoint splitting and an optional WeightedRandomSampler.
    """
    import torch
    from torch.utils.data import DataLoader, WeightedRandomSampler

    all_samples = index_crops(config.crops_dir, config.train_datasets)
    if not all_samples:
        raise RuntimeError(
            f"No face crops found under {config.crops_dir} for datasets "
            f"{config.train_datasets}. Run face extraction first."
        )

    train_s, val_s = identity_disjoint_split(
        all_samples, config.val_fraction, seed=config.seed
    )

    train_ds = FaceCropDataset(
        train_s, config.image_size, train=True,
        compression_aug=config.compression_aug, hflip=config.hflip,
        sbi_prob=config.sbi_prob if config.sbi else 0.0,
    )
    val_ds = EvalFaceCropDataset(val_s, config.image_size)

    # class balancing
    sampler = None
    pos_weight = 1.0
    train_labels = train_ds.labels()
    n_pos = max(1, sum(train_labels))
    n_neg = max(1, len(train_labels) - n_pos)
    pos_weight = n_neg / n_pos  # for BCEWithLogits pos_weight
    if config.balance_classes:
        # WeightedRandomSampler equalises class draw probability per batch.
        class_count = {0: n_neg, 1: n_pos}
        weights = [1.0 / class_count[l] for l in train_labels]
        sampler = WeightedRandomSampler(
            weights=torch.as_tensor(weights, dtype=torch.double),
            num_samples=len(weights), replacement=True,
        )

    train_loader = DataLoader(
        _as_torch_dataset(train_ds),
        batch_size=config.batch_size,
        sampler=sampler,
        shuffle=(sampler is None),
        num_workers=config.num_workers,
        pin_memory=True,
        drop_last=True,
        persistent_workers=config.num_workers > 0,
    )
    val_loader = DataLoader(
        _as_torch_dataset(val_ds),
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=True,
        persistent_workers=config.num_workers > 0,
    )

    return {
        "train": train_loader,
        "val": val_loader,
        "train_size": len(train_s),
        "val_size": len(val_s),
        "pos_weight": pos_weight,
    }


def build_eval_dataloader(config, dataset_name: str):
    """Build a no-aug eval dataloader over one dataset's crops (cross-dataset)."""
    from torch.utils.data import DataLoader

    samples = index_crops(config.crops_dir, [dataset_name])
    if not samples:
        raise RuntimeError(
            f"No crops for eval dataset '{dataset_name}' under {config.crops_dir}."
        )
    ds = EvalFaceCropDataset(samples, config.image_size)
    return DataLoader(
        _as_torch_dataset(ds),
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=True,
    ), samples
