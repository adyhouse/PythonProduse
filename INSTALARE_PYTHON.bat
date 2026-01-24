@echo off
chcp 65001 >nul
color 0A
cls

echo ═══════════════════════════════════════════════════════════════════════════
echo                     INSTALARE PYTHON 3.11 - WINDOWS
echo ═══════════════════════════════════════════════════════════════════════════
echo.

echo [1/3] Descărcăm Python 3.11.7 (64-bit)...
echo.

:: Descarcă Python
powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe' -OutFile '%TEMP%\python-installer.exe'}"

if errorlevel 1 (
    echo.
    echo ✗ EROARE: Nu s-a putut descărca Python!
    echo.
    echo Te rog descarcă manual de la: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo.
echo [2/3] Instalăm Python 3.11.7...
echo         (Se deschide installerul - IMPORTANT: Bifează "Add Python to PATH")
echo.
timeout /t 3 >nul

:: Instalează Python cu opțiuni automate
"%TEMP%\python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

timeout /t 10 >nul

echo.
echo [3/3] Verificăm instalarea...
echo.

:: Reîmprospătează variabilele de mediu
call refreshenv 2>nul

:: Verifică dacă Python este instalat
python --version >nul 2>&1

if errorlevel 1 (
    echo.
    echo ⚠ Python a fost instalat, dar trebuie să:
    echo    1. ÎNCHIZI acest terminal
    echo    2. DESCHIZI un terminal NOU
    echo    3. Rulezi din nou acest script pentru verificare
    echo.
    pause
    exit /b 0
)

echo.
echo ✓ Python instalat cu succes!
python --version
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo Următorul pas: Rulează INSTALEAZA_DEPENDINTE.bat
echo.
pause
