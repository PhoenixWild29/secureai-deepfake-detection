#!/usr/bin/env python3
"""
Check if V13 loaded completely and show status
"""
import os
import sys
import signal

os.environ['CUDA_VISIBLE_DEVICES'] = ''

# Timeout handler
def timeout_handler(signum, frame):
    print("\n⚠️  Status check timed out after 2 minutes")
    print("   V13 initialization is hanging")
    print("   This means V13 is not fully loaded")
    sys.exit(1)

# Set 2 minute timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(120)  # 2 minutes

print("=" * 70)
print("🔍 Checking V13 Status")
print("=" * 70)
print()

try:
    print("Importing V13 module...")
    from ai_model.deepfake_detector_v13 import get_deepfake_detector_v13
    print("✅ Module imported")
    print()
    
    print("Initializing V13 (this may take a moment)...")
    v13 = get_deepfake_detector_v13()
    print("✅ V13 initialized")
    print()
    
    # Cancel timeout
    signal.alarm(0)
    
    if v13:
        print(f"✅ V13 instance created")
        print(f"   Model loaded: {v13.model_loaded}")
        print(f"   Models count: {len(v13.models) if v13.models else 0}/3")
        
        if v13.models:
            print()
            print("📦 Loaded Models:")
            for i, model in enumerate(v13.models, 1):
                model_name = f"Model {i}"
                if hasattr(model, 'backbone'):
                    backbone_name = str(type(model.backbone).__name__)
                    print(f"   {i}. {backbone_name}")
                else:
                    print(f"   {i}. {type(model).__name__}")
        
        if v13.model_loaded and len(v13.models) == 3:
            print()
            print("🎉 V13 FULLY LOADED! All 3 models ready!")
            
            # Quick test
            try:
                from PIL import Image
                import numpy as np
                dummy = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
                prob = v13.detect_frame(dummy)
                print(f"   Inference test: {prob:.3f}")
                print()
                print("✅ V13 is fully working!")
            except Exception as e:
                print(f"   ⚠️  Inference test failed: {e}")
        elif v13.model_loaded:
            print()
            print(f"⚠️  V13 partially loaded: {len(v13.models)}/3 models")
            print("   Some models may have failed to load")
        else:
            print()
            print("❌ V13 not fully loaded")
    else:
        print("❌ V13 instance is None")
        print("   V13 failed to initialize")
        
except KeyboardInterrupt:
    signal.alarm(0)
    print("\n⚠️  Check interrupted by user")
    sys.exit(1)
except SystemExit:
    raise  # Re-raise SystemExit from timeout
except Exception as e:
    signal.alarm(0)
    print(f"❌ Error checking V13: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
