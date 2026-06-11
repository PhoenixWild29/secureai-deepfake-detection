# Cowork Prompt — ConvNeXt-Base Training (Phase 4, SOTA backbone)

Third Kaggle training run. Same dataset as before (already uploaded). This one
upgrades the backbone from ResNet50 to ConvNeXt-Base — a SOTA image classification
architecture used in 2024-2025 deepfake detection papers. Expected: +3-5 AUC over
the ResNet50 baseline (0.9176 → 0.95+).

Copy everything between the `===` markers into cowork.

---

```
============================ START OF COWORK PROMPT ============================

You are driving a browser to launch a third Kaggle GPU training run — this one
upgrades the backbone from ResNet50 to ConvNeXt-Base. When you hit anything you
cannot do yourself (login, 2FA, SMS, captcha), STOP and tell me exactly what
action to take, then wait for me to say 'done' before continuing.

## Context

- Project: SecureAI DeepFake Detection
- Prior runs:
  - Run 1 (ResNet50 direct-supervised): test AUC 0.9176 on full 518-video benchmark ✓
  - Run 2 (ResNet50 with SBI augmentation): test AUC 0.6078 — FAILED, abandoned
- This run: ConvNeXt-Base direct-supervised (same training recipe as Run 1, bigger backbone)
- Dataset on Kaggle: secureai-celeb-df-v2-frames (already uploaded, reuse it)
- Final deliverable: best_convnext_model.pth (~350 MB) saved to:
  C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\ai_model\trained_models\convnext_celeb_df_v2.pth

## Step 1 — Open Kaggle and confirm sign-in

1. Go to https://www.kaggle.com
2. Confirm my avatar is top-right (signed in).
3. If not signed in, stop and ask me to sign in.

## Step 2 — Create a new notebook

1. Go to https://www.kaggle.com/code
2. Click "+ New Notebook"
3. Right sidebar → Settings:
   - **Accelerator: GPU T4 x2** (or P100 if T4 unavailable)
   - Internet: ON
   - Persistence: Files only (or whatever default)
4. Right sidebar → Input / Add Data:
   - Search "secureai-celeb-df-v2-frames" under Your Datasets
   - Click "+" to attach it
   - Verify the Input tree now shows `celeb_df_v2_frames/`

## Step 3 — Paste the training code

Paste the ENTIRE code block in the "CONVNEXT TRAINING CODE" section below
into the first code cell.

## Step 4 — Run and verify startup

1. Click Run All (▶▶ or menu → Run All).
2. Within ~30 seconds you should see:
   - "Device: cuda"
   - "GPU: Tesla T4" (or P100)
   - "CUDA memory: 15+ GB" (or ~16 GB for T4)
   - "Loaded 36,137 frames from ['.../train']"  (approximately)
   - "Loaded 6,390 frames from ['.../val']"  (approximately)
   - "Loaded 5,180 frames from ['.../test']"  (approximately)
   - "Total params: 88.1M" and "Trainable params: ~85.9M"
3. If any of these numbers look wildly off, STOP and tell me.
4. If the model download step takes >2 minutes or fails, tell me.

## Step 5 — Wait for training (~90-150 minutes)

ConvNeXt-Base is bigger than ResNet50, so each epoch is slower — expect ~3-5 min
per epoch on T4, so 30 epochs = 90-150 min.

Each epoch prints:
  Epoch  12/30  TrainLoss: 0.0823  ValLoss: 0.1145  ValAUC: 0.9521  ValAcc: 89.23%  LR: 1.23e-04  Time: 210s

Watch for:
- ValAUC climbing past 0.94 in the first ~5 epochs = healthy run
- ValAUC stuck below 0.80 after 10 epochs = possible problem, screenshot and tell me
- Training stops/crashes = capture traceback

If the 12-hour Kaggle session timer is about to expire (unlikely but possible),
the notebook auto-saves. Contact me — we may need to resume from a checkpoint.

## Step 6 — Review final results

When training completes you'll see:
  ==================================================
  CONVNEXT-BASE FINAL TEST RESULTS (Celeb-DF v2 test)
  ==================================================
    AUC-ROC  : 0.9XXX
    ...
  vs. ResNet50 baseline (full 518-video): 0.9176
    Delta AUC: +0.0XXX
    Result: STRONG WIN / Modest gain / No gain

## Step 7 — Download the model and results

1. Right sidebar → /kaggle/working/ file tree should show:
   - best_convnext_model.pth (~350 MB) — the trained weights
   - convnext_test_results.json (~2 KB) — metrics summary
2. Download both (right-click → Download, or click file then Download icon).
3. They land in C:\Users\ssham\Downloads\.

## Step 8 — Move files to the repo

1. Move Downloads\best_convnext_model.pth
   TO: ai_model\trained_models\convnext_celeb_df_v2.pth
2. Move Downloads\convnext_test_results.json
   TO: ai_model\trained_models\convnext_test_results.json
3. If you cannot do the file move: tell me to do it and say 'done' when ready.

## Step 9 — Report final results

Reply with:

```
CONVNEXT-BASE TRAINING COMPLETE

Test AUC-ROC:   0.xxxx
Test Accuracy:  xx.xx%
Test F1:        0.xxxx
Best Val AUC:   0.xxxx
Training time:  xx min

vs. ResNet50 baseline (AUC 0.9176):
  Delta AUC: +x.xxxx (or -x.xxxx)
  Result: [strong win / modest gain / no gain]

Files saved:
  ai_model/trained_models/convnext_celeb_df_v2.pth
  ai_model/trained_models/convnext_test_results.json
Kaggle notebook URL: https://www.kaggle.com/code/<url>
```

Fill in actual numbers from convnext_test_results.json.

## Escalation Rules

STOP and ask me whenever you hit:
- Login / password / 2FA / SMS / captcha
- GPU quota warnings (we have 30 hrs/week, each ConvNeXt run ~2.5 hrs)
- Any error dialog you don't recognize
- Training crash (give me the traceback)
- Unexpected file path behavior

Format:
  STOP: <one-line description>
  ACTION: <specific thing I need to do>
  SAY: 'done' when finished

## CONVNEXT TRAINING CODE

```python
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
    def __len__(self): return len(self.samples)
    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform: img = self.transform(img)
        return img, label

normalize = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
train_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),
    transforms.RandomGrayscale(p=0.05),
    transforms.ToTensor(), normalize,
])
val_transform = transforms.Compose([
    transforms.Resize((224, 224)), transforms.ToTensor(), normalize,
])

DATA_ROOT = "/kaggle/input/secureai-celeb-df-v2-frames/celeb_df_v2_frames"
train_ds = FrameDataset([f"{DATA_ROOT}/train"], train_transform)
val_ds   = FrameDataset([f"{DATA_ROOT}/val"],   val_transform)
test_ds  = FrameDataset([f"{DATA_ROOT}/test"],  val_transform)

labels = [s[1] for s in train_ds.samples]
class_counts = [labels.count(0), labels.count(1)]
weights = [1.0 / class_counts[l] for l in labels]
sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)

train_loader = DataLoader(train_ds, batch_size=32, sampler=sampler,
                          num_workers=4, pin_memory=True)
val_loader   = DataLoader(val_ds, batch_size=32, shuffle=False,
                          num_workers=4, pin_memory=True)
test_loader  = DataLoader(test_ds, batch_size=32, shuffle=False,
                          num_workers=4, pin_memory=True)

print(f"Train: {len(train_ds):,}  Val: {len(val_ds):,}  Test: {len(test_ds):,}")
print(f"Real: {class_counts[0]:,}  Fake: {class_counts[1]:,}  Ratio: {class_counts[1]/class_counts[0]:.2f}")

# Cell 4 -- Model: ConvNeXt-Base with custom classifier head
model = convnext_base(weights=ConvNeXt_Base_Weights.IMAGENET1K_V1)
model.classifier[2] = nn.Sequential(
    nn.Dropout(0.5),
    nn.Linear(1024, 512), nn.GELU(),
    nn.Dropout(0.3),
    nn.Linear(512, 2),
)
model = model.to(DEVICE)

# Freeze stem + first 2 stages (transfer learning)
for name, param in model.named_parameters():
    if name.startswith("features.0") or name.startswith("features.1") or \
       name.startswith("features.2") or name.startswith("features.3"):
        param.requires_grad = False

trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total     = sum(p.numel() for p in model.parameters())
print(f"Total params:      {total/1e6:.1f}M")
print(f"Trainable params:  {trainable/1e6:.1f}M ({100*trainable/total:.1f}%)")

# Cell 5 -- Train
EPOCHS=30; LR=1e-4; WEIGHT_DECAY=5e-5
optimizer = optim.AdamW([p for p in model.parameters() if p.requires_grad],
                        lr=LR, weight_decay=WEIGHT_DECAY)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)
criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
scaler    = torch.amp.GradScaler("cuda") if DEVICE.type == "cuda" else None

best_auc=0.0; out_dir=Path("/kaggle/working")
history={"train_loss":[],"val_loss":[],"val_auc":[],"val_acc":[]}
t_start=time.time()

for epoch in range(1, EPOCHS+1):
    t0=time.time()
    model.train(); tr_loss=0
    for imgs, labels in train_loader:
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        if scaler:
            with torch.amp.autocast("cuda"):
                out=model(imgs); loss=criterion(out, labels)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer); scaler.update()
        else:
            out=model(imgs); loss=criterion(out, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
        tr_loss += loss.item()
    scheduler.step()

    model.eval(); vl_loss=0; all_probs=[]; all_labels=[]
    with torch.no_grad():
        for imgs, labels in val_loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            out=model(imgs); loss=criterion(out, labels); vl_loss += loss.item()
            probs = torch.softmax(out, 1)[:, 1].cpu().numpy()
            all_probs.extend(probs); all_labels.extend(labels.cpu().numpy())

    val_auc = roc_auc_score(all_labels, all_probs) if len(set(all_labels))>1 else 0.0
    val_acc = accuracy_score(all_labels, [p>0.5 for p in all_probs])
    elapsed = time.time()-t0

    history["train_loss"].append(tr_loss/len(train_loader))
    history["val_loss"].append(vl_loss/len(val_loader))
    history["val_auc"].append(val_auc); history["val_acc"].append(val_acc)

    print(f"Epoch {epoch:3d}/{EPOCHS}  TrainLoss: {tr_loss/len(train_loader):.4f}  "
          f"ValLoss: {vl_loss/len(val_loader):.4f}  ValAUC: {val_auc:.4f}  "
          f"ValAcc: {val_acc*100:.2f}%  LR: {scheduler.get_last_lr()[0]:.2e}  Time: {elapsed:.0f}s")

    if val_auc > best_auc:
        best_auc = val_auc
        torch.save({"epoch": epoch, "model_state_dict": model.state_dict(),
                    "val_auc": val_auc, "val_acc": val_acc},
                   out_dir/"best_convnext_model.pth")
        print(f"  --> New best AUC: {best_auc:.4f}  (saved best_convnext_model.pth)")

total_time = time.time() - t_start
print(f"\nTotal training time: {total_time/60:.1f} min")

# Cell 6 -- Test evaluation
model.load_state_dict(torch.load(out_dir/"best_convnext_model.pth")["model_state_dict"])
model.eval(); all_probs=[]; all_labels=[]
with torch.no_grad():
    for imgs, labels in test_loader:
        imgs = imgs.to(DEVICE)
        probs = torch.softmax(model(imgs), 1)[:, 1].cpu().numpy()
        all_probs.extend(probs); all_labels.extend(labels.numpy())

test_auc = roc_auc_score(all_labels, all_probs)
test_acc = accuracy_score(all_labels, [p>0.5 for p in all_probs])
test_f1  = f1_score(all_labels, [p>0.5 for p in all_probs])

print(f"\n{'='*60}")
print(f"CONVNEXT-BASE FINAL TEST RESULTS (Celeb-DF v2 test)")
print(f"{'='*60}")
print(f"  AUC-ROC  : {test_auc:.4f}")
print(f"  Accuracy : {test_acc:.4f}  ({test_acc*100:.2f}%)")
print(f"  F1 Score : {test_f1:.4f}")
print(f"  Best Val AUC: {best_auc:.4f}")
print(f"  Training time: {total_time/60:.1f} min")
print(f"{'='*60}")

RESNET50_TEST_AUC = 0.9176
delta = test_auc - RESNET50_TEST_AUC
print(f"\nvs. ResNet50 baseline (full 518-video): {RESNET50_TEST_AUC:.4f}")
print(f"  Delta AUC: {'+' if delta>=0 else ''}{delta:.4f}")
if delta > 0.02:
    print(f"  Result: STRONG WIN — SOTA-class backbone is paying off")
elif delta > 0:
    print(f"  Result: Modest gain")
else:
    print(f"  Result: No gain — unexpected, investigate")

results = {
    "test_auc_roc": test_auc, "test_accuracy": test_acc, "test_f1": test_f1,
    "best_val_auc": best_auc, "epochs_trained": EPOCHS,
    "training_time_minutes": total_time/60,
    "training_date": datetime.now().isoformat(),
    "backbone": "ConvNeXt-Base (ImageNet1K_V1)",
    "parameters_millions": total/1e6,
    "baseline_resnet50_auc": RESNET50_TEST_AUC,
    "delta_vs_resnet50": delta,
    "history": history,
}
with open(out_dir/"convnext_test_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults -> /kaggle/working/convnext_test_results.json")
print(f"Model   -> /kaggle/working/best_convnext_model.pth")
```

============================= END OF COWORK PROMPT =============================
```

---

## Usage

1. Open cowork in your browser.
2. Copy everything between the `START` and `END` markers.
3. Paste into cowork and let it run.
4. Stay nearby for the first ~5 minutes (confirm GPU attached, data loaded).
5. Training runs ~90-150 min. Cowork can minimize and check back.
6. When cowork reports "CONVNEXT-BASE TRAINING COMPLETE", you're done.

## What we expect

Based on published deepfake detection papers using ConvNeXt:
- ResNet50 baseline: 0.92 AUC
- ConvNeXt-Base: 0.95-0.97 AUC (expected)
- Plus the ensemble with learned weights should push another ~0.005-0.01

Target landing spot: **AUC 0.95+ on Celeb-DF v2, competitive with published SOTA.**

If ConvNeXt comes back at 0.95+, the next productive move is cross-dataset
evaluation (FF++, DFDC) to prove generalization. If it comes back at 0.92 or
below, something is likely off in the training setup and we should debug before
investing more Kaggle hours.
