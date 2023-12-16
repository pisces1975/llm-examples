import os
import threading

def get_running_state() -> str:
    return f"[{os.getpid()}]-[{threading.get_ident()}] "