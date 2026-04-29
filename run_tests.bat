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
echo Install Python 3.10 / 3.11 / 3.12 and make sure py or python is available.
popd
exit /b 1

:run
"%PY_EXE%" %PY_ARGS% -c "from pathlib import Path; import py_compile; files=[Path('build_release_zip.py'), Path('tategakiXTC_gui_core.py'), Path('tategakiXTC_gui_layouts.py'), Path('tategakiXTC_gui_preview_controller.py'), Path('tategakiXTC_gui_results_controller.py'), Path('tategakiXTC_gui_settings_controller.py'), Path('tategakiXTC_gui_studio.py'), Path('tategakiXTC_gui_studio_logic.py'), Path('tategakiXTC_gui_widget_factory.py'), Path('tategakiXTC_worker_logic.py'), *sorted(Path('tests').glob('*.py'))]; [py_compile.compile(str(path), doraise=True) for path in files]"
if errorlevel 1 goto :error

"%PY_EXE%" %PY_ARGS% -m mypy --config-file mypy.ini
if errorlevel 1 goto :error

"%PY_EXE%" %PY_ARGS% -m coverage erase
if errorlevel 1 goto :error

"%PY_EXE%" %PY_ARGS% -m coverage run -m unittest discover -s tests -v
if errorlevel 1 goto :error

"%PY_EXE%" %PY_ARGS% -m coverage report -m --fail-under=60 > coverage-report.txt
if errorlevel 1 goto :error

type coverage-report.txt
if errorlevel 1 goto :error

"%PY_EXE%" %PY_ARGS% -m coverage xml -o coverage.xml
if errorlevel 1 goto :error

"%PY_EXE%" %PY_ARGS% -m coverage html -d htmlcov
if errorlevel 1 goto :error

"%PY_EXE%" %PY_ARGS% tests\generate_golden_images.py --check
if errorlevel 1 goto :error

"%PY_EXE%" %PY_ARGS% build_release_zip.py
if errorlevel 1 goto :error

for %%F in (dist\*-release.zip) do (
  "%PY_EXE%" %PY_ARGS% build_release_zip.py --verify "%%~fF"
  if errorlevel 1 goto :error
)

echo.
echo All tests passed.
echo Mypy config: mypy.ini
echo Coverage report: coverage-report.txt
echo Coverage XML: coverage.xml
echo Coverage HTML: htmlcov\index.html
popd
exit /b 0

:error
echo.
echo Test run failed.
popd
exit /b 1
