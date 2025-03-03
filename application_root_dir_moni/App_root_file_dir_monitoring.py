import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import configparser
from logging_setup import setup_logging

# Load configurations from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Configuration
APP_ROOT = config['PATHS']['APP_ROOT']
EMAIL_SCRIPT = config['PATHS']['EMAIL_SCRIPT']
PAUSE_FLAG = config['PATHS']['PAUSE_FLAG']
EXCLUDED_DIRS = set(config['EXCLUSIONS']['EXCLUDED_DIRS'].split(','))
EXCLUDED_FILES = {'.swp', '.swpx', '~', '.swx', '4913', '.tmp'}  # Ignore temporary and backup files

FROM_EMAIL = config['EMAIL']['FROM']
TO_EMAIL = config['EMAIL']['TO']
CC_EMAIL = config['EMAIL']['CC']

# Set up logging
logger = setup_logging("file_monitor")

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