@echo off
echo Building Universal Game Translator GUI...
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --hidden-import _socket --hidden-import _ssl --name Universal_Translator_v1.0 app.py
move dist\Universal_Translator_v1.0.exe ..\
echo Build Complete! Check the root folder.
pause
