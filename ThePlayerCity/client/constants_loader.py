# constants_loader.py
import os

def get_registration_timeout() -> float:
    """Reads REGISTRATION_TIMEOUT from ClientConstants.md. Falls back to 10.0 if not found."""
    path = os.path.join(os.path.dirname(__file__), 'ClientConstants.md')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('REGISTRATION_TIMEOUT:'):
                        val_str = line.split('REGISTRATION_TIMEOUT:', 1)[1].strip()
                        if val_str:
                            return float(val_str)
        except Exception as e:
            print(f"[CLIENT WARNING] Failed to read ClientConstants.md: {e}")
    return 10.0
