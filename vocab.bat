@echo off
REM Wrapper for the Vocabulary Card Generator.
REM Usage: vocab embed   |   vocab tokenizer -t ML LLM
setlocal
where python >nul 2>nul
if errorlevel 1 (
    echo Error: 'python' was not found on PATH. Install Python 3.8+ and retry.
    exit /b 1
)
python "%~dp0vocab_card_generator.py" %*
endlocal
