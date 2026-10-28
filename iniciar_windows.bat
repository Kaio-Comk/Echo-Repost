@echo off
rem InstaRepost no Windows: agendador 24/7 com reinicio automatico. Sem tunel: o instagrapi envia o arquivo direto.
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist logs mkdir logs
:laco
.venv\Scripts\python.exe cli.py scheduler >> logs\scheduler.out.log 2>&1
timeout /t 60 /nobreak >nul
goto laco
