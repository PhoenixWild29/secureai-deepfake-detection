# Copy-paste commands (PowerShell)

Use this page whenever you need to run project commands. **Always run in PowerShell** and **start in the project folder** unless a section says otherwise.

---

## Step-by-step: How to run the app

**Two places you can run things:**

| Where | When to use it |
|-------|----------------|
| **PowerShell (your PC)** | Developing, testing, running the API **locally**, running diagnostics. |
| **Server console (e.g. DigitalOcean)** | Running the app in **production** (after you deploy with Docker). |

You **don’t** switch from PowerShell to the server in the middle of one run. You either run everything **locally in PowerShell** or everything **on the server** (SSH in, then use Bash there).

---

### Path A – Run locally (your PC, PowerShell)

Do this when you want to test or run the API on your machine.

**One-time (if you haven’t already):**

1. Open **PowerShell**.
2. Go to the project folder and activate the venv (sections 1 and 2 below).
3. Optionally do the **Best-in-class setup** (HF_TOKEN, MTCNN, LAA_NET_WEIGHTS) and run the diagnostic once (section 3).

**Every time you want to run the API locally:**

1. Open **PowerShell**.
2. Copy-paste and run in order:
   - Section **1** (go to project folder).
   - Section **2** (activate venv).
   - Optional: set **LAA_NET_WEIGHTS** and **HF_TOKEN** (section 4 and Best-in-class) if you want full models.
3. Start the API (section **6** – e.g. `python -m api.app`).
4. Use the app in the browser (e.g. http://localhost:5000 or whatever port the API uses).

All of that stays in **PowerShell**; you don’t move to the server.

---

### Path B – Run on the server (production)

Do this when the app is deployed (e.g. Docker on DigitalOcean) and you want to update or check it.

1. **Connect to the server** (e.g. SSH):
   - Example: `ssh root@guardian.secureai.dev` or `ssh root@your-server-ip` (use your real host and user).
2. On the server you’re in a **Linux/Bash** console (not PowerShell).
3. Go to the project directory. The path used in this project’s deployment/HTTPS docs is **`/root/secureai-deepfake-detection`** (if you use `/opt/secureai-deepfake-detection`, use that instead):
   ```bash
   cd /root/secureai-deepfake-detection
   ```
4. Pull latest code and rebuild/restart (section **8** – `git pull`, then `docker compose ...`).

So: **PowerShell = local**. **Server console (SSH) = production.** Pick one path per run.

---

## 1. Open PowerShell and go to the project folder

1. Press **Win + X** → choose **Windows PowerShell** (or **Terminal**).
2. Copy and paste this line, then press **Enter**:

```powershell
cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
```

3. Confirm you’re in the right place (optional):

```powershell
dir
```

You should see folders like `ai_model`, `api`, `external`, `scripts`, etc.

---

## Best-in-class setup (one-time, for best deepfake detection)

Do this once to enable **HF_TOKEN** (reliable CLIP downloads, higher rate limits) and **MTCNN** (best face detection). Run in **PowerShell** from the project folder.

**Step 1 – Go to project folder and activate venv**

```powershell
cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
.venv\Scripts\Activate.ps1
```

**Step 2 – Set your Hugging Face token (get one at https://huggingface.co/settings/tokens, “Read” access)**

Replace `your_hugging_face_token_here` with your real token, then paste:

```powershell
$env:HF_TOKEN = "your_hugging_face_token_here"
```

To make it permanent for your user account (optional):  
`[System.Environment]::SetEnvironmentVariable('HF_TOKEN', 'your_hugging_face_token_here', 'User')`

**Step 3 – Install MTCNN for best face detection (needs TensorFlow)**

MTCNN requires TensorFlow. Use the `[tensorflow]` extra so it installs correctly:

```powershell
pip install "mtcnn[tensorflow]"
```

If you only ran `pip install mtcnn` before, run the line above; the diagnostic will then show **✔ MTCNN available**.  
To install all project dependencies (then MTCNN may still need the line above if TensorFlow isn’t in requirements):

```powershell
pip install -r requirements.txt
pip install "mtcnn[tensorflow]"
```

**Step 4 – Set LAA-Net weights for this session (pick one)**

```powershell
$env:LAA_NET_WEIGHTS = "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\external\laa_net\weights\PoseEfficientNet_EFN_hm10_EFPN_NoBasedCLS_Focal_C3_256Cst100_8SBI_SAM(Adam)_ADV_Era1_OutSigmoid_1e7_boost500_UnFZ_model_best.pth"
```

**Step 5 – Verify everything (Success checklist)**

```powershell
$env:PYTHONIOENCODING = "utf-8"
python scripts\diagnostic\CHECK_MODEL_STATUS.py
```

You should see: **CLIP ✔**, **ResNet50 ✔**, **LAA-Net ✔**, **MTCNN ✔** (or Haar fallback), **Ensemble active with: CLIP, ResNet50, LAA-Net**. When you start the API in the same session, you should see in the logs: **Using Hugging Face token for CLIP** and **MTCNN face detection initialized successfully** (if MTCNN installed correctly).

---

## 2. Activate the virtual environment (when running Python locally)

Run this **after** the `cd` in section 1:

```powershell
.venv\Scripts\Activate.ps1
```

Your prompt should start with `(.venv)`.

---

## 3. Check model status (CLIP, ResNet50, LAA-Net)

**Where:** Project folder. **After:** section 1 and 2 (venv activated).

To avoid Windows console Unicode errors with emojis, set UTF-8 then run the script:

```powershell
$env:PYTHONIOENCODING = "utf-8"
python scripts\diagnostic\CHECK_MODEL_STATUS.py
```

---

## 4. Set LAA-Net weights (optional, for detection)

If you want the app to use LAA-Net, set the weights path. Run **after** the `cd` in section 1 (same PowerShell session or new one).

**Option A – temporary (this session only):**

```powershell
$env:LAA_NET_WEIGHTS = "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\external\laa_net\weights\PoseEfficientNet_EFN_hm10_EFPN_NoBasedCLS_Focal_C3_256Cst100_8SBI_SAM(Adam)_ADV_Era1_OutSigmoid_1e7_boost500_UnFZ_model_best.pth"
```

**Option B – use the other weights file:**

```powershell
$env:LAA_NET_WEIGHTS = "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\external\laa_net\weights\PoseEfficientNet_EFN_hm100_EFPN_NoBasedCLS_Focal_C3_256Cstency100_32BI_SAM(Adam)_ADV_Erasing1_OutSigmoid_model_best.pth"
```

Then start your API or run your detection script in the **same** PowerShell window.

---

## 5. Quick test that LAA-Net loads (Python one-liner)

**Where:** Project folder. **After:** section 1 and 2 (venv activated).

```powershell
python -c "import sys; sys.path.insert(0, '.'); from ai_model.laa_net_loader import load_laa_net; from pathlib import Path; w = next(Path('external/laa_net/weights').glob('*.pth')); m, p, d = load_laa_net(weights_path=str(w)); print('LAA-Net loaded:', m is not None)"
```

You should see: `LAA-Net loaded: True`.

---

## 6. Run the API (Flask) locally

**Where:** Project folder. **After:** section 1 and 2 (venv activated).

```powershell
python -m api.app
```

Or, if you use a run script:

```powershell
python run_api.py
```

(Use whichever file you normally use to start the API.)

---

## Deploy workflow: push from your PC, then update the server

Use this **every time you (or the AI) change code** and you want GitHub updated and the server running the latest version.

### Step 1 – On your PC (PowerShell): commit and push to GitHub

Run these in **PowerShell** from the project folder. Replace the commit message with a short description of what changed.

```powershell
cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
git status
git add -A
git commit -m "Your commit message here (e.g. Add audio pipeline for vocal authenticity)"
git push origin master
```

If `git push` asks for credentials, use your GitHub username and a **Personal Access Token** (not your GitHub password). If you use SSH, `git push` may use your SSH key automatically.

### Step 2 – On the server (Bash): pull and rebuild

SSH into the server, then run:

```bash
cd /root/secureai-deepfake-detection
git pull origin master
git submodule update --init --recursive
docker compose -f docker-compose.https.yml build --no-cache secureai-backend
docker compose -f docker-compose.https.yml up -d secureai-backend
```

**Important:** You must **rebuild** the backend image (`build --no-cache secureai-backend`) after pulling code changes. Restarting the container without rebuilding keeps the old code inside the image. If you only run `up -d` without `build`, the server will still run the previous version.

(If your server project path is different, e.g. `/opt/secureai-deepfake-detection`, use that instead of `/root/secureai-deepfake-detection`.)

That’s the full flow: **local push** → **server pull + rebuild**.

---

## 7. Git: pull latest code

**Where:** Project folder. **After:** section 1 (no need to activate venv).

```powershell
git pull origin master
```

---

## 8. Server (e.g. DigitalOcean): pull and rebuild backend

**Where:** On the server, in the project directory (e.g. after `ssh` in). Run in **Bash**, not PowerShell.

Typical server project path (used in this project’s deployment and HTTPS docs): **`/root/secureai-deepfake-detection`**. If your deploy uses a different path (e.g. `/opt/secureai-deepfake-detection`), use that instead.

```bash
cd /root/secureai-deepfake-detection
git pull origin master
git submodule update --init --recursive
docker compose -f docker-compose.https.yml build --no-cache secureai-backend
docker compose -f docker-compose.https.yml up -d secureai-backend
```

**Note:** Use `build --no-cache secureai-backend` so the container gets the latest code. Without a rebuild, the old image (and old code) keeps running.

---

## Success checklist (what to expect when everything works)

After running the model status script (section 3), you should see something like this. Use it to confirm the stack is healthy.

| Check | Expected result |
|-------|-----------------|
| **CLIP** | ✔ CLIP model available (pretrained, zero-shot) |
| **ResNet50** | ✔ Found model file: ai_model/resnet_resnet50_final.pth, Parameters: 23,565,303, Has classifier head: True |
| **LAA-Net** | ✔ LAA-Net available (and "Constructing the heatmap Decoder!" may appear) |
| **MTCNN** | Either ✔ MTCNN available, or ▲ MTCNN not available, using OpenCV Haar cascades (both OK) |
| **Ensemble** | ✔ Ensemble active with: CLIP, ResNet50, LAA-Net |

The script also prints a JSON summary at the end. Confirm:

- `"clip": { "status": "✅ Available" }`
- `"resnet50": { "status": "✅ Available" }`
- `"laa_net": { "status": "✅ Available" }`
- `"ensemble": { "status": "✅ Active", "details": { "models": ["CLIP", "ResNet50", "LAA-Net"] } }`

If all of the above match, your setup is correct.

---

## Optional: HF_TOKEN and MTCNN (do they improve the model?)

**To enable both for best-in-class detection,** use the **Best-in-class setup** section above (one-time steps with copy-paste commands). Below is the “why” and minimal commands if you only want one.

### HF_TOKEN (Hugging Face token)

- **What it does:** Lets you send *authenticated* requests to the Hugging Face Hub when loading CLIP. You get higher rate limits and more reliable downloads.
- **Does it make the model better?** **No.** Same CLIP model, same accuracy. It only affects *how* you download it (fewer rate-limit errors, faster if you hit limits).
- **Should you set it?** Optional. Set it if you often load CLIP or see "unauthenticated requests" / rate-limit warnings. Not required for normal use.

**How to set (PowerShell, this session only):**

```powershell
$env:HF_TOKEN = "your_hugging_face_token_here"
```

Get a token at: https://huggingface.co/settings/tokens (create with "Read" access).

---

### MTCNN (face detection)

- **What it does:** MTCNN is a more accurate face detector than OpenCV's Haar cascades. The pipeline *already supports both*: it tries MTCNN first, then falls back to Haar.
- **Does it make the model better?** **It can.** Better face boxes → better cropped regions → potentially better inputs to CLIP/ResNet50/LAA-Net when the pipeline uses face crops. Most noticeable with non-frontal faces, small faces, or difficult lighting.
- **Should you install it?** Optional. Install if you want the best face-detection quality and are OK with the extra dependency (the `mtcnn` package pulls in TensorFlow, which is heavier than OpenCV alone).

**How to enable MTCNN (PowerShell, project folder, venv activated):**

```powershell
pip install "mtcnn>=0.1.1"
```

Then run the model status script again (section 3). You should see **✔ MTCNN available** instead of the Haar fallback message. No code changes needed; the detector already uses MTCNN when available.

---

### Summary

| Option | Improves model accuracy? | Recommendation |
|--------|---------------------------|----------------|
| **HF_TOKEN** | No (same model, better download/rate limits) | Set only if you hit rate limits or want faster/reliable CLIP downloads. |
| **MTCNN** | Can help (better face detection → better crops → better inputs) | Install if you want the best face-detection quality and accept the TensorFlow dependency. |

---

## Troubleshooting: MTCNN install fails (Windows “path too long”)

If `pip install "mtcnn[tensorflow]"` fails with **OSError: [Errno 2] No such file or directory** and a very long path, Windows is hitting the **260-character path limit**. Your project path plus TensorFlow’s deep folders go over that limit. **Use Option C (short-path venv) for a guaranteed fix.**

### Option A – Enable long paths (try first; may need restart)

1. **Open PowerShell as Administrator:** Right-click **Start** → **Windows PowerShell (Admin)** or **Terminal (Admin)**.
2. Run this once (copy-paste the whole line):

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

3. **Restart your PC** (needed for the setting to apply).
4. After restart, in a new PowerShell:

```powershell
cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
.venv\Scripts\Activate.ps1
pip install "mtcnn[tensorflow]"
```

5. To confirm long paths are on (in Admin PowerShell):  
   `Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled`  
   You should see `LongPathsEnabled : 1`. If not, use **Option C**.

### Option C – Short-path venv (guaranteed fix; no restart)

Put the virtual environment in a **short path** so TensorFlow never hits the limit. Your **project stays where it is**; you just use a venv at e.g. `C:\SA-venv`.

**Step 1 – Create the venv (run in PowerShell):**

```powershell
python -m venv C:\SA-venv
```

**Step 2 – Activate it, go to project, install everything including MTCNN:**

```powershell
C:\SA-venv\Scripts\Activate.ps1
cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
pip install --upgrade pip
pip install -r requirements.txt
pip install "mtcnn[tensorflow]"
```

**Step 3 – From now on, use this venv for the project.** Activate `C:\SA-venv` (not `.venv`), then run your commands from the project folder:

```powershell
cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
C:\SA-venv\Scripts\Activate.ps1
$env:PYTHONIOENCODING = "utf-8"
python scripts\diagnostic\CHECK_MODEL_STATUS.py
```

You should see **✔ MTCNN available**. To run the API: same `cd` and activate, then `python -m api.app`.  
In Cursor/VS Code you can select the interpreter `C:\SA-venv\Scripts\python.exe` so the IDE uses this venv.

### Option B – Keep using OpenCV Haar (no TensorFlow)

You can skip MTCNN and keep using the OpenCV Haar cascades. The app and ensemble (CLIP, ResNet50, LAA-Net) work the same; only face-detection quality may be slightly lower in some cases. No extra steps; the diagnostic will show “MTCNN not available, using OpenCV Haar cascades” and that’s OK.

---

## Summary checklist

| Step | What to do |
|------|------------|
| 1 | Open PowerShell, `cd` to project folder (section 1). |
| 2 | For Python/API: run section 2 to activate `.venv`. |
| 3 | For model check: run section 3. |
| 4 | For LAA-Net: set `LAA_NET_WEIGHTS` (section 4) in the same session before starting the API. |
| 5 | For API: run section 6. |

All commands above are meant to be **copied and pasted** as-is (except where you must replace a path). Run them in **PowerShell** on your PC unless the section says “on the server” or “Bash”.
