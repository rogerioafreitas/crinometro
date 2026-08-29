@echo off
setlocal
pyinstaller --onefile --windowed --clean --noconfirm --icon=grilinho.ico crinometro_frontend_senior_v16.py
endlocal
