@echo off
REM ============================================================
REM  QueryDoc — Build Desktop .exe
REM  Creates dist\QueryDoc\QueryDoc.exe
REM ============================================================

setlocal

echo ============================================================
echo  QueryDoc Desktop Build
echo ============================================================

REM --- Step 1: Build the React frontend into static/ ---
echo.
echo [1/4] Building React frontend...
cd frontend
call npm install
call npm run build
cd ..

if not exist "static\index.html" (
    echo ERROR: Frontend build failed — static\index.html not found.
    exit /b 1
)
echo       Frontend built successfully.

REM --- Step 2: Install build dependencies ---
echo.
echo [2/4] Installing build dependencies (pywebview, pyinstaller)...
pip install pywebview pyinstaller

REM --- Step 3: Run PyInstaller ---
echo.
echo [3/4] Running PyInstaller...
pyinstaller --clean --noconfirm QueryDoc.spec

if not exist "dist\QueryDoc\QueryDoc.exe" (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)
echo       PyInstaller build succeeded.

REM --- Step 4: Copy runtime data alongside the exe ---
echo.
echo [4/4] Copying runtime data files...

REM Copy .env (API keys) — required, the app crashes silently without it
if not exist ".env" (
    echo ERROR: .env not found in %CD%. The packaged app needs GROQ_API_KEY at
    echo        runtime and will crash on startup without it. Aborting.
    exit /b 1
)
copy /Y ".env" "dist\QueryDoc\.env" > nul
echo       Copied .env

REM Copy faiss_store (FAISS index + registry)
if exist "faiss_store" (
    xcopy /E /I /Y "faiss_store" "dist\QueryDoc\faiss_store" > nul
    echo       Copied faiss_store\
)

REM Create uploads directory
if not exist "dist\QueryDoc\uploads" mkdir "dist\QueryDoc\uploads"
echo       Created uploads\

REM Sanity-check that PyInstaller actually bundled the frontend build —
REM this silently ends up empty if static/ wasn't populated before Step 3 ran.
if not exist "dist\QueryDoc\static\index.html" (
    echo ERROR: dist\QueryDoc\static\index.html is missing after build.
    echo        The packaged app will fail to render its UI. Re-run this
    echo        script from a clean state ^(don't invoke pyinstaller directly^).
    exit /b 1
)
echo       Verified static\ was bundled.

echo.
echo ============================================================
echo  BUILD COMPLETE!
echo.
echo  Output: dist\QueryDoc\QueryDoc.exe
echo.
echo  To run: double-click dist\QueryDoc\QueryDoc.exe
echo  or:     cd dist\QueryDoc ^&^& QueryDoc.exe
echo ============================================================

endlocal
