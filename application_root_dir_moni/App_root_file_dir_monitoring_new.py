import os
import time
import subprocess
import argparse
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
PAUSE_FLAG = config['MONITORING']['PAUSE_FLAG']  # Updated section
CHANGE_LOG = config['MONITORING']['CHANGE_LOG']  # Updated section
EXCLUDED_DIRS = set(config['EXCLUSIONS']['EXCLUDED_DIRS'].split(','))
EXCLUDED_FILES = {'.swp', '.swpx', '~', '.swx', '4913', '.tmp'}

FROM_EMAIL = config['EMAIL']['FROM']
TO_EMAIL = config['EMAIL']['TO']
CC_EMAIL = config['EMAIL']['CC']

# Set up logging
logger = setup_logging("file_monitor")

class MonitorHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_event_time = {}

    def on_any_event(self, event):
        if os.path.exists(PAUSE_FLAG):
            return

        file_name = os.path.basename(event.src_path)
        for excluded_dir in EXCLUDED_DIRS:
            if event.src_path.startswith(os.path.join(APP_ROOT, excluded_dir.strip())):
                return

        if any(file_name.endswith(ext) for ext in EXCLUDED_FILES):
            return

        current_time = time.time()
        if current_time - self.last_event_time.get(event.src_path, 0) < 2:
            return
        self.last_event_time[event.src_path] = current_time

        event_messages = {
            "modified": "File Modified",
            "created": "New File Created",
            "deleted": "File Deleted"
        }
        if event.event_type in event_messages:
            message = f"{event.src_path} has been {event.event_type}."
            logger.info(message)
            send_alert(event_messages[event.event_type], message)

# Send Alert via Email
def send_alert(subject, message):
    logger.info(f"Sending alert: {subject} - {message}")
    subprocess.run([EMAIL_SCRIPT, "-s", subject, "-m", message, "-f", FROM_EMAIL, "-t", TO_EMAIL, "-c", CC_EMAIL])

# Stop Monitoring
def stop_monitoring(change_id, description):
    with open(PAUSE_FLAG, 'w') as f:
        f.write("Paused")
    logger.info(f"Monitoring stopped - Change ID: {change_id}, Reason: {description}")
    with open(CHANGE_LOG, 'a') as log:
        log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] STOPPED - Change ID: {change_id}, Reason: {description}\n")
    send_alert("Monitoring Stopped", f"Change ID: {change_id}\nReason: {description}")

# Resume Monitoring
def resume_monitoring(change_id, description):
    if os.path.exists(PAUSE_FLAG):
        os.remove(PAUSE_FLAG)
    logger.info(f"Monitoring resumed - Change ID: {change_id}, Reason: {description}")
    with open(CHANGE_LOG, 'a') as log:
        log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] RESUMED - Change ID: {change_id}, Reason: {description}\n")
    send_alert("Monitoring Resumed", f"Change ID: {change_id}\nReason: {description}")

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
    parser = argparse.ArgumentParser(description="File System Monitor")
    parser.add_argument('--stop', nargs=2, metavar=('CHANGE_ID', 'DESCRIPTION'), help='Stop monitoring with change ID and description')
    parser.add_argument('--resume', nargs=2, metavar=('CHANGE_ID', 'DESCRIPTION'), help='Resume monitoring with change ID and description')
    args = parser.parse_args()

    if args.stop:
        stop_monitoring(args.stop[0], args.stop[1])
    elif args.resume:
        resume_monitoring(args.resume[0], args.resume[1])
    else:
        start_monitoring()