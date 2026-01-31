@echo off
chcp 65001 >nul
color 0B
cls

echo ═══════════════════════════════════════════════════════════════════════════
echo                    ACTUALIZARE PROGRAM - WebGSM Import
echo ═══════════════════════════════════════════════════════════════════════════
echo.

:: ──────────────────────────────────────────────────
:: PASUL 1: Verifică dacă Git e instalat
:: ──────────────────────────────────────────────────
git --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Git NU este instalat!
    echo.
    echo ═══════════════════════════════════════════════════════════════════════════
    echo   INSTALARE GIT:
    echo.
    echo   1. Descarcă de pe: https://git-scm.com/download/win
    echo   2. Rulează installerul (Next, Next, Next - defaults sunt OK)
    echo   3. RESTART CMD / Explorer după instalare
    echo   4. Rulează din nou ACTUALIZEAZA.bat
    echo ═══════════════════════════════════════════════════════════════════════════
    echo.
    echo Vrei să deschid pagina de download acum? (Apasă orice tastă)
    pause >nul
    start https://git-scm.com/download/win
    exit /b 1
)

echo ✓ Git detectat:
git --version
echo.

:: ──────────────────────────────────────────────────
:: PASUL 2: Verifică dacă suntem într-un repo Git
:: ──────────────────────────────────────────────────
if not exist ".git" (
    echo ✗ Acest folder NU este un repository Git!
    echo.
    echo Soluții:
    echo   A) Dacă ai repo-ul pe GitHub/GitLab, clonează-l:
    echo      git clone https://github.com/USERUL_TAU/REPO.git
    echo.
    echo   B) Dacă ai copiat folderul manual, inițializează Git:
    echo      git init
    echo      git remote add origin https://github.com/USERUL_TAU/REPO.git
    echo      git pull origin main
    echo.
    pause
    exit /b 1
)

echo ✓ Repository Git detectat
echo.

:: ──────────────────────────────────────────────────
:: PASUL 3: Salvează fișierele locale modificate
:: ──────────────────────────────────────────────────
echo ───────────────────────────────────────────────────
echo Pas 1/4: Verific dacă ai modificări locale...
echo ───────────────────────────────────────────────────

:: Verifică dacă .env există (nu trebuie pierdut!)
if exist ".env" (
    echo ✓ Fișierul .env există (credențiale protejate de .gitignore)
)

:: Verifică dacă sunt modificări locale nesalvate
git status --porcelain > "%TEMP%\git_status.tmp"
set /p GIT_STATUS=<"%TEMP%\git_status.tmp"
del "%TEMP%\git_status.tmp" >nul 2>&1

if defined GIT_STATUS (
    echo ⚠ Ai modificări locale nesalvate!
    echo.
    git status --short
    echo.
    echo Salvez modificările locale înainte de actualizare...
    git stash push -m "auto-backup inainte de actualizare %date% %time%"
    if errorlevel 1 (
        echo ⚠ Nu s-au putut salva modificările. Continuăm oricum...
    ) else (
        echo ✓ Modificări salvate temporar (git stash)
    )
) else (
    echo ✓ Nicio modificare locală
)
echo.

:: ──────────────────────────────────────────────────
:: PASUL 4: Descarcă ultima versiune
:: ──────────────────────────────────────────────────
echo ───────────────────────────────────────────────────
echo Pas 2/4: Descarc ultima versiune de pe server...
echo ───────────────────────────────────────────────────
echo.

git pull origin main
if errorlevel 1 (
    echo.
    echo ⚠ git pull origin main a eșuat, încerc alte branch-uri...
    git pull origin master
    if errorlevel 1 (
        git pull
        if errorlevel 1 (
            echo.
            echo ✗ EROARE: Nu s-a putut actualiza!
            echo.
            echo Posibile cauze:
            echo   - Nu ai conexiune la internet
            echo   - Repository-ul remote nu e configurat
            echo   - Conflict între fișiere
            echo.
            echo Rulează manual: git pull origin BRANCH_NAME
            pause
            exit /b 1
        )
    )
)

echo.
echo ✓ Cod actualizat cu succes!
echo.

:: ──────────────────────────────────────────────────
:: PASUL 5: Restaurează modificările locale
:: ──────────────────────────────────────────────────
echo ───────────────────────────────────────────────────
echo Pas 3/4: Restaurez configurația locală...
echo ───────────────────────────────────────────────────

:: Încearcă să restaureze stash-ul (dacă există)
git stash list | findstr "auto-backup" >nul 2>&1
if not errorlevel 1 (
    git stash pop >nul 2>&1
    if errorlevel 1 (
        echo ⚠ Conflict la restaurare. Configurația .env e intactă.
        echo   Modificările tale salvate cu: git stash list
    ) else (
        echo ✓ Modificări locale restaurate
    )
) else (
    echo ✓ Nimic de restaurat
)
echo.

:: ──────────────────────────────────────────────────
:: PASUL 6: Actualizează dependințele Python
:: ──────────────────────────────────────────────────
echo ───────────────────────────────────────────────────
echo Pas 4/4: Actualizez dependințele Python...
echo ───────────────────────────────────────────────────

python --version >nul 2>&1
if errorlevel 1 (
    echo ⚠ Python nu e instalat - sări actualizare dependințe
    echo   Rulează SETUP_AUTOMAT.bat pentru instalare completă
) else (
    pip install -r requirements.txt --quiet >nul 2>&1
    if errorlevel 1 (
        echo ⚠ Unele dependințe nu s-au putut actualiza
        echo   Rulează INSTALEAZA_DEPENDINTE.bat manual
    ) else (
        echo ✓ Dependințe actualizate
    )
)

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo                      ✓ ACTUALIZARE COMPLETĂ!
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo   Versiune:
git log --oneline -1
echo.
echo   Acum poți rula: START_PROGRAM.bat
echo.
echo ═══════════════════════════════════════════════════════════════════════════
pause
