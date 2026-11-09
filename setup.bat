@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo   Editor Grafico Geometrico - preparar o ambiente (Windows)
echo ============================================================
echo.

rem 1) Escolher o Python. O lancador "py" permite pedir uma versao exata.
set "PY="
for %%V in (3.12 3.13 3.11 3.14 3.10) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    python -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,14) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [ERRO] Nao encontrei o Python 3.10 a 3.14.
    echo        Instale o Python 3.12 a partir de https://www.python.org/downloads/
    echo        e marque "Add python.exe to PATH" durante a instalacao.
    pause
    exit /b 1
)
echo A usar:
%PY% --version
echo.

rem 2) Ambiente virtual .venv: as bibliotecas ficam dentro do projeto e
rem    nao mexem no Python do computador (por isso nada "parte").
if not exist ".venv\Scripts\python.exe" (
    echo A criar o ambiente virtual .venv ...
    %PY% -m venv .venv
    if errorlevel 1 goto erro
)

rem 3) Instalar as dependencias com as versoes fixas do requirements.txt
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto erro
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto erro

rem 4) Verificacao: autoteste sem janelas (matematica, ficheiros e OpenGL)
echo.
echo A verificar a instalacao (autoteste)...
".venv\Scripts\python.exe" main.py --selftest autoteste
if errorlevel 1 goto erro_teste

echo.
echo ============================================================
echo   Pronto! Para abrir o editor faca duplo clique em run.bat
echo ============================================================
pause
exit /b 0

:erro_teste
echo.
echo [AVISO] O autoteste falhou. Veja o ficheiro autoteste\autoteste.txt
echo         Se o problema for o OpenGL, experimente:  run.bat --software-gl
pause
exit /b 1

:erro
echo.
echo [ERRO] Falhou a preparacao do ambiente. Verifique a ligacao a Internet e tente de novo.
pause
exit /b 1
