@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo MultiDock1.0 - Standalone Windows build
echo Direct Meeko Python API - no mk_prepare_ligand.exe subprocess
echo ============================================================

set "PY=C:\MultiDock\meeko_env\Scripts\python.exe"
if not exist "%PY%" (
  echo ERROR: %PY% not found.
  echo Build this EXE on the computer that has the Python 3.11 Meeko environment.
  echo Suggested environment:
  echo   py -3.11 -m venv C:\MultiDock\meeko_env
  echo   C:\MultiDock\meeko_env\Scripts\python.exe -m pip install -U pip
  echo   C:\MultiDock\meeko_env\Scripts\python.exe -m pip install meeko rdkit scipy gemmi pyinstaller
  pause
  exit /b 1
)

if not exist "vina.exe" (
  echo ERROR: vina.exe not found beside this BAT file.
  pause
  exit /b 1
)
if not exist "MultiDock1.0.ico" (
  echo ERROR: MultiDock1.0.ico not found.
  pause
  exit /b 1
)

"%PY%" -c "import rdkit, meeko, scipy, gemmi; print('RDKit', rdkit.__version__); print('Meeko', meeko.__version__)"
if errorlevel 1 (
  echo ERROR: RDKit/Meeko/SciPy/Gemmi environment is incomplete.
  pause
  exit /b 1
)

"%PY%" -m pip install -U pyinstaller
if errorlevel 1 goto :fail

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MultiDock1.0.spec del /q MultiDock1.0.spec

"%PY%" -m PyInstaller ^
 --noconfirm --clean --onefile --windowed ^
 --name "MultiDock1.0" ^
 --icon "MultiDock1.0.ico" ^
 --collect-all rdkit ^
 --collect-all meeko ^
 --collect-all scipy ^
 --collect-all gemmi ^
 --add-binary "vina.exe;." ^
 --add-data "multidock_logo.png;." ^
 --add-data "MultiDock1.0.ico;." ^
 "MultiDock1.0_Standalone.py"
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo BUILD FINISHED
echo Output: dist\MultiDock1.0.exe
echo Test by copying ONLY MultiDock1.0.exe to another Windows PC.
echo Test: SDF -^> PDBQT, then 1-2 Vina docking jobs.
echo ============================================================
pause
exit /b 0

:fail
echo.
echo BUILD FAILED. Copy the complete console output for diagnosis.
pause
exit /b 1
