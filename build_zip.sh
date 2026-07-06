#!/bin/bash
# 工作助手应用 ZIP 打包脚本

echo "===================================="
echo "    工作助手应用 ZIP 打包工具"
echo "===================================="
echo ""

# 设置应用名称
APP_NAME="工作助手"
VERSION="3.0.0"
ZIP_NAME="${APP_NAME}_v${VERSION}.zip"

# 创建临时目录
TEMP_DIR="temp_package"
echo "创建临时目录..."
mkdir -p "${TEMP_DIR}/${APP_NAME}"

# 复制应用程序文件
echo "复制应用程序文件..."
cp work_assistant.py "${TEMP_DIR}/${APP_NAME}/"
cp README.md "${TEMP_DIR}/${APP_NAME}/"

# 创建数据目录
mkdir -p "${TEMP_DIR}/${APP_NAME}/data"

# 创建启动脚本（Windows/Linux/macOS通用）
cat > "${TEMP_DIR}/${APP_NAME}/启动应用.sh" << 'EOF'
#!/bin/bash
echo "正在启动工作助手..."
python3 work_assistant.py
EOF
chmod +x "${TEMP_DIR}/${APP_NAME}/启动应用.sh"

# 创建Windows启动脚本
cat > "${TEMP_DIR}/${APP_NAME}/启动应用.bat" << 'EOF'
@echo off
echo 正在启动工作助手...
python work_assistant.py
pause
EOF

# 创建使用说明
cat > "${TEMP_DIR}/${APP_NAME}/使用说明.txt" << 'EOF'
====================================
    工作助手使用说明
====================================

版本: 1.0.0
发布日期: 2026-07-06

一、安装要求
--------------
1. Python 3.6 或更高版本
2. Tkinter（Python标准库）

二、运行方式
--------------
Windows系统：
  双击 "启动应用.bat" 或运行命令: python work_assistant.py

macOS/Linux系统：
  双击 "启动应用.sh" 或运行命令: python3 work_assistant.py

三、功能介绍
--------------
1. 会议要点记录 - 记录会议主题、时间、参会人员和要点
2. 工作内容记录 - 记录日常工作内容和进度
3. 工作细节记录 - 详细记录工作细节和注意事项
4. 改进建议记录 - 提出改进建议并跟踪状态
5. 会议提醒 - 设置会议提醒，自动通知

四、数据存储
--------------
所有数据保存在 data/ 目录中：
- records.json: 会议、工作、细节记录
- config.json: 提醒设置

五、注意事项
--------------
1. 请勿删除 data 目录
2. 应用需保持运行才能触发提醒
3. 建议定期备份 data 目录

六、详细文档
--------------
查看 README.md 了解更多详细信息

====================================
祝您使用愉快！
====================================
EOF

# 打包成 ZIP
echo "打包应用为 ZIP 文件..."
cd "${TEMP_DIR}"
zip -r "../${ZIP_NAME}" "${APP_NAME}"
cd ..

# 清理临时目录
echo "清理临时文件..."
rm -rf "${TEMP_DIR}"

echo ""
echo "===================================="
echo "打包完成！"
echo "ZIP 文件: ${ZIP_NAME}"
echo "===================================="
echo ""
echo "使用方法："
echo "1. 解压 ${ZIP_NAME}"
echo "2. 进入解压后的目录"
echo "3. 运行启动脚本或直接运行 work_assistant.py"
echo ""
echo "解压命令: unzip ${ZIP_NAME}"
echo ""