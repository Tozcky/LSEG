import os
import hashlib
import subprocess
import time
import re
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
ENCRYPTION_KEY = config['SECURITY']['ENCRYPTION_KEY'].encode()
FROM_EMAIL = config['EMAIL']['FROM']
TO_EMAIL = config['EMAIL']['TO']

# Set up logging
logger = setup_logging("monitor")

# Change ID Validation
def is_valid_change_id(change_id: str) -> bool:
    """
    Validate the Change ID format.
    - Must start with "CHG" followed by numbers.
    """
    pattern = r"^CHG\d+$"
    return re.match(pattern, change_id) is not None

# Encryption Setup
def encrypt_data(data: str) -> bytes:
    """
    Encrypt data using Fernet symmetric encryption.
    """
    cipher = Fernet(ENCRYPTION_KEY)
    return cipher.encrypt(data.encode())

def decrypt_data(data: bytes) -> str:
    """
    Decrypt data using Fernet symmetric encryption.
    """
    cipher = Fernet(ENCRYPTION_KEY)
    return cipher.decrypt(data).decode()

# Save Encrypted Blueprint
def save_blueprint():
    """
    Save the current state of application.config as an encrypted blueprint.
    """
    config_path = os.path.join(APP_ROOT, CONFIG_FILE)
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            content = f.read()
        encrypted_content = encrypt_data(content)
        with open(os.path.join(BLUEPRINT_DIR, "config_blueprint.enc"), "wb") as f:
            f.write(encrypted_content)
        logger.info("Blueprint saved successfully.")
    else:
        logger.error(f"Config file {CONFIG_FILE} not found!")

# Compare Config File with Blueprint
def compare_config():
    """
    Compare the current application.config with the blueprint.
    - Returns a detailed diff if changes are detected.
    """
    config_path = os.path.join(APP_ROOT, CONFIG_FILE)
    blueprint_path = os.path.join(BLUEPRINT_DIR, "config_blueprint.enc")
    if not os.path.exists(blueprint_path):
        logger.error("Blueprint not found!")
        return "Blueprint not found!"
    """
    load the current encrypted blueprint.
    """ 
    with open(config_path, "r") as f:
        current_content = f.read().splitlines()
    """
    decrypt it for comparison.
    """ 
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
    Handles file system events (modify, create, delete).
    """
    def on_modified(self, event):
        if event.is_directory or os.path.exists(PAUSE_FLAG):
            return
        file_path = os.path.relpath(event.src_path, APP_ROOT)
        if file_path == CONFIG_FILE:
            message = compare_config()
            send_alert("Configuration File Change Alert", message)
        elif not any(folder in file_path.split(os.sep) for folder in EXCLUDED_DIRS):
            logger.info(f"File {file_path} was modified.")
            send_alert("File Modified Alert", f"File: {file_path}\nEvent: Modified\nTime: {time.strftime('%Y-%m-%d %H:%M:%S')}\nServer Details: Host: {socket.gethostname()}, IP: {socket.gethostbyname(socket.gethostname())}")
    
    def on_created(self, event):
        if event.is_directory or os.path.exists(PAUSE_FLAG):
            return
        file_path = os.path.relpath(event.src_path, APP_ROOT)
        if not any(folder in file_path.split(os.sep) for folder in EXCLUDED_DIRS):
            logger.info(f"New file {file_path} was created.")
            send_alert("File Created Alert", f"File: {file_path}\nEvent: Created\nTime: {time.strftime('%Y-%m-%d %H:%M:%S')}\nServer Details: Host: {socket.gethostname()}, IP: {socket.gethostbyname(socket.gethostname())}")
    
    def on_deleted(self, event):
        if event.is_directory or os.path.exists(PAUSE_FLAG):
            return
        file_path = os.path.relpath(event.src_path, APP_ROOT)
        if not any(folder in file_path.split(os.sep) for folder in EXCLUDED_DIRS):
            logger.info(f"File {file_path} was deleted.")
            send_alert("File Deleted Alert", f"File: {file_path}\nEvent: Deleted\nTime: {time.strftime('%Y-%m-%d %H:%M:%S')}\nServer Details: Host: {socket.gethostname()}, IP: {socket.gethostbyname(socket.gethostname())}")

# Send Alert via Email
def send_alert(subject, message):
    """
    Send an email alert using the mail_it.sh script.
    """
    logger.info(f"Sending alert: {subject} - {message}")
    subprocess.run([EMAIL_SCRIPT, "-s", subject, "-m", message, "-f", FROM_EMAIL, "-t", TO_EMAIL])

# Pause Monitoring
def pause_monitoring(change_id: str):
    """
    Pause monitoring by creating a pause flag file.
    """
    if not is_valid_change_id(change_id):
        logger.error(f"Invalid Change ID: {change_id}.")
        return
    open(PAUSE_FLAG, "a").close()
    logger.info(f"Monitoring paused for Change ID: {change_id}")
    send_alert("Monitoring Paused", f"Monitoring paused for Change ID: {change_id}")

# Resume Monitoring
def resume_monitoring(change_id: str):
    """
    Resume monitoring by removing the pause flag file.
    """
    if not is_valid_change_id(change_id):
        logger.error(f"Invalid Change ID: {change_id}.")
        return
    if os.path.exists(PAUSE_FLAG):
        os.remove(PAUSE_FLAG)
    logger.info(f"Monitoring resumed for Change ID: {change_id}")
    send_alert("Monitoring Resumed", f"Monitoring resumed for Change ID: {change_id}")

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
    save_blueprint()
    start_monitoring()