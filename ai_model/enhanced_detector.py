#!/usr/bin/env python3
"""
Enhanced DeepFake Detection Model
Combines multiple SOTA techniques from reviewed GitHub repositories:
- LAA-Net (Localized Artifact Attention) for quality-agnostic detection
- CLIP-based approaches for generalizable detection
- Multi-modal fusion for robust analysis
- Diffusion model awareness for 2025 threats
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models, transforms
import cv2
import numpy as np
from PIL import Image
import hashlib
import time
import os
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class LAABlock(nn.Module):
    """
    Localized Artifact Attention Block (inspired by LAA-Net)
    Focuses on local artifacts that are quality-agnostic
    """
    def __init__(self, in_channels: int, reduction: int = 16):
        super(LAABlock, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)

        self.fc = nn.Sequential(
            nn.Conv2d(in_channels, in_channels // reduction, 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(in_channels // reduction, in_channels, 1, bias=False)
        )

        self.sigmoid = nn.Sigmoid()

        # Local attention mechanism
        self.local_conv = nn.Conv2d(in_channels, in_channels, 3, padding=1, groups=in_channels, bias=False)

    def forward(self, x):
        # Global attention
        avg_out = self.fc(self.avg_pool(x))
        max_out = self.fc(self.max_pool(x))
        global_attn = avg_out + max_out

        # Local attention
        local_attn = self.local_conv(x)

        # Combine attentions
        attn = self.sigmoid(global_attn + local_attn)
        return x * attn

class QualityAgnosticDetector(nn.Module):
    """
    Quality-agnostic detector inspired by LAA-Net
    Handles varying video quality and compression artifacts
    """
    def __init__(self, num_classes: int = 2):
        super(QualityAgnosticDetector, self).__init__()

        # Use EfficientNet as backbone (good for various quality inputs)
        self.backbone = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)

        # Get number of features before classifier
        num_features = self.backbone.classifier[1].in_features

        # Replace classifier with identity to get features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=0.2, inplace=True),
            nn.Identity()
        )

        # LAA blocks for quality-agnostic attention
        self.laa1 = LAABlock(num_features)
        self.laa2 = LAABlock(num_features)

        # Final classification head
        self.classifier = nn.Sequential(
            nn.Linear(num_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes)
        )

        # Auxiliary heads for multi-task learning
        self.artifact_detector = nn.Linear(num_features, 1)  # Detect manipulation artifacts
        self.quality_estimator = nn.Linear(num_features, 1)  # Estimate video quality

    def forward(self, x):
        # Extract features using EfficientNet
        features = self.backbone(x)  # This should be [batch, num_features]

        # Ensure features is 2D: [batch, features]
        if features.dim() > 2:
            features = torch.flatten(features, start_dim=1)

        # Apply LAA blocks (reshape to spatial dimensions for attention)
        b, c = features.shape
        spatial_features = features.view(b, c, 1, 1)  # [batch, channels, 1, 1]

        spatial_features = self.laa1(spatial_features)
        spatial_features = self.laa2(spatial_features)

        # Flatten back to feature vector
        features = spatial_features.view(b, c)

        # Classification
        logits = self.classifier(features)

        # Auxiliary predictions
        artifact_score = torch.sigmoid(self.artifact_detector(features))
        quality_score = torch.sigmoid(self.quality_estimator(features))

        return logits, artifact_score, quality_score

class CLIPBasedDetector(nn.Module):
    """
    CLIP-based detector inspired by LNCLIP-DF
    Uses pre-trained CLIP for generalizable detection
    """
    def __init__(self):
        super(CLIPBasedDetector, self).__init__()
        self.clip_available = False
        try:
            import clip
            self.clip = clip  # Store reference to clip module
            self.clip_model, self.preprocess = clip.load("ViT-B/32")
            self.text_features = None
            self.clip_available = True
            self._prepare_text_features()
        except ImportError:
            print("CLIP not available, falling back to CNN-based approach")
            self.clip = None
            self.clip_model = None

        # Fallback CNN if CLIP unavailable
        if self.clip_model is None:
            self.fallback_cnn = models.resnet50(pretrained=True)
            self.fallback_cnn.fc = nn.Linear(2048, 2)

    def _prepare_text_features(self):
        """Prepare text features for deepfake detection prompts"""
        if not self.clip_available or self.clip is None or self.clip_model is None:
            return

        prompts = [
            "a real photograph of a person",
            "a fake manipulated image of a person",
            "authentic human face",
            "synthetically generated face",
            "real video frame",
            "deepfake manipulated video frame",
            "genuine facial expression",
            "artificial facial manipulation"
        ]

        try:
            text_tokens = self.clip.tokenize(prompts).to(next(self.clip_model.parameters()).device)
            with torch.no_grad():
                self.text_features = self.clip_model.encode_text(text_tokens)
                self.text_features /= self.text_features.norm(dim=-1, keepdim=True)
        except Exception as e:
            print(f"Failed to prepare CLIP text features: {e}")
            self.text_features = None

    def forward(self, image):
        if self.clip_model is not None and self.text_features is not None:
            # CLIP-based detection
            image_features = self.clip_model.encode_image(image)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            # Compute similarities with text prompts
            similarities = (image_features @ self.text_features.T)

            # Convert to binary classification (real vs fake)
            real_score = similarities[:, [0, 2, 4]].mean(dim=1)  # Real prompts
            fake_score = similarities[:, [1, 3, 5]].mean(dim=1)  # Fake prompts

            logits = torch.stack([real_score, fake_score], dim=1)
            return logits
        else:
            # Fallback to CNN
            return self.fallback_cnn(image)

class DiffusionAwareDetector(nn.Module):
    """
    Diffusion Model Aware Detector
    Specialized for detecting DM-generated content (2025 threat landscape)
    """
    def __init__(self):
        super(DiffusionAwareDetector, self).__init__()

        # Multi-scale feature extraction
        self.conv1 = nn.Conv2d(3, 64, 3, padding=1)
        self.conv2 = nn.Conv2d(64, 128, 3, padding=1)
        self.conv3 = nn.Conv2d(128, 256, 3, padding=1)

        # Frequency domain analysis (common DM artifacts)
        self.freq_conv = nn.Conv2d(256, 128, 1)

        # Attention for artifact localization
        self.attention = nn.MultiheadAttention(128, 8, batch_first=True)

        # Classification head
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(64, 2)
        )

    def forward(self, x):
        # Multi-scale features
        x1 = F.relu(self.conv1(x))
        x2 = F.relu(self.conv2(x1))
        x3 = F.relu(self.conv3(x2))

        # Frequency analysis
        freq_features = self.freq_conv(x3)

        # Reshape for attention
        b, c, h, w = freq_features.shape
        freq_flat = freq_features.view(b, c, -1).permute(0, 2, 1)  # (batch, seq_len, features)

        # Self-attention
        attn_out, _ = self.attention(freq_flat, freq_flat, freq_flat)
        attn_out = attn_out.permute(0, 2, 1).view(b, c, h, w)

        # Classification
        return self.classifier(attn_out)

class EnsembleDetector:
    """
    Ensemble detector combining multiple approaches
    Inspired by comprehensive detection frameworks
    """
    def __init__(self, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        self.device = device

        # Initialize detectors
        self.quality_detector = QualityAgnosticDetector().to(device)
        self.clip_detector = CLIPBasedDetector().to(device)
        self.dm_detector = DiffusionAwareDetector().to(device)

        # Ensemble weights (learned or fixed)
        self.weights = {
            'quality': 0.4,
            'clip': 0.3,
            'dm': 0.3
        }

        # Set to evaluation mode
        self.quality_detector.eval()
        self.dm_detector.eval()

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def preprocess_frame(self, frame: np.ndarray) -> torch.Tensor:
        """Preprocess video frame for detection"""
        # Convert BGR to RGB
        if frame.shape[2] == 3:  # BGR format
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert to PIL Image
        pil_image = Image.fromarray(frame)

        # Apply transforms
        tensor = self.transform(pil_image).unsqueeze(0).to(self.device)
        return tensor

    def detect_frame(self, frame: np.ndarray) -> Dict:
        """Detect deepfake in a single frame"""
        try:
            tensor = self.preprocess_frame(frame)

            # Get predictions from each detector
            with torch.no_grad():
                # Quality-agnostic detection
                qa_logits, artifact_score, quality_score = self.quality_detector(tensor)
                qa_probs = F.softmax(qa_logits, dim=1)
                qa_fake_prob = qa_probs[0, 1].item()

                # CLIP-based detection
                clip_logits = self.clip_detector(tensor)
                clip_probs = F.softmax(clip_logits, dim=1)
                clip_fake_prob = clip_probs[0, 1].item()

                # DM-aware detection
                dm_logits = self.dm_detector(tensor)
                dm_probs = F.softmax(dm_logits, dim=1)
                dm_fake_prob = dm_probs[0, 1].item()

                # Ensemble prediction
                ensemble_fake_prob = (
                    self.weights['quality'] * qa_fake_prob +
                    self.weights['clip'] * clip_fake_prob +
                    self.weights['dm'] * dm_fake_prob
                )

                # Determine final result
                is_fake = ensemble_fake_prob > 0.5
                confidence = ensemble_fake_prob if is_fake else (1 - ensemble_fake_prob)

                return {
                    'is_fake': is_fake,
                    'confidence': confidence,
                    'ensemble_score': ensemble_fake_prob,
                    'detector_scores': {
                        'quality_agnostic': qa_fake_prob,
                        'clip_based': clip_fake_prob,
                        'dm_aware': dm_fake_prob
                    },
                    'artifact_score': artifact_score.item(),
                    'quality_score': quality_score.item(),
                    'method': 'ensemble_sota'
                }

        except Exception as e:
            print(f"Frame detection error: {e}")
            return {
                'is_fake': False,
                'confidence': 0.0,
                'error': str(e),
                'method': 'ensemble_sota'
            }

    def detect_video(self, video_path: str, sample_rate: int = 30) -> Dict:
        """Detect deepfake in video using ensemble approach"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError("Could not open video file")

            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            # Sample frames
            frame_indices = np.linspace(0, frame_count - 1, min(sample_rate, frame_count), dtype=int)

            frame_results = []
            for idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    result = self.detect_frame(frame)
                    frame_results.append(result)

            cap.release()

            if not frame_results:
                raise ValueError("No frames could be processed")

            # Aggregate results
            fake_scores = [r['ensemble_score'] for r in frame_results]
            avg_fake_score = np.mean(fake_scores)
            std_fake_score = np.std(fake_scores)

            # Confidence based on consistency
            consistency = 1 - std_fake_score
            final_confidence = (avg_fake_score + consistency) / 2

            is_fake = avg_fake_score > 0.5

            # Generate video hash
            with open(video_path, 'rb') as f:
                video_hash = hashlib.sha256(f.read()).hexdigest()

            return {
                'is_fake': is_fake,
                'confidence': final_confidence,
                'video_hash': video_hash,
                'authenticity_score': 1 - avg_fake_score,
                'frame_count': len(frame_results),
                'avg_fake_score': avg_fake_score,
                'score_std': std_fake_score,
                'method': 'ensemble_sota',
                'detector_breakdown': {
                    'quality_agnostic': np.mean([r['detector_scores']['quality_agnostic'] for r in frame_results]),
                    'clip_based': np.mean([r['detector_scores']['clip_based'] for r in frame_results]),
                    'dm_aware': np.mean([r['detector_scores']['dm_aware'] for r in frame_results])
                },
                'processing_time': time.time()
            }

        except Exception as e:
            print(f"Video detection error: {e}")
            return {
                'is_fake': False,
                'confidence': 0.0,
                'error': str(e),
                'method': 'ensemble_sota'
            }

# Global detector instance
_detector_instance = None

def get_enhanced_detector() -> EnsembleDetector:
    """Get or create enhanced detector instance"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = EnsembleDetector()
    return _detector_instance

def detect_fake_enhanced(video_path: str) -> Dict:
    """
    Enhanced deepfake detection using ensemble of SOTA methods
    Combines quality-agnostic, CLIP-based, and DM-aware detection
    """
    detector = get_enhanced_detector()
    return detector.detect_video(video_path)

if __name__ == "__main__":
    # Test the enhanced detector
    print("Testing Enhanced DeepFake Detector...")

    detector = get_enhanced_detector()
    print(f"Detector initialized on device: {detector.device}")

    # Test with sample video if available
    sample_video = "sample_video.mp4"
    if os.path.exists(sample_video):
        print(f"Testing with {sample_video}...")
        result = detector.detect_video(sample_video)
        print("Detection Result:", result)
    else:
        print("Sample video not found. Enhanced detector ready for use.")