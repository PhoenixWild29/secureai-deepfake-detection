# Cowork Prompt — ConvNeXt-Base Training on Google Colab Pro

Sam has upgraded to Colab Pro. This is a CLEAN run — we're discarding the earlier
`MAX_BATCHES=300` partial-epoch hack and running proper full training.

Copy everything between the `===` markers into cowork.

---

```
============================ START OF COWORK PROMPT ============================

You are driving a browser to train a ConvNeXt-Base deepfake detection model on
Google Colab Pro. Sam purchased Colab Pro today specifically so this run can
complete without disconnects — DO NOT re-introduce any batch-limiting or short-
epoch hacks. We want a full, proper 30-epoch training run.

When you hit anything only Sam can do (Drive auth popup, captcha, network error,
unexpected dialog), STOP and give him clear instructions, then wait for him to
say 'done'.

## Context

- Project: SecureAI DeepFake Detection
- Prior training runs:
  - Run 1 (ResNet50, Kaggle): test AUC **0.9176** on full 518-video Celeb-DF-v2 benchmark (completed)
  - Run 2 (ResNet50 + SBI): test AUC 0.6078 — FAILED, abandoned
  - Run 3 (ConvNeXt, Colab free): 1 partial epoch only (MAX_BATCHES=300), not comparable — discard
- This run: ConvNeXt-Base full training, same data, same architecture as Run 3
  but WITHOUT the batch limit. Full 30 epochs.
- Target: test AUC 0.95+ (SOTA-class)
- Sam has Colab Pro now so longer runtime + better GPU access are available
- Dataset zip is already in Sam's Google Drive (somewhere under My Drive — use
  recursive glob to find it, don't assume a specific folder)
- Final deliverable: best_convnext_model.pth (~350 MB) at:
  C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\ai_model\trained_models\convnext_celeb_df_v2.pth

## Step 1 — Verify Colab Pro is active

1. Go to https://colab.research.google.com
2. Click the account icon (top-right). You should see "Colab Pro" listed under
   the account. If not, STOP and tell Sam:
     STOP: I don't see Colab Pro activated on the current account.
     ACTION: Check that you're signed into the same Google account you used to
             subscribe to Pro. If you used a different account, switch to that one.
     SAY: 'done' when you've confirmed Pro is active on the signed-in account.
3. Open a new notebook: File → New notebook (or + New notebook button)

## Step 2 — Configure Pro runtime

1. Menu: Runtime → Change runtime type
2. Hardware accelerator: select **L4 GPU** if available (Pro perk, ~2x faster
   than T4). If L4 isn't in the dropdown, pick **T4 GPU**.
3. Runtime shape: leave at default (Standard)
4. Save.
5. Top-right should show "Connected" with a GPU icon. If it says "Allocating...",
   wait 30s. If it fails, try the other GPU option.

## Step 3 — Mount Google Drive

Paste into the first code cell and run:

```python
# Cell 1 — Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')
```

If Drive asks for auth, STOP:
  STOP: Colab is asking permission to access your Google Drive.
  ACTION: Click the URL/Allow button that appears, sign in with the SAME Google
          account you just subscribed to Pro with, and grant access.
  SAY: 'done' when Drive shows as mounted (you'll see "Mounted at /content/drive").

## Step 4 — Find zip in Drive, copy to local, extract

Paste into a NEW cell and run:

```python
# Cell 2 — Find zip anywhere in MyDrive, copy to local /content, extract
import os, shutil, zipfile, time, glob

matches = glob.glob('/content/drive/MyDrive/**/celeb_df_v2_frames.zip', recursive=True)
if not matches:
    print("ERROR: celeb_df_v2_frames.zip not found under /content/drive/MyDrive/")
    print("Listing top-level MyDrive:")
    for f in sorted(os.listdir('/content/drive/MyDrive'))[:30]:
        print(f"  {f}")
    raise FileNotFoundError("celeb_df_v2_frames.zip not in Drive")

DRIVE_ZIP = matches[0]
print(f"Found zip at: {DRIVE_ZIP}")
print(f"Size: {os.path.getsize(DRIVE_ZIP) / 1e6:.0f} MB")

LOCAL_ZIP   = '/content/celeb_df_v2_frames.zip'
EXTRACT_DIR = '/content/dataset'
os.makedirs(EXTRACT_DIR, exist_ok=True)

if not os.path.exists(LOCAL_ZIP):
    print("\nCopying zip from Drive to local SSD ...")
    t0 = time.time()
    shutil.copy(DRIVE_ZIP, LOCAL_ZIP)
    print(f"  Copied {os.path.getsize(LOCAL_ZIP)/1e6:.0f} MB in {time.time()-t0:.0f}s")

if not os.path.exists(f"{EXTRACT_DIR}/celeb_df_v2_frames/train/real"):
    print("Extracting ...")
    t0 = time.time()
    with zipfile.ZipFile(LOCAL_ZIP) as z:
        z.extractall(EXTRACT_DIR)
    print(f"  Extracted in {time.time()-t0:.0f}s")

n_tr_real = len(glob.glob(f"{EXTRACT_DIR}/celeb_df_v2_frames/train/real/*.jpg"))
n_tr_fake = len(glob.glob(f"{EXTRACT_DIR}/celeb_df_v2_frames/train/fake/*.jpg"))
n_va_real = len(glob.glob(f"{EXTRACT_DIR}/celeb_df_v2_frames/val/real/*.jpg"))
n_va_fake = len(glob.glob(f"{EXTRACT_DIR}/celeb_df_v2_frames/val/fake/*.jpg"))
n_te_real = len(glob.glob(f"{EXTRACT_DIR}/celeb_df_v2_frames/test/real/*.jpg"))
n_te_fake = len(glob.glob(f"{EXTRACT_DIR}/celeb_df_v2_frames/test/fake/*.jpg"))
print(f"\n  train/real: {n_tr_real:>6}   fake: {n_tr_fake:>6}   (expected ~18,121 / ~18,016)")
print(f"  val/real:   {n_va_real:>6}   fake: {n_va_fake:>6}   (expected ~3,210  / ~3,180)")
print(f"  test/real:  {n_te_real:>6}   fake: {n_te_fake:>6}   (expected ~1,780  / ~3,400)")
```

If any count is wildly off, STOP and tell Sam.

## Step 5 — Paste FULL training code (no batch limiting)

IMPORTANT: The code block at the bottom of this prompt is the REAL training loop
that runs all ~1,129 batches per epoch for 30 epochs. DO NOT add a MAX_BATCHES
variable. DO NOT add `if batch_idx > X: break`. DO NOT reduce the epoch count.
Sam paid for Pro specifically to run the full thing.

Paste the entire CONVNEXT TRAINING CODE block (at the bottom) into a new cell.

## Step 6 — Verify startup (first ~90 seconds of the run)

After clicking run, watch for:
  - "Device: cuda"
  - "GPU: Tesla T4" or "NVIDIA L4"
  - "CUDA memory: ~15 GB" (T4) or "~22 GB" (L4)
  - "Loaded 36,137 frames from [...]/train"
  - "Loaded 6,390 frames from [...]/val"
  - "Loaded 5,180 frames from [...]/test"
  - "Total params: 88.1M"
  - "Trainable params: 85.9M (97.5%)"
  - ImageNet pretrained weights download progress (one-time ~340 MB, takes 1-2 min)

If any of these are wildly off, STOP and tell Sam.

## Step 7 — Watch epoch 1, 2, 3 for health signs

Each epoch prints:
  Epoch  N/30  TrainLoss: ...  ValLoss: ...  ValAUC: 0.9XXX  ValAcc: XX.XX%  LR: ...  Time: XXXs

Expected:
  - Epoch 1 should take ~3-5 min on T4, ~2-3 min on L4 (full ~1,129 batches, NOT 300)
  - ValAUC epoch 1: ~0.90-0.93 (pretrained transfer warm start)
  - ValAUC should generally climb through first ~10 epochs
  - By epoch 15-20 expect ValAUC 0.94-0.97

Red flags — STOP and tell Sam if:
  - Epoch 1 completes in under 60 seconds (means batch limiting snuck in)
  - ValAUC goes DOWN for 5+ consecutive epochs early on
  - Loss goes to NaN or Inf
  - GPU out-of-memory error

## Step 8 — Let it finish (~60-120 min total)

With Colab Pro you can:
  - Minimize the browser
  - Close the laptop lid (if in Pro's background execution mode)
  - Walk away

The notebook automatically saves best_convnext_model.pth to /content/ on every
improvement. Check back every 20-30 minutes.

## Step 9 — CRITICAL: back up to Drive before doing anything else

The moment "CONVNEXT-BASE FINAL TEST RESULTS" prints, add a NEW cell and run:

```python
# Back up outputs to Drive so they survive if Colab session dies
import shutil
shutil.copy('/content/best_convnext_model.pth', '/content/drive/MyDrive/best_convnext_model.pth')
shutil.copy('/content/convnext_test_results.json', '/content/drive/MyDrive/convnext_test_results.json')
print("Both files backed up to /content/drive/MyDrive/")
```

## Step 10 — Download the two files

Left sidebar → file browser → /content/ → right-click each, Download:
  - best_convnext_model.pth (~350 MB)
  - convnext_test_results.json (~2 KB)

Files land in C:\Users\ssham\Downloads\.

If download from /content/ fails (slow, stalls), grab them from Drive instead.

## Step 11 — Move files into the repo

1. Move Downloads\best_convnext_model.pth
   TO: C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\ai_model\trained_models\convnext_celeb_df_v2.pth
2. Move Downloads\convnext_test_results.json
   TO: C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\ai_model\trained_models\convnext_test_results.json

If you can't do the file move, tell Sam:
  STOP: I need you to move two files manually.
  ACTION: Open C:\Users\ssham\Downloads\, move best_convnext_model.pth (rename to
          convnext_celeb_df_v2.pth) and convnext_test_results.json into
          ai_model\trained_models\ in the repo.
  SAY: 'done' when moved.

## Step 12 — Report final results

Reply with:

```
CONVNEXT-BASE TRAINING COMPLETE (Colab Pro, full 30 epochs)

Test AUC-ROC:   0.xxxx
Test Accuracy:  xx.xx%
Test F1:        0.xxxx
Best Val AUC:   0.xxxx
Training time:  xx min (GPU: T4 or L4)

vs. ResNet50 baseline (AUC 0.9176):
  Delta AUC: +x.xxxx
  Result: [strong win / modest gain / no gain]

Files saved:
  ai_model/trained_models/convnext_celeb_df_v2.pth
  ai_model/trained_models/convnext_test_results.json
  (also backed up to Google Drive MyDrive/)
Colab notebook URL: https://colab.research.google.com/drive/<id>
```

## Escalation Rules

STOP and ask Sam whenever you hit:
- Any Drive auth / Google sign-in prompt
- Runtime disconnected warning (rare on Pro but possible)
- "No backend available" when selecting GPU (Pro usually has priority; if it
  persists, try the other GPU option)
- Training crash (capture full traceback)
- File not found in Drive
- Any error dialog you don't recognize

Format:
  STOP: <one-line problem>
  ACTION: <specific thing Sam should do, include URL/button name>
  SAY: 'done' when finished

## IMPORTANT GUARDRAILS — things you MUST NOT do

- Do NOT set `MAX_BATCHES` or add `if batch_idx > N: break` in the training loop
- Do NOT reduce EPOCHS below 30
- Do NOT skip the test evaluation cell
- Do NOT skip the Drive backup cell in Step 9
- Do NOT reduce `batch_size` below 32 unless you get an out-of-memory error
  (then drop to 24 and report it to Sam)
- Do NOT use a smaller architecture (convnext_tiny, convnext_small) — we
  specifically want convnext_base

## CONVNEXT TRAINING CODE

```python
# ==========================================================================
# ConvNeXt-Base FULL Training — SecureAI DeepFake Detection (Phase 4 SOTA)
# Colab Pro, runs on dataset at /content/dataset/celeb_df_v2_frames/
# NO BATCH LIMITING. FULL 30 EPOCHS. REAL COMPARISON RUN.
# ==========================================================================

import subprocess
subprocess.run(["pip", "install", "-q", "scikit-learn"], check=True)

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

# --- Data ---
class FrameDataset(Dataset):
    def __init__(self, root_dirs, transform=None):
        self.samples = []; self.transform = transform
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

DATA_ROOT = "/content/dataset/celeb_df_v2_frames"
train_ds = FrameDataset([f"{DATA_ROOT}/train"], train_transform)
val_ds   = FrameDataset([f"{DATA_ROOT}/val"],   val_transform)
test_ds  = FrameDataset([f"{DATA_ROOT}/test"],  val_transform)

labels = [s[1] for s in train_ds.samples]
class_counts = [labels.count(0), labels.count(1)]
weights = [1.0 / class_counts[l] for l in labels]
sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)

train_loader = DataLoader(train_ds, batch_size=32, sampler=sampler,
                          num_workers=2, pin_memory=True)
val_loader   = DataLoader(val_ds, batch_size=32, shuffle=False,
                          num_workers=2, pin_memory=True)
test_loader  = DataLoader(test_ds, batch_size=32, shuffle=False,
                          num_workers=2, pin_memory=True)

print(f"Train: {len(train_ds):,}  Val: {len(val_ds):,}  Test: {len(test_ds):,}")
print(f"Real: {class_counts[0]:,}  Fake: {class_counts[1]:,}  Ratio: {class_counts[1]/class_counts[0]:.2f}")
print(f"Train batches per epoch: {len(train_loader)}  (full epoch — no batch limit)")

# --- Model ---
model = convnext_base(weights=ConvNeXt_Base_Weights.IMAGENET1K_V1)
model.classifier[2] = nn.Sequential(
    nn.Dropout(0.5),
    nn.Linear(1024, 512), nn.GELU(),
    nn.Dropout(0.3),
    nn.Linear(512, 2),
)
model = model.to(DEVICE)

for name, param in model.named_parameters():
    if name.startswith("features.0") or name.startswith("features.1") or \
       name.startswith("features.2") or name.startswith("features.3"):
        param.requires_grad = False

trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total     = sum(p.numel() for p in model.parameters())
print(f"Total params:     {total/1e6:.1f}M")
print(f"Trainable params: {trainable/1e6:.1f}M ({100*trainable/total:.1f}%)")

# --- Train ---
EPOCHS       = 30
LR           = 1e-4
WEIGHT_DECAY = 5e-5

optimizer = optim.AdamW([p for p in model.parameters() if p.requires_grad],
                        lr=LR, weight_decay=WEIGHT_DECAY)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)
criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
scaler    = torch.amp.GradScaler("cuda") if DEVICE.type == "cuda" else None

best_auc=0.0; out_dir=Path("/content")
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

# --- Test ---
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
if delta > 0.02: print(f"  Result: STRONG WIN — SOTA-class backbone paying off")
elif delta > 0:  print(f"  Result: Modest gain")
else:            print(f"  Result: No gain — unexpected, investigate")

results = {
    "test_auc_roc": test_auc, "test_accuracy": test_acc, "test_f1": test_f1,
    "best_val_auc": best_auc, "epochs_trained": EPOCHS,
    "training_time_minutes": total_time/60,
    "training_date": datetime.now().isoformat(),
    "backbone": "ConvNeXt-Base (ImageNet1K_V1)",
    "parameters_millions": total/1e6,
    "baseline_resnet50_auc": RESNET50_TEST_AUC,
    "delta_vs_resnet50": delta,
    "platform": "Google Colab Pro",
    "batches_per_epoch": len(train_loader),
    "max_batches_used": "ALL — no batch limiting",
    "history": history,
}
with open(out_dir/"convnext_test_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults -> /content/convnext_test_results.json")
print(f"Model   -> /content/best_convnext_model.pth")
print(f"\n*** Now run the backup-to-Drive cell (Step 9 in your instructions) ***")
```

============================= END OF COWORK PROMPT =============================
```

---

## Usage

1. Open cowork.
2. Copy everything between the `START` and `END` markers above.
3. Paste into cowork.
4. Stay nearby for the first ~10 min (Pro status check, Drive auth, data load, epoch 1 verification).
5. Walk away for ~60-120 min while training runs.
6. When cowork reports "CONVNEXT-BASE TRAINING COMPLETE", you're done.

## What I'll do when it comes back

Once the `.pth` + `.json` are in `ai_model/trained_models/`:
1. Wire ConvNeXt into `enhanced_detector.py` as a 4th ensemble detector
2. Re-fit the learned ensemble weights (logistic regression) with the 4 inputs on val set
3. Re-run the 518-video benchmark
4. Report the final ensemble AUC vs the current 0.918 baseline

If ConvNeXt alone hits 0.94+, the ensemble should land at 0.95+. That's SOTA-class territory.
