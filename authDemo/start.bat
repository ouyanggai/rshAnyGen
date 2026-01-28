@echo off
setlocal enabledelayedexpansion

set "BASE_DIR=%~dp0"
set "BACKEND_DIR=%BASE_DIR%java-backend"
set "FRONTEND_DIR=%BASE_DIR%vue-frontend"
set "MAVEN_BIN=%BASE_DIR%maven\apache-maven-3.9.6\bin\mvn.cmd"

echo [INFO] Starting Auth Demo...

rem 1. 检查环境
java -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Java is not installed or not in PATH.
    pause
    exit /b 1
)

call npm -v >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm is not installed or not in PATH.
    pause
    exit /b 1
)

rem 2. 启动后端
echo [INFO] Starting Java Backend...
cd /d "%BACKEND_DIR%"

if exist "%MAVEN_BIN%" (
    set "MVN_CMD=%MAVEN_BIN%"
) else (
    set "MVN_CMD=mvn"
)

rem 在新窗口启动后端
start "AuthDemo Backend" cmd /k "%MVN_CMD% spring-boot:run"

rem 3. 启动前端
echo [INFO] Starting Vue Frontend...
cd /d "%FRONTEND_DIR%"

echo [INFO] Installing dependencies...
call npm install

echo [INFO] Starting dev server...
rem 在新窗口启动前端
start "AuthDemo Frontend" cmd /k "npm run dev"

rem 4. 打开浏览器
echo [INFO] Opening browser...
timeout /t 5 >nul
start http://192.168.1.212:5174

echo [SUCCESS] All services started in background windows.
pause
