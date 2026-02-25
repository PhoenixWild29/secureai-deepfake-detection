# LAA-Net Setup (Optional)

LAA-Net (Localized Artifact Attention Network) is an optional detector that runs alongside CLIP and ResNet when the repo and weights are present. By default it is **not** used.

## 1. Clone LAA-Net

From the project root:

```bash
mkdir -p external
cd external
git clone https://github.com/10Ring/LAA-Net laa_net
cd laa_net
```

Or from project root in one line:

```bash
git clone https://github.com/10Ring/LAA-Net external/laa_net
```

## 2. Install LAA-Net dependencies

LAA-Net needs extra packages. From the project root (with your venv active):

```bash
pip install pyyaml "python-box>=5.0"
cd external/laa_net
pip install -r requirements.txt
cd ../..
```

Their recommended env includes: PyTorch, torchvision, albumentations, scikit-image, tensorboardX, imgaug. If you already have PyTorch/torchvision from this project, you may only need `albumentations` and `python-box`.

## 3. Download pretrained weights

- Weights (BI and SBI) are on Dropbox: [LAA-Net pretrained models](https://www.dropbox.com/scl/fo/dzmldaytujdeuky69d5x1/AIJrH2mit1hxnl1qzavM3vk?rlkey=nzzliincrfwejw2yr0ovldru1&st=z8ds7il7&dl=0)
- Download at least one `.pth` file (e.g. `efn4_fpn_hm_adv_best.pth` or the SBI variant).
- Place it under `external/laa_net/weights/`:

```bash
mkdir -p external/laa_net/weights
# Copy your downloaded .pth into external/laa_net/weights/
```

## 4. Point the app at LAA-Net

Either set environment variables or rely on defaults.

**Option A – Default paths (no env)**  
If the repo is at `external/laa_net` and a `.pth` is in `external/laa_net/weights/`, the enhanced detector will use it automatically.

**Option B – Environment variables**

```bash
# Optional: if LAA-Net is not in external/laa_net
export LAA_NET_ROOT=/path/to/laa_net

# Optional: if weights are not in external/laa_net/weights/
export LAA_NET_WEIGHTS=/path/to/efn4_fpn_hm_adv_best.pth
```

For Docker, add to `docker-compose` or `.env`:

```yaml
environment:
  - LAA_NET_ROOT=/app/external/laa_net
  - LAA_NET_WEIGHTS=/app/external/laa_net/weights/efn4_fpn_hm_adv_best.pth
```

And mount the repo + weights:

```yaml
volumes:
  - ./external/laa_net:/app/external/laa_net:ro
```

## 5. Verify

Run the model status script:

```bash
python scripts/diagnostic/CHECK_MODEL_STATUS.py
```

You should see `LAA-Net: ✅ Available` when the loader finds the repo and weights.

Or in Python:

```python
from ai_model.enhanced_detector import get_enhanced_detector
d = get_enhanced_detector()
print("LAA-Net available:", d.laa_available)
```

## Troubleshooting

- **"LAA-Net root not found"** – Ensure `external/laa_net` exists and contains `configs/`, `models/`, `package_utils/`. Or set `LAA_NET_ROOT`.
- **"LAA-Net weights file not found"** – Ensure a `.pth` file exists under `external/laa_net/weights/` or set `LAA_NET_WEIGHTS` to the full path.
- **Import errors** – Install LAA-Net deps (`pip install -r external/laa_net/requirements.txt`) and ensure the clone is the [10Ring/LAA-Net](https://github.com/10Ring/LAA-Net) layout (configs, models, package_utils).
- **Config not found** – The loader expects `configs/efn4_fpn_hm_adv.yaml` in the LAA-Net repo. Use an unmodified clone of 10Ring/LAA-Net.

When LAA-Net is available, the ensemble uses it automatically and reports it in logs as an active model.
