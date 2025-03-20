import os
import time
import subprocess
import difflib
import base64
import configparser
import socket
from cryptography.fernet import Fernet
from logging_setup import setup_logging
import argparse
import logging.handlers  # For log rotation

# Load configurations from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Configuration
APP_ROOT = config['PATHS']['APP_ROOT']
CONFIG_FILE = config['PATHS']['CONFIG_FILE']
BLUEPRINT_DIR = config['PATHS']['BLUEPRINT_DIR']
EMAIL_SCRIPT = config['PATHS']['EMAIL_SCRIPT']
PAUSE_FLAG = config['PATHS']['PAUSE_FLAG']
CHANGE_LOG = config['PATHS']['CHANGE_LOG']

FROM_EMAIL = config['EMAIL']['FROM']
TO_EMAIL = config['EMAIL']['TO']
CC_EMAIL = config['EMAIL']['CC']

# Set up logging with rotation
logger = setup_logging("config_monitor")
handler = logging.handlers.RotatingFileHandler('monitor.log', maxBytes=5*1024*1024, backupCount=3)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Validate and decode encryption key
def get_valid_fernet_key():
    try:
        key = config['SECURITY']['ENCRYPTION_KEY'].strip()
        if len(key) % 4:
            key += '=' * (4 - len(key) % 4)
        decoded_key = base64.urlsafe_b64decode(key)
        if len(decoded_key) != 32:
            raise ValueError("Invalid Fernet key length")
        return Fernet(base64.urlsafe_b64encode(decoded_key))
    except Exception as e:
        logger.error(f"Invalid Fernet key: {e}")
        raise

cipher = get_valid_fernet_key()

# Encryption Setup
def encrypt_data(data: str) -> bytes:
    return cipher.encrypt(data.encode())

def decrypt_data(data: bytes) -> str:
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
        current_content = f.read().splitlines()

    with open(blueprint_path, "rb") as f:
        blueprint_content = decrypt_data(f.read()).splitlines()

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

# Send Alert via Email (HTML Formatting)
def send_alert(subject, message):
    server_name = socket.gethostname()
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    formatted_subject = f"{subject} - Server: {server_name} - Time: {current_time}"

    # Convert diff to HTML with color formatting
    html_lines = []
    for line in message.splitlines():
        if line.startswith('+'):
            html_lines.append(f"<span style='color: green;'>{line}</span>")
        elif line.startswith('-'):
            html_lines.append(f"<span style='color: red;'>{line}</span>")
        elif line.startswith('@@'):
            html_lines.append(f"<span style='color: blue; font-weight: bold;'>{line}</span>")
        else:
            html_lines.append(line)

    formatted_diff = "<br>".join(html_lines)

    html_message = f"""
    <html>
    <body>
        <p><strong>Server:</strong> {server_name}<br>
        <strong>Time:</strong> {current_time}</p>
        <div style='font-family: monospace; background-color: #f4f4f4; padding: 10px;'>{formatted_diff}</div>
    </body>
    </html>
    """

    logger.info(f"Sending alert: {formatted_subject}")
    subprocess.run([EMAIL_SCRIPT, "-s", formatted_subject, "-m", html_message, "-f", FROM_EMAIL, "-t", TO_EMAIL, "-c", CC_EMAIL])


# Stop Monitoring with Change ID
def stop_monitoring(change_id, description):
    with open(PAUSE_FLAG, 'w') as f:
        f.write("Paused")
    with open(CHANGE_LOG, 'a') as log:
        log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] STOPPED - Change ID: {change_id}, Reason: {description}\n")
    send_alert("Config Monitoring Stopped", f"Change ID: {change_id}\nReason: {description}")

# Resume Monitoring with Change ID
def resume_monitoring(change_id, description):
    if os.path.exists(PAUSE_FLAG):
        os.remove(PAUSE_FLAG)
    with open(CHANGE_LOG, 'a') as log:
        log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] RESUMED - Change ID: {change_id}, Reason: {description}\n")
    send_alert("Config Monitoring Resumed", f"Change ID: {change_id}\nReason: {description}")

# Start Monitoring
def start_monitoring():
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

# CLI Commands
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configuration File Monitor")
    parser.add_argument('--stop', nargs=2, metavar=('CHANGE_ID', 'DESCRIPTION'), help='Stop monitoring with change ID and description')
    parser.add_argument('--resume', nargs=2, metavar=('CHANGE_ID', 'DESCRIPTION'), help='Resume monitoring with change ID and description')
    args = parser.parse_args()

    if args.stop:
        stop_monitoring(args.stop[0], args.stop[1])
    elif args.resume:
        resume_monitoring(args.resume[0], args.resume[1])
    else:
        start_monitoring()
