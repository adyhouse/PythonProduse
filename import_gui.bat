@echo off
REM Script launcher pentru import_gui.py
REM Setează encoding UTF-8 și lansează programul cu GUI

setlocal enabledelayedexpansion
set PYTHONIOENCODING=utf-8

python import_gui.py %*

endlocal
