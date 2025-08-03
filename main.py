# main.py
import sys
import subprocess
import platform

MIN_PYTHON = (3, 12)
REQUIRED_MODULES = ["playwright", "discord", "clipboard", "stripe", "asyncio"]

def check_python_version():
    if sys.version_info < MIN_PYTHON:
        sys.exit(f"[X] Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required.")

def check_dependencies():
    missing = []
    for module in REQUIRED_MODULES:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)

    if missing:
        print(f"[!] Missing dependencies: {', '.join(missing)}")
        print("Installing with pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])

def run_bot():
    import ghost_purchase_and_support_integration
    ghost_purchase_and_support_integration.run()

if __name__ == "__main__":
    print("[✓] Booting Ghost Support Console...")
    check_python_version()
    check_dependencies()
    run_bot()