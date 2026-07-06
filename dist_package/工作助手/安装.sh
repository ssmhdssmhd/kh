#!/bin/bash
# 工作助手 - 安装脚本

APP_NAME="工作助手"
INSTALL_DIR="/opt/workassistant"
DESKTOP_FILE="$HOME/.local/share/applications/workassistant.desktop"

echo "===================================="
echo "    工作助手安装程序"
echo "===================================="
echo ""

# 检查是否为 root
if [ "$(id -u)" -ne 0 ]; then
    echo "⚠️  注意：建议以 root 用户运行此脚本以获得完整安装权限"
    echo ""
fi

# 创建安装目录
echo "📦 创建安装目录..."
mkdir -p "$INSTALL_DIR"

# 复制文件
echo "📁 复制应用文件..."
cp -r ./* "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/工作助手"

# 创建桌面快捷方式
echo "🖥️ 创建桌面快捷方式..."
mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=工作助手
Comment=专业会议记录应用，实时语音转文字，智能总结
Exec=$INSTALL_DIR/工作助手
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=Office;Utility;
StartupWMClass=工作助手
EOF

chmod +x "$DESKTOP_FILE"

# 创建命令别名
echo "🔗 创建命令别名..."
if [ -f "$HOME/.bashrc" ]; then
    echo "alias workassistant='$INSTALL_DIR/工作助手'" >> "$HOME/.bashrc"
fi

if [ -f "$HOME/.zshrc" ]; then
    echo "alias workassistant='$INSTALL_DIR/工作助手'" >> "$HOME/.zshrc"
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "===================================="
echo "安装信息："
echo "应用目录: $INSTALL_DIR"
echo "桌面快捷方式: $DESKTOP_FILE"
echo "命令别名: workassistant"
echo ""
echo "启动方式："
echo "1. 在桌面查找「工作助手」图标并双击"
echo "2. 在终端输入: workassistant"
echo "3. 在终端输入: $INSTALL_DIR/工作助手"
echo ""
echo "首次运行需要："
echo "- 连接麦克风设备"
echo "- 授予麦克风权限"
echo "- 保持网络连接（语音识别需要联网）"
echo "===================================="