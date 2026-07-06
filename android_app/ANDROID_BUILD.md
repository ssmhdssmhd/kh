# 工作助手 - 安卓版本构建指南

## 概述

本指南介绍如何为工作助手应用构建安卓 APK 安装包。应用基于 Kivy 框架开发，可以在安卓手机上运行，具备完整的会议记录功能。

## 环境要求

### 基础环境
- **Python 3.8+**: 开发语言
- **Java JDK 11+**: Android 构建必需
- **pip3**: Python 包管理工具

### 推荐系统
- **Ubuntu 20.04+/Debian 11+**: 推荐构建环境
- **macOS 11+**: 支持构建
- **Windows 10/11**: 支持构建（需配置环境变量）

## 安装步骤

### 1. 安装基础依赖

#### Ubuntu/Debian
```bash
# 更新系统
sudo apt update
sudo apt upgrade -y

# 安装 Python 和工具
sudo apt install -y python3 python3-pip python3-dev python3-setuptools

# 安装 Java JDK 11
sudo apt install -y openjdk-11-jdk

# 安装其他依赖
sudo apt install -y build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev
sudo apt install -y autoconf automake libtool pkg-config
sudo apt install -y git curl unzip
```

#### macOS
```bash
# 安装 Homebrew（如未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python
brew install python@3.11

# 安装 Java
brew install openjdk@11
echo 'export PATH="/usr/local/opt/openjdk@11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### Windows
1. 安装 Python: https://www.python.org/downloads/
2. 安装 JDK 11: https://adoptium.net/temurin/releases/?version=11
3. 确保 python、java 已添加到系统 PATH

### 2. 安装构建工具

```bash
# 安装 buildozer
pip3 install buildozer

# 安装 Kivy 和语音识别库
pip3 install kivy SpeechRecognition
```

### 3. 构建 APK

```bash
# 进入安卓应用目录
cd android_app

# 运行打包脚本
chmod +x build_apk.sh
./build_apk.sh
```

或者手动构建：

```bash
cd android_app
buildozer android debug
```

### 4. 安装到手机

构建成功后，APK 文件位于 `bin/` 目录：

```bash
# 查看生成的 APK
ls ./bin/

# 通过 USB 安装
adb install ./bin/workassistant-*-debug.apk
```

## 构建说明

### 首次构建
- 首次构建会下载 Android SDK、NDK 和其他依赖
- 下载量较大（约 2-3 GB），请确保网络通畅
- 构建时间可能较长（30分钟-1小时）

### 后续构建
- 后续构建会使用缓存，速度较快
- 如果需要清理缓存：`buildozer android clean`

### debug vs release
- **debug**: 调试版本，用于开发测试
- **release**: 发布版本，用于正式发布（需要签名）

发布版本构建：

```bash
# 生成签名密钥
keytool -genkey -v -keystore workassistant.keystore -alias workassistant -keyalg RSA -keysize 2048 -validity 10000

# 构建发布版本
buildozer android release
```

## 常见问题

### 1. Java 版本错误
```
Error: JAVA_HOME is not set and no 'java' command could be found in your PATH.
```
解决方案：设置 JAVA_HOME 环境变量

```bash
# Ubuntu/Debian
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH

# macOS
export JAVA_HOME=/usr/local/opt/openjdk@11
export PATH=$JAVA_HOME/bin:$PATH
```

### 2. Android SDK 下载失败
```
Error: Could not download sdk-tools
```
解决方案：
1. 检查网络连接
2. 确保代理配置正确（如需要）
3. 手动下载 SDK 并设置环境变量

### 3. 内存不足
```
OutOfMemoryError: Java heap space
```
解决方案：增加 Java 堆内存

```bash
export JAVA_OPTS="-Xmx4G"
buildozer android debug
```

### 4. 权限问题
```
Permission denied: ./build_apk.sh
```
解决方案：

```bash
chmod +x build_apk.sh
```

### 5. 构建卡住
构建过程中可能会卡在下载步骤，这是正常现象，请耐心等待。

## 应用权限

应用需要以下权限：
- **INTERNET**: 语音识别需要联网
- **RECORD_AUDIO**: 录音功能
- **WRITE_EXTERNAL_STORAGE**: 保存数据
- **READ_EXTERNAL_STORAGE**: 读取数据

## 目录结构

```
android_app/
├── main.py              # 主应用代码
├── buildozer.spec       # Buildozer 配置文件
├── build_apk.sh         # 一键打包脚本
├── ANDROID_BUILD.md     # 构建指南
├── data/                # 数据目录
└── bin/                 # 构建产物（APK）
```

## 版本信息

- **应用版本**: 3.0.0
- **Kivy 版本**: 2.0.0+
- **Android API**: 33
- **Android NDK**: 25b

## 技术支持

如有问题，请查看：
- Buildozer 文档: https://buildozer.readthedocs.io/
- Kivy 文档: https://kivy.org/doc/stable/
- Android 开发者文档: https://developer.android.com/docs

---

**祝构建顺利！** 🚀