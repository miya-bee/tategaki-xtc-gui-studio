@echo off
setlocal

set "PYTHONDONTWRITEBYTECODE=1"

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul 2>nul
if errorlevel 1 (
  echo.
  echo Could not switch to the script folder.
  exit /b 1
)

set "PY_EXE="
set "PY_ARGS="
set "PY_VERSION_CHECK=import sys; assert sys.version_info.major == 3 and sys.version_info.minor in [10, 11, 12]"
where py >nul 2>nul
if not errorlevel 1 (
  for %%V in (3.12 3.11 3.10) do (
    py -%%V -c "%PY_VERSION_CHECK%" >nul 2>nul
    if not errorlevel 1 (
      set "PY_EXE=py"
      set "PY_ARGS=-%%V"
      goto :install
    )
  )
)

where python >nul 2>nul
if not errorlevel 1 (
  python -c "%PY_VERSION_CHECK%" >nul 2>nul
  if not errorlevel 1 (
    set "PY_EXE=python"
    goto :install
  )
)

for %%V in (312 311 310) do (
  if exist "%LocalAppData%\Programs\Python\Python%%V\python.exe" (
    "%LocalAppData%\Programs\Python\Python%%V\python.exe" -c "%PY_VERSION_CHECK%" >nul 2>nul
    if not errorlevel 1 (
      set "PY_EXE=%LocalAppData%\Programs\Python\Python%%V\python.exe"
      goto :install
    )
  )
)

echo.
echo Python was not found.
echo Install Python 3.10 / 3.11 / 3.12 and make sure py or python is available.
popd
pause
exit /b 1

:install
"%PY_EXE%" %PY_ARGS% -m pip install --upgrade pip
if errorlevel 1 (
  echo.
  echo Failed to upgrade pip.
  popd
  pause
  exit /b 1
)

"%PY_EXE%" %PY_ARGS% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Failed to install requirements.txt.
  popd
  pause
  exit /b 1
)

echo.
echo Dependencies installed successfully.
popd
pause
exit /b 0
