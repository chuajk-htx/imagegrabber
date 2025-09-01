import os
import base64
import time
import json
import threading
import websocket
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from pathlib import Path
from queue import Queue
import signal
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebSocketClient:
    def __init__(self, ws_url, api_key=None):
        self.ws_url = ws_url
        self.api_key = api_key
        self.ws = None
        self.connected = False
        self.message_queue = Queue()
        self.reconnect_interval = 5
        self.max_reconnect_attempts = 10
        self.reconnect_attempts = 0
        
        # Start connection in a separate thread
        self.connect_thread = threading.Thread(target=self._connect_loop, daemon=True)
        self.connect_thread.start()
        
        # Start message sender thread
        self.sender_thread = threading.Thread(target=self._message_sender, daemon=True)
        self.sender_thread.start()
    
    def _connect_loop(self):
        """Continuously try to maintain WebSocket connection"""
        while True:
            try:
                self._connect()
                self.ws.run_forever()
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
            
            if self.reconnect_attempts < self.max_reconnect_attempts:
                self.reconnect_attempts += 1
                wait_time = min(self.reconnect_interval * self.reconnect_attempts, 60)
                logger.info(f"Reconnecting in {wait_time} seconds (attempt {self.reconnect_attempts})")
                time.sleep(wait_time)
            else:
                logger.error("Max reconnection attempts reached")
                break
    
    def _connect(self):
        """Establish WebSocket connection"""
        headers = {}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            header=headers,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
    
    def _on_open(self, ws):
        """Handle WebSocket connection opened"""
        logger.info("WebSocket connection established")
        self.connected = True
        self.reconnect_attempts = 0
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            logger.info(f"Received message: {data}")
            
            # Handle server commands
            if data.get('type') == 'command':
                self._handle_command(data)
            elif data.get('type') == 'ack':
                logger.info(f"Image acknowledged: {data.get('filename')}")
                
        except json.JSONDecodeError:
            logger.warning(f"Received non-JSON message: {message}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")
        self.connected = False
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closed"""
        logger.warning(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        self.connected = False
    
    def _handle_command(self, data):
        """Handle commands from server"""
        command = data.get('command')
        if command == 'ping':
            self.send_message({'type': 'pong', 'timestamp': time.time()})
        elif command == 'status':
            self.send_message({
                'type': 'status_response',
                'connected': self.connected,
                'queue_size': self.message_queue.qsize(),
                'timestamp': time.time()
            })
        else:
            logger.info(f"Unknown command received: {command}")
    
    def _message_sender(self):
        """Background thread to send queued messages"""
        while True:
            try:
                # Wait for a message to send
                message = self.message_queue.get(timeout=1)
                
                if self.connected and self.ws and self.ws.sock:
                    try:
                        self.ws.send(json.dumps(message))
                        logger.debug(f"Sent message: {message.get('type', 'unknown')}")
                    except Exception as e:
                        logger.error(f"Failed to send message: {e}")
                        # Put message back in queue for retry
                        self.message_queue.put(message)
                else:
                    # Put message back in queue if not connected
                    self.message_queue.put(message)
                    time.sleep(1)
                    
            except:
                # Timeout - continue loop
                continue
    
    def send_message(self, message):
        """Queue a message to be sent"""
        self.message_queue.put(message)
    
    def send_image(self, message):
        """Send image data via WebSocket"""
        self.send_message(message)
    
    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()
        self.connected = False