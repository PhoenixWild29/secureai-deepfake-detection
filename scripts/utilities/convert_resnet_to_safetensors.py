#!/usr/bin/env python3
"""
One-time script: convert ResNet50 .pth checkpoint to .safetensors for faster ensemble load.
Run from repo root: python scripts/utilities/convert_resnet_to_safetensors.py
Ensemble detector will prefer .safetensors over .pth when both exist (safetensors loads much faster).
"""
import os
import sys

def main():
    try:
        from safetensors.torch import save_file
    except ImportError:
        print("Install safetensors: pip install safetensors")
        sys.exit(1)
    import torch

    candidates = [
        "ai_model/resnet_resnet50_best.pth",
        "ai_model/resnet_resnet50_final.pth",
        "resnet_resnet50_best.pth",
        "resnet_resnet50_final.pth",
    ]
    for pth_path in candidates:
        if not os.path.exists(pth_path):
            continue
        base, _ = os.path.splitext(pth_path)
        out_path = base + ".safetensors"
        if os.path.exists(out_path):
            print(f"Skip (exists): {out_path}")
            continue
        print(f"Loading {pth_path}...")
        ckpt = torch.load(pth_path, map_location="cpu", weights_only=True)
        state = ckpt.get("state_dict", ckpt) if isinstance(ckpt, dict) else ckpt
        if not isinstance(state, dict):
            print(f"  Skip: not a state dict")
            continue
        print(f"Saving {out_path}...")
        save_file(state, out_path)
        print(f"  Done. Delete {pth_path} optional; ensemble will use {out_path}.")
    print("Done.")

if __name__ == "__main__":
    main()
