@echo off
rem InstaRepost no Windows: agendador 24/7 com reinicio automatico. Sem tunel: o instagrapi envia o arquivo direto.
cd /d "%~dp0"
set PYTHONUTF8=1
set OLLAMA_MODELS=B:\Projetos\NetHub\NetHub DB\ollama\models
if not exist logs mkdir logs
:laco
curl -s -m 3 http://127.0.0.1:11434/api/version >nul 2>&1 || start "" /b "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
.venv\Scripts\python.exe cli.py scheduler >> logs\scheduler.out.log 2>&1
timeout /t 60 /nobreak >nul
goto laco
