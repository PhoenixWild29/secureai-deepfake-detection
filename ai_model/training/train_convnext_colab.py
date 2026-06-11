# ==========================================================================
# ConvNeXt-Base Training — SecureAI DeepFake Detection (Phase 4, SOTA push)
# Runs on Google Colab with GPU runtime (L4 preferred, T4 fallback)
# Dataset: Celeb-DF v2 frames at /content/dataset/celeb_df_v2_frames/
#
# Full 30-epoch training — NO batch limiting
# Target: test AUC 0.95+ (SOTA-class)
# ==========================================================================

# ── Step 0: Mount Google Drive ──
from google.colab import drive
drive.mount('/content/drive')

# ── Step 1: Find zip, copy to local, extract ──
import os, shutil, zipfile, time, glob

matches = glob.glob('/content/drive/MyDrive/**/celeb_df_v2_frames.zip', recursive=True)
if not matches:
    print("ERROR: celeb_df_v2_frames.zip not found anywhere under /content/drive/MyDrive/")
    print("Listing top-level MyDrive contents for debugging:")
    for f in sorted(os.listdir('/content/drive/MyDrive'))[:30]:
        print(f"  {f}")
    raise FileNotFoundError("celeb_df_v2_frames.zip not in Drive")

DRIVE_ZIP = matches[0]
print(f"Found zip at: {DRIVE_ZIP}")
print(f"Size: {os.path.getsize(DRIVE_ZIP) / 1e6:.0f} MB")

LOCAL_ZIP = '/content/celeb_df_v2_frames.zip'
EXTRACT_DIR = '/content/dataset'
os.makedirs(EXTRACT_DIR, exist_ok=True)

if not os.path.exists(LOCAL_ZIP):
    print("\nCopying zip from Drive to local SSD (faster I/O during training) ...")
    t0 = time.time()
    shutil.copy(DRIVE_ZIP, LOCAL_ZIP)
    print(f"  Copied {os.path.getsize(LOCAL_ZIP)/1e6:.0f} MB in {time.time()-t0:.0f}s")

if not os.path.exists(f"{EXTRACT_DIR}/celeb_df_v2_frames/train/real"):
    print("Extracting ...")
    t0 = time.time()
    with zipfile.ZipFile(LOCAL_ZIP) as z:
        z.extractall(EXTRACT_DIR)
    print(f"  Extracted in {time.time()-t0:.0f}s")

# Verify counts
n_tr_real = len(glob.glob(f"{EXTRACT_DIR}/celeb_df_v2_frames/train/real/*.jpg"))
n_tr_fake = len(glob.glob(f"{EXTRACT_DIR}/celeb_df_v2_frames/train/fake/*.jpg"))
n_va_real = len(glob.glob(f"{EXTRACT_DIR}/celeb_df_v2_frames/val/real/*.jpg"))
n_va_fake = len(glob.glob(f"{EXTRACT_DIR}/celeb_df_v2_frames/val/fake/*.jpg"))
n_te_real = len(glob.glob(f"{EXTRACT_DIR}/celeb_df_v2_frames/test/real/*.jpg"))
n_te_fake = len(glob.glob(f"{EXTRACT_DIR}/celeb_df_v2_frames/test/fake/*.jpg"))
print(f"\n  train/real: {n_tr_real:>6}   fake: {n_tr_fake:>6}   (expected ~18,121 / ~18,016)")
print(f"  val/real:   {n_va_real:>6}   fake: {n_va_fake:>6}   (expected ~3,210  / ~3,180)")
print(f"  test/real:  {n_te_real:>6}   fake: {n_te_fake:>6}   (expected ~1,780  / ~3,400)")

# ── Step 2: Install & Imports ──
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

# ── Step 3: Dataset ──
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

DATA_ROOT = "/content/dataset/celeb_df_v2_frames"

train_ds = FrameDataset([f"{DATA_ROOT}/train"], train_transform)
val_ds   = FrameDataset([f"{DATA_ROOT}/val"],   val_transform)
test_ds  = FrameDataset([f"{DATA_ROOT}/test"],  val_transform)

labels = [s[1] for s in train_ds.samples]
class_counts = [labels.count(0), labels.count(1)]
weights = [1.0 / class_counts[l] for l in labels]
sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)

train_loader = DataLoader(train_ds, batch_size=32, sampler=sampler, num_workers=2, pin_memory=True)
val_loader   = DataLoader(val_ds,   batch_size=32, shuffle=False, num_workers=2, pin_memory=True)
test_loader  = DataLoader(test_ds,  batch_size=32, shuffle=False, num_workers=2, pin_memory=True)
print(f"Train: {len(train_ds):,}  Val: {len(val_ds):,}  Test: {len(test_ds):,}")
print(f"Real: {class_counts[0]:,}  Fake: {class_counts[1]:,}  Ratio: {class_counts[1]/class_counts[0]:.2f}")

# ── Step 4: Model ──
model = convnext_base(weights=ConvNeXt_Base_Weights.IMAGENET1K_V1)
model.classifier[2] = nn.Sequential(
    nn.Dropout(0.5),
    nn.Linear(1024, 512),
    nn.GELU(),
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
print(f"Total params:      {total/1e6:.1f}M")
print(f"Trainable params:  {trainable/1e6:.1f}M ({100*trainable/total:.1f}%)")

# ── Step 5: Training (30 epochs, NO batch limiting) ──
EPOCHS = 30
LR = 1e-4
WEIGHT_DECAY = 5e-5

optimizer = optim.AdamW([p for p in model.parameters() if p.requires_grad],
                        lr=LR, weight_decay=WEIGHT_DECAY)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)
criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
scaler    = torch.amp.GradScaler("cuda") if DEVICE.type == "cuda" else None

best_auc = 0.0
out_dir = Path("/content")
history = {"train_loss": [], "val_loss": [], "val_auc": [], "val_acc": []}
t_start = time.time()

for epoch in range(1, EPOCHS + 1):
    t0 = time.time()
    model.train()
    tr_loss = 0
    for imgs, labels in train_loader:
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        if scaler:
            with torch.amp.autocast("cuda"):
                out = model(imgs)
                loss = criterion(out, labels)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            out = model(imgs)
            loss = criterion(out, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
        tr_loss += loss.item()
    scheduler.step()

    # Validation
    model.eval()
    vl_loss = 0
    all_probs = []
    all_labels = []
    with torch.no_grad():
        for imgs, labels in val_loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            out = model(imgs)
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

    print(f"Epoch {epoch:3d}/{EPOCHS}  TrainLoss: {tr_loss/len(train_loader):.4f}  "
          f"ValLoss: {vl_loss/len(val_loader):.4f}  ValAUC: {val_auc:.4f}  "
          f"ValAcc: {val_acc*100:.2f}%  LR: {scheduler.get_last_lr()[0]:.2e}  Time: {elapsed:.0f}s")

    if val_auc > best_auc:
        best_auc = val_auc
        torch.save({
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "val_auc": val_auc,
            "val_acc": val_acc,
        }, out_dir / "best_convnext_model.pth")
        print(f"  --> New best AUC: {best_auc:.4f}  (saved best_convnext_model.pth)")

total_time = time.time() - t_start
print(f"\nTotal training time: {total_time/60:.1f} min")

# ── Step 6: Test Evaluation ──
model.load_state_dict(torch.load(out_dir / "best_convnext_model.pth", weights_only=False)["model_state_dict"])
model.eval()
all_probs = []
all_labels = []
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
print(f"  AUC-ROC :  {test_auc:.4f}")
print(f"  Accuracy:  {test_acc:.4f} ({test_acc*100:.2f}%)")
print(f"  F1 Score:  {test_f1:.4f}")
print(f"  Best Val AUC: {best_auc:.4f}")
print(f"  Training time: {total_time/60:.1f} min")
print(f"{'='*60}")

RESNET50_TEST_AUC = 0.9176
delta = test_auc - RESNET50_TEST_AUC
print(f"\nvs. ResNet50 baseline (full 518-video): {RESNET50_TEST_AUC:.4f}")
print(f"  Delta AUC: {'+' if delta >= 0 else ''}{delta:.4f}")
if delta > 0.02:
    print(f"  Result: STRONG WIN -- SOTA-class backbone paying off")
elif delta > 0:
    print(f"  Result: Modest gain")
else:
    print(f"  Result: No gain -- unexpected, investigate")

# ── Step 7: Save Results JSON ──
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
    "platform": "Google Colab (L4 GPU)",
    "history": history,
}
with open(out_dir / "convnext_test_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\nResults -> /content/convnext_test_results.json")
print(f"Model  -> /content/best_convnext_model.pth")
print(f"\n*** IMPORTANT: Run the next cell to back up these files to Google Drive ***")

# ── Step 8: Backup to Google Drive (run as separate cell in Colab) ──
# import shutil
# shutil.copy('/content/best_convnext_model.pth', '/content/drive/MyDrive/best_convnext_model.pth')
# shutil.copy('/content/convnext_test_results.json', '/content/drive/MyDrive/convnext_test_results.json')
# print("Saved both files to Google Drive (MyDrive root).")
