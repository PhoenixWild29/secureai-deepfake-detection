"""Training loop for the generalizing deepfake backbone.

Design (per MODEL_IMPROVEMENT_PLAN.md):
  * Backbone via ``timm.create_model(name, pretrained=True, num_classes=1)``.
  * Loss: BCEWithLogitsLoss with optional class-balanced ``pos_weight``.
  * Optimiser: AdamW. Schedule: cosine with linear warmup.
  * Mixed precision (torch.cuda.amp) for speed/memory on A100/H100.
  * Model selection by VAL AUC (never accuracy) — mandatory.
  * Early stopping on val AUC.
  * Resumable from checkpoint for spot/preemption safety.
  * Saves model weights + a metadata json (real metrics, config, timestamp).

Pure-python callable: ``train(config) -> dict``. No notebook.

All heavy imports are inside functions so the module imports torch-free.
"""

from __future__ import annotations

import os
import json
import math
import time
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
def _seed_everything(seed: int) -> None:
    import random
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------------------
# Model / optim builders
# ---------------------------------------------------------------------------
def build_model(config, device):
    """Create the timm backbone with a single-logit head."""
    import timm

    model = timm.create_model(
        config.backbone,
        pretrained=config.pretrained,
        num_classes=config.num_classes,  # 1 -> single logit
    )
    return model.to(device)


def build_optimizer(model, config):
    import torch

    if config.optimizer.lower() == "sgd":
        return torch.optim.SGD(
            model.parameters(), lr=config.lr, momentum=0.9,
            weight_decay=config.weight_decay, nesterov=True,
        )
    return torch.optim.AdamW(
        model.parameters(), lr=config.lr, weight_decay=config.weight_decay
    )


def build_scheduler(optimizer, config, steps_per_epoch: int):
    """Cosine schedule with linear warmup, stepped per-iteration."""
    import torch

    total_steps = max(1, steps_per_epoch * config.epochs)
    warmup_steps = max(0, steps_per_epoch * config.warmup_epochs)

    if config.scheduler == "none":
        return None

    def lr_lambda(step: int) -> float:
        if step < warmup_steps and warmup_steps > 0:
            return float(step + 1) / float(warmup_steps)
        if config.scheduler in ("cosine", "cosine_warmup"):
            progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
            progress = min(1.0, max(0.0, progress))
            return 0.5 * (1.0 + math.cos(math.pi * progress))
        return 1.0

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


# ---------------------------------------------------------------------------
# Checkpoint helpers (resume for spot preemption)
# ---------------------------------------------------------------------------
def _ckpt_paths(config) -> Dict[str, str]:
    os.makedirs(config.checkpoint_dir, exist_ok=True)
    tag = config.backbone.replace("/", "_")
    return {
        "last": os.path.join(config.checkpoint_dir, f"{tag}_last.pth"),
        "best": os.path.join(config.checkpoint_dir, f"{tag}_best.pth"),
        "meta": os.path.join(config.checkpoint_dir, f"{tag}_meta.json"),
    }


def _save_ckpt(path, model, optimizer, scheduler, scaler, epoch, best_auc, config):
    import torch

    torch.save({
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict() if scheduler is not None else None,
        "scaler": scaler.state_dict() if scaler is not None else None,
        "epoch": epoch,
        "best_auc": best_auc,
        "backbone": config.backbone,
        "image_size": config.image_size,
    }, path)


def _load_ckpt(path, model, optimizer=None, scheduler=None, scaler=None):
    import torch

    state = torch.load(path, map_location="cpu")
    model.load_state_dict(state["model"])
    if optimizer is not None and state.get("optimizer") is not None:
        optimizer.load_state_dict(state["optimizer"])
    if scheduler is not None and state.get("scheduler") is not None:
        scheduler.load_state_dict(state["scheduler"])
    if scaler is not None and state.get("scaler") is not None:
        scaler.load_state_dict(state["scaler"])
    return state.get("epoch", 0), state.get("best_auc", 0.0)


# ---------------------------------------------------------------------------
# Validation (val AUC drives model selection)
# ---------------------------------------------------------------------------
def _validate(model, val_loader, device) -> Dict[str, float]:
    import numpy as np
    import torch

    model.eval()
    all_logits, all_labels = [], []
    with torch.no_grad():
        for batch in val_loader:
            # eval dataset returns (x, y, path)
            x, y = batch[0], batch[1]
            x = x.to(device, non_blocking=True)
            with torch.cuda.amp.autocast(enabled=torch.cuda.is_available()):
                logits = model(x).squeeze(-1)
            all_logits.append(logits.float().cpu().numpy())
            all_labels.append(y.numpy())
    logits = np.concatenate(all_logits)
    labels = np.concatenate(all_labels)
    probs = 1.0 / (1.0 + np.exp(-logits))

    from .evaluate import compute_metrics  # reuse the harness
    return compute_metrics(labels, probs)


# ---------------------------------------------------------------------------
# Main training entrypoint
# ---------------------------------------------------------------------------
def train(config) -> dict:
    """Train the backbone end-to-end and return a summary dict.

    Selects the best checkpoint by VAL AUC, supports resume, and writes a
    metadata json next to the best checkpoint. Returns the summary including
    best val AUC and the best-checkpoint path (consumed by evaluate/ensemble).
    """
    import numpy as np
    import torch
    import torch.nn as nn

    from .dataset import build_dataloaders

    _seed_everything(config.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[train] device={device} backbone={config.backbone} "
          f"img={config.image_size} bs={config.batch_size} epochs={config.epochs}")

    loaders = build_dataloaders(config)
    train_loader, val_loader = loaders["train"], loaders["val"]
    print(f"[train] train_size={loaders['train_size']} "
          f"val_size={loaders['val_size']} pos_weight={loaders['pos_weight']:.3f}")

    model = build_model(config, device)
    optimizer = build_optimizer(model, config)
    steps_per_epoch = max(1, len(train_loader))
    scheduler = build_scheduler(optimizer, config, steps_per_epoch)

    use_amp = config.mixed_precision and torch.cuda.is_available()
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    pos_weight = torch.tensor([loaders["pos_weight"]], device=device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    paths = _ckpt_paths(config)
    start_epoch = 0
    best_auc = 0.0
    epochs_no_improve = 0

    # Resume from last checkpoint if present (spot-preemption safety).
    if os.path.exists(paths["last"]):
        try:
            start_epoch, best_auc = _load_ckpt(
                paths["last"], model, optimizer, scheduler, scaler
            )
            start_epoch += 1
            print(f"[train] resumed from epoch {start_epoch}, best_auc={best_auc:.4f}")
        except Exception as exc:
            print(f"[train] could not resume ({exc}); starting fresh.")

    history = []
    for epoch in range(start_epoch, config.epochs):
        model.train()
        t0 = time.time()
        running = 0.0
        for it, (x, y) in enumerate(train_loader):
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=use_amp):
                logits = model(x).squeeze(-1)
                loss = criterion(logits, y)
            scaler.scale(loss).backward()
            if config.grad_clip and config.grad_clip > 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.grad_clip)
            scaler.step(optimizer)
            scaler.update()
            if scheduler is not None:
                scheduler.step()
            running += loss.item()

        train_loss = running / steps_per_epoch
        val_metrics = _validate(model, val_loader, device)
        val_auc = val_metrics["auc"]
        dt = time.time() - t0
        lr_now = optimizer.param_groups[0]["lr"]
        print(f"[train] epoch {epoch+1}/{config.epochs} "
              f"loss={train_loss:.4f} val_auc={val_auc:.4f} "
              f"val_ap={val_metrics['ap']:.4f} lr={lr_now:.2e} ({dt:.0f}s)")
        history.append({"epoch": epoch + 1, "train_loss": train_loss, **val_metrics})

        # always save 'last' for resume
        _save_ckpt(paths["last"], model, optimizer, scheduler, scaler,
                   epoch, best_auc, config)

        # model selection by VAL AUC
        if val_auc > best_auc:
            best_auc = val_auc
            epochs_no_improve = 0
            _save_ckpt(paths["best"], model, optimizer, scheduler, scaler,
                       epoch, best_auc, config)
            print(f"[train]   ^ new best val_auc={best_auc:.4f} -> {paths['best']}")
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= config.early_stop_patience:
                print(f"[train] early stop at epoch {epoch+1} "
                      f"(no val-AUC gain in {epochs_no_improve} epochs)")
                break

    # write metadata json with the REAL metrics
    meta = {
        "backbone": config.backbone,
        "image_size": config.image_size,
        "best_val_auc": best_auc,
        "train_datasets": config.train_datasets,
        "test_datasets": config.test_datasets,
        "epochs_run": (history[-1]["epoch"] if history else 0),
        "config": config.to_dict(),
        "history": history,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "selection": "best checkpoint by VAL AUC (identity-disjoint split)",
    }
    with open(paths["meta"], "w") as f:
        json.dump(meta, f, indent=2, default=str)

    print(f"[train] done. best_val_auc={best_auc:.4f} best_ckpt={paths['best']}")
    return {
        "best_val_auc": best_auc,
        "best_checkpoint": paths["best"],
        "last_checkpoint": paths["last"],
        "meta_path": paths["meta"],
        "history": history,
    }


def load_trained_model(checkpoint_path: str, config=None):
    """Reload a trained backbone for evaluation/inference."""
    import torch
    import timm

    state = torch.load(checkpoint_path, map_location="cpu")
    backbone = state.get("backbone") or (config.backbone if config else None)
    if backbone is None:
        raise ValueError("Cannot infer backbone name; pass a config.")
    model = timm.create_model(backbone, pretrained=False, num_classes=1)
    model.load_state_dict(state["model"])
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return model.to(device)
