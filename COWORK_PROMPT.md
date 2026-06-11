# Cowork Prompt — Kaggle GPU Training for SecureAI DeepFake Detection

Copy everything between the `===` markers into cowork. This is a single self-contained prompt.

---

```
============================ START OF COWORK PROMPT ============================

You are driving a browser to train a deepfake detection model on Kaggle's free GPU. I have the browser extension installed and can step in whenever you ask. When you cannot do something yourself (captchas, SMS verification, login credentials, email confirmations, anything that requires me personally), STOP and tell me EXACTLY what to do and WHERE in the browser to click. Then wait for me to say "done" before you continue. Do not guess or skip.

## Context

- Project: SecureAI DeepFake Detection Model
- I have already: extracted 47,707 JPG frames from Celeb-DF-v2, balanced the classes, and zipped them.
- File ready to upload: `C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\celeb_df_v2_frames.zip` (598 MB)
- Dataset contents (already inside the zip):
  - train/real: 18,121 JPGs, train/fake: 18,016 JPGs (ratio 0.99, balanced)
  - val/real: 3,210 JPGs, val/fake: 3,180 JPGs (ratio 0.99, balanced)
  - test/real: 1,780 JPGs, test/fake: 3,400 JPGs (official Celeb-DF-v2 test split)
- Goal: Train a ResNet50 deepfake classifier on Kaggle's free T4 GPU, target AUC-ROC > 0.88
- Final deliverable: download the trained `best_model.pth` (~90 MB) and save it to `C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\ai_model\trained_models\resnet50_celeb_df_v2.pth`

## Step 1 — Open Kaggle and sign in

1. Go to https://www.kaggle.com
2. Check if I'm already signed in (look for my avatar top-right). If yes, proceed to Step 2.
3. If not signed in, click "Sign In" and attempt to proceed.
   - If Kaggle asks for email/password: STOP and say "I need your Kaggle email and password to sign in — please type them into the sign-in form, then say 'done'."
   - If Google SSO: STOP and say "Please sign in with Google in the popup, then say 'done'."
   - If 2FA / captcha: STOP and say "Please complete the 2FA/captcha, then say 'done'."
4. Confirm I'm now signed in before moving on.

## Step 2 — Upload the dataset

1. Go to https://www.kaggle.com/datasets/new
2. If Kaggle prompts for phone verification (first-time GPU/dataset users often see this), STOP and say: "Kaggle needs phone verification. Please complete the SMS verification flow in the browser, then say 'done'."
3. Drag-and-drop or click-to-upload the file at:
   `C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\celeb_df_v2_frames.zip`
   (If the drop zone won't accept it via automation, tell me: "Please drag celeb_df_v2_frames.zip from the repo folder into the Kaggle upload zone, then say 'done'.")
4. The upload is 598 MB. Wait for it to complete — monitor the progress bar. If it fails or stalls >3 min without progress, tell me and ask what to do.
5. In the "Dataset title" field, enter exactly: `secureai-celeb-df-v2-frames`
6. Leave the license as "Unknown" or default.
7. Click "Create" (button label may be "Create Dataset" or similar).
8. Wait for Kaggle to finish processing the dataset — this can take 3–10 minutes for 598 MB. You will see a status that transitions from "Processing" to "Ready/Available".
9. Confirm the dataset is live by navigating to its URL: `https://www.kaggle.com/datasets/<my-username>/secureai-celeb-df-v2-frames`. If you cannot determine the username, ask me: "What is your Kaggle username?"

## Step 3 — Create a new notebook

1. Go to https://www.kaggle.com/code
2. Click "+ New Notebook" (button top-right or on the side).
3. When the notebook opens, in the right sidebar find "Settings" or the gear icon.
4. Under "Accelerator", select **"GPU T4 x2"**.
   - If Kaggle requires phone verification to enable GPU (first time only), STOP and say: "Kaggle needs phone verification for GPU access. Please complete SMS verification, then say 'done'."
5. Under "Internet", toggle ON.
6. Under "Environment" leave as default (pinned to latest).

## Step 4 — Attach the dataset

1. In the right sidebar, find "Input" or "+ Add Input" / "Add Data".
2. Click it, search for `secureai-celeb-df-v2-frames` (filter by "Your Datasets").
3. Click "+" next to it to add it. The path inside the notebook will be `/kaggle/input/secureai-celeb-df-v2-frames/`.
4. Verify by expanding the Input tree in the sidebar — you should see `celeb_df_v2_frames/` as a subfolder.

## Step 5 — Paste the training code

1. Click on the first (empty) code cell in the notebook.
2. Paste the ENTIRE training code block from the "TRAINING CODE" section at the bottom of this prompt.
3. Do not modify it — it expects the path `/kaggle/input/secureai-celeb-df-v2-frames/celeb_df_v2_frames`.

## Step 6 — Run the training

1. Click "Run All" (▶▶ button at top, or menu → Run All).
2. Watch the first output for a few seconds to confirm:
   - "Device: cuda" appears (means GPU was allocated)
   - "GPU: Tesla T4" or similar appears
   - The dataset loads successfully (prints "Loaded XXXXX frames from ...")
3. If you see "Device: cpu" instead of cuda, STOP and tell me: "GPU did not attach. Please check the notebook settings — Accelerator should be GPU T4 x2."
4. If the data-loading step prints 0 frames, STOP and tell me: "Dataset path mismatch. The Input folder structure may differ."

## Step 7 — Wait for training (~90 minutes)

Training runs 50 epochs. Each epoch prints a line like:
`Epoch  23/50  TrainLoss: 0.1234  ValLoss: 0.1456  ValAUC: 0.9123  ValAcc: 87.45%  LR: 1.23e-04  Time: 102s`

1. You don't need to sit watching it. Do any of these:
   - Minimize the browser but do NOT close the Kaggle tab (the notebook keeps running even if you close the tab, but if you close it you lose live output).
   - Periodically refresh and check progress every ~15–20 minutes.
2. If any epoch's ValAUC is > 0.95, that's great — training is going well.
3. If training fails with an error, capture the traceback and tell me: "Training failed — here is the error: [paste traceback]. What should I do?"
4. If training completes successfully, you will see a final block starting with:
   `FINAL TEST RESULTS (Celeb-DF v2 official test split)`
   followed by AUC-ROC, Accuracy, F1 scores.

## Step 8 — Download the trained model

1. In the right sidebar, find "Output" or the file tree for `/kaggle/working/`.
2. You should see two files:
   - `best_model.pth` (~90 MB) — the trained weights
   - `test_results.json` (~2 KB) — metrics summary
3. Right-click `best_model.pth` → Download (or click the file, then the Download icon).
   - If download doesn't auto-trigger, tell me: "Please click Download on best_model.pth, then say 'done'."
4. Also download `test_results.json`.
5. The downloads go to the default Downloads folder (`C:\Users\ssham\Downloads`).

## Step 9 — Move the model to the repo

1. Move `C:\Users\ssham\Downloads\best_model.pth` to:
   `C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\ai_model\trained_models\resnet50_celeb_df_v2.pth`
   (Create the `trained_models` folder if it doesn't exist.)
2. Move `C:\Users\ssham\Downloads\test_results.json` to:
   `C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\ai_model\trained_models\celeb_df_v2_results.json`
3. If you cannot perform file system operations, tell me: "Please move best_model.pth and test_results.json to ai_model/trained_models/ in the repo, then say 'done'."

## Step 10 — Report final results

Reply to me with a summary in this exact format:

```
TRAINING COMPLETE ✓

Test AUC-ROC:   0.xxxx
Test Accuracy:  xx.xx%
Test F1:        0.xxxx
Best Val AUC:   0.xxxx
Epochs trained: 50
Training time:  xx min

Model saved to: ai_model/trained_models/resnet50_celeb_df_v2.pth
Metrics saved to: ai_model/trained_models/celeb_df_v2_results.json
Kaggle notebook URL: https://www.kaggle.com/code/<url>
```

Fill in actual numbers from the test_results.json file.

## Escalation Rules — IMPORTANT

Any time you hit any of these, STOP immediately and tell me what to do:
- Login/password prompt
- 2FA code prompt
- SMS / phone verification
- Captcha of any kind
- Email verification link
- Payment / billing prompt (Kaggle should never ask for this — if it does, something is wrong)
- File upload UI that won't accept automation
- Download that won't trigger via click
- Any error dialog you don't know how to dismiss
- Any warning about quotas, rate limits, or bans
- Any step where you're uncertain

For each escalation, give me:
1. A one-line description of what's blocking you
2. The exact action I need to take (click where, type what)
3. What to say when I'm done (usually "say 'done'")

Example escalation:
"STOP: Kaggle is asking for phone verification.
ACTION: Click 'Send SMS code' in the dialog. Enter the code you receive on your phone.
SAY: 'done' when the verification succeeds."

Do NOT make up credentials. Do NOT skip steps. Do NOT fabricate progress.

## TRAINING CODE (paste this into the Kaggle notebook)

```python
# Cell 1 -- Install dependencies (Kaggle usually has these, safe to run)
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

labels = [s[1] for s in train_ds.samples]
class_counts = [labels.count(0), labels.count(1)]
weights = [1.0 / class_counts[l] for l in labels]
sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)

train_loader = DataLoader(train_ds, batch_size=64, sampler=sampler, num_workers=4, pin_memory=True)
val_loader   = DataLoader(val_ds,   batch_size=64, shuffle=False, num_workers=4, pin_memory=True)
test_loader  = DataLoader(test_ds,  batch_size=64, shuffle=False, num_workers=4, pin_memory=True)

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

optimizer = optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=WEIGHT_DECAY)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)
criterion = nn.CrossEntropyLoss()
scaler    = torch.amp.GradScaler("cuda") if DEVICE.type == "cuda" else None

best_auc  = 0.0
out_dir   = Path("/kaggle/working")
history   = {"train_loss": [], "val_loss": [], "val_auc": [], "val_acc": []}
t_start   = time.time()

for epoch in range(1, EPOCHS + 1):
    t0 = time.time()
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
        tr_loss    += loss.item()
        tr_correct += out.argmax(1).eq(labels).sum().item()
        tr_total   += labels.size(0)
    scheduler.step()

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

    print(f"Epoch {epoch:3d}/{EPOCHS}  TrainLoss: {tr_loss/len(train_loader):.4f}  "
          f"ValLoss: {vl_loss/len(val_loader):.4f}  ValAUC: {val_auc:.4f}  "
          f"ValAcc: {val_acc*100:.2f}%  LR: {scheduler.get_last_lr()[0]:.2e}  Time: {elapsed:.0f}s")

    if val_auc > best_auc:
        best_auc = val_auc
        torch.save({"epoch": epoch, "model_state_dict": model.state_dict(),
                    "val_auc": val_auc, "val_acc": val_acc}, out_dir / "best_model.pth")
        print(f"  --> New best AUC: {best_auc:.4f}  (saved best_model.pth)")

total_time = time.time() - t_start
print(f"\nTotal training time: {total_time/60:.1f} min")

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

test_auc = roc_auc_score(all_labels, all_probs)
test_acc = accuracy_score(all_labels, [p > 0.5 for p in all_probs])
test_f1  = f1_score(all_labels, [p > 0.5 for p in all_probs])

print(f"\n{'='*50}")
print(f"FINAL TEST RESULTS (Celeb-DF v2 official test split)")
print(f"{'='*50}")
print(f"  AUC-ROC  : {test_auc:.4f}")
print(f"  Accuracy : {test_acc:.4f}  ({test_acc*100:.2f}%)")
print(f"  F1 Score : {test_f1:.4f}")
print(f"  Best Val AUC: {best_auc:.4f}")
print(f"  Total training time: {total_time/60:.1f} min")
print(f"{'='*50}")

results = {
    "test_auc_roc": test_auc,
    "test_accuracy": test_acc,
    "test_f1": test_f1,
    "best_val_auc": best_auc,
    "epochs_trained": EPOCHS,
    "training_time_minutes": total_time / 60,
    "training_date": datetime.now().isoformat(),
    "history": history,
}
with open(out_dir / "test_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"Results saved to /kaggle/working/test_results.json")
print(f"Model saved to /kaggle/working/best_model.pth")
```

============================= END OF COWORK PROMPT =============================
```

---

## Usage

1. Open cowork in your browser.
2. Copy everything between the `============================ START` and `============================ END` markers above.
3. Paste into cowork and let it run.
4. Stay nearby for the first ~10 minutes (login, phone verification, dataset upload) — cowork will ping you when it needs you.
5. After training kicks off, you can walk away. Check back in ~90 minutes.
6. Once cowork reports "TRAINING COMPLETE", verify `ai_model/trained_models/resnet50_celeb_df_v2.pth` exists in your repo.

## Fallback

If cowork gets stuck on something not covered above, ask it to:
1. Describe what it's seeing
2. Share a screenshot
3. Pause and let you take over

Then when you've fixed it, tell cowork "continue from Step N" where N is the current step number.
