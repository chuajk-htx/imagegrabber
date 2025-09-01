import base64
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImageFileHandler(FileSystemEventHandler):
    def __init__(self, websocket_client):
        self.websocket_client = websocket_client
        # Supported image extensions
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'} # This is a set
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Check if it's an image file
        if file_path.suffix.lower() in self.image_extensions:
            logger.info(f"New image file detected: {file_path}")
            self.process_image(file_path)
    
    def process_image(self, file_path):
        try:
            # Wait a bit to ensure file is fully written
            time.sleep(1)
            
            # Read and encode the image
            with open(file_path, 'rb') as image_file:
                base64_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Prepare message
            message = {
                'type': 'image',
                'filename': file_path.name,
                'file_path': str(file_path),
                'base64_data': base64_data,
                'timestamp': time.time()
            }
            self.websocket_client.send(message)
                        
            logger.info(f"Queued {file_path.name} for sending via WebSocket") ")
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")