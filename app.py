import os
import base64
import time
import socket
import json
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from pathlib import Path
from dotenv import load_dotenv
from websocketclient import WebSocketClient
from imagefilehandler import ImageFileHandler


def main():
    load_dotenv()
    # Configuration from environment variables
    watch_directory = os.getenv('WATCH_DIRECTORY', '/images')
    SERVER_HOST = os.getenv('SERVER_HOST', 'localhost')
    SERVER_PORT = int(os.getenv('SERVER_PORT', '8000'))
    URL_PATH = os.getenv('URL_PATH', '/images')
    websocket_url = f"ws://{SERVER_HOST}:{SERVER_PORT}{URL_PATH}"
    
    logger.info(f"Starting image monitor...")
    logger.info(f"Watching directory: {watch_directory}")
    logger.info(f"Target server: {SERVER_HOST}:{SERVER_PORT}")
    
    # Ensure watch directory exists
    os.makedirs(watch_directory, exist_ok=True)
    
    try:
        #initialize WebSocket client
        ws_client = WebSocketClient(websocket_url)
        
        # Set up event handler and observer
        event_handler = ImageFileHandler(ws_client)
        observer = Observer()
        observer.schedule(event_handler, path=watch_directory, recursive=True)
        observer.start()
        logger.info("Image monitor started successfully")
        
        # Keep the script running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping image monitor...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        if 'observer' in locals():
           observer.stop()
           observer.join()
        if 'ws_client' in locals():
            ws_client.close()
        logger.info("Image monitor stopped.")
            
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    main()