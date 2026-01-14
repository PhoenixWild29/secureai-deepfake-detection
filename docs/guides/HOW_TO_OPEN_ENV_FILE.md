# How to Open .env File

## Location

The `.env` file is located in the **project root directory**:

```
C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\.env
```

---

## Method 1: Using File Explorer (Easiest)

1. **Open File Explorer** (Windows Key + E)
2. **Navigate to**:
   ```
   C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection
   ```
3. **Look for** `.env` file (it might be hidden - see below)
4. **Right-click** → **Open with** → **Notepad** (or your preferred text editor)

**Note:** If you don't see `.env`, it might be hidden. In File Explorer:
- Click **View** tab
- Check **"Hidden items"** ✓
- Or press **Alt + V** → **H**

---

## Method 2: Using VS Code / Cursor

1. **Open VS Code or Cursor**
2. **File** → **Open Folder**
3. Navigate to: `C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection`
4. **Click on** `.env` file in the file explorer sidebar
5. If it doesn't exist, **right-click** in the folder → **New File** → Name it `.env`

---

## Method 3: Using Command Line

1. **Open Command Prompt** or **PowerShell**
2. **Navigate to project**:
   ```bash
   cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
   ```
3. **Open with Notepad**:
   ```bash
   notepad .env
   ```
   Or if it doesn't exist, this will create it.

---

## Method 4: Direct Path

1. Press **Windows Key + R**
2. Type:
   ```
   notepad "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\.env"
   ```
3. Press **Enter**

---

## If .env File Doesn't Exist

If the file doesn't exist, **create it**:

1. Open any text editor (Notepad, VS Code, etc.)
2. **Save As** → Name it `.env` (with the dot at the beginning)
3. **Save location**: `C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection`
4. **File type**: All Files (not .txt)

---

## What to Add

Once you have the `.env` file open, add these lines:

```bash
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_DEFAULT_REGION=us-east-2
S3_BUCKET_NAME=secureai-deepfake-videos
S3_RESULTS_BUCKET_NAME=secureai-deepfake-results
```

**Replace:**
- `your_access_key_id_here` with your Access Key ID from the CSV
- `your_secret_access_key_here` with your Secret Access Key from the CSV
- `us-east-2` is your region (US East Ohio)
- Bucket names are already filled in based on your notes

---

## Quick Tip

The easiest way is probably **Method 3** (Command Prompt):
```bash
cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
notepad .env
```

This will open it in Notepad, or create it if it doesn't exist!

