#!/usr/bin/env python3
"""
Train ResNet-based DeepFake Detection Model
Uses pre-trained ResNet backbone for better accuracy
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import transforms
import os
from pathlib import Path
from datetime import datetime
import json
import matplotlib.pyplot as plt
from tqdm import tqdm

# Import our models
from ai_model.deepfake_classifier import ResNetDeepfakeClassifier, DeepfakeDataset

def create_data_transforms():
    """Create data transformations for training and validation"""
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),  # ResNet expects 224x224
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    return train_transform, val_transform

def train_resnet_model(model_name='resnet50', epochs=10, batch_size=32, learning_rate=1e-4):
    """Train ResNet-based deepfake detection model"""

    print(f"🚀 Training {model_name.upper()} DeepFake Detection Model")
    print("=" * 60)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # Create model
    model = ResNetDeepfakeClassifier(model_name=model_name, pretrained=True)
    model = model.to(device)

    # Data transforms
    train_transform, val_transform = create_data_transforms()

    # Create datasets
    train_dataset = DeepfakeDataset('datasets/train', transform=train_transform)
    val_dataset = DeepfakeDataset('datasets/val', transform=val_transform)

    print(f"Training samples: {len(train_dataset)}")
    print(f"Validation samples: {len(val_dataset)}")

    if len(train_dataset) == 0:
        print("❌ No training data found! Please ensure datasets/train has 'real' and 'fake' folders with images.")
        return

    # Data loaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=2)

    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)

    # Training history
    history = {
        'train_loss': [], 'train_acc': [],
        'val_loss': [], 'val_acc': [],
        'epochs': []
    }

    best_accuracy = 0.0

    for epoch in range(epochs):
        print(f"\n📊 Epoch {epoch+1}/{epochs}")
        print("-" * 30)

        # Training phase
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        train_bar = tqdm(train_loader, desc="Training")
        for inputs, labels in train_bar:
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

            train_bar.set_postfix({
                'loss': f'{train_loss/len(train_loader):.4f}',
                'acc': f'{100.*train_correct/train_total:.2f}%'
            })

        train_accuracy = 100. * train_correct / train_total
        avg_train_loss = train_loss / len(train_loader)

        # Validation phase
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            val_bar = tqdm(val_loader, desc="Validating")
            for inputs, labels in val_bar:
                inputs, labels = inputs.to(device), labels.to(device)

                outputs = model(inputs)
                loss = criterion(outputs, labels)

                val_loss += loss.item()
                _, predicted = outputs.max(1)
                val_total += labels.size(0)
                val_correct += predicted.eq(labels).sum().item()

                val_bar.set_postfix({
                    'loss': f'{val_loss/len(val_loader):.4f}',
                    'acc': f'{100.*val_correct/val_total:.2f}%'
                })

        val_accuracy = 100. * val_correct / val_total
        avg_val_loss = val_loss / len(val_loader)

        # Update learning rate
        scheduler.step()

        # Save history
        history['epochs'].append(epoch + 1)
        history['train_loss'].append(avg_train_loss)
        history['train_acc'].append(train_accuracy)
        history['val_loss'].append(avg_val_loss)
        history['val_acc'].append(val_accuracy)

        print(".4f")
        print(".4f")
        print(".2f")
        print(".2f")

        # Save best model
        if val_accuracy > best_accuracy:
            best_accuracy = val_accuracy
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Create model directory
            os.makedirs('ai_model', exist_ok=True)

            # Save model
            model_path = f'ai_model/resnet_{model_name}_best.pth'
            torch.save(model.state_dict(), model_path)

            # Save training metadata
            metadata = {
                'model_name': model_name,
                'architecture': 'ResNet',
                'epochs_trained': epoch + 1,
                'best_accuracy': best_accuracy,
                'training_date': timestamp,
                'hyperparameters': {
                    'learning_rate': learning_rate,
                    'batch_size': batch_size,
                    'epochs': epochs
                },
                'final_metrics': {
                    'train_accuracy': train_accuracy,
                    'val_accuracy': val_accuracy,
                    'train_loss': avg_train_loss,
                    'val_loss': avg_val_loss
                }
            }

            with open(f'ai_model/resnet_{model_name}_metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            print(f"💾 Saved best model: {model_path} ({best_accuracy:.2f}%)")

    # Save final model
    final_path = f'ai_model/resnet_{model_name}_final.pth'
    torch.save(model.state_dict(), final_path)

    # Plot training history
    plt.figure(figsize=(12, 4))

    plt.subplot(1, 2, 1)
    plt.plot(history['epochs'], history['train_loss'], label='Train Loss')
    plt.plot(history['epochs'], history['val_loss'], label='Val Loss')
    plt.title('Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(history['epochs'], history['train_acc'], label='Train Acc')
    plt.plot(history['epochs'], history['val_acc'], label='Val Acc')
    plt.title('Training Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy (%)')
    plt.legend()

    plt.tight_layout()
    plt.savefig(f'training_results/resnet_{model_name}_training_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
    plt.show()

    print("\n🎉 Training Complete!")
    print(f"Best Validation Accuracy: {best_accuracy:.2f}%")
    print(f"Model saved as: ai_model/resnet_{model_name}_best.pth")

    return model, history

if __name__ == "__main__":
    # Train ResNet50 model
    model, history = train_resnet_model(
        model_name='resnet50',
        epochs=10,
        batch_size=16,  # Smaller batch size for ResNet
        learning_rate=1e-4
    )