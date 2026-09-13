@echo off
REM 026 sentinel - conformance enforcer (Windows one-click).
REM Runs the fleet scan using the project venv if present, else system python.
setlocal
set "ROOT=%~dp0.."
if exist "%ROOT%\.venv\Scripts\python.exe" (
  set "PY=%ROOT%\.venv\Scripts\python.exe"
) else (
  set "PY=python"
)
pushd "%ROOT%"
"%PY%" -m security.sentinel scan %*
set "CODE=%ERRORLEVEL%"
popd
endlocal & exit /b %CODE%
