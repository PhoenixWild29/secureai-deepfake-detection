#!/bin/bash
# Fix Tailwind v4 PostCSS configuration

echo "=========================================="
echo "🔧 Fixing Tailwind CSS v4 Configuration"
echo "=========================================="
echo ""

cd ~/secureai-deepfake-detection/secureai-guardian || exit 1

echo "1. Checking current setup..."
echo "   PostCSS config:"
cat postcss.config.js
echo ""
echo "   index.css:"
cat index.css
echo ""
echo "   index.tsx CSS import:"
grep -A 2 "import.*css" index.tsx
echo ""

echo "2. Verifying Tailwind v4 packages..."
npm list @tailwindcss/postcss tailwindcss 2>/dev/null | grep -E "@tailwindcss/postcss|tailwindcss" || echo "   ⚠️  Packages may not be installed"
echo ""

echo "3. Testing PostCSS processing..."
# Create a test CSS file
echo "@import 'tailwindcss';" > test-tailwind.css
npx postcss test-tailwind.css -o test-output.css 2>&1 | head -20
if [ -f "test-output.css" ]; then
    echo "   ✅ PostCSS processed CSS file"
    CSS_SIZE=$(wc -c < test-output.css)
    echo "   Output size: $CSS_SIZE bytes"
    if [ "$CSS_SIZE" -gt 1000 ]; then
        echo "   ✅ CSS output looks good (has content)"
    else
        echo "   ⚠️  CSS output is very small (may be empty)"
    fi
    rm -f test-output.css
else
    echo "   ❌ PostCSS failed to process CSS"
fi
rm -f test-tailwind.css
echo ""

echo "4. Building frontend to check CSS generation..."
rm -rf dist
npm run build 2>&1 | tail -30

if [ -d "dist/assets" ]; then
    echo ""
    echo "5. Checking generated CSS files..."
    CSS_FILES=$(find dist/assets -name "*.css" 2>/dev/null)
    if [ -n "$CSS_FILES" ]; then
        echo "   ✅ CSS files found:"
        for file in $CSS_FILES; do
            SIZE=$(wc -c < "$file")
            echo "      - $file ($SIZE bytes)"
        done
    else
        echo "   ❌ No CSS files found in dist/assets/"
        echo "   This is the problem - CSS is not being generated!"
    fi
fi

echo ""
echo "=========================================="
echo "✅ Diagnostic complete"
echo "=========================================="