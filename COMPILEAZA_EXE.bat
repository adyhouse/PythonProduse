@echo off
chcp 65001 >nul
color 0A
cls

echo ═══════════════════════════════════════════════════════════════════════════
echo                    COMPILARE EXE - IMPORT PRODUSE
echo ═══════════════════════════════════════════════════════════════════════════
echo.

:: Verifică Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python NU este instalat!
    echo.
    echo Rulează mai întâi: INSTALARE_PYTHON.bat
    echo.
    pause
    exit /b 1
)

echo ✓ Python detectat
echo.

:: Verifică PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo ✗ PyInstaller NU este instalat!
    echo.
    echo Rulează mai întâi: INSTALEAZA_DEPENDINTE.bat
    echo.
    pause
    exit /b 1
)

echo ✓ PyInstaller detectat
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo 🔧 Compilez import_gui.py în EXE standalone...
echo    (Acest proces poate dura 2-3 minute)
echo.

:: Șterge foldere vechi
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "ImportProduse.spec" del /f /q "ImportProduse.spec"

:: Compilează cu PyInstaller
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name="ImportProduse" ^
    --icon=NONE ^
    --add-data=".env.example;." ^
    --hidden-import=PIL._tkinter_finder ^
    --hidden-import=bs4 ^
    --hidden-import=woocommerce ^
    import_gui.py

if errorlevel 1 (
    echo.
    echo ✗ EROARE la compilare!
    echo.
    pause
    exit /b 1
)

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo ✓ Compilare reușită!
echo.
echo 📦 Fișierul EXE se află în: dist\ImportProduse.exe
echo.
echo Poți copia acest EXE pe orice calculator Windows și va funcționa
echo fără să mai trebuiască instalat Python!
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.

:: Deschide folder dist
if exist "dist\ImportProduse.exe" (
    echo 📂 Deschid folderul dist...
    timeout /t 2 >nul
    explorer dist
)

pause
