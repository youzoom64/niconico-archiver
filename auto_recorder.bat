@echo off
cd /d %~dp0
venv\Scripts\python.exe main_recorder.py %*
pause