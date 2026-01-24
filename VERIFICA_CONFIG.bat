@echo off
chcp 65001 >nul
color 0E
cls

echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                                                                            ║
echo ║                   🔧 VERIFICARE ȘI REPARARE CONFIG                         ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

echo 📋 Verificare fișier .env...
echo.

if not exist .env (
    echo ✗ Fișierul .env NU există!
    echo.
    echo 🔧 Creez .env din template...
    copy .env.example .env >nul 2>&1
    
    if errorlevel 1 (
        echo ✗ Nu am putut crea .env
        pause
        exit /b 1
    )
    
    echo ✓ Fișier .env creat!
    echo.
    echo ⚠️ IMPORTANT: Editează .env și completează:
    echo    - WOOCOMMERCE_URL=https://webgsm.ro
    echo    - WOOCOMMERCE_CONSUMER_KEY=ck_...
    echo    - WOOCOMMERCE_CONSUMER_SECRET=cs_...
    echo.
    notepad .env
    pause
    exit /b 0
)

echo ✓ Fișierul .env există
echo.
echo 📄 Conținut actual:
echo ════════════════════════════════════════════════════════════════════════════
type .env
echo ════════════════════════════════════════════════════════════════════════════
echo.

echo 🔍 Verificare valori...
echo.

:: Verifică URL
findstr /C:"WOOCOMMERCE_URL=https://" .env >nul
if errorlevel 1 (
    echo ⚠️ URL-ul WooCommerce nu este valid sau lipsește!
    echo    Ar trebui să fie: WOOCOMMERCE_URL=https://webgsm.ro
    echo.
)

:: Verifică Consumer Key
findstr /C:"WOOCOMMERCE_CONSUMER_KEY=ck_" .env >nul
if errorlevel 1 (
    echo ⚠️ Consumer Key lipsește sau nu este valid!
    echo    Ar trebui să înceapă cu: ck_
    echo.
)

:: Verifică Consumer Secret
findstr /C:"WOOCOMMERCE_CONSUMER_SECRET=cs_" .env >nul
if errorlevel 1 (
    echo ⚠️ Consumer Secret lipsește sau nu este valid!
    echo    Ar trebui să înceapă cu: cs_
    echo.
)

echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo 💡 Opțiuni:
echo.
echo    [1] Deschide .env pentru editare
echo    [2] Resetează .env la valori default
echo    [3] Continuă fără modificări
echo.
set /p choice="Alege opțiune (1-3): "

if "%choice%"=="1" (
    echo.
    echo 📝 Deschid .env în Notepad...
    notepad .env
    echo.
    echo ✓ Modificări salvate!
)

if "%choice%"=="2" (
    echo.
    echo 🔄 Resetez .env la valori default...
    
    echo # WooCommerce Configuration > .env
    echo WOOCOMMERCE_URL=https://webgsm.ro >> .env
    echo WOOCOMMERCE_CONSUMER_KEY= >> .env
    echo WOOCOMMERCE_CONSUMER_SECRET= >> .env
    echo. >> .env
    echo # Currency Conversion >> .env
    echo EXCHANGE_RATE=4.97 >> .env
    
    echo ✓ .env resetat!
    echo.
    echo 📝 Deschid pentru editare...
    notepad .env
)

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo ✓ Gata! Poți porni programul acum.
echo.
pause
