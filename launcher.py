"""
QueryDoc — Desktop Launcher
Entry point for the packaged .exe application.
Starts the FastAPI server in a background thread, shows a splash screen,
then opens the main application window.
"""

import os
import sys
import time
import signal
import threading
import logging
import webbrowser

# ---------------------------------------------------------------------------
# Path resolution — works in both dev mode and PyInstaller frozen mode
# ---------------------------------------------------------------------------

def get_app_dir():
    """Return the directory where the application lives."""
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller bundle — exe is in dist/QueryDoc/
        return os.path.dirname(sys.executable)
    else:
        # Running as a normal Python script
        return os.path.dirname(os.path.abspath(__file__))


APP_DIR = get_app_dir()

# Set the working directory so that relative paths in the app resolve correctly
os.chdir(APP_DIR)

# ---------------------------------------------------------------------------
# Logging — write to a log file next to the exe
# ---------------------------------------------------------------------------

LOG_FILE = os.path.join(APP_DIR, "querydoc.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("QueryDoc-Launcher")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HOST = "127.0.0.1"
PORT = 8765
SERVER_URL = f"http://{HOST}:{PORT}"

# ---------------------------------------------------------------------------
# Splash screen HTML
# ---------------------------------------------------------------------------

SPLASH_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>QueryDoc</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 40%, #24243e 100%);
    color: #e0e0e0;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    overflow: hidden;
  }

  .splash {
    text-align: center;
    animation: fadeIn 0.6s ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .logo {
    font-size: 48px;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 12px;
    letter-spacing: -1px;
  }

  .tagline {
    font-size: 14px;
    color: #8888aa;
    margin-bottom: 48px;
    letter-spacing: 0.5px;
  }

  /* Spinner */
  .spinner {
    width: 48px;
    height: 48px;
    margin: 0 auto 28px;
    border: 3px solid rgba(102, 126, 234, 0.15);
    border-top-color: #667eea;
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .status {
    font-size: 13px;
    color: #7777aa;
    animation: pulse 2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 0.6; }
    50%      { opacity: 1; }
  }

  /* Floating particles */
  .particles {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    overflow: hidden;
    z-index: -1;
  }

  .particle {
    position: absolute;
    width: 4px;
    height: 4px;
    background: rgba(102, 126, 234, 0.3);
    border-radius: 50%;
    animation: float linear infinite;
  }

  @keyframes float {
    0%   { transform: translateY(100vh) scale(0); opacity: 0; }
    10%  { opacity: 1; }
    90%  { opacity: 1; }
    100% { transform: translateY(-10vh) scale(1); opacity: 0; }
  }
</style>
</head>
<body>
  <div class="particles" id="particles"></div>
  <div class="splash">
    <div class="logo">QueryDoc</div>
    <div class="tagline">AI-Powered Document Assistant</div>
    <div class="spinner"></div>
    <div class="status">Loading engine &amp; models…</div>
  </div>

  <script>
    // Generate floating particles
    const container = document.getElementById('particles');
    for (let i = 0; i < 30; i++) {
      const p = document.createElement('div');
      p.classList.add('particle');
      p.style.left = Math.random() * 100 + '%';
      p.style.animationDuration = (6 + Math.random() * 10) + 's';
      p.style.animationDelay = (Math.random() * 8) + 's';
      p.style.width = p.style.height = (2 + Math.random() * 4) + 'px';
      container.appendChild(p);
    }
  </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------

_server_thread = None
_uvicorn_server = None


def start_server():
    """Start the Uvicorn server in a background thread."""
    global _uvicorn_server
    import uvicorn

    logger.info("Starting Uvicorn server on %s:%s ...", HOST, PORT)

    config = uvicorn.Config(
        "server:app",
        host=HOST,
        port=PORT,
        log_level="info",
        reload=False,  # reload is incompatible with PyInstaller
    )
    _uvicorn_server = uvicorn.Server(config)
    _uvicorn_server.run()


def wait_for_server(timeout: int = 120) -> bool:
    """Block until the server responds to a health check or timeout expires."""
    import urllib.request
    import urllib.error

    logger.info("Waiting for server to become ready (timeout=%ds)...", timeout)
    start = time.time()

    while time.time() - start < timeout:
        try:
            req = urllib.request.urlopen(f"{SERVER_URL}/api/status", timeout=2)
            if req.status == 200:
                logger.info("Server is ready! (took %.1fs)", time.time() - start)
                return True
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(1)

    logger.error("Server did not start within %ds.", timeout)
    return False


def stop_server():
    """Signal the Uvicorn server to shut down."""
    global _uvicorn_server
    if _uvicorn_server is not None:
        logger.info("Shutting down server...")
        _uvicorn_server.should_exit = True


# ---------------------------------------------------------------------------
# UI — splash screen → main window (with browser fallback)
# ---------------------------------------------------------------------------

def open_ui():
    """
    Open the application UI with a splash loading screen.
    Shows a beautiful loading animation while the server boots,
    then navigates to the main app once ready.
    Falls back to the system browser if pywebview isn't available.
    """
    try:
        import webview

        logger.info("Opening splash screen...")

        # Create the window with splash HTML first
        window = webview.create_window(
            title="QueryDoc — Loading...",
            html=SPLASH_HTML,
            width=520,
            height=400,
            resizable=False,
            frameless=True,
        )

        def on_loaded():
            """Called once the webview window is shown. Wait for server, then switch."""
            logger.info("Splash screen visible. Waiting for server...")

            if wait_for_server():
                # Server is ready — resize and navigate to the real app
                logger.info("Navigating to main application...")
                window.set_title("QueryDoc — AI Document Assistant")
                window.resize(1280, 820)
                window.resizable = True
                window.load_url(SERVER_URL)
            else:
                # Server failed to start
                window.load_html("""
                    <html><body style="font-family:Segoe UI,sans-serif;background:#1a1a3e;color:#ff6b6b;
                    display:flex;justify-content:center;align-items:center;height:100vh;text-align:center;">
                    <div>
                        <h2>Failed to Start</h2>
                        <p style="color:#8888aa;">Check querydoc.log for details.</p>
                    </div>
                    </body></html>
                """)

        # Start webview — the on_loaded callback runs in a separate thread
        webview.start(on_loaded)
        logger.info("Window closed by user.")

    except ImportError:
        logger.warning("pywebview not available — falling back to system browser.")
        if wait_for_server():
            webbrowser.open(SERVER_URL)
        # Keep the process alive until Ctrl+C
        try:
            logger.info("Press Ctrl+C to stop the server.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 60)
    logger.info("QueryDoc Desktop Launcher")
    logger.info("App directory : %s", APP_DIR)
    logger.info("Server URL    : %s", SERVER_URL)
    logger.info("=" * 60)

    # Start server in background thread
    global _server_thread
    _server_thread = threading.Thread(target=start_server, daemon=True)
    _server_thread.start()

    # Open the UI with splash screen (blocks until closed)
    # The splash screen handles waiting for the server internally
    open_ui()

    # Cleanup
    stop_server()
    logger.info("QueryDoc exited.")


if __name__ == "__main__":
    main()
