@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ================================================================
echo 路由器测试框架 - 完整自动化安装脚本
echo ================================================================
echo.
echo 此脚本将自动完成：
echo   1. 安装 Chocolatey 包管理器
echo   2. 安装 Python 3.12
echo   3. 安装 Git
echo   4. 安装 GitHub Desktop
echo   5. 配置 Git 用户信息
echo   6. 克隆项目代码
echo   7. 安装所有依赖
echo   8. 启动测试框架
echo.
echo 全程自动化，请确保网络连接正常！
echo ================================================================
echo.
pause

REM 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [错误] 请右键选择"以管理员身份运行"此脚本！
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo [准备] 安装 Chocolatey 包管理器...
echo ================================================================

where choco >nul 2>&1
if %errorLevel% neq 0 (
    echo Chocolatey 未安装，正在自动安装...
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"

    if %errorLevel% neq 0 (
        echo [错误] Chocolatey 安装失败！
        echo 请检查网络连接
        pause
        exit /b 1
    )

    REM 刷新环境变量
    call refreshenv 2>nul
    echo Chocolatey 安装成功 ✓
) else (
    choco --version
    echo Chocolatey 已安装 ✓
)

echo.
echo ================================================================
echo [1/7] 安装 Python 3.12...
echo ================================================================

python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo Python 未安装，正在通过 Chocolatey 自动安装...
    echo 请稍候，这可能需要几分钟...
    echo.
    choco install python --version=3.12.0 -y --force

    REM 刷新环境变量
    call refreshenv 2>nul

    python --version >nul 2>&1
    if %errorLevel% neq 0 (
        echo [修复] Python 未正确加入 PATH，正在设置...
        set "PATH=C:\Python312;C:\Python312\Scripts;%PATH%"
    )

    echo Python 安装成功 ✓
) else (
    python --version
    echo Python 已安装 ✓
)

echo.
echo ================================================================
echo [2/7] 安装 Git...
echo ================================================================

git --version >nul 2>&1
if %errorLevel% neq 0 (
    echo Git 未安装，正在通过 Chocolatey 自动安装...
    echo 请稍候，这可能需要几分钟...
    echo.
    choco install git -y --force --params "/GitAndUnixToolsOnPath /NoAutoCrlf"

    REM 刷新环境变量
    call refreshenv 2>nul

    echo Git 安装成功 ✓
) else (
    git --version
    echo Git 已安装 ✓
)

echo.
echo ================================================================
echo [3/7] 安装 GitHub Desktop...
echo ================================================================

where github >nul 2>&1
if %errorLevel% neq 0 (
    if not exist "%LOCALAPPDATA%\GitHubDesktop\GitHubDesktop.exe" (
        echo GitHub Desktop 未安装，正在自动安装...
        echo 请稍候，这可能需要几分钟...
        echo.
        choco install github-desktop -y --force

        REM 刷新环境变量
        call refreshenv 2>nul

        echo GitHub Desktop 安装成功 ✓
        echo.
        echo [提示] GitHub Desktop 已安装到桌面
    ) else (
        echo GitHub Desktop 已安装 ✓
    )
) else (
    echo GitHub Desktop 已安装 ✓
)

echo.
echo ================================================================
echo [4/7] 配置 Git...
echo ================================================================

REM 检查 Git 是否已配置
git config --global user.name >nul 2>&1
if %errorLevel% neq 0 (
    echo Git 用户信息未配置，请输入您的信息：
    echo.
    set /p GIT_USERNAME="请输入您的 Git 用户名（例如：heyp）: "
    set /p GIT_EMAIL="请输入您的 Git 邮箱（例如：heyp@milesight.com）: "

    git config --global user.name "!GIT_USERNAME!"
    git config --global user.email "!GIT_EMAIL!"

    echo.
    echo Git 配置完成 ✓
) else (
    echo Git 用户信息已配置：
    git config --global user.name
    git config --global user.email
    echo.
    set /p RECONFIG="是否重新配置？(y/N): "
    if /i "!RECONFIG!"=="y" (
        set /p GIT_USERNAME="请输入您的 Git 用户名: "
        set /p GIT_EMAIL="请输入您的 Git 邮箱: "
        git config --global user.name "!GIT_USERNAME!"
        git config --global user.email "!GIT_EMAIL!"
        echo Git 配置已更新 ✓
    )
)

echo.
echo [配置] Git 全局设置...
git config --global core.autocrlf false
git config --global core.quotepath false
git config --global gui.encoding utf-8
git config --global i18n.commit.encoding utf-8
git config --global i18n.logoutputencoding utf-8
echo Git 全局配置完成 ✓

REM 再次检查确保环境变量生效
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [修复] 正在手动设置 Python 路径...
    set "PATH=C:\Python312;C:\Python312\Scripts;%PATH%"
)

git --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [修复] 正在手动设置 Git 路径...
    set "PATH=C:\Program Files\Git\cmd;%PATH%"
)

echo.
echo ================================================================
echo [5/7] 克隆项目代码...
echo ================================================================

if not exist "E:\GIT" mkdir "E:\GIT"
cd /d E:\GIT

if exist "ROUTER_TEST" (
    echo 项目目录已存在，正在更新代码...
    cd ROUTER_TEST
    git fetch origin 2>nul
    git checkout RouterAuto 2>nul
    git pull origin RouterAuto 2>nul
    if %errorLevel% neq 0 (
        echo [警告] 代码更新失败，使用本地版本
    ) else (
        echo 代码更新成功 ✓
    )
) else (
    echo 正在从 GitHub 克隆项目（RouterAuto 分支）...
    git clone -b RouterAuto https://github.com/heyp5655/router_test.git ROUTER_TEST

    if %errorLevel% neq 0 (
        echo [错误] 代码克隆失败！
        echo.
        echo 可能原因：
        echo   1. 网络问题
        echo   2. GitHub 访问受限
        echo   3. Git 配置问题
        echo.
        echo 请检查网络后重试，或使用 GitHub Desktop 手动克隆
        pause
        exit /b 1
    )
    cd ROUTER_TEST
    echo 代码克隆成功 ✓
)

echo.
echo ================================================================
echo [6/7] 安装 Python 依赖...
echo ================================================================

echo [升级] pip 到最新版本...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple 2>nul
if %errorLevel% neq 0 (
    python -m pip install --upgrade pip
)

echo.
echo [安装] 项目依赖包...
echo 使用预编译包，避免编译错误（使用清华镜像加速）
echo 这可能需要几分钟，请耐心等待...
echo.

REM 第一次尝试：使用清华镜像 + 预编译包
pip install --only-binary :all: --prefer-binary -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 2>nul

if %errorLevel% neq 0 (
    echo.
    echo [重试1] 使用清华镜像，允许部分从源码安装...
    pip install --prefer-binary -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 2>nul

    if %errorLevel% neq 0 (
        echo.
        echo [重试2] 使用官方源 + 预编译包...
        pip install --prefer-binary -r requirements.txt 2>nul

        if %errorLevel% neq 0 (
            echo.
            echo [最后尝试] 逐个安装关键依赖包...
            echo.

            echo 安装 Flask...
            pip install Flask==2.3.3 --prefer-binary

            echo 安装 requests...
            pip install requests --prefer-binary

            echo 安装 PyYAML（预编译版本）...
            pip install PyYAML --only-binary :all: 2>nul
            if %errorLevel% neq 0 (
                echo PyYAML 预编译包安装失败，尝试旧版本...
                pip install PyYAML==5.4.1 --prefer-binary
            )

            echo 安装 selenium...
            pip install selenium==4.12.0 --prefer-binary

            echo 安装 webdriver-manager...
            pip install webdriver-manager==4.0.1 --prefer-binary

            echo 安装 pyserial...
            pip install pyserial==3.5 --prefer-binary

            echo 安装 paho-mqtt...
            pip install paho-mqtt --prefer-binary

            echo 安装 openpyxl...
            pip install openpyxl --prefer-binary

            echo 安装 paramiko（SSH 支持）...
            pip install paramiko --prefer-binary

            echo.
            echo [完成] 核心依赖安装完成
        )
    )
)

echo.
echo 依赖安装完成 ✓

echo.
echo ================================================================
echo [7/7] 创建桌面快捷方式...
echo ================================================================

REM 创建 GitHub Desktop 桌面快捷方式（如果不存在）
if exist "%LOCALAPPDATA%\GitHubDesktop\GitHubDesktop.exe" (
    if not exist "%USERPROFILE%\Desktop\GitHub Desktop.lnk" (
        powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\GitHub Desktop.lnk'); $Shortcut.TargetPath = '%LOCALAPPDATA%\GitHubDesktop\GitHubDesktop.exe'; $Shortcut.Save()"
        echo GitHub Desktop 快捷方式已创建 ✓
    ) else (
        echo GitHub Desktop 快捷方式已存在 ✓
    )
)

echo.
echo ================================================================
echo 安装完成！
echo ================================================================
echo.
echo 项目位置: E:\GIT\ROUTER_TEST
echo 当前分支: RouterAuto
echo.
echo 已安装工具:
python --version 2>nul || echo Python: 未正确配置
git --version 2>nul || echo Git: 未正确配置
echo.
echo Git 配置信息:
git config --global user.name 2>nul && git config --global user.email 2>nul || echo Git: 未配置
echo.
echo ================================================================
echo.
echo GitHub Desktop 已安装到桌面，您可以：
echo   1. 打开 GitHub Desktop
echo   2. 登录您的 GitHub 账号
echo   3. 在 GitHub Desktop 中打开项目: E:\GIT\ROUTER_TEST
echo.
echo ================================================================
echo.
echo 按任意键启动测试框架...
pause

echo.
echo [启动] 正在启动测试框架...
cd /d E:\GIT\ROUTER_TEST

if exist "start_admin.bat" (
    start start_admin.bat
) else (
    echo [警告] start_admin.bat 未找到，尝试直接启动...
    python app.py
)

endlocal
