#!/bin/bash
echo "🚀 Starting Build Process for Rox Quant..."

# 1. Clean previous build
rm -rf build dist

# 2. Run PyInstaller
# Ensure pyinstaller is installed
/Users/mac/Documents/trae_projects/word/.venv/bin/pip install pyinstaller

echo "📦 Packaging Application..."
/Users/mac/Documents/trae_projects/word/.venv/bin/pyinstaller rox_gui.spec --clean --noconfirm

# 3. Verify Build
if [ -d "dist/RoxQuant.app" ]; then
    echo "✅ Build Successful!"
    
    # 4. Zip the App for distribution
    echo "🗜️ Zipping for distribution..."
    cd dist
    zip -r ../RoxQuant_Mac_v13.9.zip RoxQuant.app
    cd ..
    
    echo "🎉 Done! File ready at: RoxQuant_Mac_v13.9.zip"
else
    echo "❌ Build Failed!"
    exit 1
fi
