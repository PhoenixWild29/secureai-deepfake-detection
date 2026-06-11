#!/usr/bin/env python3
"""
Kaggle ConvNeXt-Base training helper (Phase 4 — SOTA backbone).

Run `python scripts/setup/kaggle_convnext_training.py --print-notebook`
to print a self-contained training notebook that trains a ConvNeXt-Base
deepfake detector — same direct-supervised approach that worked for ResNet50,
but with a modern SOTA backbone (~88M params vs ~25M for ResNet50).

Expected: +3-5 AUC over ResNet50 baseline (0.92 → 0.95+). ConvNeXt-Base is used
in multiple recent deepfake detection papers and is the current go-to backbone
for image classification leaderboards.

The notebook uses the same `secureai-celeb-df-v2-frames` dataset already on Kaggle.
"""
import argparse


CONVNEXT_NOTEBOOK_CODE = r'''
# ==========================================================================
# ConvNeXt-Base Training — SecureAI DeepFake Detection (Phase 4, SOTA push)
# ==========================================================================

# Cell 1 -- Install
import subprocess
subprocess.run(["pip", "install", "-q", "scikit-learn"], check=True)

# Cell 2 -- Imports
import os, json, random, time
from pathlib import Path
from datetime import datetime
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
import torchvision.transforms as transforms
from torchvision.models import convnext_base, ConvNeXt_Base_Weights
from PIL import Image
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {DEVICE}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"CUDA memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# Cell 3 -- Dataset
class FrameDataset(Dataset):
    def __init__(self, root_dirs, transform=None):
        self.samples = []
        self.transform = transform
        for root in root_dirs:
            root = Path(root)
            for label_name, label_val in [("real", 0), ("fake", 1)]:
                d = root / label_name
                if d.exists():
                    for f in sorted(d.glob("*.jpg")):
                        self.samples.append((str(f), label_val))
        random.shuffle(self.samples)
        print(f"  Loaded {len(self.samples)} frames from {root_dirs}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label

normalize = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
train_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),
    transforms.RandomGrayscale(p=0.05),
    transforms.ToTensor(),
    normalize,
])
val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    normalize,
])

DATA_ROOT = "/kaggle/input/secureai-celeb-df-v2-frames/celeb_df_v2_frames"
train_ds = FrameDataset([f"{DATA_ROOT}/train"], train_transform)
val_ds   = FrameDataset([f"{DATA_ROOT}/val"],   val_transform)
test_ds  = FrameDataset([f"{DATA_ROOT}/test"],  val_transform)

# Weighted sampler for any residual imbalance
labels = [s[1] for s in train_ds.samples]
class_counts = [labels.count(0), labels.count(1)]
weights = [1.0 / class_counts[l] for l in labels]
sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)

# ConvNeXt-Base is bigger than ResNet50 — use smaller batch_size for T4 16GB
train_loader = DataLoader(train_ds, batch_size=32, sampler=sampler,
                          num_workers=4, pin_memory=True)
val_loader   = DataLoader(val_ds,   batch_size=32, shuffle=False,
                          num_workers=4, pin_memory=True)
test_loader  = DataLoader(test_ds,  batch_size=32, shuffle=False,
                          num_workers=4, pin_memory=True)

print(f"Train: {len(train_ds):,}  Val: {len(val_ds):,}  Test: {len(test_ds):,}")
print(f"Real: {class_counts[0]:,}  Fake: {class_counts[1]:,}  Ratio: {class_counts[1]/class_counts[0]:.2f}")

# Cell 4 -- Model: ConvNeXt-Base with custom classifier head
model = convnext_base(weights=ConvNeXt_Base_Weights.IMAGENET1K_V1)

# ConvNeXt's classifier is Sequential[LayerNorm2d, Flatten, Linear(1024, 1000)]
# Replace the final Linear with our MLP head
model.classifier[2] = nn.Sequential(
    nn.Dropout(0.5),
    nn.Linear(1024, 512),
    nn.GELU(),
    nn.Dropout(0.3),
    nn.Linear(512, 2),
)
model = model.to(DEVICE)

# Freeze early feature stages (stem + first 2 of 4 ConvNeXt stages)
# ConvNeXt structure: features[0]=stem, [1]=stage1, [2]=down, [3]=stage2, [4]=down, [5]=stage3, [6]=down, [7]=stage4
for name, param in model.named_parameters():
    if name.startswith("features.0") or name.startswith("features.1") or \
       name.startswith("features.2") or name.startswith("features.3"):
        param.requires_grad = False

trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total     = sum(p.numel() for p in model.parameters())
print(f"Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.1f}%)")

# Cell 5 -- Training setup
EPOCHS       = 30
LR           = 1e-4   # smaller than ResNet50's 3e-4 — ConvNeXt is sensitive
WEIGHT_DECAY = 5e-5

optimizer = optim.AdamW(
    [p for p in model.parameters() if p.requires_grad],
    lr=LR, weight_decay=WEIGHT_DECAY
)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)
criterion = nn.CrossEntropyLoss(label_smoothing=0.1)   # small label smoothing helps ConvNeXt
scaler    = torch.amp.GradScaler("cuda") if DEVICE.type == "cuda" else None

best_auc = 0.0
out_dir  = Path("/kaggle/working")
history  = {"train_loss": [], "val_loss": [], "val_auc": [], "val_acc": []}
t_start  = time.time()

# Cell 6 -- Training loop
for epoch in range(1, EPOCHS + 1):
    t0 = time.time()

    # --- Train ---
    model.train()
    tr_loss, tr_correct, tr_total = 0, 0, 0
    for imgs, labels in train_loader:
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        if scaler:
            with torch.amp.autocast("cuda"):
                out  = model(imgs)
                loss = criterion(out, labels)
            scaler.scale(loss).backward()
            # Gradient clipping (helps with ConvNeXt stability)
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            out  = model(imgs)
            loss = criterion(out, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
        tr_loss    += loss.item()
        tr_correct += out.argmax(1).eq(labels).sum().item()
        tr_total   += labels.size(0)
    scheduler.step()

    # --- Validate ---
    model.eval()
    vl_loss, all_probs, all_labels = 0, [], []
    with torch.no_grad():
        for imgs, labels in val_loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            out  = model(imgs)
            loss = criterion(out, labels)
            vl_loss += loss.item()
            probs = torch.softmax(out, 1)[:, 1].cpu().numpy()
            all_probs.extend(probs)
            all_labels.extend(labels.cpu().numpy())

    val_auc = roc_auc_score(all_labels, all_probs) if len(set(all_labels)) > 1 else 0.0
    val_acc = accuracy_score(all_labels, [p > 0.5 for p in all_probs])
    elapsed = time.time() - t0

    history["train_loss"].append(tr_loss / len(train_loader))
    history["val_loss"].append(vl_loss / len(val_loader))
    history["val_auc"].append(val_auc)
    history["val_acc"].append(val_acc)

    print(f"Epoch {epoch:3d}/{EPOCHS}  "
          f"TrainLoss: {tr_loss/len(train_loader):.4f}  "
          f"ValLoss: {vl_loss/len(val_loader):.4f}  "
          f"ValAUC: {val_auc:.4f}  ValAcc: {val_acc*100:.2f}%  "
          f"LR: {scheduler.get_last_lr()[0]:.2e}  Time: {elapsed:.0f}s")

    if val_auc > best_auc:
        best_auc = val_auc
        torch.save({"epoch": epoch, "model_state_dict": model.state_dict(),
                    "val_auc": val_auc, "val_acc": val_acc},
                   out_dir / "best_convnext_model.pth")
        print(f"  --> New best AUC: {best_auc:.4f}  (saved best_convnext_model.pth)")

total_time = time.time() - t_start
print(f"\nTotal training time: {total_time/60:.1f} min")

# Cell 7 -- Test evaluation
model.load_state_dict(torch.load(out_dir / "best_convnext_model.pth")["model_state_dict"])
model.eval()
all_probs, all_labels = [], []
with torch.no_grad():
    for imgs, labels in test_loader:
        imgs = imgs.to(DEVICE)
        probs = torch.softmax(model(imgs), 1)[:, 1].cpu().numpy()
        all_probs.extend(probs)
        all_labels.extend(labels.numpy())

test_auc = roc_auc_score(all_labels, all_probs)
test_acc = accuracy_score(all_labels, [p > 0.5 for p in all_probs])
test_f1  = f1_score(all_labels, [p > 0.5 for p in all_probs])

print(f"\n{'='*60}")
print(f"CONVNEXT-BASE FINAL TEST RESULTS (Celeb-DF v2 test)")
print(f"{'='*60}")
print(f"  AUC-ROC  : {test_auc:.4f}  <-- primary benchmark metric")
print(f"  Accuracy : {test_acc:.4f}  ({test_acc*100:.2f}%)")
print(f"  F1 Score : {test_f1:.4f}")
print(f"  Best Val AUC: {best_auc:.4f}")
print(f"  Training time: {total_time/60:.1f} min")
print(f"{'='*60}")

# Comparison to prior ResNet50 baseline
RESNET50_TEST_AUC = 0.9176  # our full 518-video benchmark
delta = test_auc - RESNET50_TEST_AUC
print(f"\nvs. ResNet50 baseline (full 518-video): {RESNET50_TEST_AUC:.4f}")
print(f"  Delta AUC: {'+' if delta >= 0 else ''}{delta:.4f}")
if delta > 0.02:
    print(f"  Result: STRONG WIN — SOTA-class backbone is paying off")
elif delta > 0:
    print(f"  Result: Modest gain — marginal improvement")
else:
    print(f"  Result: No gain — unexpected, investigate")

results = {
    "test_auc_roc": test_auc,
    "test_accuracy": test_acc,
    "test_f1": test_f1,
    "best_val_auc": best_auc,
    "epochs_trained": EPOCHS,
    "training_time_minutes": total_time / 60,
    "training_date": datetime.now().isoformat(),
    "backbone": "ConvNeXt-Base (ImageNet1K_V1)",
    "parameters_millions": total / 1e6,
    "baseline_resnet50_auc": RESNET50_TEST_AUC,
    "delta_vs_resnet50": delta,
    "history": history,
}
with open(out_dir / "convnext_test_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults -> /kaggle/working/convnext_test_results.json")
print(f"Model   -> /kaggle/working/best_convnext_model.pth")
'''


def print_notebook():
    print("=" * 70)
    print("KAGGLE CONVNEXT-BASE TRAINING NOTEBOOK")
    print("Paste this entire block into a Kaggle notebook cell")
    print("=" * 70)
    print(CONVNEXT_NOTEBOOK_CODE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-notebook", action="store_true")
    args = parser.parse_args()
    if args.print_notebook:
        print_notebook()
    else:
        print(__doc__)
        print("Usage:")
        print("  python scripts/setup/kaggle_convnext_training.py --print-notebook")


if __name__ == "__main__":
    main()
