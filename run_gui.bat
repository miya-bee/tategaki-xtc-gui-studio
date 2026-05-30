@echo off
setlocal

set "PYTHONDONTWRITEBYTECODE=1"

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul 2>nul
if errorlevel 1 cd /d "%SCRIPT_DIR%" >nul 2>nul
if not exist "tategakiXTC_gui_studio.py" (
  echo.
  echo Could not switch to the app folder, or app files are missing:
  echo   %SCRIPT_DIR%
  echo Extract the whole zip to a normal local folder, then run run_gui.bat there.
  echo ^(do not run it from inside the zip preview or a network path^).
  pause
  exit /b 1
)
if not exist "requirements.txt" (
  echo.
  echo requirements.txt was not found in the app folder:
  echo   %CD%
  echo Extract the whole zip again, then run run_gui.bat from the extracted folder.
  pause
  exit /b 1
)

set "PY_EXE="
set "PY_ARGS="
set "PY_VERSION_CHECK=import sys; assert sys.version_info.major == 3 and sys.version_info.minor in [10, 11, 12]"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "%PY_VERSION_CHECK%" >nul 2>nul
  if not errorlevel 1 (
    set "PY_EXE=.venv\Scripts\python.exe"
    goto :run
  )
)

where py >nul 2>nul
if not errorlevel 1 (
  for %%V in (3.12 3.11 3.10) do (
    py -%%V -c "%PY_VERSION_CHECK%" >nul 2>nul
    if not errorlevel 1 (
      set "PY_EXE=py"
      set "PY_ARGS=-%%V"
      goto :run
    )
  )
)

where python >nul 2>nul
if not errorlevel 1 (
  python -c "%PY_VERSION_CHECK%" >nul 2>nul
  if not errorlevel 1 (
    set "PY_EXE=python"
    goto :run
  )
)

for %%V in (312 311 310) do (
  if exist "%LocalAppData%\Programs\Python\Python%%V\python.exe" (
    "%LocalAppData%\Programs\Python\Python%%V\python.exe" -c "%PY_VERSION_CHECK%" >nul 2>nul
    if not errorlevel 1 (
      set "PY_EXE=%LocalAppData%\Programs\Python\Python%%V\python.exe"
      goto :run
    )
  )
)

echo.
echo Python was not found.
echo Install Python 3.10 / 3.11 / 3.12, then run install_requirements.bat.
popd
pause
exit /b 1

:run
echo.
echo Starting TategakiXTC GUI Studio...
echo App folder: %CD%
echo Python: "%PY_EXE%" %PY_ARGS%
"%PY_EXE%" %PY_ARGS% tategakiXTC_gui_studio.py
if errorlevel 1 (
  echo.
  echo Launch failed. Check the message shown above.
  echo If dependencies are missing, run install_requirements.bat.
  echo Or run:
  echo   "%PY_EXE%" %PY_ARGS% -m pip install -r requirements.txt
  echo Expected Python versions: 3.10 / 3.11 / 3.12.
  popd
  pause
  exit /b 1
)
popd
pause
exit /b 0
