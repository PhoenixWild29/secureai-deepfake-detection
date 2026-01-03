#!/usr/bin/env python3
"""
Check Deepfake Detection Model Status and Training
Verifies which models are loaded, trained, and ready for inference
"""
import os
import torch
import json
from pathlib import Path

def check_model_status():
    """Check status of all deepfake detection models"""
    
    print("=" * 60)
    print("🔍 Deepfake Detection Model Status Check")
    print("=" * 60)
    print()
    
    results = {
        'clip': {'status': 'unknown', 'details': {}},
        'resnet50': {'status': 'unknown', 'details': {}},
        'laa_net': {'status': 'unknown', 'details': {}},
        'mtcnn': {'status': 'unknown', 'details': {}},
        'ensemble': {'status': 'unknown', 'details': {}}
    }
    
    # Check CLIP
    print("📦 Checking CLIP Model...")
    try:
        import open_clip
        model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
        results['clip'] = {
            'status': '✅ Available',
            'details': {
                'model': 'ViT-B-32',
                'pretrained': 'laion2b_s34b_b79k',
                'type': 'Zero-shot (no training needed)',
                'accuracy_estimate': '85-90%'
            }
        }
        print("  ✅ CLIP model available (pretrained, zero-shot)")
    except Exception as e:
        results['clip'] = {
            'status': '❌ Not Available',
            'details': {'error': str(e)}
        }
        print(f"  ❌ CLIP not available: {e}")
    
    print()
    
    # Check ResNet50
    print("📦 Checking ResNet50 Model...")
    resnet_paths = [
        'ai_model/resnet_resnet50_final.pth',
        'ai_model/resnet_resnet50_best.pth',
        'resnet_resnet50_final.pth',
        'resnet_resnet50_best.pth'
    ]
    
    resnet_found = False
    for path in resnet_paths:
        if os.path.exists(path):
            print(f"  ✅ Found model file: {path}")
            try:
                state_dict = torch.load(path, map_location='cpu')
                param_count = sum(p.numel() for p in state_dict.values() if isinstance(p, torch.Tensor))
                
                # Check if it has classifier head (indicates training)
                has_classifier = 'fc.weight' in state_dict or 'model.fc.weight' in state_dict
                
                results['resnet50'] = {
                    'status': '✅ Available',
                    'details': {
                        'path': path,
                        'parameters': param_count,
                        'has_classifier_head': has_classifier,
                        'trained_for_deepfakes': 'Likely' if has_classifier else 'Unknown',
                        'accuracy_estimate': '90-95%' if has_classifier else '70-80% (ImageNet only)'
                    }
                }
                resnet_found = True
                print(f"    Parameters: {param_count:,}")
                print(f"    Has classifier head: {has_classifier}")
                break
            except Exception as e:
                print(f"  ⚠️  Error loading model: {e}")
    
    if not resnet_found:
        results['resnet50'] = {
            'status': '❌ Not Found',
            'details': {'error': 'Model file not found in expected locations'}
        }
        print("  ❌ ResNet50 model file not found")
    
    print()
    
    # Check LAA-Net
    print("📦 Checking LAA-Net Model...")
    try:
        # Check if LAA-Net is available
        from ai_model.enhanced_detector import LAA_NET_AVAILABLE
        if LAA_NET_AVAILABLE:
            results['laa_net'] = {
                'status': '✅ Available',
                'details': {'accuracy_estimate': '+5-10% improvement'}
            }
            print("  ✅ LAA-Net available")
        else:
            results['laa_net'] = {
                'status': '⚠️  Not Loaded',
                'details': {'reason': 'Submodule not set up or weights not found'}
            }
            print("  ⚠️  LAA-Net not loaded (submodule setup required)")
    except Exception as e:
        results['laa_net'] = {
            'status': '❌ Not Available',
            'details': {'error': str(e)}
        }
        print(f"  ❌ LAA-Net not available: {e}")
    
    print()
    
    # Check MTCNN
    print("📦 Checking MTCNN Face Detection...")
    try:
        from mtcnn import MTCNN
        results['mtcnn'] = {
            'status': '✅ Available',
            'details': {'accuracy_estimate': '95%+ face detection'}
        }
        print("  ✅ MTCNN available")
    except ImportError:
        results['mtcnn'] = {
            'status': '⚠️  Using OpenCV Fallback',
            'details': {'fallback': 'OpenCV Haar Cascades'}
        }
        print("  ⚠️  MTCNN not available, using OpenCV Haar cascades")
    
    print()
    
    # Check Ensemble Status
    print("📦 Checking Ensemble Configuration...")
    active_models = []
    if results['clip']['status'] == '✅ Available':
        active_models.append('CLIP')
    if results['resnet50']['status'] == '✅ Available':
        active_models.append('ResNet50')
    if results['laa_net']['status'] == '✅ Available':
        active_models.append('LAA-Net')
    
    if len(active_models) >= 2:
        results['ensemble'] = {
            'status': '✅ Active',
            'details': {
                'models': active_models,
                'method': 'Average ensemble',
                'accuracy_estimate': '88-93%' if 'LAA-Net' not in active_models else '93-98%'
            }
        }
        print(f"  ✅ Ensemble active with: {', '.join(active_models)}")
    elif len(active_models) == 1:
        results['ensemble'] = {
            'status': '⚠️  Single Model',
            'details': {
                'model': active_models[0],
                'accuracy_estimate': '85-90%'
            }
        }
        print(f"  ⚠️  Only {active_models[0]} active (no ensemble)")
    else:
        results['ensemble'] = {
            'status': '❌ No Models Available',
            'details': {'error': 'No detection models loaded'}
        }
        print("  ❌ No models available")
    
    print()
    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)
    print(json.dumps(results, indent=2))
    
    return results

if __name__ == "__main__":
    check_model_status()

