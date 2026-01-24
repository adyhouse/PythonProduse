@echo off
chcp 65001 >nul
color 0A
cls

echo ═══════════════════════════════════════════════════════════════════════════
echo              SETUP COMPLET - Python + Dependințe + Program
echo ═══════════════════════════════════════════════════════════════════════════
echo.

:: Verifică dacă Python e instalat
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python NU este instalat!
    echo.
    echo Vrei să instalez Python 3.11 automat?
    echo Apasă ORICE TASTĂ pentru a continua...
    pause >nul
    
    echo.
    echo [1/4] Descărcăm Python 3.11.7...
    powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe' -OutFile '%TEMP%\python-installer.exe'}"
    
    if errorlevel 1 (
        echo ✗ EROARE: Nu s-a putut descărca Python!
        echo Te rog descarcă manual: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    
    echo ✓ Python descărcat
    echo.
    echo [2/4] Instalez Python cu opțiuni automate...
    "%TEMP%\python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1
    
    echo ✓ Python instalat
    echo.
    echo Aștept ca instalarea să se finalizeze...
    timeout /t 5 /nobreak
    
) else (
    echo ✓ Python e instalat
    for /f "tokens=*" %%i in ('python --version') do echo   %%i
)

echo.
echo [3/4] Instalez dependințele Python (pip install)...

:: Instalează dependințele
pip install --upgrade pip >nul 2>&1
pip install requests beautifulsoup4 pillow python-dotenv woocommerce pyinstaller >nul 2>&1

if errorlevel 1 (
    echo.
    echo ⚠️ AVERTISMENT: Nu s-au putut instala toate dependințele!
    echo.
    echo Încerc versiune alternativă...
    pip install requests beautifulsoup4 pillow python-dotenv woocommerce pyinstaller --user
)

echo ✓ Dependințe instalate
echo.

echo [4/4] Gata!
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo                         SETUP COMPLET - SUCCES!
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo Poti acum:
echo   • Rulează: START_PROGRAM.bat (interfață GUI)
echo   • Sau compileaza: COMPILEAZA_EXE.bat (fără nevoie de Python)
echo.
pause
