from ultralytics import YOLO
import os
import torch
from pathlib import Path
import json
from datetime import datetime

def train_yolo_model(data_yaml, epochs=100, imgsz=640, batch_size=16):
    """
    Train YOLO model for deepfake detection with optimized parameters
    """
    print("🚀 Starting SecureAI YOLO Training")
    print("=" * 50)
    print(f"📊 Dataset: {data_yaml}")
    print(f"🎯 Epochs: {epochs}")
    print(f"📏 Image Size: {imgsz}x{imgsz}")
    print(f"📦 Batch Size: {batch_size}")
    print(f"🖥️  Device: {torch.device('cuda' if torch.cuda.is_available() else 'cpu')}")
    print()

    # Load pretrained YOLOv8 model
    model = YOLO('yolov8n.pt')  # Nano model for faster training

    # Training configuration
    training_args = {
        'data': data_yaml,
        'epochs': epochs,
        'imgsz': imgsz,
        'batch': batch_size,
        'patience': 20,  # Early stopping patience
        'save': True,
        'save_period': 10,  # Save checkpoint every 10 epochs
        'cache': True,  # Cache dataset for faster training
        'device': 0 if torch.cuda.is_available() else 'cpu',
        'workers': 2,  # Number of worker threads
        'project': 'ai_model/training_runs',
        'name': f'secureai_deepfake_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'exist_ok': True,
        'pretrained': True,
        'optimizer': 'Adam',  # Adam optimizer
        'lr0': 0.001,  # Initial learning rate
        'lrf': 0.01,  # Final learning rate fraction
        'momentum': 0.937,
        'weight_decay': 0.0005,
        'warmup_epochs': 3.0,
        'warmup_momentum': 0.8,
        'warmup_bias_lr': 0.1,
        'box': 7.5,  # Box loss gain
        'cls': 0.5,  # Classification loss gain
        'dfl': 1.5,  # Distribution focal loss gain
        'cos_lr': True,  # Cosine learning rate scheduler
        'close_mosaic': 10,  # Disable mosaic augmentation in last 10 epochs
    }

    # Start training
    print("🏃 Training in progress...")
    results = model.train(**training_args)

    # Save the trained model
    model_path = 'ai_model/trained_model.pt'
    model.save(model_path)
    print(f"💾 Model saved to: {model_path}")

    # Save training metadata
    metadata = {
        'training_date': datetime.now().isoformat(),
        'model_type': 'YOLOv8n',
        'dataset': data_yaml,
        'epochs': epochs,
        'imgsz': imgsz,
        'batch_size': batch_size,
        'final_metrics': {
            'mAP50': float(results.results_dict.get('metrics/mAP50(B)', 0)),
            'mAP50-95': float(results.results_dict.get('metrics/mAP50-95(B)', 0)),
            'precision': float(results.results_dict.get('metrics/precision(B)', 0)),
            'recall': float(results.results_dict.get('metrics/recall(B)', 0)),
        } if hasattr(results, 'results_dict') else {}
    }

    with open('ai_model/training_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)

    print("✅ Training completed!")
    print(f"📈 Final mAP50: {metadata['final_metrics'].get('mAP50', 'N/A'):.3f}")
    print(f"🎯 Final mAP50-95: {metadata['final_metrics'].get('mAP50-95', 'N/A'):.3f}")

    return model, results

def validate_model(model_path, data_yaml):
    """Validate the trained model"""
    print("\n🔍 Validating trained model...")
    model = YOLO(model_path)
    results = model.val(data=data_yaml, split='val')

    print("📊 Validation Results:")
    print(f"   mAP50: {results.results_dict.get('metrics/mAP50(B)', 0):.3f}")
    print(f"   mAP50-95: {results.results_dict.get('metrics/mAP50-95(B)', 0):.3f}")
    print(f"   Precision: {results.results_dict.get('metrics/precision(B)', 0):.3f}")
    print(f"   Recall: {results.results_dict.get('metrics/recall(B)', 0):.3f}")

    return results

if __name__ == "__main__":
    # Check if dataset exists
    if not os.path.exists('datasets/train') or not os.path.exists('datasets/val'):
        print("❌ Training dataset not found!")
        print("   Run 'python datasets/setup_training_data.py' first")
        exit(1)

    # Train the model
    model, training_results = train_yolo_model(
        data_yaml='datasets/data.yaml',
        epochs=50,  # Reduced for demo, increase for production
        imgsz=640,
        batch_size=8  # Smaller batch size for limited data
    )

    # Validate the model
    validate_model('ai_model/trained_model.pt', 'datasets/data.yaml')

    print("\n🎉 AI training phase completed!")
    print("🔄 Ready for next phase: Web Interface Development")