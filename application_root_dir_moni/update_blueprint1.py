import os
import sys
import re
import base64
import subprocess
import configparser
from datetime import datetime
import socket
from cryptography.fernet import Fernet
from logging_setup import setup_logging

# Load configurations from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Configuration Paths
APP_ROOT = config['PATHS']['APP_ROOT']
CONFIG_FILE = config['PATHS']['CONFIG_FILE']
BLUEPRINT_DIR = config['PATHS']['BLUEPRINT_DIR']
EMAIL_SCRIPT = config['PATHS']['EMAIL_SCRIPT']

# Email Config
FROM_EMAIL = config['EMAIL']['FROM']
TO_EMAIL = config['EMAIL']['TO']
CC_EMAIL = config['EMAIL'].get('CC', '')  # CC is optional

# Set up logging
logger = setup_logging("update_blueprint")

# Validate and Load Encryption Key
def get_encryption_key():
    """
    Retrieves and validates the encryption key from config.ini.
    Ensures it is a valid 32-byte (44-character) Base64 key.
    """
    key = config['SECURITY']['ENCRYPTION_KEY'].strip()

    # Check if the key length is valid
    if len(key) != 44:
        logger.error("Invalid ENCRYPTION_KEY length. Expected a 44-character Base64-encoded key.")
        sys.exit(1)

    try:
        return Fernet(key)  # Return a valid Fernet cipher instance
    except Exception as e:
        logger.error(f"Invalid encryption key: {e}")
        sys.exit(1)

# Initialize the encryption cipher
cipher = get_encryption_key()

# Change ID Validation
def is_valid_change_id(change_id: str) -> bool:
    """Validate Change ID format (e.g., CHG12345)."""
    pattern = r"^CHG\d+$"
    return re.match(pattern, change_id) is not None

# Encryption Function
def encrypt_data(data: str) -> bytes:
    """Encrypt data using Fernet symmetric encryption."""
    return cipher.encrypt(data.encode())

# Save Encrypted Blueprint
def save_blueprint(change_id: str):
    """
    Saves the current application.config as an encrypted blueprint.
    Sends an acknowledgment email upon successful update.
    """
    config_path = os.path.join(APP_ROOT, CONFIG_FILE)

    if not os.path.exists(config_path):
        logger.error(f"Config file {CONFIG_FILE} not found!")
        return

    # Read configuration file content
    with open(config_path, "r") as f:
        content = f.read()

    # Encrypt and save blueprint
    encrypted_content = encrypt_data(content)
    blueprint_path = os.path.join(BLUEPRINT_DIR, f"config_blueprint_{change_id}.enc")

    with open(blueprint_path, "wb") as f:
        f.write(encrypted_content)

    logger.info(f"Blueprint updated with Change ID: {change_id}")
    send_ack_email(change_id, config_path, blueprint_path)

# Send Acknowledgment Email
def send_ack_email(change_id: str, original_file: str, blueprint_file: str):
    """
    Sends an acknowledgment email after updating the blueprint.
    Includes timestamp, Change ID, file paths, and server details.
    """
    # Get server details
    server_host = socket.gethostname()
    server_ip = socket.gethostbyname(server_host)
    server_details = f"Host: {server_host}, IP: {server_ip}"

    # Prepare email subject and body
    subject = f"Blueprint Update Acknowledgment - {change_id}"
    body = f"""
    Blueprint Update Details:
    - Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    - Change ID: {change_id}
    - Original File: {original_file}
    - Blueprint File: {blueprint_file}
    - Server Details: {server_details}
    """

    # Send email using the mail script
    try:
        email_command = [EMAIL_SCRIPT, "-s", subject, "-m", body, "-f", FROM_EMAIL, "-t", TO_EMAIL]
        if CC_EMAIL:
            email_command.extend(["-c", CC_EMAIL])  # Add CC if available
        subprocess.run(email_command, check=True)
        logger.info(f"Acknowledgment email sent for Change ID: {change_id}")
    except Exception as e:
        logger.error(f"Failed to send acknowledgment email: {e}")

# Main Execution
if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("Usage: python update_blueprint.py <change_id>")
        sys.exit(1)

    change_id = sys.argv[1]

    if not is_valid_change_id(change_id):
        logger.error(f"Invalid Change ID: {change_id}. It must start with 'CHG' followed by numbers.")
        sys.exit(1)

    save_blueprint(change_id)
