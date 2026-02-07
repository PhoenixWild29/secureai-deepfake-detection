# NNPACK and CPU Inference Backends

## What is NNPACK?

**NNPACK** is an optional CPU acceleration library used by PyTorch for **Conv2d (2D convolution)** operations. It is one of several backends PyTorch can use when running neural networks on CPU:

- **NNPACK** – Optimized for certain CPU instruction sets (e.g. some ARM, some x86). Used when available and supported.
- **oneDNN (MKLDNN)** – Intel’s library; often used on x86 for optimized CPU inference.
- **Default ATen kernels** – PyTorch’s built-in CPU implementations; always available as fallback.

Your models (ResNet, CLIP, Xception, EfficientNet, etc.) use Conv2d heavily. PyTorch chooses which backend to use automatically; you don’t pick it in application code.

## Do we need NNPACK?

**No.** It is optional. When NNPACK is not available or is disabled, PyTorch uses other backends (oneDNN on Intel, or default ATen). Inference still runs correctly and is still accelerated where the CPU supports it.

## Why we set `USE_NNPACK=0` in production

On many cloud VMs (including typical DigitalOcean droplets), NNPACK **cannot** initialize. The CPU is reported as “Unsupported hardware,” so PyTorch never actually uses NNPACK there—it is already on the fallback path. The only effect of that is a repeated warning in the logs.

Setting `USE_NNPACK=0`:

- **Does not remove a capability** – On that hardware, NNPACK was never usable.
- **Does not change which code path runs** – PyTorch was already using the non-NNPACK path.
- **Only stops the warning** – So logs are readable and not filled with the same message.

So we are not “turning off a tool we could use.” On supported hardware, NNPACK would give an extra speed option for Conv2d; on your current server, that option is not available, and disabling it only cleans up the logs.

## Summary

| Question | Answer |
|----------|--------|
| What is NNPACK used for? | Optional CPU acceleration for Conv2d in PyTorch. |
| Do we need it? | No. PyTorch uses oneDNN or default CPU kernels when NNPACK is disabled or unavailable. |
| Why disable it? | On our cloud VMs it fails with “Unsupported hardware” and spams logs; disabling only suppresses the warning. |
| Are we still using optimized CPU? | Yes. oneDNN (on Intel) and/or default ATen CPU kernels are still used. |

If you later move to hardware that supports NNPACK and you want to try it, you can remove `USE_NNPACK=0` from the environment and restart the backend; PyTorch will use NNPACK if it initializes successfully.
