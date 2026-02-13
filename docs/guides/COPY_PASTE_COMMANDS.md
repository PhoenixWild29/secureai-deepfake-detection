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

## Push to GitHub + Server commands (after any code changes)

Use this sequence whenever you (or the assistant) make changes and you want them on GitHub and on the server.

### Step 1 – On your PC (PowerShell): push to GitHub master

Run from the project folder:

```powershell
cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
git add -A
git status
git commit -m "Describe your change here"
git push origin master
```

If `git status` shows nothing to commit, your changes are already committed; run `git push origin master` only.

### Step 2 – On the server (Bash): pull and rebuild backend + frontend

After the push succeeds, SSH to the server and run (use your real project path if different). Use **pull without submodules** so the broken submodule does not block the deploy:

```bash
cd /root/secureai-deepfake-detection
git pull origin master --no-recurse-submodules
cd secureai-guardian
npm ci
npm run build
cd ..
docker compose -f docker-compose.https.yml down
docker compose -f docker-compose.https.yml build --no-cache secureai-backend
docker compose -f docker-compose.https.yml up -d
```

- **`--no-recurse-submodules`** avoids the "No url found for submodule path 'external/laa_net'" error so the pull always succeeds.
- **Frontend:** `npm ci` and `npm run build` update `secureai-guardian/dist` so Nginx serves the latest UI.
- **Important:** Use `down` **without** `-v` so the database and results volumes are kept.

If you prefer to update submodules (and have fixed `.gitmodules`), you can run `git submodule update --init --recursive` after the pull; if it fails, use the block above without it.

---

## Verify ensemble is running (on the server)

After pulling and rebuilding, confirm the backend is up and the full ensemble is loaded.

### 1. Health check

```bash
curl -s http://localhost:8000/api/health
```

Expected: `{"status":"healthy","timestamp":"...","version":"2.0.0"}` (or similar). If you use Nginx in front, use your domain and path, e.g. `curl -s https://your-domain.com/api/health`.

### 2. Backend logs – ensemble loaded

```bash
docker logs secureai-backend 2>&1 | grep -E "Ensemble loaded|EnsembleDetector loaded|Ultimate EnsembleDetector"
```

You should see at least one of:

- `Ensemble loaded in worker; every scan will use the full ensemble.`
- `EnsembleDetector loaded successfully. Every scan will use the full ensemble.`
- `Ultimate EnsembleDetector initialized`

If the worker is still starting, wait 2–5 minutes (ensemble load is slow) and run the same `grep` again.

### 3. Optional: run one scan and check the response

From the SecureAI Guardian UI, run a single video scan. When it finishes, open the result and confirm the engine/method shows **Full Ensemble** or a method like **ultimate_ensemble_***. Alternatively, from the server (if you have a test video):

```bash
curl -s -X POST -F "file=@/path/to/short-video.mp4" http://localhost:8000/api/analyze | jq -r '.model_type, .result.method'
```

You should see the model type and a method string that indicates the ensemble (e.g. not `ensemble_unavailable`).

---

## Login flow — fast; models load on first scan

Workers **do not** load the detection ensemble at startup. Login and device authentication are **fast** (usually under a second). The ensemble loads **lazy** when the first **scan** is run.

### What happens on login

1. **Page load**  
   The app loads. If there is no saved identity in localStorage (e.g. after clearing cache), you see the **Login** screen.

2. **Auto device resolution**  
   The Login component immediately calls **`/api/identity/resolve`** with your device fingerprint (no button click). The worker is **ready immediately** (no model load at startup), so that request is a quick DB lookup (or new device + in-memory Solana wallet) — usually **under a second**.

3. **Existing device**  
   If the backend returns “existing device,” the app writes `nodeId`/alias/tier to localStorage and calls `onLogin()` → you go to the Dashboard. No “Provisioning ID” screen.

4. **New device**  
   If the backend returns “new device,” the app shows the **entry** screen (optional alias + “Initialize Neural Passport”). When you click the button, the app calls **`/api/identity/resolve`** again with your alias; that call is also fast (DB + wallet only). The “Provisioning ID” screen is just the short animation plus that one fast API call.

5. **After login**  
   Identity is stored in localStorage. Later visits use that stored identity and skip the resolve call, so you go straight to the Dashboard.

### When do models load?

| When | What happens |
|------|----------------|
| **Login / device auth** | No model load. Worker is ready; `/api/health` and `/api/identity/resolve` respond immediately. |
| **First scan (upload or URL)** | The worker loads the full ensemble (CLIP, ResNet, V13, etc.) on that request. The **first** analysis may take **2–5 minutes** (model load + run). Subsequent scans in the same worker are fast (model already in memory). |
| **After worker restart** | Again, login is fast; the next **first** scan in that worker triggers the 2–5 min load once. |

So: **login and device auth are fast. The only long wait (2–5 min) is the first scan after a worker start, when the ensemble loads on demand.**

---

## "Backend service unavailable" when running a scan

The Forensic Lab runs a **health check** (`GET /api/health`) before starting a scan. If that request fails or returns non‑OK, you see **"ANALYSIS ERROR – Backend service unavailable. Please ensure the API server is running."** So the issue is between the browser and the backend (or the backend not responding).

### Likely causes

1. **Backend container not running** – e.g. after a server reboot or failed deploy.
2. **Backend still starting** – container or worker not yet listening; health is answered as soon as the worker binds (models load on first scan, not at startup).
3. **Backend crashed** – OOM, exception during ensemble load, or worker restart.
4. **Nginx ↔ backend** – wrong proxy, backend host/port, or timeout.

### Commands to run on the server (Bash)

**1. Is the backend container up?**

```bash
docker ps --filter name=secureai-backend
```

If it’s missing or `Exited`, start the stack:

```bash
cd /root/secureai-deepfake-detection
docker compose -f docker-compose.https.yml up -d secureai-backend
```

**2. Can the backend answer health locally?**

```bash
docker exec secureai-backend curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health
```

Expect `200`. If you get nothing or 5xx, the app inside the container isn’t responding (still loading or crashed).

**3. Recent backend logs (crash / ensemble load):**

```bash
docker logs secureai-backend --tail 100 2>&1
```

Look for `Ensemble loaded in worker` (ready) or Python tracebacks / OOM (crashed).

**4. From your PC (optional) – does the public URL reach the API?**

```powershell
curl -s -o NUL -w "%{http_code}" https://guardian.secureai.dev/api/health
```

Expect `200`. If you get 502/503/504, Nginx is up but the backend isn’t responding or is timing out.

### Quick fix

If the container was down or restarted, start it and wait 2–5 minutes for the ensemble to load, then try the scan again. If the container is up but health still fails, use the logs (step 3) to see why the worker isn’t responding.

### Container "unhealthy" and curl to /api/health gives no response

If **command 2** (curl from inside the container) produces **no output**, the app inside the container is **not listening** on port 8000. That usually means the Gunicorn **worker never finished starting**: it blocks in **ensemble loading** (`post_worker_init`) until the full model is loaded. If that step hangs or crashes, the worker never accepts connections, so:

- The healthcheck fails → container shows **unhealthy**.
- `curl http://localhost:8000/api/health` gets no reply (connection refused or hang).

**Do this next:**

**A. See where startup stops (full logs from boot)**

```bash
docker logs secureai-backend 2>&1 | head -200
```

Look for, in order:

- `Starting SecureAI Guardian server...`
- `SecureAI Guardian server is ready. Spawning workers...`
- `Loading full ensemble...` and then either `Ensemble loaded in worker` (success) or a **traceback** / error (failure or hang).

If you see **"Loading full ensemble"** but never **"Ensemble loaded in worker"**, the worker is stuck or crashed during model load (e.g. OOM, missing file, or slow disk).

**B. Confirm nothing is listening on 8000**

```bash
docker exec secureai-backend sh -c "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null" | grep 8000
```

No output = nothing listening = worker never became ready.

**C. Restart and watch logs live**

```bash
cd /root/secureai-deepfake-detection
docker compose -f docker-compose.https.yml restart secureai-backend
docker logs -f secureai-backend 2>&1
```

Wait 5–10 minutes. You should see **"Ensemble loaded in worker"** and then the healthcheck will start passing. If after 10 minutes you still don’t see that line, note the **last message** (e.g. which model or step it’s on) and check disk space / memory:

```bash
df -h
free -m
```

**D. Healthcheck start period**

The compose file uses **start_period: 600s** (10 minutes) for the backend so Docker doesn’t mark the container unhealthy during the 2–5 minute ensemble load. After a deploy, give the backend at least 5 minutes before treating "unhealthy" as a real failure.

### Restart loop: same logs repeating, port 8000 never listens

If you see the **same initialization block** (ResNet, Jetson, S3, etc.) **repeating** every minute or so and **nothing ever listens on port 8000**, the worker is almost certainly **crash‑looping**: it starts loading the ensemble, then the process is **killed** (often by the Linux **OOM killer** when RAM is too low), and Gunicorn respawns it, so the cycle repeats.

**1. Confirm restart loop and OOM**

```bash
docker inspect secureai-backend --format 'RestartCount: {{.RestartCount}} ExitCode: {{.State.ExitCode}}'
dmesg | tail -50 | grep -i "out of memory\|oom\|killed process"
```

If **RestartCount** is increasing and you see OOM messages, the server is running out of memory during ensemble load.

**2. Check memory**

```bash
free -m
```

The full ensemble (CLIP, ResNet, V13, EfficientNet, etc.) can use **4–6+ GB** RAM. A **2 vCPU / 4 GB** droplet is often **too small**; the worker gets OOM‑killed and never reaches “Ensemble loaded in worker”.

**3. Add swap (recommended on 4 GB instances)**

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -m
```

Then restart the backend and watch logs again; the worker may complete ensemble load with swap.

**4. After code fix: look for new log lines**

After updating the repo, you should see in logs:

- **"Worker starting: loading full ensemble..."** — worker entered `post_worker_init`.
- Then either **"Ensemble loaded in worker"** (success) or **"Worker init complete; binding to socket"** (ensemble failed but worker still starts; scans will 503).
- If you see **"Worker starting"** but **never** "Worker init complete" or "Ensemble loaded", the process is being killed (e.g. OOM) during model load. Add swap or use a larger instance (e.g. 8 GB RAM).

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

**If the build fails with "no space left on device":** Free disk space on the server (e.g. `docker system prune -a`, remove old images, clear `uploads/` or `results/` if acceptable), then rebuild. The repo’s `.dockerignore` excludes `uploads/`, `results/`, and large files so the build context stays small.

---

## 9. Data persistence (Docker): keep DB and results across reloads

The Security Hub dashboard (Neutralized, Proofs, Total Analyses, etc.) reads from the **backend**: Postgres DB and the **results** folder. To keep those numbers across rebuilds/restarts:

### 1. Persist the database

Postgres already uses a **named volume** `postgres_data` in `docker-compose.https.yml`, `docker-compose.quick.yml`, and `docker-compose.prod.yml`. Data is kept as long as you **do not** remove volumes.

**Commands (on the server, Bash):**

```bash
# Stop and remove containers but KEEP volumes (DB and results stay)
docker compose -f docker-compose.https.yml down
# Then rebuild/start as usual:
docker compose -f docker-compose.https.yml build --no-cache secureai-backend
docker compose -f docker-compose.https.yml up -d
```

**Do NOT run** `docker compose down -v` if you want to keep data. The `-v` flag deletes named volumes (`postgres_data`, `results_data`), so the DB and result JSONs would be wiped.

### 2. Persist the results folder

The compose files use a **named volume** `results_data` for `/app/results`, so result JSONs survive container restarts and rebuilds. No extra host directory is required.

### 3. Repopulate after a one-time reset

If you already ran `down -v` once and the hub shows 0:

- Run new scans from the app. Each scan is stored in the current DB and in the results volume.
- The hub will show the new totals after each scan (and after a short delay when the dashboard fetches `/api/dashboard/stats`).

**Quick reference:**

| Goal | Command |
|------|--------|
| Rebuild backend but **keep** DB and results | `docker compose -f docker-compose.https.yml down` then `build` and `up -d` (no `-v`) |
| Full wipe (new DB, empty results) | `docker compose -f docker-compose.https.yml down -v` then `up -d` |

For **production**: analyses and device data are **never auto-deleted** by default. See **DATA_RETENTION_AND_PRODUCTION_DB.md** for the full policy and opt-in retention.

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
