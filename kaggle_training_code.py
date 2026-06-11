# Cell 1: Install
import subprocess
subprocess.run(['pip', 'install', '-q', 'scikit-learn', 'timm'], check=True)

# Cell 2: Imports
import os
import json
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import transforms, models
from PIL import Image
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score, precision_score, recall_score, confusion_matrix

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Device: {device}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"GPU Count: {torch.cuda.device_count()}")

# Cell 3: Dataset
DATA_ROOT = "/kaggle/input/secureai-celeb-df-v2-frames/celeb_df_v2_frames"

class FrameDataset(Dataset):
    def __init__(self, root, split, transform=None):
        self.transform = transform
        self.samples = []
        split_dir = os.path.join(root, split)
        for label_name, label in [('real', 0), ('fake', 1)]:
            d = os.path.join(split_dir, label_name)
            if os.path.isdir(d):
                for fn in os.listdir(d):
                    if fn.lower().endswith(('.jpg', '.jpeg', '.png')):
                        self.samples.append((os.path.join(d, fn), label))
    def __len__(self):
        return len(self.samples)
    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert('RGB')
        if self.transform:
            img = self.transform(img)
        return img, label

train_tf = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])
eval_tf = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

train_ds = FrameDataset(DATA_ROOT, 'train', train_tf)
val_ds = FrameDataset(DATA_ROOT, 'val', eval_tf)
test_ds = FrameDataset(DATA_ROOT, 'test', eval_tf)
print(f"Train: {len(train_ds)}, Val: {len(val_ds)}, Test: {len(test_ds)}")

labels = [l for _, l in train_ds.samples]
class_counts = np.bincount(labels)
weights = 1.0 / class_counts
sample_weights = [weights[l] for l in labels]
sampler = WeightedRandomSampler(sample_weights, len(sample_weights))

BATCH = 64
train_loader = DataLoader(train_ds, batch_size=BATCH, sampler=sampler, num_workers=4, pin_memory=True)
val_loader = DataLoader(val_ds, batch_size=BATCH, shuffle=False, num_workers=4, pin_memory=True)
test_loader = DataLoader(test_ds, batch_size=BATCH, shuffle=False, num_workers=4, pin_memory=True)

# Cell 4: Model
model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
for name, param in model.named_parameters():
    if name.startswith('conv1') or name.startswith('bn1') or name.startswith('layer1') or name.startswith('layer2'):
        param.requires_grad = False
model.fc = nn.Sequential(
    nn.Dropout(0.5),
    nn.Linear(2048, 512),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(512, 2),
)
model = model.to(device)

# Cell 5: Train
EPOCHS = 50
LR = 3e-4
WEIGHT_DECAY = 1e-4

criterion = nn.CrossEntropyLoss()
optimizer = optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=WEIGHT_DECAY)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
scaler = torch.amp.GradScaler('cuda')

best_auc = 0.0
best_state = None

for epoch in range(EPOCHS):
    t0 = time.time()
    model.train()
    tl = 0.0
    for imgs, lbls in train_loader:
        imgs = imgs.to(device, non_blocking=True)
        lbls = lbls.to(device, non_blocking=True)
        optimizer.zero_grad()
        with torch.amp.autocast('cuda'):
            out = model(imgs)
            loss = criterion(out, lbls)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        tl += loss.item()
    scheduler.step()

    model.eval()
    probs, gts = [], []
    with torch.no_grad():
        for imgs, lbls in val_loader:
            imgs = imgs.to(device, non_blocking=True)
            with torch.amp.autocast('cuda'):
                out = model(imgs)
            probs.extend(torch.softmax(out, dim=1)[:, 1].cpu().numpy())
            gts.extend(lbls.numpy())
    auc = roc_auc_score(gts, probs)
    preds = [1 if p >= 0.5 else 0 for p in probs]
    acc = accuracy_score(gts, preds)
    print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {tl/len(train_loader):.4f} | Val AUC: {auc:.4f} | Val Acc: {acc:.4f} | Time: {time.time()-t0:.1f}s")

    if auc > best_auc:
        best_auc = auc
        best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        torch.save(best_state, '/kaggle/working/best_model.pth')
        print(f"  -> saved best (AUC {auc:.4f})")

# Cell 6: Test
model.load_state_dict(torch.load('/kaggle/working/best_model.pth'))
model.eval()
probs, gts = [], []
with torch.no_grad():
    for imgs, lbls in test_loader:
        imgs = imgs.to(device, non_blocking=True)
        with torch.amp.autocast('cuda'):
            out = model(imgs)
        probs.extend(torch.softmax(out, dim=1)[:, 1].cpu().numpy())
        gts.extend(lbls.numpy())
preds = [1 if p >= 0.5 else 0 for p in probs]
auc = roc_auc_score(gts, probs)
acc = accuracy_score(gts, preds)
f1 = f1_score(gts, preds)
prec = precision_score(gts, preds)
rec = recall_score(gts, preds)
cm = confusion_matrix(gts, preds).tolist()

results = {
    "test_auc_roc": auc,
    "test_accuracy": acc,
    "test_f1": f1,
    "test_precision": prec,
    "test_recall": rec,
    "confusion_matrix": cm,
    "best_val_auc": best_auc,
    "epochs": EPOCHS,
    "batch_size": BATCH,
    "lr": LR,
    "weight_decay": WEIGHT_DECAY,
    "architecture": "ResNet50",
    "dataset": "Celeb-DF v2",
}
print(json.dumps(results, indent=2))
with open('/kaggle/working/test_results.json', 'w') as f:
    json.dump(results, f, indent=2)
