#!/bin/bash

# Build script for Calendar Harvest Integration Desktop App
# This script builds the macOS application and creates a .dmg installer

set -e

echo "🔨 Building Calendar Harvest Integration Desktop App..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="Calendar Harvest Integration"
APP_VERSION="1.0.0"
BUILD_DIR="build"
DIST_DIR="dist"
DMG_NAME="Calendar-Harvest-Integration-${APP_VERSION}.dmg"

# Step 1: Check dependencies
echo -e "${YELLOW}Step 1: Checking dependencies...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

if ! command -v pyinstaller &> /dev/null; then
    echo -e "${YELLOW}Installing PyInstaller...${NC}"
    pip install pyinstaller
fi

if ! command -v create-dmg &> /dev/null; then
    echo -e "${YELLOW}Installing create-dmg...${NC}"
    brew install create-dmg
fi

# Step 2: Clean previous builds
echo -e "${YELLOW}Step 2: Cleaning previous builds...${NC}"
rm -rf "$BUILD_DIR" "$DIST_DIR" "*.dmg"

# Step 3: Install/update dependencies
echo -e "${YELLOW}Step 3: Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Step 4: Build with PyInstaller
echo -e "${YELLOW}Step 4: Building application with PyInstaller...${NC}"
pyinstaller desktop_app.spec --clean

# Step 5: Verify build
echo -e "${YELLOW}Step 5: Verifying build...${NC}"
if [ ! -d "$DIST_DIR/$APP_NAME.app" ]; then
    echo -e "${RED}Error: Application bundle not created${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Application bundle created successfully${NC}"

# Step 6: Create .dmg installer
echo -e "${YELLOW}Step 6: Creating .dmg installer...${NC}"

# Create temporary directory for DMG contents
DMG_TEMP_DIR="dmg_temp"
rm -rf "$DMG_TEMP_DIR"
mkdir -p "$DMG_TEMP_DIR"

# Copy app to DMG directory
cp -r "$DIST_DIR/$APP_NAME.app" "$DMG_TEMP_DIR/"

# Create symlink to Applications folder
ln -s /Applications "$DMG_TEMP_DIR/Applications"

# Create .dmg file
create-dmg \
    --volname "$APP_NAME" \
    --volicon "static/icon.icns" \
    --window-pos 200 120 \
    --window-size 800 400 \
    --icon-size 100 \
    --icon "$APP_NAME.app" 200 190 \
    --hide-extension "$APP_NAME.app" \
    --app-drop-link 600 190 \
    "$DMG_NAME" \
    "$DMG_TEMP_DIR"

# Clean up temporary directory
rm -rf "$DMG_TEMP_DIR"

# Step 7: Verify DMG
echo -e "${YELLOW}Step 7: Verifying .dmg file...${NC}"
if [ ! -f "$DMG_NAME" ]; then
    echo -e "${RED}Error: DMG file not created${NC}"
    exit 1
fi
echo -e "${GREEN}✓ DMG file created successfully${NC}"

# Step 8: Generate checksums
echo -e "${YELLOW}Step 8: Generating checksums...${NC}"
shasum -a 256 "$DMG_NAME" > "${DMG_NAME}.sha256"
echo -e "${GREEN}✓ Checksums generated${NC}"

# Step 9: Summary
echo ""
echo -e "${GREEN}✅ Build completed successfully!${NC}"
echo ""
echo "📦 Build artifacts:"
echo "   Application: $DIST_DIR/$APP_NAME.app"
echo "   Installer: $DMG_NAME"
echo "   Checksum: ${DMG_NAME}.sha256"
echo ""
echo "📋 Next steps:"
echo "   1. Test the application: open \"$DIST_DIR/$APP_NAME.app\""
echo "   2. Test the installer: open \"$DMG_NAME\""
echo "   3. Upload to GitHub releases"
echo ""
echo "🚀 To upload to GitHub:"
echo "   gh release create v${APP_VERSION} ${DMG_NAME} ${DMG_NAME}.sha256 --draft"
echo ""

