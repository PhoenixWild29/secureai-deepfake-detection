import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from torchvision.models import ResNet50_Weights, ResNet101_Weights, EfficientNet_B0_Weights
from PIL import Image
import os
from pathlib import Path
import numpy as np
# from sklearn.metrics import precision_score, recall_score, f1_score  # Moved to functions
import json
from datetime import datetime
import cv2
import hashlib
from typing import Dict, Any, Optional

class DeepfakeDataset(Dataset):
    """Custom dataset for deepfake classification"""
    def __init__(self, root_dir, transform=None):
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.samples = []

        # Load real images
        real_dir = self.root_dir / "real"
        if real_dir.exists():
            for img_path in real_dir.glob("*.jpg"):
                self.samples.append((str(img_path), 0))  # 0 = real

        # Load fake images
        fake_dir = self.root_dir / "fake"
        if fake_dir.exists():
            for img_path in fake_dir.glob("*.jpg"):
                self.samples.append((str(img_path), 1))  # 1 = fake

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert('RGB')

        if self.transform:
            image = self.transform(image)

        return image, label

class DeepfakeClassifier(nn.Module):
    """CNN-based deepfake classifier"""
    def __init__(self):
        super(DeepfakeClassifier, self).__init__()

        # Feature extraction layers
        self.features = nn.Sequential(
            # Conv Block 1
            nn.Conv2d(3, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            nn.Dropout(0.25),

            # Conv Block 2
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            nn.Dropout(0.25),

            # Conv Block 3
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            nn.Dropout(0.25),

            # Conv Block 4
            nn.Conv2d(256, 512, kernel_size=3, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.Conv2d(512, 512, kernel_size=3, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            nn.Dropout(0.25),
        )

        # Classification layers
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(128, 2)  # Binary classification: real vs fake
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

class ResNetDeepfakeClassifier(nn.Module):
    """ResNet-based deepfake classifier with pre-trained backbone"""
    def __init__(self, model_name='resnet50', num_classes=2, pretrained=True):
        super(ResNetDeepfakeClassifier, self).__init__()

        self.model_name = model_name

        # Load pre-trained ResNet and modify classifier
        if model_name == 'resnet50':
            self.model = models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V2 if pretrained else None)
            # ResNet50 has 2048 features before fc layer
            self.model.fc = nn.Linear(2048, num_classes)
        elif model_name == 'resnet101':
            self.model = models.resnet101(weights=ResNet101_Weights.IMAGENET1K_V2 if pretrained else None)
            # ResNet101 has 2048 features before fc layer
            self.model.fc = nn.Linear(2048, num_classes)
        elif model_name == 'efficientnet_b0':
            self.model = models.efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None)
            # EfficientNet B0 has 1280 features before classifier
            self.model.classifier[1] = nn.Linear(1280, num_classes)

    def forward(self, x):
        return self.model(x)

    def predict_video(self, video_path: str, model_path: Optional[str] = None) -> Dict[str, Any]:
        """Predict if a video is real or fake by analyzing multiple frames"""
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # Load model - use ResNet model path
        if model_path and os.path.exists(model_path):
            self.load_state_dict(torch.load(model_path, map_location=device))
        elif os.path.exists('ai_model/resnet_resnet50_best.pth'):
            self.load_state_dict(torch.load('ai_model/resnet_resnet50_best.pth', map_location=device))
        else:
            raise FileNotFoundError("No trained ResNet model found")

        self.to(device)
        self.eval()

        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Could not open video file")

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Sample frames (up to 30 frames evenly distributed)
        sample_frames = min(30, frame_count)
        frame_indices = np.linspace(0, frame_count - 1, sample_frames, dtype=int)

        predictions = []
        probabilities = []

        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Preprocess frame
                frame_tensor = transform(frame_rgb)
                if not isinstance(frame_tensor, torch.Tensor):
                    frame_tensor = torch.from_numpy(frame_tensor).float()
                frame_tensor = frame_tensor.unsqueeze(0).to(device)

                # Get prediction
                with torch.no_grad():
                    outputs = self(frame_tensor)
                    probs = torch.softmax(outputs, dim=1)
                    pred_class = int(torch.argmax(outputs, dim=1).item())
                    confidence = probs[0][pred_class].item()

                predictions.append(pred_class)
                probabilities.append(confidence)

        cap.release()

        # Aggregate predictions
        if predictions:
            # Use majority voting for final prediction
            final_prediction = max(set(predictions), key=predictions.count)
            avg_confidence = sum(probabilities) / len(probabilities)

            # Calculate fake probability (class 1)
            fake_prob = sum(1 for p in predictions if p == 1) / len(predictions)
            real_prob = 1 - fake_prob

            result = {
                'is_fake': final_prediction == 1,
                'confidence': avg_confidence,
                'fake_probability': fake_prob,
                'real_probability': real_prob,
                'frames_analyzed': len(predictions),
                'video_hash': hashlib.md5(open(video_path, 'rb').read()).hexdigest(),
                'model_used': f'resnet_{self.model_name}'
            }
        else:
            result = {
                'error': 'No frames could be processed from video',
                'is_fake': False,
                'confidence': 0.0,
                'frames_analyzed': 0
            }

        return result

def train_classifier(train_dir, val_dir=None, epochs=50, batch_size=32, learning_rate=0.001, backbone='resnet50'):
    """
    Train the deepfake classifier
    """
    print("🚀 Starting SecureAI Deepfake Classifier Training")
    print("=" * 60)
    print(f"📊 Train Directory: {train_dir}")
    print(f"🎯 Epochs: {epochs}")
    print(f"📦 Batch Size: {batch_size}")
    print(f"🧠 Learning Rate: {learning_rate}")
    print(f"🖥️  Device: {torch.device('cuda' if torch.cuda.is_available() else 'cpu')}")
    print(f"🔧 Backbone: {backbone}")
    print()

    # Data transforms
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # Create datasets
    train_dataset = DeepfakeDataset(train_dir, transform=train_transform)
    val_dataset = DeepfakeDataset(val_dir, transform=val_transform) if val_dir else None

    print(f"📈 Training samples: {len(train_dataset)}")
    if val_dataset:
        print(f"📊 Validation samples: {len(val_dataset)}")

    # Create data loaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=2) if val_dataset else None

    # Initialize model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = ResNetDeepfakeClassifier(model_name=backbone).to(device)

    # Loss function and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=5)

    # Training loop
    best_accuracy = 0.0
    training_history = []

    for epoch in range(epochs):
        print(f"\nEpoch {epoch+1}/{epochs}")

        # Training phase
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            _, predicted = outputs.max(1)
            train_total += labels.size(0)
            train_correct += predicted.eq(labels).sum().item()

        train_accuracy = 100. * train_correct / train_total
        train_loss = train_loss / len(train_loader)

        print(".2f")

        # Validation phase
        if val_loader:
            model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            all_preds = []
            all_labels = []

            with torch.no_grad():
                for inputs, labels in val_loader:
                    inputs, labels = inputs.to(device), labels.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)

                    val_loss += loss.item()
                    _, predicted = outputs.max(1)
                    val_total += labels.size(0)
                    val_correct += predicted.eq(labels).sum().item()

                    all_preds.extend(predicted.cpu().numpy())
                    all_labels.extend(labels.cpu().numpy())

            val_accuracy = 100. * val_correct / val_total
            val_loss = val_loss / len(val_loader)

            # Calculate additional metrics
            from sklearn.metrics import precision_score, recall_score, f1_score  # Moved here to avoid import issues
            precision = precision_score(all_labels, all_preds, average='weighted', zero_division=0)
            recall = recall_score(all_labels, all_preds, average='weighted', zero_division=0)
            f1 = f1_score(all_labels, all_preds, average='weighted', zero_division=0)

            print(".2f")

            # Save best model
            if val_accuracy > best_accuracy:
                best_accuracy = val_accuracy
                torch.save(model.state_dict(), 'ai_model/deepfake_classifier_best.pth')
                print("💾 Best model saved!")

            scheduler.step(val_accuracy)

            training_history.append({
                'epoch': epoch + 1,
                'train_loss': train_loss,
                'train_accuracy': train_accuracy,
                'val_loss': val_loss,
                'val_accuracy': val_accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1
            })
        else:
            training_history.append({
                'epoch': epoch + 1,
                'train_loss': train_loss,
                'train_accuracy': train_accuracy
            })

    # Save final model
    torch.save(model.state_dict(), 'ai_model/deepfake_classifier_final.pth')

    # Save training metadata
    metadata = {
        'training_date': datetime.now().isoformat(),
        'model_type': 'CNN_Classifier',
        'epochs': epochs,
        'batch_size': batch_size,
        'learning_rate': learning_rate,
        'best_accuracy': best_accuracy,
        'final_metrics': training_history[-1] if training_history else {},
        'training_history': training_history
    }

    with open('ai_model/classifier_training_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)

    print("\n✅ Training completed!")
    print(".2f")
    return model, training_history

def predict_image(model_path, image_path):
    """Predict if an image is real or fake"""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Load model
    model = ResNetDeepfakeClassifier()
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()

    # Load and preprocess image
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    image = Image.open(image_path).convert('RGB')
    image = transform(image)
    if not isinstance(image, torch.Tensor):
        image = torch.from_numpy(np.array(image)).float()
    image = image.unsqueeze(0).to(device)

    # Predict
    with torch.no_grad():
        outputs = model(image)
        _, predicted = outputs.max(1)
        probabilities = torch.softmax(outputs, dim=1)

    return predicted.item(), probabilities[0][predicted.item()].item()

if __name__ == "__main__":
    # Train the classifier
    model, history = train_classifier(
        train_dir='datasets/train',
        val_dir='datasets/val',
        epochs=30,  # Reduced for demo
        batch_size=16,
        learning_rate=0.001
    )

    print("\n🎉 Deepfake classifier training completed!")
    print("🔄 Ready for integration with detection pipeline")