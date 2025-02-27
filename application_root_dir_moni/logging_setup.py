import logging
import os

def setup_logging(script_name: str):
    """
    Set up logging for the script.
    - Creates a /logs/ directory if it doesn't exist.
    - Configures logging to write to a file and the console.
    - Log file is named after the script (e.g., monitor.log).
    """
    # Ensure the logs directory exists
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Create a log file named after the script
    log_file = os.path.join(logs_dir, f"{script_name}.log")

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),  # Log to file
            logging.StreamHandler()  # Log to console
        ]
    )

    return logging.getLogger(script_name)