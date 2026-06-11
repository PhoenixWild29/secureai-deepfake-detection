#!/usr/bin/env python3
"""
Kaggle SBI training helper.

Run `python scripts/setup/kaggle_sbi_training.py --print-notebook`
to print a self-contained training notebook that trains a ResNet50 deepfake
detector using Self-Blended Images (SBI) augmentation.

The notebook expects the dataset `secureai-celeb-df-v2-frames` already uploaded
to Kaggle (the same one used for the first training run).

Training regime:
  - Only real face frames are used as input (train/real/ under the dataset)
  - Half of each batch is SBI-generated fakes (labels flipped to 1)
  - Val/test evaluation uses the ACTUAL Celeb-DF v2 val/test splits (both real+fake)
  - This tests true generalization: model trained on SBI, evaluated on real deepfakes

Expected outcome: cross-dataset generalization significantly better than the
first run. Same-dataset test AUC may be slightly lower than the direct-trained
model (because it never saw actual fakes), but the ensemble of both gives the
best result overall.
"""
import argparse

SBI_NOTEBOOK_CODE = r'''
# ==========================================================================
# SBI (Self-Blended Images) Training — SecureAI DeepFake Detection Phase 4
# ==========================================================================

# Cell 1 -- Install
import subprocess
subprocess.run(["pip", "install", "-q", "scikit-learn"], check=True)

# Cell 2 -- Imports
import os, json, random, time
from pathlib import Path
from datetime import datetime
import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
from torchvision.models import resnet50, ResNet50_Weights
from PIL import Image
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {DEVICE}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# Cell 3 -- SBI augmentation (inlined for Kaggle portability)
def _random_color_jitter(img, rng):
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV).astype(np.int32)
    hsv[..., 0] = (hsv[..., 0] + rng.randint(-8, 8)) % 180
    hsv[..., 1] = np.clip(hsv[..., 1] * rng.uniform(0.85, 1.15), 0, 255)
    hsv[..., 2] = np.clip(hsv[..., 2] * rng.uniform(0.85, 1.15), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

def _random_geometric(img, rng):
    h, w = img.shape[:2]
    angle = rng.uniform(-4, 4); scale = rng.uniform(0.97, 1.03)
    tx = rng.uniform(-0.02, 0.02) * w; ty = rng.uniform(-0.02, 0.02) * h
    M = cv2.getRotationMatrix2D((w/2, h/2), angle, scale)
    M[0, 2] += tx; M[1, 2] += ty
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT_101)

def _maybe_blur(img, rng):
    if rng.random() < 0.3:
        k = rng.choice([3, 5])
        img = cv2.GaussianBlur(img, (k, k), 0)
    return img

def _build_elliptical_mask(h, w, rng):
    mask = np.zeros((h, w), dtype=np.float32)
    cx = w // 2 + rng.randint(-4, 4); cy = h // 2 + rng.randint(-4, 4)
    ax = int(w * rng.uniform(0.35, 0.45)); ay = int(h * rng.uniform(0.40, 0.50))
    angle = rng.uniform(-15, 15)
    cv2.ellipse(mask, (cx, cy), (ax, ay), angle, 0, 360, 1.0, -1)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=rng.uniform(6, 12))
    return np.clip(mask, 0, 1)

def self_blend(img_rgb, rng=None):
    if rng is None: rng = random
    target = img_rgb.copy(); source = img_rgb.copy()
    source = _random_color_jitter(source, rng)
    source = _random_geometric(source, rng)
    source = _maybe_blur(source, rng)
    if rng.random() < 0.5:
        target = _random_color_jitter(target, rng)
    h, w = img_rgb.shape[:2]
    mask = _build_elliptical_mask(h, w, rng)[..., None]
    blended = source.astype(np.float32) * mask + target.astype(np.float32) * (1 - mask)
    return np.clip(blended, 0, 255).astype(np.uint8)

# Cell 4 -- Datasets
class SBIDataset(Dataset):
    """Train dataset: real frames, with half made into SBI fakes on-the-fly."""
    def __init__(self, root, transform=None, sbi_prob=0.5):
        self.files = sorted(Path(root).rglob("*.jpg"))
        self.transform = transform; self.sbi_prob = sbi_prob
        print(f"  SBI train pool: {len(self.files)} real frames")
    def __len__(self): return len(self.files)
    def __getitem__(self, idx):
        rng = random.Random()
        img = np.array(Image.open(self.files[idx]).convert("RGB"))
        if rng.random() < self.sbi_prob:
            img = self_blend(img, rng); label = 1
        else:
            label = 0
        pil = Image.fromarray(img)
        if self.transform: pil = self.transform(pil)
        return pil, label

class RealFrameDataset(Dataset):
    """Val/test dataset: actual Celeb-DF v2 real+fake frames (not SBI)."""
    def __init__(self, root, transform=None):
        self.samples = []
        self.transform = transform
        for label_name, label_val in [("real", 0), ("fake", 1)]:
            d = Path(root) / label_name
            if d.exists():
                for f in sorted(d.glob("*.jpg")):
                    self.samples.append((str(f), label_val))
        random.shuffle(self.samples)
        print(f"  {root}: {len(self.samples)} frames")
    def __len__(self): return len(self.samples)
    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform: img = self.transform(img)
        return img, label

# Cell 5 -- Transforms
normalize = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
train_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.15, hue=0.03),
    transforms.ToTensor(),
    normalize,
])
val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    normalize,
])

DATA_ROOT = "/kaggle/input/secureai-celeb-df-v2-frames/celeb_df_v2_frames"
train_ds = SBIDataset(f"{DATA_ROOT}/train/real", train_transform, sbi_prob=0.5)
val_ds   = RealFrameDataset(f"{DATA_ROOT}/val",  val_transform)
test_ds  = RealFrameDataset(f"{DATA_ROOT}/test", val_transform)

train_loader = DataLoader(train_ds, batch_size=64, shuffle=True,  num_workers=4, pin_memory=True)
val_loader   = DataLoader(val_ds,   batch_size=64, shuffle=False, num_workers=4, pin_memory=True)
test_loader  = DataLoader(test_ds,  batch_size=64, shuffle=False, num_workers=4, pin_memory=True)

# Cell 6 -- Model (same architecture as previous training for clean A/B)
model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
model.fc = nn.Sequential(
    nn.Dropout(0.5),
    nn.Linear(2048, 512),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(512, 2),
)
model = model.to(DEVICE)

# Freeze low-level features (same as previous run)
for name, param in model.named_parameters():
    if "layer1" in name or "layer2" in name or "bn1" in name or "conv1" in name:
        param.requires_grad = False

trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total     = sum(p.numel() for p in model.parameters())
print(f"Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.1f}%)")

# Cell 7 -- Training loop
EPOCHS        = 30
LR            = 3e-4
WEIGHT_DECAY  = 1e-4

optimizer = optim.AdamW([p for p in model.parameters() if p.requires_grad],
                        lr=LR, weight_decay=WEIGHT_DECAY)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)
criterion = nn.CrossEntropyLoss()
scaler    = torch.amp.GradScaler("cuda") if DEVICE.type == "cuda" else None

best_auc = 0.0
out_dir  = Path("/kaggle/working")
history  = {"train_loss": [], "val_loss": [], "val_auc": [], "val_acc": []}
t_start  = time.time()

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
            scaler.step(optimizer); scaler.update()
        else:
            out  = model(imgs); loss = criterion(out, labels)
            loss.backward(); optimizer.step()
        tr_loss    += loss.item()
        tr_correct += out.argmax(1).eq(labels).sum().item()
        tr_total   += labels.size(0)
    scheduler.step()

    # --- Validate on ACTUAL Celeb-DF val ---
    model.eval()
    vl_loss, all_probs, all_labels = 0, [], []
    with torch.no_grad():
        for imgs, labels in val_loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            out  = model(imgs); loss = criterion(out, labels)
            vl_loss += loss.item()
            probs = torch.softmax(out, 1)[:, 1].cpu().numpy()
            all_probs.extend(probs); all_labels.extend(labels.cpu().numpy())

    val_auc = roc_auc_score(all_labels, all_probs) if len(set(all_labels)) > 1 else 0.0
    val_acc = accuracy_score(all_labels, [p > 0.5 for p in all_probs])
    elapsed = time.time() - t0

    history["train_loss"].append(tr_loss / len(train_loader))
    history["val_loss"].append(vl_loss / len(val_loader))
    history["val_auc"].append(val_auc); history["val_acc"].append(val_acc)

    print(f"Epoch {epoch:3d}/{EPOCHS}  "
          f"TrainLoss: {tr_loss/len(train_loader):.4f}  "
          f"ValLoss: {vl_loss/len(val_loader):.4f}  "
          f"ValAUC: {val_auc:.4f}  ValAcc: {val_acc*100:.2f}%  "
          f"Time: {elapsed:.0f}s")

    if val_auc > best_auc:
        best_auc = val_auc
        torch.save({"epoch": epoch, "model_state_dict": model.state_dict(),
                    "val_auc": val_auc, "val_acc": val_acc},
                   out_dir / "best_sbi_model.pth")
        print(f"  --> New best AUC: {best_auc:.4f}  (saved best_sbi_model.pth)")

total_time = time.time() - t_start
print(f"\nTotal training time: {total_time/60:.1f} min")

# Cell 8 -- Test evaluation (on ACTUAL Celeb-DF test split)
model.load_state_dict(torch.load(out_dir / "best_sbi_model.pth")["model_state_dict"])
model.eval()
all_probs, all_labels = [], []
with torch.no_grad():
    for imgs, labels in test_loader:
        imgs = imgs.to(DEVICE)
        probs = torch.softmax(model(imgs), 1)[:, 1].cpu().numpy()
        all_probs.extend(probs); all_labels.extend(labels.numpy())

test_auc = roc_auc_score(all_labels, all_probs)
test_acc = accuracy_score(all_labels, [p > 0.5 for p in all_probs])
test_f1  = f1_score(all_labels, [p > 0.5 for p in all_probs])

print(f"\n{'='*60}")
print(f"SBI-TRAINED RESNET50 — FINAL TEST RESULTS")
print(f"(Trained on self-blended REALS; tested on ACTUAL Celeb-DF v2 fakes)")
print(f"{'='*60}")
print(f"  AUC-ROC  : {test_auc:.4f}")
print(f"  Accuracy : {test_acc:.4f}  ({test_acc*100:.2f}%)")
print(f"  F1 Score : {test_f1:.4f}")
print(f"  Best Val AUC: {best_auc:.4f}")
print(f"  Training time: {total_time/60:.1f} min")
print(f"{'='*60}")

results = {
    "test_auc_roc": test_auc, "test_accuracy": test_acc, "test_f1": test_f1,
    "best_val_auc": best_auc, "epochs_trained": EPOCHS,
    "training_time_minutes": total_time / 60,
    "training_date": datetime.now().isoformat(),
    "augmentation": "Self-Blended Images (SBI)",
    "note": "Trained only on REAL Celeb-DF frames with SBI fakes as label=1. Test uses actual fakes.",
    "history": history,
}
with open(out_dir / "sbi_test_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"Results -> /kaggle/working/sbi_test_results.json")
print(f"Model   -> /kaggle/working/best_sbi_model.pth")
'''


def print_notebook():
    print("=" * 70)
    print("KAGGLE SBI TRAINING NOTEBOOK")
    print("Paste this entire block into a Kaggle notebook cell")
    print("=" * 70)
    print(SBI_NOTEBOOK_CODE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-notebook", action="store_true",
                        help="Print the Kaggle notebook code")
    args = parser.parse_args()
    if args.print_notebook:
        print_notebook()
    else:
        print(__doc__)
        print("Usage:")
        print("  python scripts/setup/kaggle_sbi_training.py --print-notebook")


if __name__ == "__main__":
    main()
