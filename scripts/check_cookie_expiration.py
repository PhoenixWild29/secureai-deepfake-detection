#!/usr/bin/env python3
"""
Check if X cookies file is expired or about to expire
Run this via cron to get alerts before cookies expire
"""

import os
import sys
from datetime import datetime, timedelta

COOKIES_FILE = os.getenv('X_COOKIES_FILE', '/app/secrets/x_cookies.txt')
WARNING_DAYS = 7  # Warn if cookies expire within 7 days

def check_cookie_expiration():
    """Check if cookies file exists and when it expires"""
    if not os.path.exists(COOKIES_FILE):
        print(f"❌ Cookies file not found: {COOKIES_FILE}")
        return False
    
    # Read cookies file and find expiration dates
    try:
        with open(COOKIES_FILE, 'r') as f:
            lines = f.readlines()
        
        # Parse Netscape cookie format
        # Format: domain	flag	path	secure	expiration	name	value
        now = datetime.now().timestamp()
        max_expiration = 0
        valid_cookies = 0
        expired_cookies = 0
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('\t')
            if len(parts) >= 5:
                try:
                    expiration = int(parts[4])
                    if expiration > 0:  # 0 means session cookie
                        max_expiration = max(max_expiration, expiration)
                        if expiration > now:
                            valid_cookies += 1
                        else:
                            expired_cookies += 1
                except (ValueError, IndexError):
                    continue
        
        if max_expiration == 0:
            print("⚠️  No expiration dates found in cookies file (may be session cookies)")
            return True
        
        expiration_date = datetime.fromtimestamp(max_expiration)
        days_until_expiry = (expiration_date - datetime.now()).days
        
        if days_until_expiry < 0:
            print(f"❌ Cookies EXPIRED {abs(days_until_expiry)} days ago!")
            print(f"   Expiration date: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Valid cookies: {valid_cookies}, Expired: {expired_cookies}")
            return False
        elif days_until_expiry <= WARNING_DAYS:
            print(f"⚠️  Cookies expire in {days_until_expiry} days!")
            print(f"   Expiration date: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Valid cookies: {valid_cookies}, Expired: {expired_cookies}")
            print(f"   Action: Re-export cookies from browser and upload to server")
            return False
        else:
            print(f"✅ Cookies valid for {days_until_expiry} more days")
            print(f"   Expiration date: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Valid cookies: {valid_cookies}")
            return True
            
    except Exception as e:
        print(f"❌ Error checking cookies: {e}")
        return False

if __name__ == '__main__':
    success = check_cookie_expiration()
    sys.exit(0 if success else 1)
