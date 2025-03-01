import os
import hashlib
import subprocess
import time
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
ENCRYPTION_KEY = base64.b64decode(config['SECURITY']['ENCRYPTION_KEY'])
FROM_EMAIL = config['EMAIL']['FROM']
TO_EMAIL = config['EMAIL']['TO']
CC_EMAIL = config.get('EMAIL', 'CC', fallback='')

# Set up logging
logger = setup_logging("monitor")

# Encryption Setup
def encrypt_data(data: str) -> bytes:
    cipher = Fernet(ENCRYPTION_KEY)
    return cipher.encrypt(data.encode())

def decrypt_data(data: bytes) -> str:
    cipher = Fernet(ENCRYPTION_KEY)
    return cipher.decrypt(data).decode()

# Get Latest Blueprint File
def get_latest_blueprint():
    enc_files = [f for f in os.listdir(BLUEPRINT_DIR) if f.endswith(".enc")]
    if not enc_files:
        logger.error("No blueprint files found!")
        return None
    latest_file = max(enc_files, key=lambda f: os.path.getctime(os.path.join(BLUEPRINT_DIR, f)))
    return os.path.join(BLUEPRINT_DIR, latest_file)

# Compare Config File with Blueprint
def compare_config():
    config_path = os.path.join(APP_ROOT, CONFIG_FILE)
    blueprint_path = get_latest_blueprint()
    if not blueprint_path:
        return "No blueprint found!"
    
    with open(config_path, "r") as f:
        current_content = f.readlines()

    with open(blueprint_path, "rb") as f:
        blueprint_content = decrypt_data(f.read()).splitlines()
    
    diff = difflib.unified_diff(blueprint_content, current_content, fromfile="blueprint", tofile="current", lineterm="")
    diff_output = "\n".join(diff)
    
    if diff_output:
        logger.info("Configuration file has changed.")
        return format_diff_for_email(diff_output)
    return "No changes detected."

# Format diff output in HTML for email
def format_diff_for_email(diff_output):
    formatted_diff = "<pre>"
    for line in diff_output.split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            formatted_diff += f'<span style="color: red;">{line}</span><br>'
        else:
            formatted_diff += line + "<br>"
    formatted_diff += "</pre>"
    return formatted_diff

# Send Alert via Email
def send_alert(subject, message, is_html=False):
    logger.info(f"Sending alert: {subject}")
    email_cmd = [EMAIL_SCRIPT, "-s", subject, "-m", message, "-f", FROM_EMAIL, "-t", TO_EMAIL]
    if CC_EMAIL:
        email_cmd += ["-c", CC_EMAIL]
    if is_html:
        email_cmd.append("-h")
    subprocess.run(email_cmd)

# File Event Handler
class MonitorHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory or os.path.exists(PAUSE_FLAG):
            return
        if any(event.src_path.startswith(d) for d in EXCLUDED_DIRS):
            return
        logger.info(f"File modified: {event.src_path}")
        if os.path.basename(event.src_path) == CONFIG_FILE:
            message = compare_config()
            send_alert("Configuration File Change Alert", message, is_html=True)
        else:
            send_alert("File Modified", f"File modified: {event.src_path}")

    def on_created(self, event):
        if event.is_directory or os.path.exists(PAUSE_FLAG):
            return
        if any(event.src_path.startswith(d) for d in EXCLUDED_DIRS):
            return
        logger.info(f"New file created: {event.src_path}")
        send_alert("New File Created", f"A new file was created: {event.src_path}")

    def on_deleted(self, event):
        if event.is_directory or os.path.exists(PAUSE_FLAG):
            return
        if any(event.src_path.startswith(d) for d in EXCLUDED_DIRS):
            return
        logger.info(f"File deleted: {event.src_path}")
        send_alert("File Deleted", f"A file was deleted: {event.src_path}")

# Start Monitoring
def start_monitoring():
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
