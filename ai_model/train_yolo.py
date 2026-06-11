#!/usr/bin/env python3
"""
YOLOv8 Classification Training for DeepFake Detection
======================================================

NOTE: Previous version used YOLO in DETECTION mode (bounding boxes), which requires
per-image .txt annotation files. Deepfake datasets only have class folders (real/fake),
so detection mode always produced mAP50=0.0.

FIX: Use YOLO CLASSIFICATION mode (task='classify'), which accepts:
    datasets/<name>/train/real/  *.jpg
    datasets/<name>/train/fake/  *.jpg
No annotation files needed — the folder name IS the class label.

Usage:
    python ai_model/train_yolo.py
    python ai_model/train_yolo.py --dataset datasets/celeb_df_v2 --epochs 50
    FORCE_CPU=1 python ai_model/train_yolo.py
"""
import os
import argparse
import torch
import json
from pathlib import Path
from datetime import datetime

if os.getenv('FORCE_CPU', '0') == '1':
    os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')

from ultralytics import YOLO


def find_dataset(base_hint: str = None) -> Path:
    """Return the first dataset directory that has train/real and train/fake splits."""
    candidates = []
    if base_hint:
        candidates.append(Path(base_hint))
    candidates += [
        Path('datasets/celeb_df_v2'),
        Path('datasets/face_forensics_pp'),
        Path('datasets/unified_deepfake'),
        Path('datasets/celeb_df_pp'),
        Path('datasets/train'),
    ]
    for c in candidates:
        if (c / 'train' / 'real').exists() and (c / 'train' / 'fake').exists():
            return c
    return None


def train_yolo_classify(dataset_dir: Path, epochs: int = 50, imgsz: int = 224,
                        batch_size: int = 16) -> None:
    """
    Train YOLOv8 in classification mode on a real/fake dataset.

    Args:
        dataset_dir: Path with sub-dirs train/real, train/fake, val/real, val/fake
        epochs:      Number of training epochs
        imgsz:       Input image size (224 matches ResNet/EfficientNet convention)
        batch_size:  Training batch size
    """
    device = 'cpu' if (os.getenv('CUDA_VISIBLE_DEVICES') == '' or
                       not torch.cuda.is_available()) else 0

    run_name = f'yolo_classify_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

    print("Starting YOLO Classification Training")
    print("=" * 50)
    print(f"  Dataset:    {dataset_dir}")
    print(f"  Mode:       classify  (real/fake folder structure)")
    print(f"  Epochs:     {epochs}")
    print(f"  Image size: {imgsz}x{imgsz}")
    print(f"  Batch:      {batch_size}")
    print(f"  Device:     {device}")
    print()

    # YOLOv8n-cls: nano classification model
    model = YOLO('yolov8n-cls.pt')

    results = model.train(
        data=str(dataset_dir),        # points to dir with train/ and val/ sub-dirs
        task='classify',
        epochs=epochs,
        imgsz=imgsz,
        batch=batch_size,
        patience=15,
        save=True,
        device=device,
        workers=2,
        project='ai_model/training_runs',
        name=run_name,
        exist_ok=True,
        pretrained=True,
        optimizer='Adam',
        lr0=0.001,
        lrf=0.01,
        cos_lr=True,
        close_mosaic=10,
    )

    # Persist the trained model
    model_path = 'ai_model/trained_model.pt'
    model.save(model_path)
    print(f"\nModel saved to: {model_path}")

    # Save training metadata
    metrics = results.results_dict if hasattr(results, 'results_dict') else {}
    metadata = {
        'training_date': datetime.now().isoformat(),
        'model_type': 'YOLOv8n-cls',
        'task': 'classify',
        'dataset': str(dataset_dir),
        'epochs': epochs,
        'imgsz': imgsz,
        'batch_size': batch_size,
        'final_metrics': {
            'top1_accuracy': float(metrics.get('metrics/accuracy_top1', 0)),
            'top5_accuracy': float(metrics.get('metrics/accuracy_top5', 0)),
        },
    }

    meta_path = 'ai_model/training_metadata.json'
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"  Top-1 Accuracy: {metadata['final_metrics']['top1_accuracy']:.4f}")
    print(f"  Metadata saved: {meta_path}")
    print("\n[OK] YOLO classification training complete!")
    return model, results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train YOLOv8 classifier for deepfake detection')
    parser.add_argument('--dataset', type=str, default=None,
                        help='Path to dataset root (must have train/real, train/fake sub-dirs)')
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--imgsz', type=int, default=224)
    parser.add_argument('--batch', type=int, default=16)
    args = parser.parse_args()

    dataset_dir = find_dataset(args.dataset)
    if dataset_dir is None:
        print('[ERROR] No suitable dataset found.')
        print('   Run:  python scripts/setup/download_datasets.py --dataset celeb_df_v2')
        raise SystemExit(1)

    print(f'[OK] Using dataset: {dataset_dir}')
    train_yolo_classify(dataset_dir, epochs=args.epochs,
                        imgsz=args.imgsz, batch_size=args.batch)
