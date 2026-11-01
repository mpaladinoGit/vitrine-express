@echo off
cd /d "%~dp0"
echo Iniciando o Painel da Vitrine Express em http://localhost:8080 ...
start "" "http://localhost:8080"
python servidor_painel.py
pause
