@echo off
setlocal EnableExtensions EnableDelayedExpansion

title MAOPKKB Kurulum

echo ==========================================
echo           MAOPKKB KURULUM
echo ==========================================
echo.

if /I not "%~1"=="MAOPKKB" (
    echo Kurulum komutu:
    echo.
    echo     install MAOPKKB
    echo.
    echo Kurulum baslatiliyor...
    echo.
)

set "SOURCE_DIR=%~dp0"
set "INSTALL_DIR=%LOCALAPPDATA%\MAOPKKB"
set "BIN_DIR=%LOCALAPPDATA%\MAOPKKB\bin"

echo Python kontrol ediliyor...
echo.

python --version >nul 2>&1

if errorlevel 1 (
    echo Python bulunamadi.
    echo.
    echo Python 3 kurulu olmali ve PATH'e eklenmis olmali.
    echo.
    echo Kurulum durduruldu.
    pause
    exit /b 1
)

for /f "tokens=*" %%A in ('python --version 2^>^&1') do (
    echo %%A bulundu.
)

echo.
echo Kurulum klasoru:
echo %INSTALL_DIR%
echo.

if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
)

if not exist "%BIN_DIR%" (
    mkdir "%BIN_DIR%"
)

echo maopkkb.py kopyalaniyor...

copy /Y "%SOURCE_DIR%maopkkb.py" "%INSTALL_DIR%\maopkkb.py" >nul

if errorlevel 1 (
    echo maopkkb.py kopyalanamadi.
    pause
    exit /b 1
)

echo Launcher olusturuluyor...

(
    echo @echo off
    echo python "%INSTALL_DIR%\maopkkb.py" %%*
) > "%BIN_DIR%\MAOPKKB.bat"

if errorlevel 1 (
    echo Launcher olusturulamadi.
    pause
    exit /b 1
)

echo.
echo Kullanici PATH'i kontrol ediliyor...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$bin = [Environment]::GetEnvironmentVariable('Path','User'); ^
if ([string]::IsNullOrWhiteSpace($bin)) { $bin = '' }; ^
$items = $bin -split ';' | Where-Object { $_ -and $_.Trim() -ne '' }; ^
if ($items -notcontains '%BIN_DIR%') { ^
    $newPath = (($items + '%BIN_DIR%') -join ';'); ^
    [Environment]::SetEnvironmentVariable('Path',$newPath,'User'); ^
    Write-Host 'MAOPKKB bin klasoru kullanici PATH adresine eklendi.' ^
} else { ^
    Write-Host 'MAOPKKB zaten kullanici PATH adresinde.' ^
}"

if errorlevel 1 (
    echo.
    echo PATH otomatik eklenemedi.
    echo Launcher yine olusturuldu.
    echo.
)

echo.
echo ==========================================
echo             KURULUM TAMAMLANDI
echo ==========================================
echo.
echo MAOPKKB kuruldu.
echo.
echo Yeni CMD penceresi acip:
echo.
echo     MAOPKKB
echo.
echo yazabilirsiniz.
echo.
echo Secilen EXE calistirilmaz.
echo Analiz statik olarak yapilir.
echo.

endlocal
pause