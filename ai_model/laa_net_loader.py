"""
Optional loader for LAA-Net (Localized Artifact Attention Network) inference.
Only used when external/laa_net is cloned and weights are provided.
See external/README.md and docs/guides/LAA_NET_SETUP.md.
"""
import logging
import math
import os
import sys
from pathlib import Path
from typing import Optional, Tuple, Callable, Any

logger = logging.getLogger(__name__)

# Default paths (container: /app, host: project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LAA_NET_DEFAULT_ROOT = _PROJECT_ROOT / "external" / "laa_net"
_LAA_NET_CONFIG_NAME = "efn4_fpn_hm_adv.yaml"


def _find_laa_root() -> Optional[Path]:
    root = os.getenv("LAA_NET_ROOT")
    if root and Path(root).is_dir():
        return Path(root)
    if _LAA_NET_DEFAULT_ROOT.is_dir():
        return _LAA_NET_DEFAULT_ROOT
    return None


def load_laa_net(
    laa_root: Optional[Path] = None,
    weights_path: Optional[str] = None,
    device: str = "cpu",
) -> Tuple[Any, Optional[Callable], Optional[str]]:
    """
    Load LAA-Net model and build preprocessing function.
    Requires: LAA-Net repo at laa_root (or LAA_NET_ROOT / external/laa_net),
              weights .pth at weights_path (or LAA_NET_WEIGHTS).
    Returns:
        (model, preprocess_fn, device) or (None, None, None) on failure.
    """
    root = laa_root or _find_laa_root()
    if not root or not root.is_dir():
        logger.info("LAA-Net root not found (set LAA_NET_ROOT or clone to external/laa_net)")
        return (None, None, None)

    wpath = weights_path or os.getenv("LAA_NET_WEIGHTS")
    if not wpath:
        logger.info("LAA-Net weights path not set (LAA_NET_WEIGHTS or laa_weights_path)")
        return (None, None, None)
    wpath = Path(wpath)
    if not wpath.is_file():
        logger.warning(f"LAA-Net weights file not found: {wpath}")
        return (None, None, None)

    config_path = root / "configs" / _LAA_NET_CONFIG_NAME
    if not config_path.is_file():
        logger.warning(f"LAA-Net config not found: {config_path}")
        return (None, None, None)

    # Insert LAA-Net root so their imports work
    laa_root_str = str(root.resolve())
    if laa_root_str not in sys.path:
        sys.path.insert(0, laa_root_str)

    try:
        from yaml import load as yaml_load
        try:
            from yaml import CLoader as Loader
        except ImportError:
            from yaml import Loader

        with open(config_path) as f:
            cfg = yaml_load(f, Loader=Loader)
        if not isinstance(cfg, dict):
            cfg = {}

        # Override weights path to absolute
        cfg.setdefault("TEST", {})["pretrained"] = str(wpath.resolve())
        cfg["TEST"]["subtask"] = "test_img"

        # Ensure DATASET.IMAGE_SIZE and TRANSFORM for preprocessing
        cfg.setdefault("DATASET", {})
        cfg["DATASET"].setdefault("IMAGE_SIZE", [384, 384])
        cfg["DATASET"].setdefault("TRANSFORM", {}).setdefault("normalize", {"mean": [0.5, 0.5, 0.5], "std": [0.5, 0.5, 0.5]})

        from models import build_model, load_pretrained, MODELS
        from package_utils.transform import get_center_scale, get_affine_transform, final_transform
        import torch
        import cv2
        import numpy as np

        # Build model (same as LAA-Net test.py)
        model = build_model(cfg["MODEL"], MODELS)
        model = load_pretrained(model, cfg["TEST"]["pretrained"])
        model = model.to(device)
        model.eval()

        # Use float32 for compatibility (LAA-Net training uses float64)
        model = model.float()
        image_size = list(cfg["DATASET"].get("IMAGE_SIZE", [384, 384]))
        aspect_ratio = image_size[1] * 1.0 / image_size[0]
        pixel_std = 200
        # final_transform expects obj.TRANSFORM.normalize.mean and .std
        norm = cfg["DATASET"].get("TRANSFORM", {}).get("normalize", {"mean": [0.5, 0.5, 0.5], "std": [0.5, 0.5, 0.5]})
        class _Norm:
            mean = norm.get("mean", [0.5, 0.5, 0.5])
            std = norm.get("std", [0.5, 0.5, 0.5])
        class _T:
            normalize = _Norm()
        class _Cfg:
            TRANSFORM = _T()
        transforms = final_transform(_Cfg())

        def preprocess_frame(frame_bgr: np.ndarray):
            """frame_bgr: numpy (H,W,3) BGR. Returns tensor (1, 3, 384, 384)."""
            img = cv2.resize(frame_bgr, (317, 317))
            img = img[60:317, 30:287, :]
            c, s = get_center_scale(img.shape[:2], aspect_ratio, pixel_std)
            trans = get_affine_transform(c, s, 0, image_size)
            out = cv2.warpAffine(
                img, trans,
                (int(image_size[0]), int(image_size[1])),
                flags=cv2.INTER_LINEAR,
            )
            # LAA-Net expects input/255 then ToTensor+Normalize
            x = transforms(out / 255.0)
            x = x.unsqueeze(0).float()
            return x

        logger.info("LAA-Net model and preprocess loaded successfully")
        return (model, preprocess_frame, device)

    except Exception as e:
        logger.warning("LAA-Net load failed: %s", e, exc_info=True)
        return (None, None, None)


def run_laa_inference(
    model: Any,
    preprocess_fn: Callable,
    frame_bgr: Any,
    device: str = "cpu",
) -> float:
    """
    Run LAA-Net on one frame. frame_bgr: numpy (H,W,3) BGR.
    Returns fake probability in [0, 1].
    """
    import torch
    try:
        x = preprocess_fn(frame_bgr)
        x = x.to(device)
        with torch.no_grad():
            outputs = model(x)
        if isinstance(outputs, list):
            outputs = outputs[0]
        cls_out = outputs["cls"]
        if hasattr(cls_out, "cpu"):
            logit = cls_out.cpu().numpy()[0, -1]
        else:
            logit = float(cls_out[0, -1])
        prob = 1.0 / (1.0 + math.exp(-logit))
        return float(prob)
    except Exception as e:
        logger.debug("LAA-Net inference error: %s", e)
        return 0.5
