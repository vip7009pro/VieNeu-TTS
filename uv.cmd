@echo off
REM Simple wrapper for `uv run vieneu-stream` to run the project's venv entrypoint on Windows
SETLOCAL
REM Resolve script dir
set SCRIPT_DIR=%~dp0
if "%1"=="run" (
  if "%2"=="vieneu-stream" (
    "%SCRIPT_DIR%\.venv\Scripts\python.exe" -m apps.web_stream
    exit /b %ERRORLEVEL%
  )
)
REM Fallback: try to run uvicorn in venv if provided
"%SCRIPT_DIR%\.venv\Scripts\python.exe" -m uvicorn %*
ENDLOCAL
