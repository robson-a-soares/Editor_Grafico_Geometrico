@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo   Criar o executavel dist\EditorGeometrico.exe (PyInstaller)
echo ============================================================
if not exist ".venv\Scripts\python.exe" (
    call setup.bat
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if errorlevel 1 goto erro
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean EditorGeometrico.spec
if errorlevel 1 goto erro

echo.
echo A testar o executavel (autoteste)...
start "" /wait "dist\EditorGeometrico.exe" --selftest dist\autoteste
if errorlevel 1 (
    echo [AVISO] O autoteste do executavel falhou: veja dist\autoteste\autoteste.txt
    pause
    exit /b 1
)
type dist\autoteste\autoteste.txt
echo.
echo ============================================================
echo   Pronto: dist\EditorGeometrico.exe  (funciona sem Python)
echo ============================================================
pause
exit /b 0

:erro
echo [ERRO] Falhou a criacao do executavel.
pause
exit /b 1
