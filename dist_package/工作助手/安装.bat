@echo off
chcp 65001 >nul
echo ====================================
echo     工作助手安装程序
echo ====================================
echo.

set APP_NAME=工作助手
set INSTALL_DIR=%ProgramFiles%\workassistant
set START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs

echo 📦 创建安装目录...
mkdir "%INSTALL_DIR%" 2>nul

echo 📁 复制应用文件...
xcopy /E /I /Y "*" "%INSTALL_DIR%\"

echo 🖥️ 创建桌面快捷方式...
set SHORTCUT="%USERPROFILE%\Desktop\%APP_NAME%.lnk"
set TARGET="%INSTALL_DIR%\工作助手.exe"
set ICON="%SystemRoot%\System32\shell32.dll,13"

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%TARGET%'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%ICON%'; $Shortcut.Save()"

echo 📂 创建开始菜单快捷方式...
mkdir "%START_MENU%\%APP_NAME%" 2>nul
set START_SHORTCUT="%START_MENU%\%APP_NAME%\%APP_NAME%.lnk"
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%START_SHORTCUT%'); $Shortcut.TargetPath = '%TARGET%'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%ICON%'; $Shortcut.Save()"

echo.
echo ✅ 安装完成！
echo.
echo ====================================
echo 安装信息：
echo 应用目录: %INSTALL_DIR%
echo 桌面快捷方式: 桌面\%APP_NAME%.lnk
echo 开始菜单: 开始菜单 > %APP_NAME%
echo.
echo 启动方式：
echo 1. 在桌面查找「工作助手」图标并双击
echo 2. 在开始菜单查找「工作助手」
echo 3. 直接运行: %INSTALL_DIR%\工作助手.exe
echo.
echo 首次运行需要：
echo - 连接麦克风设备
echo - 授予麦克风权限
echo - 保持网络连接（语音识别需要联网）
echo ====================================
echo.
pause