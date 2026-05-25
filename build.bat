@echo off
echo Building Universal Game Translator GUI...
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --hidden-import _socket --hidden-import _ssl --add-data "config.json;." --add-data "system_prompt.txt;." app.py
echo Build Complete! Check the 'dist' folder.
pause
