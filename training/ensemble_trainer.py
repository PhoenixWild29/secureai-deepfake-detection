#!/usr/bin/env python3
"""
Ensemble Model Training Logic
Core training implementation for ensemble deepfake detection models
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.ensemble import VotingClassifier
import joblib
import json

logger = logging.getLogger(__name__)


class DeepfakeDataset(Dataset):
    """
    PyTorch dataset for deepfake detection training data.
    """
    
    def __init__(self, features: np.ndarray, labels: np.ndarray, transform=None):
        """
        Initialize dataset.
        
        Args:
            features: Feature matrix
            labels: Label array
            transform: Optional data transformation
        """
        self.features = torch.FloatTensor(features)
        self.labels = torch.LongTensor(labels)
        self.transform = transform
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        feature = self.features[idx]
        label = self.labels[idx]
        
        if self.transform:
            feature = self.transform(feature)
        
        return feature, label


class ResNet50FeatureExtractor(nn.Module):
    """
    ResNet50-based feature extractor for deepfake detection.
    """
    
    def __init__(self, pretrained: bool = True, feature_dim: int = 2048):
        """
        Initialize ResNet50 feature extractor.
        
        Args:
            pretrained: Whether to use pretrained weights
            feature_dim: Output feature dimension
        """
        super(ResNet50FeatureExtractor, self).__init__()
        
        # Load pretrained ResNet50
        import torchvision.models as models
        self.backbone = models.resnet50(pretrained=pretrained)
        
        # Remove final classification layer
        self.backbone = nn.Sequential(*list(self.backbone.children())[:-1])
        
        # Add custom feature extraction layers
        self.feature_extractor = nn.Sequential(
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(2048, feature_dim),
            nn.ReLU(),
            nn.Dropout(0.5)
        )
    
    def forward(self, x):
        """Forward pass."""
        features = self.backbone(x)
        features = self.feature_extractor(features)
        return features


class CLIPFeatureExtractor(nn.Module):
    """
    CLIP-based feature extractor for deepfake detection.
    """
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """
        Initialize CLIP feature extractor.
        
        Args:
            model_name: CLIP model name
        """
        super(CLIPFeatureExtractor, self).__init__()
        
        from transformers import CLIPModel, CLIPProcessor
        
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        
        # Freeze CLIP parameters
        for param in self.model.parameters():
            param.requires_grad = False
    
    def forward(self, x):
        """Forward pass."""
        # Extract visual features
        visual_features = self.model.get_image_features(x)
        return visual_features


class EnsembleClassifier(nn.Module):
    """
    Ensemble classifier combining multiple feature extractors.
    """
    
    def __init__(
        self,
        resnet_feature_dim: int = 512,
        clip_feature_dim: int = 512,
        num_classes: int = 2
    ):
        """
        Initialize ensemble classifier.
        
        Args:
            resnet_feature_dim: ResNet50 feature dimension
            clip_feature_dim: CLIP feature dimension
            num_classes: Number of output classes
        """
        super(EnsembleClassifier, self).__init__()
        
        # Feature extractors
        self.resnet_extractor = ResNet50FeatureExtractor(feature_dim=resnet_feature_dim)
        self.clip_extractor = CLIPFeatureExtractor()
        
        # Ensemble fusion layer
        total_features = resnet_feature_dim + clip_feature_dim
        self.fusion_layer = nn.Sequential(
            nn.Linear(total_features, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x):
        """Forward pass."""
        # Extract features from both models
        resnet_features = self.resnet_extractor(x)
        clip_features = self.clip_extractor(x)
        
        # Concatenate features
        combined_features = torch.cat([resnet_features, clip_features], dim=1)
        
        # Final classification
        output = self.fusion_layer(combined_features)
        return output


class EnsembleTrainer:
    """
    Ensemble model trainer for deepfake detection.
    """
    
    def __init__(
        self,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        learning_rate: float = 0.001,
        batch_size: int = 32,
        num_epochs: int = 50,
        validation_split: float = 0.2
    ):
        """
        Initialize ensemble trainer.
        
        Args:
            device: Training device (cuda/cpu)
            learning_rate: Learning rate
            batch_size: Batch size
            num_epochs: Number of training epochs
            validation_split: Validation data split ratio
        """
        self.device = device
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.num_epochs = num_epochs
        self.validation_split = validation_split
        
        # Initialize model
        self.model = EnsembleClassifier()
        self.model.to(self.device)
        
        # Initialize optimizer and loss function
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.CrossEntropyLoss()
        
        # Training history
        self.history = {
            'train_loss': [],
            'train_acc': [],
            'val_loss': [],
            'val_acc': []
        }
        
        logger.info(f"Ensemble trainer initialized on device: {self.device}")
    
    def prepare_data(
        self,
        data: pd.DataFrame,
        feature_columns: List[str],
        label_column: str
    ) -> Tuple[DataLoader, DataLoader]:
        """
        Prepare training and validation data loaders.
        
        Args:
            data: Training data DataFrame
            feature_columns: Feature column names
            label_column: Label column name
            
        Returns:
            Tuple of (train_loader, val_loader)
        """
        try:
            # Extract features and labels
            X = data[feature_columns].values
            y = data[label_column].values
            
            # Split data
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=self.validation_split, random_state=42, stratify=y
            )
            
            # Create datasets
            train_dataset = DeepfakeDataset(X_train, y_train)
            val_dataset = DeepfakeDataset(X_val, y_val)
            
            # Create data loaders
            train_loader = DataLoader(
                train_dataset, batch_size=self.batch_size, shuffle=True
            )
            val_loader = DataLoader(
                val_dataset, batch_size=self.batch_size, shuffle=False
            )
            
            logger.info(f"Data prepared: {len(X_train)} train, {len(X_val)} validation samples")
            return train_loader, val_loader
            
        except Exception as e:
            logger.error(f"Error preparing data: {str(e)}")
            raise
    
    def train_epoch(self, train_loader: DataLoader) -> Tuple[float, float]:
        """
        Train for one epoch.
        
        Args:
            train_loader: Training data loader
            
        Returns:
            Tuple of (average_loss, accuracy)
        """
        self.model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(self.device), target.to(self.device)
            
            # Zero gradients
            self.optimizer.zero_grad()
            
            # Forward pass
            output = self.model(data)
            loss = self.criterion(output, target)
            
            # Backward pass
            loss.backward()
            self.optimizer.step()
            
            # Statistics
            total_loss += loss.item()
            pred = output.argmax(dim=1)
            correct += pred.eq(target).sum().item()
            total += target.size(0)
        
        avg_loss = total_loss / len(train_loader)
        accuracy = 100.0 * correct / total
        
        return avg_loss, accuracy
    
    def validate_epoch(self, val_loader: DataLoader) -> Tuple[float, float]:
        """
        Validate for one epoch.
        
        Args:
            val_loader: Validation data loader
            
        Returns:
            Tuple of (average_loss, accuracy)
        """
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for data, target in val_loader:
                data, target = data.to(self.device), target.to(self.device)
                
                output = self.model(data)
                loss = self.criterion(output, target)
                
                total_loss += loss.item()
                pred = output.argmax(dim=1)
                correct += pred.eq(target).sum().item()
                total += target.size(0)
        
        avg_loss = total_loss / len(val_loader)
        accuracy = 100.0 * correct / total
        
        return avg_loss, accuracy
    
    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        early_stopping_patience: int = 10
    ) -> Dict[str, Any]:
        """
        Train the ensemble model.
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            early_stopping_patience: Early stopping patience
            
        Returns:
            Training results dictionary
        """
        try:
            logger.info(f"Starting training for {self.num_epochs} epochs")
            
            best_val_acc = 0.0
            patience_counter = 0
            
            for epoch in range(self.num_epochs):
                # Train
                train_loss, train_acc = self.train_epoch(train_loader)
                
                # Validate
                val_loss, val_acc = self.validate_epoch(val_loader)
                
                # Update history
                self.history['train_loss'].append(train_loss)
                self.history['train_acc'].append(train_acc)
                self.history['val_loss'].append(val_loss)
                self.history['val_acc'].append(val_acc)
                
                # Early stopping
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    patience_counter = 0
                    # Save best model
                    self.save_checkpoint(f'best_model_epoch_{epoch}.pth')
                else:
                    patience_counter += 1
                
                if patience_counter >= early_stopping_patience:
                    logger.info(f"Early stopping at epoch {epoch}")
                    break
                
                # Log progress
                if epoch % 10 == 0:
                    logger.info(
                        f"Epoch {epoch}: Train Loss: {train_loss:.4f}, "
                        f"Train Acc: {train_acc:.2f}%, Val Loss: {val_loss:.4f}, "
                        f"Val Acc: {val_acc:.2f}%"
                    )
            
            logger.info(f"Training completed. Best validation accuracy: {best_val_acc:.2f}%")
            
            return {
                'best_val_accuracy': best_val_acc,
                'total_epochs': epoch + 1,
                'final_train_loss': train_loss,
                'final_train_accuracy': train_acc,
                'final_val_loss': val_loss,
                'final_val_accuracy': val_acc,
                'history': self.history
            }
            
        except Exception as e:
            logger.error(f"Error during training: {str(e)}")
            raise
    
    def evaluate(
        self,
        test_loader: DataLoader
    ) -> Dict[str, float]:
        """
        Evaluate model on test data.
        
        Args:
            test_loader: Test data loader
            
        Returns:
            Evaluation metrics dictionary
        """
        try:
            self.model.eval()
            all_predictions = []
            all_targets = []
            all_probabilities = []
            
            with torch.no_grad():
                for data, target in test_loader:
                    data, target = data.to(self.device), target.to(self.device)
                    
                    output = self.model(data)
                    probabilities = torch.softmax(output, dim=1)
                    predictions = output.argmax(dim=1)
                    
                    all_predictions.extend(predictions.cpu().numpy())
                    all_targets.extend(target.cpu().numpy())
                    all_probabilities.extend(probabilities[:, 1].cpu().numpy())  # Probability of positive class
            
            # Calculate metrics
            accuracy = accuracy_score(all_targets, all_predictions)
            precision = precision_score(all_targets, all_predictions, average='weighted')
            recall = recall_score(all_targets, all_predictions, average='weighted')
            f1 = f1_score(all_targets, all_predictions, average='weighted')
            auc = roc_auc_score(all_targets, all_probabilities)
            
            metrics = {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'auc_score': auc
            }
            
            logger.info(f"Evaluation completed: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error during evaluation: {str(e)}")
            raise
    
    def save_model(self, filepath: str):
        """
        Save trained model.
        
        Args:
            filepath: Model save path
        """
        try:
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'optimizer_state_dict': self.optimizer.state_dict(),
                'history': self.history,
                'hyperparameters': {
                    'learning_rate': self.learning_rate,
                    'batch_size': self.batch_size,
                    'num_epochs': self.num_epochs,
                    'validation_split': self.validation_split
                }
            }, filepath)
            
            logger.info(f"Model saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            raise
    
    def save_checkpoint(self, filepath: str):
        """
        Save model checkpoint.
        
        Args:
            filepath: Checkpoint save path
        """
        self.save_model(filepath)
    
    def load_model(self, filepath: str):
        """
        Load trained model.
        
        Args:
            filepath: Model load path
        """
        try:
            checkpoint = torch.load(filepath, map_location=self.device)
            
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            self.history = checkpoint['history']
            
            logger.info(f"Model loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise


# Utility functions for easy access
def create_ensemble_trainer(**kwargs) -> EnsembleTrainer:
    """Create ensemble trainer instance."""
    return EnsembleTrainer(**kwargs)


def train_ensemble_model(
    data: pd.DataFrame,
    feature_columns: List[str],
    label_column: str,
    hyperparameters: Optional[Dict[str, Any]] = None
) -> Tuple[EnsembleTrainer, Dict[str, Any]]:
    """
    Train ensemble model with given data and hyperparameters.
    
    Args:
        data: Training data
        feature_columns: Feature column names
        label_column: Label column name
        hyperparameters: Training hyperparameters
        
    Returns:
        Tuple of (trained_model, training_results)
    """
    try:
        # Set up hyperparameters
        hp = hyperparameters or {}
        trainer = EnsembleTrainer(
            learning_rate=hp.get('learning_rate', 0.001),
            batch_size=hp.get('batch_size', 32),
            num_epochs=hp.get('epochs', 50),
            validation_split=hp.get('validation_split', 0.2)
        )
        
        # Prepare data
        train_loader, val_loader = trainer.prepare_data(
            data, feature_columns, label_column
        )
        
        # Train model
        training_results = trainer.train(train_loader, val_loader)
        
        return trainer, training_results
        
    except Exception as e:
        logger.error(f"Error training ensemble model: {str(e)}")
        raise


# Export
__all__ = [
    'DeepfakeDataset',
    'ResNet50FeatureExtractor',
    'CLIPFeatureExtractor',
    'EnsembleClassifier',
    'EnsembleTrainer',
    'create_ensemble_trainer',
    'train_ensemble_model'
]
