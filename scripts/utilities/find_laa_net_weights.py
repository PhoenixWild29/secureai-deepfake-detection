#!/usr/bin/env python3
"""
Script to clone LAA-Net repository and find pretrained weights download links
"""
import os
import subprocess
import sys
from pathlib import Path
import re

def run_command(cmd, cwd=None):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=True,
                              capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return None

def find_laa_net_weights():
    """Clone LAA-Net and find pretrained weights information"""
    project_root = Path(__file__).parent
    external_dir = project_root / "external"
    laa_net_dir = external_dir / "laa_net"
    
    print("=" * 70)
    print("🔍 Finding LAA-Net Pretrained Weights")
    print("=" * 70)
    
    # Create external directory
    external_dir.mkdir(exist_ok=True)
    
    # Clone repository if not exists
    if not laa_net_dir.exists():
        print("\n📦 Cloning LAA-Net repository...")
        os.chdir(external_dir)
        result = run_command("git clone https://github.com/10Ring/LAA-Net laa_net")
        if result is None:
            print("❌ Failed to clone repository")
            return False
        print("✅ Repository cloned successfully")
    else:
        print("\n✅ LAA-Net repository already exists")
    
    # Check README for weights links
    readme_path = laa_net_dir / "README.md"
    if readme_path.exists():
        print("\n📄 Reading README.md for pretrained weights information...")
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        # Look for common patterns
        print("\n🔍 Searching for pretrained weights download links...")
        print("-" * 70)
        
        # Look for Google Drive links
        gdrive_pattern = r'https://drive\.google\.com/[^\s\)]+'
        gdrive_links = re.findall(gdrive_pattern, readme_content)
        
        # Look for weight-related sections
        weight_section_pattern = r'(?i)(pre[- ]?trained|weights|model|download).{0,200}'
        weight_sections = re.findall(weight_section_pattern, readme_content)
        
        # Look for file extensions
        weight_file_pattern = r'[\w/]+\.(pth|pkl|ckpt|pt|h5|weights)[^\s\)]*'
        weight_files = re.findall(weight_file_pattern, readme_content)
        
        if gdrive_links:
            print("\n✅ Found Google Drive links:")
            for i, link in enumerate(set(gdrive_links), 1):
                print(f"   {i}. {link}")
        
        if weight_files:
            print("\n✅ Found potential weight files mentioned:")
            for i, file in enumerate(set(weight_files[:10]), 1):  # Limit to 10
                print(f"   {i}. {file}")
        
        if weight_sections:
            print("\n📋 Relevant sections found (first 500 chars):")
            for i, section in enumerate(weight_sections[:5], 1):
                print(f"\n   Section {i}:")
                print(f"   {section[:500]}...")
        
        # Save key information
        info_file = project_root / "LAA_NET_WEIGHTS_INFO.txt"
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write("LAA-Net Pretrained Weights Information\n")
            f.write("=" * 70 + "\n\n")
            f.write("Repository: https://github.com/10Ring/LAA-Net\n\n")
            
            if gdrive_links:
                f.write("Google Drive Links:\n")
                for link in set(gdrive_links):
                    f.write(f"  - {link}\n")
                f.write("\n")
            
            if weight_files:
                f.write("Potential Weight Files:\n")
                for file in set(weight_files[:20]):
                    f.write(f"  - {file}\n")
                f.write("\n")
            
            # Extract README sections about weights
            lines = readme_content.split('\n')
            in_weight_section = False
            weight_section_lines = []
            
            for i, line in enumerate(lines):
                if re.search(r'(?i)(pre[- ]?trained|weights|model|download)', line):
                    in_weight_section = True
                    weight_section_lines.append(f"\nLine {i+1}: {line}")
                    
                    # Capture next 10 lines
                    for j in range(i+1, min(i+11, len(lines))):
                        weight_section_lines.append(f"Line {j+1}: {lines[j]}")
                    weight_section_lines.append("")
            
            if weight_section_lines:
                f.write("Relevant README Sections:\n")
                f.write("\n".join(weight_section_lines))
        
        print(f"\n✅ Information saved to: {info_file}")
        
        # Check repository structure
        print("\n📁 Repository structure:")
        print("-" * 70)
        if (laa_net_dir / "pretrained").exists():
            print("✅ Found 'pretrained' directory")
            pretrained_files = list((laa_net_dir / "pretrained").glob("*"))
            if pretrained_files:
                print(f"   Files: {[f.name for f in pretrained_files[:5]]}")
        
        if (laa_net_dir / "weights").exists():
            print("✅ Found 'weights' directory")
            weight_files = list((laa_net_dir / "weights").glob("*"))
            if weight_files:
                print(f"   Files: {[f.name for f in weight_files[:5]]}")
        
        if (laa_net_dir / "checkpoints").exists():
            print("✅ Found 'checkpoints' directory")
        
        # Check for common files
        common_files = ["README.md", "requirements.txt", "setup.py", "configs"]
        for file in common_files:
            path = laa_net_dir / file
            if path.exists():
                print(f"✅ Found: {file}")
        
        return True
    else:
        print("❌ README.md not found in repository")
        return False

if __name__ == "__main__":
    find_laa_net_weights()
