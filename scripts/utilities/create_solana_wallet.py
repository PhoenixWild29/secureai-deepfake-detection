#!/usr/bin/env python3
"""Create a Solana wallet using Python (no CLI needed)"""

import os
import json
from solders.keypair import Keypair

def create_wallet(wallet_path: str):
    """Create a new Solana wallet and save it to a file"""
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(wallet_path), exist_ok=True)
    
    # Generate new keypair
    print("🔑 Generating new Solana keypair...")
    keypair = Keypair()
    
    # Get the secret key as a list (Solana wallet format)
    secret_key = list(keypair.secret())
    
    # Save to file in Solana wallet format
    with open(wallet_path, 'w') as f:
        json.dump(secret_key, f)
    
    print(f"✅ Wallet created successfully!")
    print(f"   Location: {wallet_path}")
    print(f"   Public Key: {keypair.pubkey()}")
    print(f"\n⚠️  IMPORTANT: Keep this wallet file secure!")
    print(f"   Never commit it to Git or share it publicly.")
    
    return keypair.pubkey()

if __name__ == "__main__":
    # Default wallet path
    wallet_path = os.getenv('SOLANA_WALLET_PATH', '/app/wallet/id.json')
    
    # If running from command line, allow custom path
    if len(os.sys.argv) > 1:
        wallet_path = os.sys.argv[1]
    
    try:
        pubkey = create_wallet(wallet_path)
        print(f"\n✅ Wallet ready! Public address: {pubkey}")
        print(f"\nNext steps:")
        print(f"1. Fund this wallet on devnet: https://faucet.solana.com/")
        print(f"2. Or use: solana airdrop 1 <address> (if you have Solana CLI)")
        print(f"3. Update your .env file with: SOLANA_WALLET_PATH={wallet_path}")
    except Exception as e:
        print(f"❌ Error creating wallet: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

