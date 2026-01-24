@echo off
REM Script launcher pentru master_extractor.py
REM Setează encoding UTF-8 și lansează programul

setlocal enabledelayedexpansion
set PYTHONIOENCODING=utf-8

REM Dacă se lansează cu argumente, trece-le direct
if "%1"=="" (
    python master_extractor.py
) else (
    python master_extractor.py %*
)

endlocal
