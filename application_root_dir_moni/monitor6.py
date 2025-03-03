import os
import hashlib
import subprocess
import time
import re
import base64
import difflib
import socket
import configparser
from cryptography.fernet import Fernet
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from logging_setup import setup_logging

# Load configurations from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Configuration
APP_ROOT = config['PATHS']['APP_ROOT']
CONFIG_FILE = config['PATHS']['CONFIG_FILE']
BLUEPRINT_DIR = config['PATHS']['BLUEPRINT_DIR']
EMAIL_SCRIPT = config['PATHS']['EMAIL_SCRIPT']
PAUSE_FLAG = config['PATHS']['PAUSE_FLAG']
EXCLUDED_DIRS = set(config['EXCLUSIONS']['EXCLUDED_DIRS'].split(','))
EXCLUDED_FILES = {'.swp', '.swpx', '~', '.swx', '4913', '.tmp'}  # Ignore temporary and backup files

# Validate and decode encryption key
def get_valid_fernet_key():
    try:
        key = config['SECURITY']['ENCRYPTION_KEY']
        key = key.strip()
        if len(key) % 4:
            key += '=' * (4 - len(key) % 4)
        decoded_key = base64.urlsafe_b64decode(key)
        if len(decoded_key) != 32:
            raise ValueError("Invalid Fernet key length")
        return Fernet(base64.urlsafe_b64encode(decoded_key))
    except Exception as e:
        logger.error(f"Invalid Fernet key: {e}")
        raise ValueError("Invalid Fernet key: Ensure it is a 32-byte base64-encoded string") from e

cipher = get_valid_fernet_key()

FROM_EMAIL = config['EMAIL']['FROM']
TO_EMAIL = config['EMAIL']['TO']
CC_EMAIL = config['EMAIL']['CC']

# Set up logging
logger = setup_logging("monitor")

# Encryption Setup
def encrypt_data(data: str) -> bytes:
    """
    Encrypt data using Fernet symmetric encryption.
    """
    return cipher.encrypt(data.encode())

def decrypt_data(data: bytes) -> str:
    """
    Decrypt data using Fernet symmetric encryption.
    """
    return cipher.decrypt(data).decode()

# Get Latest Blueprint File
def get_latest_blueprint():
    """
    Retrieve the latest .enc blueprint file based on system time.
    """
    enc_files = [f for f in os.listdir(BLUEPRINT_DIR) if f.endswith(".enc")]
    if not enc_files:
        logger.error("No blueprint files found!")
        return None
    latest_file = max(enc_files, key=lambda f: os.path.getctime(os.path.join(BLUEPRINT_DIR, f)))
    return os.path.join(BLUEPRINT_DIR, latest_file)

# Compare Config File with Blueprint
def compare_config():
    """
    Compare the current application.config with the latest blueprint.
    - Returns a detailed diff if changes are detected.
    """
    config_path = os.path.join(APP_ROOT, CONFIG_FILE)
    blueprint_path = get_latest_blueprint()
    if not blueprint_path:
        return "No blueprint found!"

    with open(config_path, "r") as f:
        current_content = f.read().splitlines()

    with open(blueprint_path, "rb") as f:
        blueprint_content = decrypt_data(f.read()).splitlines()

    # Generate a detailed diff
    diff = difflib.unified_diff(
        blueprint_content,
        current_content,
        fromfile="blueprint",
        tofile="current",
        lineterm=""
    )
    diff_output = "\n".join(diff)

    if diff_output:
        logger.info("Configuration file has changed.")
        return f"Configuration file has changed. Details:\n{diff_output}"
    logger.info("No changes detected in the configuration file.")
    return "No changes detected."

# File Event Handler
class MonitorHandler(FileSystemEventHandler):
    """
    Handles file system events (modify, create, delete), excluding specific directories and temporary files.
    Implements debouncing to avoid flooding alerts.
    """
    def __init__(self):
        self.last_event_time = {}  # Track the last event time for each file/directory

    def on_any_event(self, event):
        if os.path.exists(PAUSE_FLAG):
            return

        file_name = os.path.basename(event.src_path)
        file_path = os.path.relpath(event.src_path, APP_ROOT)

        # Check if the file or directory is inside an excluded directory
        for excluded_dir in EXCLUDED_DIRS:
            excluded_path = os.path.join(APP_ROOT, excluded_dir.strip())
            if event.src_path.startswith(excluded_path):
                return  # Ignore events from excluded directories

        # Ignore temporary files
        if any(file_name.endswith(ext) for ext in EXCLUDED_FILES):
            return

        # Debounce logic: Group events that occur within 2 seconds
        current_time = time.time()
        last_time = self.last_event_time.get(event.src_path, 0)
        if current_time - last_time < 2:  # 2-second debounce window
            return
        self.last_event_time[event.src_path] = current_time

        # Log and send alerts
        if event.event_type == "modified":
            if not event.is_directory:
                logger.info(f"File modified: {event.src_path}")
                send_alert("File Modified", f"{event.src_path} has been modified.")
                if file_path == CONFIG_FILE:
                    message = compare_config()
                    send_alert("Configuration File Change Alert", message)
            else:
                logger.info(f"Directory modified: {event.src_path}")
                send_alert("Directory Modified", f"{event.src_path} has been modified.")
        elif event.event_type == "created":
            if not event.is_directory:
                logger.info(f"New file created: {event.src_path}")
                send_alert("New File Created", f"{event.src_path} has been created.")
            else:
                logger.info(f"New directory created: {event.src_path}")
                send_alert("New Directory Created", f"{event.src_path} has been created.")
        elif event.event_type == "deleted":
            if not event.is_directory:
                logger.info(f"File deleted: {event.src_path}")
                send_alert("File Deleted", f"{event.src_path} has been deleted.")
            else:
                logger.info(f"Directory deleted: {event.src_path}")
                send_alert("Directory Deleted", f"{event.src_path} has been deleted.")

# Send Alert via Email
def send_alert(subject, message):
    """
    Send an email alert using the mail_it.sh script.
    """
    logger.info(f"Sending alert: {subject} - {message}")
    subprocess.run([EMAIL_SCRIPT, "-s", subject, "-m", message, "-f", FROM_EMAIL, "-t", TO_EMAIL, "-c", CC_EMAIL])

# Start Monitoring
def start_monitoring():
    """
    Start the file system monitoring process.
    """
    logger.info("Starting monitoring...")
    observer = Observer()
    event_handler = MonitorHandler()
    observer.schedule(event_handler, APP_ROOT, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_monitoring()