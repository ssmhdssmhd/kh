#!/bin/bash
# 工作助手 - 安卓 APK 打包脚本

echo "===================================="
echo "    工作助手 - 安卓打包工具"
echo "===================================="
echo ""

APP_NAME="工作助手"
VERSION="3.0.0"

echo "📦 检查环境..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    echo "请安装 Python3: https://www.python.org/downloads/"
    exit 1
fi

# 检查 pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ 错误: 未找到 pip3"
    exit 1
fi

# 检查 Java
if ! command -v java &> /dev/null; then
    echo "❌ 错误: 未找到 Java"
    echo "请安装 JDK 11+:"
    echo "  Ubuntu/Debian: sudo apt install openjdk-11-jdk"
    echo "  macOS: brew install openjdk@11"
    echo "  Windows: https://adoptium.net/"
    exit 1
fi

JAVA_VERSION=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2 | cut -d'.' -f1)
echo "✅ Java 版本: $JAVA_VERSION"

# 检查 buildozer
if ! command -v buildozer &> /dev/null; then
    echo "📥 安装 buildozer..."
    pip3 install buildozer
fi

echo "✅ Buildozer 已安装"

# 检查依赖
echo ""
echo "📦 安装应用依赖..."
pip3 install kivy SpeechRecognition

echo ""
echo "🚀 开始构建 APK..."
echo ""

# 创建数据目录
mkdir -p data

# 运行 buildozer
buildozer android debug deploy run

echo ""
echo "===================================="

if [ -f "./bin/workassistant-*-debug.apk" ]; then
    APK_FILE=$(ls ./bin/workassistant-*-debug.apk | head -n 1)
    echo "✅ 构建成功！"
    echo "APK 文件: $APK_FILE"
    echo ""
    echo "📱 安装方法:"
    echo "1. 将 APK 文件复制到安卓手机"
    echo "2. 在手机上点击 APK 文件进行安装"
    echo "3. 首次安装需允许「未知来源」权限"
else
    echo "❌ 构建失败，请检查错误信息"
    echo ""
    echo "💡 常见问题:"
    echo "- 确保已安装 Android SDK"
    echo "- 确保已安装 Android NDK"
    echo "- 确保网络连接正常（首次构建需下载大量依赖）"
    echo "- 构建时间较长，请耐心等待"
fi

echo "===================================="