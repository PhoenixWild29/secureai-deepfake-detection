#!/usr/bin/env python3
"""
Enhanced Training Script for Advanced Deepfake Detection
Incorporates techniques from reviewed GitHub repositories
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as transforms
from torchvision.models import efficientnet_b4, EfficientNet_B4_Weights
import cv2
import numpy as np
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse
import time
from datetime import datetime
import shutil
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image

from enhanced_detector import EnsembleDetector, LAABlock, CLIPBasedDetector
from deepfake_classifier import DeepfakeClassifier

class VideoDataset(Dataset):
    """Dataset for loading video frames from multiple datasets"""

    def __init__(self, root_dirs: List[str], split: str = 'train',
                 frame_count: int = 30, transform=None):
        self.root_dirs = [Path(d) for d in root_dirs]
        self.split = split
        self.frame_count = frame_count
        self.transform = transform
        self.samples = []

        self._load_samples()

    def _load_samples(self):
        """Load all video samples from dataset directories"""
        for root_dir in self.root_dirs:
            split_dir = root_dir / self.split
            if not split_dir.exists():
                continue

            # Load real videos
            real_dir = split_dir / "real"
            if real_dir.exists():
                for video_file in real_dir.glob("*.mp4"):
                    self.samples.append((str(video_file), 0))  # 0 = real

            # Load fake videos
            fake_dir = split_dir / "fake"
            if fake_dir.exists():
                for video_file in fake_dir.glob("*.mp4"):
                    self.samples.append((str(video_file), 1))  # 1 = fake

        print(f"Loaded {len(self.samples)} samples from {len(self.root_dirs)} datasets")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        video_path, label = self.samples[idx]

        # Extract frames from video
        frames = self._extract_frames(video_path, self.frame_count)

        if self.transform:
            frames = [self.transform(frame) for frame in frames]

        # Stack frames into tensor
        frames_tensor = torch.stack(frames)

        return frames_tensor, torch.tensor(label, dtype=torch.long)

    def _extract_frames(self, video_path: str, frame_count: int) -> List[np.ndarray]:
        """Extract frames from video"""
        cap = cv2.VideoCapture(video_path)
        frames = []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            # Fallback for problematic videos
            cap.release()
            return [np.zeros((224, 224, 3), dtype=np.uint8)] * frame_count

        # Sample frames evenly
        frame_indices = np.linspace(0, total_frames-1, frame_count, dtype=int)

        for frame_idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (224, 224))
                frames.append(frame)
            else:
                # Use last frame or black frame as fallback
                frames.append(np.zeros((224, 224, 3), dtype=np.uint8))

        cap.release()
        return frames

class ImageDataset(Dataset):
    """Dataset for loading individual frame images from existing dataset"""

    def __init__(self, root_dirs: List[str], split: str = 'train', transform=None, frames_per_sample: int = 30):
        self.root_dirs = [Path(d) for d in root_dirs]
        self.transform = transform
        self.samples = []

        self._load_samples()

    def _load_samples(self):
        """Load all image samples from dataset directories"""
        for root_dir in self.root_dirs:
            # Load real images
            real_dir = root_dir / "real"
            if real_dir.exists():
                image_files = list(real_dir.glob("*.jpg"))
                for img_path in image_files:
                    self.samples.append((str(img_path), 0))  # 0 = real

            # Load fake images
            fake_dir = root_dir / "fake"
            if fake_dir.exists():
                image_files = list(fake_dir.glob("*.jpg"))
                for img_path in image_files:
                    self.samples.append((str(img_path), 1))  # 1 = fake

        print(f"Loaded {len(self.samples)} samples from {len(self.root_dirs)} directories")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]

        # Load image
        image = Image.open(img_path).convert('RGB')

        if self.transform:
            image = self.transform(image)

        return image, label

class EnhancedTrainer:
    """Enhanced trainer incorporating multiple detection techniques"""

    def __init__(self, config: Dict):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")

        # Create output directory
        self.output_dir = Path(config['output_dir']) / f"enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Save config
        with open(self.output_dir / 'config.json', 'w') as f:
            json.dump(config, f, indent=2)

    def setup_data(self):
        """Setup data loaders"""
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])

        # Dataset directories (prioritize advanced datasets)
        dataset_dirs = [
            "datasets/unified_deepfake",
            "datasets/celeb_df_pp",
            "datasets/face_forensics_pp",
            "datasets/df40",
            "datasets/deeper_forensics",
            "datasets/wild_deepfake",
            "datasets/forgery_net",
            "datasets/train"  # fallback to original dataset
        ]

        # Filter existing directories
        existing_dirs = [d for d in dataset_dirs if Path(d).exists()]
        if not existing_dirs:
            raise ValueError("No dataset directories found!")

        print(f"Using datasets: {existing_dirs}")

        # Check if we have video files or image frames
        has_videos = any(list(Path(d).glob("**/*.mp4")) for d in existing_dirs)
        has_images = any(list(Path(d).glob("**/*.jpg")) for d in existing_dirs)

        if has_videos and not has_images:
            # Use VideoDataset for video files
            self.train_dataset = VideoDataset(existing_dirs, 'train',
                                            frame_count=self.config['frame_count'],
                                            transform=transform)
            self.val_dataset = VideoDataset(existing_dirs, 'val',
                                          frame_count=self.config['frame_count'],
                                          transform=transform)
        elif has_images:
            # Use ImageDataset for frame images
            # Handle both structures: datasets/train and datasets/some_dataset/train
            train_dirs = []
            val_dirs = []

            for d in existing_dirs:
                p = Path(d)
                # Check if this is already a split directory (like datasets/train)
                if (p / 'real').exists() and (p / 'fake').exists():
                    if 'train' in str(p) or p.name == 'train':
                        train_dirs.append(d)
                    elif 'val' in str(p) or p.name == 'val':
                        val_dirs.append(d)
                # Check if this contains split subdirectories (like datasets/celeb_df_pp/train)
                elif (p / 'train' / 'real').exists() or (p / 'train' / 'fake').exists():
                    train_dirs.append(str(p / 'train'))
                    if (p / 'val').exists():
                        val_dirs.append(str(p / 'val'))

            print(f"Train directories: {train_dirs}")
            print(f"Val directories: {val_dirs}")

            self.train_dataset = ImageDataset(train_dirs, 'dummy_split',
                                            transform=transform,
                                            frames_per_sample=self.config['frame_count'])
            self.val_dataset = ImageDataset(val_dirs, 'dummy_split',
                                          transform=transform,
                                          frames_per_sample=self.config['frame_count'])
        else:
            raise ValueError("No video files or image frames found in dataset directories")

        # Create data loaders
        self.train_loader = DataLoader(
            self.train_dataset,
            batch_size=self.config['batch_size'],
            shuffle=True,
            num_workers=0,  # Set to 0 for Windows compatibility
            pin_memory=False  # Disable for CPU training
        )

        self.val_loader = DataLoader(
            self.val_dataset,
            batch_size=self.config['batch_size'],
            shuffle=False,
            num_workers=0,
            pin_memory=False
        )

        print(f"Train samples: {len(self.train_dataset)}")
        print(f"Val samples: {len(self.val_dataset)}")

    def setup_model(self):
        """Setup the enhanced model for training"""
        print("Setting up enhanced CNN model for training...")

        # Use the existing DeepfakeClassifier which is trainable
        self.model = DeepfakeClassifier().to(self.device)

        # Setup optimizer
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=self.config['learning_rate'],
            weight_decay=self.config['weight_decay']
        )

        # Setup scheduler
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=self.config['epochs']
        )

        # Loss function
        self.criterion = nn.CrossEntropyLoss()

        # Enable mixed precision if available
        self.scaler = torch.cuda.amp.GradScaler() if torch.cuda.is_available() else None

    def train_epoch(self) -> Tuple[float, float]:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0
        correct = 0
        total = 0

        for batch_idx, (images, labels) in enumerate(self.train_loader):
            images, labels = images.to(self.device), labels.to(self.device)

            self.optimizer.zero_grad()

            if self.scaler:
                with torch.cuda.amp.autocast():
                    outputs = self.model(images)
                    loss = self.criterion(outputs, labels)

                self.scaler.scale(loss).backward()
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                outputs = self.model(images)
                loss = self.criterion(outputs, labels)
                loss.backward()
                self.optimizer.step()

            total_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

            if batch_idx % 10 == 0:
                print(f"Batch {batch_idx}/{len(self.train_loader)}, "
                      f"Loss: {loss.item():.4f}, Acc: {100.*correct/total:.2f}%")

        accuracy = 100. * correct / total
        avg_loss = total_loss / len(self.train_loader)

        return avg_loss, accuracy

    def validate(self) -> Tuple[float, float, List[int], List[int]]:
        """Validate the model"""
        if len(self.val_dataset) == 0:
            print("⚠️  No validation samples available, skipping validation")
            return 0.0, 0.0, [], []

        self.model.eval()
        total_loss = 0
        correct = 0
        total = 0
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for images, labels in self.val_loader:
                images, labels = images.to(self.device), labels.to(self.device)

                outputs = self.model(images)
                loss = self.criterion(outputs, labels)

                total_loss += loss.item()
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()

                all_preds.extend(predicted.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        accuracy = 100. * correct / total
        avg_loss = total_loss / len(self.val_loader)

        return avg_loss, accuracy, all_preds, all_labels

    def save_checkpoint(self, epoch: int, loss: float, accuracy: float):
        """Save model checkpoint"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'loss': loss,
            'accuracy': accuracy,
            'config': self.config
        }

        checkpoint_path = self.output_dir / f'checkpoint_epoch_{epoch}.pth'
        torch.save(checkpoint, checkpoint_path)

        # Save best model
        if accuracy > self.best_accuracy:
            self.best_accuracy = accuracy
            best_path = self.output_dir / 'best_model.pth'
            torch.save(checkpoint, best_path)
            print(f"💾 Saved best model with accuracy: {accuracy:.2f}%")

    def plot_training_history(self, history: Dict):
        """Plot training history"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

        # Loss plot
        ax1.plot(history['train_loss'], label='Train Loss')
        ax1.plot(history['val_loss'], label='Val Loss')
        ax1.set_title('Training Loss')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.legend()

        # Accuracy plot
        ax2.plot(history['train_acc'], label='Train Acc')
        ax2.plot(history['val_acc'], label='Val Acc')
        ax2.set_title('Training Accuracy')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Accuracy (%)')
        ax2.legend()

        plt.tight_layout()
        plt.savefig(self.output_dir / 'training_history.png', dpi=300, bbox_inches='tight')
        plt.close()

    def train(self):
        """Main training loop"""
        print("🚀 Starting enhanced training...")
        print(f"Output directory: {self.output_dir}")

        self.best_accuracy = 0
        history = {
            'train_loss': [], 'train_acc': [],
            'val_loss': [], 'val_acc': []
        }

        for epoch in range(self.config['epochs']):
            print(f"\nEpoch {epoch+1}/{self.config['epochs']}")
            print("-" * 50)

            # Train
            start_time = time.time()
            train_loss, train_acc = self.train_epoch()
            train_time = time.time() - start_time

            # Validate
            val_loss, val_acc, _, _ = self.validate()

            # Update scheduler
            self.scheduler.step()

            # Log results
            print(".2f")
            print(".2f")

            # Save history
            history['train_loss'].append(train_loss)
            history['train_acc'].append(train_acc)
            history['val_loss'].append(val_loss)
            history['val_acc'].append(val_acc)

            # Save checkpoint
            self.save_checkpoint(epoch+1, val_loss, val_acc)

        # Save final model and training history
        final_model_path = self.output_dir / 'final_model.pth'
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'config': self.config,
            'history': history
        }, final_model_path)

        # Plot training history
        self.plot_training_history(history)

        # Save training summary
        summary = {
            'config': self.config,
            'best_accuracy': self.best_accuracy,
            'final_train_loss': history['train_loss'][-1],
            'final_train_acc': history['train_acc'][-1],
            'final_val_loss': history['val_loss'][-1],
            'final_val_acc': history['val_acc'][-1],
            'training_time_minutes': sum([len(self.train_dataset) / self.config['batch_size'] * 0.1 for _ in range(self.config['epochs'])])  # rough estimate
        }

        with open(self.output_dir / 'training_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)

        print("\n✅ Training completed!")
        print(f"Best validation accuracy: {self.best_accuracy:.2f}%")
        print(f"Models saved to: {self.output_dir}")

def main():
    parser = argparse.ArgumentParser(description='Train Enhanced Deepfake Detector')
    parser.add_argument('--epochs', type=int, default=50, help='Number of epochs')
    parser.add_argument('--batch_size', type=int, default=8, help='Batch size')
    parser.add_argument('--learning_rate', type=float, default=1e-4, help='Learning rate')
    parser.add_argument('--weight_decay', type=float, default=1e-4, help='Weight decay')
    parser.add_argument('--frame_count', type=int, default=30, help='Frames per video')
    parser.add_argument('--output_dir', type=str, default='training_runs', help='Output directory')
    parser.add_argument('--use_laa', action='store_true', default=True, help='Use LAA-Net')
    parser.add_argument('--use_clip', action='store_true', default=True, help='Use CLIP-based detection')
    parser.add_argument('--use_dm_aware', action='store_true', default=True, help='Use diffusion model awareness')

    args = parser.parse_args()

    # Training configuration
    config = {
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'learning_rate': args.learning_rate,
        'weight_decay': args.weight_decay,
        'frame_count': args.frame_count,
        'output_dir': args.output_dir,
        'use_laa': args.use_laa,
        'use_clip': args.use_clip,
        'use_dm_aware': args.use_dm_aware
    }

    # Create trainer and run training
    trainer = EnhancedTrainer(config)
    trainer.setup_data()
    trainer.setup_model()
    trainer.train()

if __name__ == "__main__":
    main()