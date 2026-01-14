# Solana Blockchain Setup Guide

This guide will help you set up real Solana blockchain integration for SecureAI Guardian.

## Prerequisites

1. **Solana CLI** (optional, for wallet management)
2. **Solana Wallet** (keypair file)
3. **Network Selection** (devnet for testing, mainnet for production)

## Step 1: Install Solana CLI (Optional but Recommended)

### On Linux/Mac:
```bash
sh -c "$(curl -sSfL https://release.solana.com/stable/install)"
export PATH="$HOME/.local/share/solana/install/active_release/bin:$PATH"
```

### On Windows:
Download from: https://github.com/solana-labs/solana/releases

## Step 2: Create or Use Existing Wallet

### Option A: Create New Wallet (Recommended for Devnet)
```bash
solana-keygen new --outfile ~/.config/solana/id.json
```

### Option B: Use Existing Wallet
If you already have a Solana wallet, copy it to:
```
~/.config/solana/id.json
```

Or set the path in your `.env` file:
```
SOLANA_WALLET_PATH=/path/to/your/wallet.json
```

## Step 3: Configure Network

### For Development (Devnet - Free):
```bash
solana config set --url https://api.devnet.solana.com
```

### For Production (Mainnet - Costs SOL):
```bash
solana config set --url https://api.mainnet-beta.solana.com
```

Or set in your `.env` file:
```
SOLANA_NETWORK=devnet
```

## Step 4: Fund Your Wallet (Devnet Only)

For devnet, you can get free SOL from the faucet:
```bash
solana airdrop 1
```

**Note:** Mainnet requires real SOL. Never use mainnet for testing!

## Step 5: Verify Setup

Check your wallet balance:
```bash
solana balance
```

Check your wallet address:
```bash
solana address
```

## Step 6: Update Environment Variables

Add to your `.env` file:
```bash
# Solana Configuration
SOLANA_NETWORK=devnet
SOLANA_WALLET_PATH=~/.config/solana/id.json
```

## Step 7: Test Blockchain Integration

After setting up, the backend will automatically:
1. ✅ Detect Solana libraries
2. ✅ Load your wallet
3. ✅ Submit real transactions to Solana
4. ✅ Return real transaction signatures

## Troubleshooting

### "Solana wallet not found"
- Check that `SOLANA_WALLET_PATH` is correct
- Ensure the wallet file exists and is readable
- Default location: `~/.config/solana/id.json`

### "Failed to get recent blockhash"
- Check your internet connection
- Verify the RPC URL is correct for your network
- Try switching networks (devnet/testnet)

### "Transaction failed"
- Ensure your wallet has SOL (for mainnet) or devnet SOL (for devnet)
- Check transaction fees are sufficient
- Verify network connectivity

## Security Notes

⚠️ **IMPORTANT:**
- Never commit your wallet file to Git
- Keep your private key secure
- Use devnet for testing, mainnet only for production
- Consider using a separate wallet for the application

## Next Steps

Once set up, blockchain submissions will:
- Create real transactions on Solana
- Store analysis data in transaction memos
- Return verifiable transaction signatures
- Be viewable on Solana Explorer

Example transaction URL:
```
https://explorer.solana.com/tx/YOUR_SIGNATURE?cluster=devnet
```

