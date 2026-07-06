#!/bin/bash
# 工作助手应用打包脚本

echo "===================================="
echo "    工作助手应用打包工具"
echo "===================================="
echo ""

# 设置应用名称
APP_NAME="工作助手"
APP_DIR="${APP_NAME}.app"
CONTENTS_DIR="${APP_DIR}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"

# 清理旧的构建
echo "清理旧的构建文件..."
rm -rf "${APP_DIR}"

# 创建应用目录结构
echo "创建应用目录结构..."
mkdir -p "${MACOS_DIR}"
mkdir -p "${RESOURCES_DIR}"

# 复制主程序
echo "复制应用程序文件..."
cp work_assistant.py "${MACOS_DIR}/"
chmod +x "${MACOS_DIR}/work_assistant.py"

# 创建数据目录
mkdir -p "${MACOS_DIR}/data"

# 创建启动脚本
cat > "${MACOS_DIR}/${APP_NAME}" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
python3 work_assistant.py
EOF
chmod +x "${MACOS_DIR}/${APP_NAME}"

# 创建 Info.plist
cat > "${CONTENTS_DIR}/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>com.workassistant.app</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
</dict>
</plist>
EOF

echo ""
echo "===================================="
echo "打包完成！"
echo "应用已创建: ${APP_DIR}"
echo "===================================="
echo ""
echo "使用方法："
echo "1. 双击 ${APP_DIR} 即可运行应用"
echo "2. 或者在终端中运行: open \"${APP_DIR}\""
echo ""