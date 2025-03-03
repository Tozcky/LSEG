import os
import time
import subprocess
import difflib
import base64
import configparser
import socket
from cryptography.fernet import Fernet
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

FROM_EMAIL = config['EMAIL']['FROM']
TO_EMAIL = config['EMAIL']['TO']
CC_EMAIL = config['EMAIL']['CC']

# Set up logging
logger = setup_logging("config_monitor")

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

# Send Alert via Email
def send_alert(subject, message):
    """
    Send an email alert using the mail_it.sh script.
    """
    # Get server details
    server_name = socket.gethostname()
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # Format subject and message
    formatted_subject = f"{subject} - Server: {server_name} - Time: {current_time}"
    formatted_message = f"Server: {server_name}\nTime: {current_time}\n\n{message}"

    logger.info(f"Sending alert: {formatted_subject} - {formatted_message}")
    subprocess.run([EMAIL_SCRIPT, "-s", formatted_subject, "-m", formatted_message, "-f", FROM_EMAIL, "-t", TO_EMAIL, "-c", CC_EMAIL])

# Start Monitoring
def start_monitoring():
    """
    Start the configuration file monitoring process.
    """
    logger.info("Starting configuration file monitoring...")
    last_modified_time = 0

    while True:
        if os.path.exists(PAUSE_FLAG):
            time.sleep(1)
            continue

        config_path = os.path.join(APP_ROOT, CONFIG_FILE)
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found: {config_path}")
            time.sleep(10)
            continue

        current_modified_time = os.path.getmtime(config_path)
        if current_modified_time != last_modified_time:
            last_modified_time = current_modified_time
            message = compare_config()
            if "Configuration file has changed" in message:
                send_alert("Configuration File Change Alert", message)

        time.sleep(5)

if __name__ == "__main__":
    start_monitoring()