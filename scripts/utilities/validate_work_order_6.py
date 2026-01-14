#!/usr/bin/env python3
"""
Simple validation script for Work Order #6
"""

import os

def main():
    print("🔍 Validating Work Order #6 Implementation...")
    
    # Check key files
    files_to_check = [
        "src/components/UploadValidationFeedback/UploadValidationFeedback.tsx",
        "src/components/UploadValidationFeedback/UploadValidationFeedback.module.css",
        "src/utils/uploadValidationUtils.ts",
        "src/constants/uploadConstants.ts",
        "src/types/upload.d.ts",
        "src/components/ProgressiveVideoUploader/ProgressiveVideoUploader.tsx"
    ]
    
    all_good = True
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            all_good = False
    
    if all_good:
        print("\n🎉 Work Order #6 implementation files are present!")
    else:
        print("\n⚠️  Some files are missing.")
    
    return all_good

if __name__ == "__main__":
    main()
