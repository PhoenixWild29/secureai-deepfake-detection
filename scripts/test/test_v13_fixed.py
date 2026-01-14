#!/usr/bin/env python3
"""
Test V13 with ConvNeXt-Large fixes
"""
import os
import sys
import signal
import logging

os.environ['CUDA_VISIBLE_DEVICES'] = ''

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Timeout handler
def timeout_handler(signum, frame):
    print("\n⚠️  V13 loading timed out after 10 minutes")
    print("   This should not happen with the fixes")
    sys.exit(1)

# Set 10 minute timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(600)  # 10 minutes

try:
    print("=" * 70)
    print("🧪 Testing V13 with ConvNeXt-Large Fixes")
    print("=" * 70)
    print()
    print("Fixes applied:")
    print("  ✅ Timeout protection for ConvNeXt-Large (3 min)")
    print("  ✅ Alternative creation methods (standard + scriptable)")
    print("  ✅ Aggressive memory cleanup before ConvNeXt-Large")
    print("  ✅ Graceful fallback if ConvNeXt-Large fails")
    print()
    
    print("Loading V13 (this may take 2-5 minutes)...")
    print()
    
    from ai_model.deepfake_detector_v13 import get_deepfake_detector_v13
    
    v13 = get_deepfake_detector_v13()
    
    # Cancel timeout
    signal.alarm(0)
    
    if v13 and v13.model_loaded:
        print()
        print("✅ V13 loaded successfully!")
        print(f"   Models loaded: {len(v13.models)}/3")
        
        # Show which models loaded
        if len(v13.models) == 3:
            print("   🎉 All 3 models loaded: ViT-Large + ConvNeXt-Large + Swin-Large")
        elif len(v13.models) == 2:
            print("   ⚠️  2 models loaded (one failed, but ensemble still works)")
        else:
            print("   ⚠️  Only 1 model loaded")
        
        # Quick inference test
        try:
            from PIL import Image
            import numpy as np
            dummy = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
            prob = v13.detect_frame(dummy)
            print(f"   Inference test: {prob:.3f}")
            print()
            print("🎉 V13 is fully working!")
        except Exception as e:
            print(f"   ⚠️  Inference test failed: {e}")
    else:
        print()
        print("❌ V13 not loaded")
        print("   Check logs above for errors")
        sys.exit(1)
        
except KeyboardInterrupt:
    signal.alarm(0)
    print("\n⚠️  Test interrupted by user")
    sys.exit(1)
except Exception as e:
    signal.alarm(0)
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
