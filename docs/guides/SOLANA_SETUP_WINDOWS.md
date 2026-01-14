# Solana Setup Guide for Windows (PowerShell)

This is a detailed, step-by-step guide for setting up Solana blockchain integration on Windows.

## Prerequisites

- Windows 10/11
- PowerShell (comes with Windows)
- Internet connection

---

## Step 1: Download Solana CLI

### Option A: Using PowerShell (Recommended)

1. **Open PowerShell as Administrator:**
   - Press `Windows Key + X`
   - Select "Windows PowerShell (Admin)" or "Terminal (Admin)"
   - Click "Yes" when prompted by User Account Control

2. **Download Solana Installer:**
   ```powershell
   # Navigate to your Downloads folder (or any folder you prefer)
   cd $HOME\Downloads
   
   # Download the latest Solana release for Windows
   Invoke-WebRequest -Uri "https://github.com/solana-labs/solana/releases/latest/download/solana-install-init-x86_64-pc-windows-msvc.exe" -OutFile "solana-install.exe"
   ```

### Option B: Manual Download

1. Go to: https://github.com/solana-labs/solana/releases/latest
2. Download: `solana-install-init-x86_64-pc-windows-msvc.exe`
3. Save it to your Downloads folder

---

## Step 2: Install Solana CLI

1. **Run the installer:**
   ```powershell
   # If you downloaded it, navigate to Downloads
   cd $HOME\Downloads
   
   # Run the installer
   .\solana-install.exe
   ```
;
2. **Follow the installer prompts:**
   - It will ask for installation directory (default is fine)
   - It will ask if you want to add to PATH (say Yes)
   - Wait for installation to complete

3. **Verify installation:**
   ```powershell
   # Close and reopen PowerShell, then check version
   solana --version
   ```
   
   You should see something like: `solana-cli 1.18.x` or similar

4. **If `solana` command not found:**
   - Close PowerShell completely
   - Reopen PowerShell as Administrator
   - The installer should have added Solana to your PATH
   - If still not found, manually add to PATH:
     ```powershell
     # Find where Solana was installed (usually):
     # C:\Users\YourUsername\.local\share\solana\install\active_release\bin
     
     # Add to PATH temporarily (this session only):
     $env:Path += ";C:\Users\$env:USERNAME\.local\share\solana\install\active_release\bin"
     
     # Or add permanently:
     [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Users\$env:USERNAME\.local\share\solana\install\active_release\bin", "User")
     ```

---

## Step 3: Create Solana Wallet

1. **Open PowerShell** (regular, not admin is fine for wallet creation)

2. **Navigate to your project folder** (optional, but organized):
   ```powershell
   cd "C:\Users\$env:USERNAME\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
   ```

3. **Create the Solana config directory:**
   ```powershell
   # Create the directory if it doesn't exist
   New-Item -ItemType Directory -Force -Path "$HOME\.config\solana"
   ```

4. **Create a new wallet:**
   ```powershell
   # Create new keypair for devnet (testing)
   solana-keygen new --outfile "$HOME\.config\solana\id.json"
   ```

5. **Follow the prompts:**
   - It will ask for a passphrase (optional, but recommended)
   - Press Enter to skip passphrase, or type one and remember it
   - **IMPORTANT:** Save the seed phrase it shows you! Write it down securely.
   - Press Enter to continue

6. **Verify wallet was created:**
   ```powershell
   # Check your wallet address
   solana address
   ```
   
   You should see a long string like: `7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU`

7. **Check wallet file exists:**
   ```powershell
   # Verify the file exists
   Test-Path "$HOME\.config\solana\id.json"
   ```
   
   Should return: `True`

---

## Step 4: Configure Solana Network

1. **Set to Devnet (Free Testing Network):**
   ```powershell
   solana config set --url https://api.devnet.solana.com
   ```

2. **Verify configuration:**
   ```powershell
   solana config get
   ```
   
   You should see:
   ```
   Config File: C:\Users\YourUsername\config\solana\cli\config.yml
   RPC URL: https://api.devnet.solana.com
   WebSocket URL: wss://api.devnet.solana.com (computed)
   Keypair Path: C:\Users\YourUsername\.config\solana\id.json
   ```

---

## Step 5: Fund Your Wallet (Devnet Only)

**Important:** This only works on devnet (test network). Mainnet requires real SOL.

1. **Get free devnet SOL:**
   ```powershell
   # Request airdrop (free test SOL)
   solana airdrop 1
   ```
   
   If successful, you'll see: `1 SOL`

2. **Check your balance:**
   ```powershell
   solana balance
   ```
   
   Should show: `1 SOL` (or whatever amount you airdropped)

3. **If airdrop fails:**
   - Wait a few minutes and try again
   - Devnet faucet has rate limits
   - You can also use: https://faucet.solana.com/ (web interface)

---

## Step 6: Update Your Application .env File

1. **Navigate to your project folder:**
   ```powershell
   cd "C:\Users\$env:USERNAME\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
   ```

2. **Open or create `.env` file:**
   ```powershell
   # If file doesn't exist, create it
   if (-not (Test-Path ".env")) {
       New-Item -ItemType File -Path ".env"
   }
   
   # Open in notepad (or use your preferred editor)
   notepad .env
   ```

3. **Add these lines to your `.env` file:**
   ```env
   # Solana Configuration
   SOLANA_NETWORK=devnet
   SOLANA_WALLET_PATH=C:\Users\YOUR_USERNAME\.config\solana\id.json
   ```
   
   **Replace `YOUR_USERNAME` with your actual Windows username!**
   
   To find your username:
   ```powershell
   $env:USERNAME
   ```

4. **Save and close the file**

---

## Step 7: Verify Everything Works

1. **Test Solana CLI:**
   ```powershell
   # Check version
   solana --version
   
   # Check config
   solana config get
   
   # Check wallet address
   solana address
   
   # Check balance
   solana balance
   ```

2. **Test wallet file exists:**
   ```powershell
   Test-Path "$HOME\.config\solana\id.json"
   ```

3. **Verify .env file:**
   ```powershell
   # Check if .env has Solana config
   Select-String -Path ".env" -Pattern "SOLANA"
   ```

---

## Step 8: Update Docker Container (On Your Server)

**On your cloud server** (not Windows), you'll need to:

1. **Pull latest code:**
   ```bash
   cd ~/secureai-deepfake-detection
   git pull origin master
   ```

2. **Rebuild backend container:**
   ```bash
   docker compose -f docker-compose.https.yml down
   docker compose -f docker-compose.https.yml build --no-cache secureai-backend
   docker compose -f docker-compose.https.yml up -d
   ```

3. **Copy wallet to server (if needed):**
   - **Option A:** Create wallet on server (recommended for production)
   - **Option B:** Copy wallet file from Windows to server (use SCP or similar)
   - **Option C:** Use environment variable for wallet path on server

---

## Troubleshooting

### "solana: command not found"
- Close and reopen PowerShell
- Check PATH: `$env:Path -split ';' | Select-String "solana"`
- Manually add to PATH (see Step 2)

### "Failed to get recent blockhash"
- Check internet connection
- Verify network URL: `solana config get`
- Try switching networks: `solana config set --url https://api.devnet.solana.com`

### "Wallet not found"
- Check path: `Test-Path "$HOME\.config\solana\id.json"`
- Verify .env file has correct path
- Use absolute path in .env (not `~`)

### "Insufficient funds"
- Request airdrop: `solana airdrop 1`
- Check balance: `solana balance`
- Use devnet faucet: https://faucet.solana.com/

---

## Quick Reference Commands

```powershell
# Check Solana version
solana --version

# Check configuration
solana config get

# Check wallet address
solana address

# Check balance
solana balance

# Request devnet SOL
solana airdrop 1

# Set network
solana config set --url https://api.devnet.solana.com

# View transaction history (if you have explorer URL)
# Go to: https://explorer.solana.com/?cluster=devnet
```

---

## Security Notes

⚠️ **IMPORTANT:**
- **Never commit your wallet file to Git!**
- Keep your private key secure
- Use devnet for testing, mainnet only for production
- Consider using a separate wallet for the application
- Store your seed phrase securely (password manager, safe, etc.)

---

## Next Steps

Once setup is complete:
1. ✅ Solana CLI installed
2. ✅ Wallet created
3. ✅ Network configured (devnet)
4. ✅ Wallet funded
5. ✅ .env file updated
6. ✅ Backend container rebuilt

Your application will now:
- Use MTCNN for face detection
- Submit real transactions to Solana blockchain
- Store analysis data on-chain
- Return verifiable transaction signatures

Test by running an analysis and checking the logs for Solana transaction signatures!

