#!/usr/bin/env python3
"""
SecureAI DeepFake Detection -- Kaggle GPU Training Notebook
============================================================

HOW TO USE THIS ON KAGGLE (free T4/P100 GPU, 30 hrs/week):
------------------------------------------------------------
1. Go to https://www.kaggle.com  and sign in (or create a free account)

2. Upload the frames dataset:
   a. Zip the extracted frames:
      cd SecureAI-DeepFake-Detection
      python scripts/setup/kaggle_training.py --zip-dataset
   b. Go to kaggle.com/datasets -> New Dataset
   c. Upload the zip (celeb_df_v2_frames.zip, ~2.3 GB)
   d. Name it: secureai-celeb-df-v2-frames

3. Upload the code:
   a. Go to kaggle.com/code -> New Notebook
   b. Settings -> Accelerator -> GPU T4 x2  (or P100)
   c. Settings -> Internet -> On
   d. Add Data -> Your Datasets -> secureai-celeb-df-v2-frames
   e. Paste this entire file into a code cell and run

4. After training, download the model:
   a. In the notebook output, the model saves to /kaggle/working/
   b. Download best_model.pth (~90 MB)
   c. Place at: ai_model/trained_models/resnet50_celeb_df_v2.pth

EXPECTED RESULTS ON FREE KAGGLE GPU:
   - ~2 min per epoch on T4
   - 50 epochs = ~100 min total
   - Expected AUC-ROC: 0.85-0.92 (ResNet50 baseline)
   - State-of-the-art (LAA-Net ensemble): 0.95+  <- Phase 3 target
"""

# ============================================================
# KAGGLE NOTEBOOK CODE STARTS HERE
# (paste everything below into a Kaggle notebook cell)
# ============================================================

KAGGLE_NOTEBOOK_CODE = '''
# Cell 1 -- Install dependencies
import subprocess
subprocess.run(["pip", "install", "-q", "scikit-learn", "timm"], check=True)

# Cell 2 -- Imports
import os, json, time, random
from pathlib import Path
from datetime import datetime
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
import torchvision.transforms as transforms
from torchvision.models import resnet50, ResNet50_Weights
from PIL import Image
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {DEVICE}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

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

train_loader = DataLoader(train_ds, batch_size=64, sampler=sampler,
                          num_workers=4, pin_memory=True)
val_loader   = DataLoader(val_ds,   batch_size=64, shuffle=False,
                          num_workers=4, pin_memory=True)
test_loader  = DataLoader(test_ds,  batch_size=64, shuffle=False,
                          num_workers=4, pin_memory=True)

print(f"Train: {len(train_ds):,}  Val: {len(val_ds):,}  Test: {len(test_ds):,}")
print(f"Real: {class_counts[0]:,}  Fake: {class_counts[1]:,}  Ratio: {class_counts[1]/class_counts[0]:.2f}")

# Cell 4 -- Model (ResNet50 fine-tuned)
model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
model.fc = nn.Sequential(
    nn.Dropout(0.5),
    nn.Linear(2048, 512),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(512, 2),
)
model = model.to(DEVICE)

# Freeze early layers, train from layer3 onwards (transfer learning)
for name, param in model.named_parameters():
    if "layer1" in name or "layer2" in name or "bn1" in name or "conv1" in name:
        param.requires_grad = False

trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total     = sum(p.numel() for p in model.parameters())
print(f"Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.1f}%)")

# Cell 5 -- Training loop
EPOCHS       = 50
LR           = 3e-4
WEIGHT_DECAY = 1e-4

optimizer = optim.AdamW(
    [p for p in model.parameters() if p.requires_grad],
    lr=LR, weight_decay=WEIGHT_DECAY
)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)
criterion = nn.CrossEntropyLoss()
scaler    = torch.amp.GradScaler("cuda") if DEVICE.type == "cuda" else None

best_auc  = 0.0
out_dir   = Path("/kaggle/working")
history   = {"train_loss": [], "val_loss": [], "val_auc": [], "val_acc": []}

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
            scaler.step(optimizer)
            scaler.update()
        else:
            out  = model(imgs)
            loss = criterion(out, labels)
            loss.backward()
            optimizer.step()
        tr_loss   += loss.item()
        tr_correct += out.argmax(1).eq(labels).sum().item()
        tr_total  += labels.size(0)
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
          f"ValAUC: {val_auc:.4f}  "
          f"ValAcc: {val_acc*100:.2f}%  "
          f"LR: {scheduler.get_last_lr()[0]:.2e}  "
          f"Time: {elapsed:.0f}s")

    if val_auc > best_auc:
        best_auc = val_auc
        torch.save({
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "val_auc": val_auc,
            "val_acc": val_acc,
        }, out_dir / "best_model.pth")
        print(f"  --> New best AUC: {best_auc:.4f}  (saved best_model.pth)")

# Cell 6 -- Test set evaluation
model.load_state_dict(torch.load(out_dir / "best_model.pth")["model_state_dict"])
model.eval()
all_probs, all_labels = [], []
with torch.no_grad():
    for imgs, labels in test_loader:
        imgs = imgs.to(DEVICE)
        probs = torch.softmax(model(imgs), 1)[:, 1].cpu().numpy()
        all_probs.extend(probs)
        all_labels.extend(labels.numpy())

test_auc  = roc_auc_score(all_labels, all_probs)
test_acc  = accuracy_score(all_labels, [p > 0.5 for p in all_probs])
test_f1   = f1_score(all_labels, [p > 0.5 for p in all_probs])

print(f"\\n{'='*50}")
print(f"FINAL TEST RESULTS (Celeb-DF v2 official test split)")
print(f"{'='*50}")
print(f"  AUC-ROC  : {test_auc:.4f}  <-- primary benchmark metric")
print(f"  Accuracy : {test_acc:.4f}  ({test_acc*100:.2f}%)")
print(f"  F1 Score : {test_f1:.4f}")
print(f"  Best Val AUC: {best_auc:.4f}")
print(f"{'='*50}")

# Save final results
results = {
    "test_auc_roc": test_auc,
    "test_accuracy": test_acc,
    "test_f1": test_f1,
    "best_val_auc": best_auc,
    "epochs_trained": EPOCHS,
    "training_date": datetime.now().isoformat(),
    "history": history,
}
with open(out_dir / "test_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"Results saved to /kaggle/working/test_results.json")
print(f"Model saved to /kaggle/working/best_model.pth")
'''

# ============================================================
# ZIP HELPER
# ============================================================

import argparse
import sys

def zip_dataset():
    """Zip the extracted frames for upload to Kaggle."""
    import shutil
    from pathlib import Path

    src = Path("datasets/celeb_df_v2_frames")
    if not src.exists():
        print("ERROR: datasets/celeb_df_v2_frames/ not found.")
        print("       Run frame extraction first:")
        print("       python scripts/setup/kaggle_training.py  (without --zip-dataset)")
        sys.exit(1)

    # Count files
    n_files = sum(1 for f in src.rglob("*.jpg"))
    if n_files == 0:
        print(f"ERROR: No JPG files found in {src}. Frame extraction may still be running.")
        sys.exit(1)

    print(f"Found {n_files:,} JPG files in {src}")
    print("Creating celeb_df_v2_frames.zip ...")

    zip_path = shutil.make_archive("celeb_df_v2_frames", "zip", "datasets", "celeb_df_v2_frames")
    size_mb = Path(zip_path).stat().st_size / (1024 * 1024)
    print(f"\n[OK] Created: {zip_path}  ({size_mb:.0f} MB)")
    print(f"\nNext steps:")
    print(f"  1. Go to https://www.kaggle.com/datasets/new")
    print(f"  2. Upload: {zip_path}")
    print(f"  3. Name it: secureai-celeb-df-v2-frames")
    print(f"  4. Create a new notebook at https://www.kaggle.com/code")
    print(f"  5. Add the dataset, enable GPU T4, paste the notebook code")
    print(f"\nThe full Kaggle notebook code is printed by:")
    print(f"  python scripts/setup/kaggle_training.py --print-notebook")


def print_notebook():
    """Print the Kaggle notebook code to stdout."""
    print("=" * 70)
    print("KAGGLE NOTEBOOK CODE")
    print("Copy everything between the dashes into a Kaggle notebook cell")
    print("=" * 70)
    print(KAGGLE_NOTEBOOK_CODE)


def main():
    parser = argparse.ArgumentParser(
        description="Kaggle GPU training helper for SecureAI deepfake detection")
    parser.add_argument("--zip-dataset", action="store_true",
                        help="Zip celeb_df_v2_frames/ for Kaggle upload")
    parser.add_argument("--print-notebook", action="store_true",
                        help="Print the Kaggle notebook code")
    args = parser.parse_args()

    if args.zip_dataset:
        zip_dataset()
    elif args.print_notebook:
        print_notebook()
    else:
        print(__doc__)
        print("\nUsage:")
        print("  python scripts/setup/kaggle_training.py --zip-dataset      # after frame extraction")
        print("  python scripts/setup/kaggle_training.py --print-notebook   # see notebook code")


if __name__ == "__main__":
    main()
