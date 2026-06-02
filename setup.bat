@echo off
chcp 65001 >nul
title AIGG — Setup

echo ============================================
echo  AIGG Market Basket Analysis — Setup
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден. Установите Python 3.9+ и добавьте его в PATH.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo Найден: %%v
echo.

:: Create venv
if exist ".venv\Scripts\activate.bat" (
    echo [OK] Виртуальное окружение уже существует, пропускаем создание.
) else (
    echo [1/3] Создание виртуального окружения .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Не удалось создать виртуальное окружение.
        pause
        exit /b 1
    )
    echo [OK] Виртуальное окружение создано.
)
echo.

:: Activate venv
echo [2/3] Активация виртуального окружения ...
call .venv\Scripts\activate.bat
echo [OK] Активировано.
echo.

:: Install dependencies
echo [3/3] Установка зависимостей из requirements.txt ...
pip install --upgrade pip --quiet
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Не удалось установить зависимости.
    pause
    exit /b 1
)
echo.
echo ============================================
echo  Готово! Все зависимости установлены.
echo ============================================
echo.
echo Для запуска приложений:
echo   GUI:       python gui_app.py
echo   Console:   python main.py
echo   Streamlit: streamlit run streamlit_app.py
echo.
pause
