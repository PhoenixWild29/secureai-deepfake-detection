#!/usr/bin/env python3
"""Test Solana runtime functionality"""

import os
import json
import sys

print("Testing Solana runtime functionality...\n")

# Test imports
try:
    from solana.rpc.api import Client
    from solders.keypair import Keypair
    from solders.transaction import Transaction
    from solders.pubkey import Pubkey
    from solders.message import Message
    from solders.instruction import Instruction, AccountMeta
    print("✅ All imports successful\n")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 1: Create a test keypair
print("Test 1: Creating test keypair...")
try:
    test_keypair = Keypair()
    print(f"✅ Keypair created: {test_keypair.pubkey()}")
except Exception as e:
    print(f"❌ Keypair creation failed: {e}")

# Test 2: Load keypair from file (if exists)
print("\nTest 2: Loading keypair from file...")
wallet_path = os.getenv('SOLANA_WALLET_PATH', os.path.expanduser('~/.config/solana/id.json'))
if os.path.exists(wallet_path):
    try:
        with open(wallet_path, 'r') as f:
            keypair_data = json.load(f)
        print(f"✅ Wallet file found: {wallet_path}")
        print(f"   Data type: {type(keypair_data)}")
        print(f"   Data length: {len(keypair_data) if isinstance(keypair_data, (list, dict)) else 'N/A'}")
        
        # Try to load keypair
        if isinstance(keypair_data, list) and len(keypair_data) == 64:
            secret_key = bytes(keypair_data)
            loaded_keypair = Keypair.from_bytes(secret_key)
            print(f"✅ Keypair loaded successfully: {loaded_keypair.pubkey()}")
        else:
            print(f"⚠️  Unexpected keypair format: {type(keypair_data)}")
    except Exception as e:
        print(f"❌ Keypair loading failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"⚠️  Wallet file not found: {wallet_path}")

# Test 3: Create RPC client
print("\nTest 3: Creating RPC client...")
try:
    client = Client("https://api.devnet.solana.com")
    print("✅ RPC client created")
    
    # Test getting blockhash
    print("   Testing get_latest_blockhash...")
    blockhash_resp = client.get_latest_blockhash()
    if blockhash_resp.value:
        print(f"✅ Blockhash retrieved: {blockhash_resp.value.blockhash}")
    else:
        print("❌ Failed to get blockhash")
except Exception as e:
    print(f"❌ RPC client creation failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Create memo instruction
print("\nTest 4: Creating memo instruction...")
try:
    memo_program_id = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
    test_keypair = Keypair()
    memo_data = b"Test memo data"
    
    memo_instruction = Instruction(
        program_id=memo_program_id,
        accounts=[AccountMeta(pubkey=test_keypair.pubkey(), is_signer=True, is_writable=False)],
        data=list(memo_data)
    )
    print("✅ Memo instruction created")
except Exception as e:
    print(f"❌ Memo instruction creation failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Create transaction
print("\nTest 5: Creating transaction...")
try:
    test_keypair = Keypair()
    client = Client("https://api.devnet.solana.com")
    blockhash_resp = client.get_latest_blockhash()
    
    if blockhash_resp.value:
        recent_blockhash = blockhash_resp.value.blockhash
        memo_program_id = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
        memo_instruction = Instruction(
            program_id=memo_program_id,
            accounts=[AccountMeta(pubkey=test_keypair.pubkey(), is_signer=True, is_writable=False)],
            data=list(b"Test")
        )
        
        message = Message.new_with_blockhash(
            [memo_instruction],
            test_keypair.pubkey(),
            recent_blockhash
        )
        
        transaction = Transaction.new_unsigned(message)
        transaction.sign([test_keypair], recent_blockhash)
        
        print("✅ Transaction created and signed")
        print(f"   Transaction signature: {transaction.signatures[0] if transaction.signatures else 'None'}")
    else:
        print("❌ Could not get blockhash for transaction test")
except Exception as e:
    print(f"❌ Transaction creation failed: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ All runtime tests completed!")

