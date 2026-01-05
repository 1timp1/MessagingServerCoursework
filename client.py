#!/usr/bin/env python3
"""
Instant Messenger Client
Python 3.13 implementation using socket library
"""

import socket
import select
import sys
import os
import struct
import threading

class Client:
    def __init__(self, username, hostname, port):
        self.username = username
        self.hostname = hostname
        self.port = port
        self.socket = None
        self.running = False
        self.udp_socket = None
        self.udp_port = None
        self.download_dir = username  # Folder named by username
        
        # Create download directory if it doesn't exist
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
    
    def connect(self):
        """Connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.hostname, self.port))
            self.running = True
            
            # Send username to server
            self.send_message(self.username)
            
            # Start receiving thread
            receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            receive_thread.start()
            
            return True
        except Exception as e:
            print(f"Error connecting to server: {e}")
            return False
    
    def send_message(self, message):
        """Send a message to the server"""
        try:
            message_bytes = message.encode('utf-8')
            message_len = len(message_bytes)
            # Send length as 4-byte integer, then message
            self.socket.sendall(struct.pack('!I', message_len))
            self.socket.sendall(message_bytes)
        except Exception as e:
            print(f"Error sending message: {e}")
            self.running = False
    
    def receive_message(self):
        """Receive a message from the server"""
        try:
            # Receive message length (4 bytes)
            length_data = self.socket.recv(4)
            if len(length_data) < 4:
                return None
            message_len = struct.unpack('!I', length_data)[0]
            
            # Receive message
            message = b''
            while len(message) < message_len:
                chunk = self.socket.recv(message_len - len(message))
                if not chunk:
                    return None
                message += chunk
            
            return message.decode('utf-8')
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None
    
    def receive_messages(self):
        """Thread function to continuously receive messages"""
        while self.running:
            try:
                readable, _, _ = select.select([self.socket], [], [], 0.1)
                if self.socket in readable:
                    message = self.receive_message()
                    if not message:
                        print("\nConnection lost")
                        self.running = False
                        break
                    
                    # Handle special messages
                    if message.startswith("DOWNLOAD_START:"):
                        self.handle_download_start(message)
                    elif message.startswith("DOWNLOAD_START_UDP:"):
                        self.handle_download_start_udp(message)
                    elif message.startswith("UDP_PORT:"):
                        self.handle_udp_port(message)
                    elif message.startswith("DOWNLOAD_COMPLETE:"):
                        self.handle_download_complete(message)
                    elif message.startswith("DOWNLOAD_COMPLETE_UDP:"):
                        self.handle_download_complete_udp(message)
                    else:
                        print(f"\n{message}")
                        print(f"[{self.username}]> ", end='', flush=True)
            except Exception as e:
                if self.running:
                    print(f"\nError receiving messages: {e}")
                self.running = False
                break
    
    def handle_download_start(self, message):
        """Handle TCP file download start"""
        # Format: DOWNLOAD_START:filename:file_size
        parts = message.split(':')
        if len(parts) >= 3:
            filename = parts[1]
            file_size = int(parts[2])
            self.receive_file_tcp(filename, file_size)
    
    def handle_download_start_udp(self, message):
        """Handle UDP file download start"""
        # Format: DOWNLOAD_START_UDP:filename:file_size
        parts = message.split(':')
        if len(parts) >= 3:
            self.download_filename = parts[1]
            self.download_file_size = int(parts[2])
            self.download_chunks = {}
            self.download_received = 0
    
    def handle_udp_port(self, message):
        """Handle UDP port assignment"""
        # Format: UDP_PORT:port
        parts = message.split(':')
        if len(parts) >= 2:
            self.udp_port = int(parts[1])
            self.setup_udp_receiver()
    
    def setup_udp_receiver(self):
        """Setup UDP socket to receive file"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(('', self.udp_port))
            self.udp_socket.settimeout(1.0)
            
            # Start UDP receive thread
            udp_thread = threading.Thread(target=self.receive_file_udp, daemon=True)
            udp_thread.start()
        except Exception as e:
            print(f"Error setting up UDP receiver: {e}")
    
    def receive_file_tcp(self, filename, file_size):
        """Receive file via TCP"""
        try:
            filepath = os.path.join(self.download_dir, filename)
            received = 0
            
            with open(filepath, 'wb') as f:
                while received < file_size:
                    # Receive chunk length
                    length_data = self.socket.recv(4)
                    if len(length_data) < 4:
                        break
                    chunk_len = struct.unpack('!I', length_data)[0]
                    
                    # Receive chunk data
                    chunk = b''
                    while len(chunk) < chunk_len:
                        data = self.socket.recv(chunk_len - len(chunk))
                        if not data:
                            break
                        chunk += data
                    
                    f.write(chunk)
                    received += len(chunk)
            
            if received == file_size:
                print(f"\nFile '{filename}' downloaded successfully ({file_size} bytes)")
            else:
                print(f"\nFile download incomplete. Received {received}/{file_size} bytes")
            print(f"[{self.username}]> ", end='', flush=True)
        except Exception as e:
            print(f"\nError receiving file: {e}")
            print(f"[{self.username}]> ", end='', flush=True)
    
    def receive_file_udp(self):
        """Receive file via UDP"""
        try:
            filepath = os.path.join(self.download_dir, self.download_filename)
            expected_chunks = (self.download_file_size + 1023) // 1024  # Round up
            
            while self.download_received < self.download_file_size:
                try:
                    data, addr = self.udp_socket.recvfrom(1032)  # 8 bytes header + 1024 data
                    if len(data) >= 8:
                        chunk_num, chunk_len = struct.unpack('!II', data[:8])
                        chunk_data = data[8:8+chunk_len]
                        
                        if chunk_num not in self.download_chunks:
                            self.download_chunks[chunk_num] = chunk_data
                            self.download_received += len(chunk_data)
                except socket.timeout:
                    # Check if we have all chunks
                    if len(self.download_chunks) >= expected_chunks:
                        break
                    continue
                except Exception as e:
                    print(f"UDP receive error: {e}")
                    break
            
            # Write file in order
            with open(filepath, 'wb') as f:
                for i in range(expected_chunks):
                    if i in self.download_chunks:
                        f.write(self.download_chunks[i])
            
            if self.download_received == self.download_file_size:
                print(f"\nFile '{self.download_filename}' downloaded successfully via UDP ({self.download_file_size} bytes)")
            else:
                print(f"\nFile download incomplete via UDP. Received {self.download_received}/{self.download_file_size} bytes")
            
            if self.udp_socket:
                self.udp_socket.close()
                self.udp_socket = None
            
            print(f"[{self.username}]> ", end='', flush=True)
        except Exception as e:
            print(f"\nError receiving file via UDP: {e}")
            if self.udp_socket:
                self.udp_socket.close()
                self.udp_socket = None
            print(f"[{self.username}]> ", end='', flush=True)
    
    def handle_download_complete(self, message):
        """Handle TCP download completion message"""
        # Format: DOWNLOAD_COMPLETE:filename:file_size
        parts = message.split(':')
        if len(parts) >= 3:
            filename = parts[1]
            file_size = int(parts[2])
            print(f"\nDownload complete: {filename} ({file_size} bytes)")
            print(f"[{self.username}]> ", end='', flush=True)
    
    def handle_download_complete_udp(self, message):
        """Handle UDP download completion message"""
        # Format: DOWNLOAD_COMPLETE_UDP:filename:file_size
        parts = message.split(':')
        if len(parts) >= 3:
            filename = parts[1]
            file_size = int(parts[2])
            # Already handled in receive_file_udp, but acknowledge
            pass
    
    def handle_input(self):
        """Thread function to handle user input"""
        try:
            while self.running:
                # Use sys.stdin.readline() for cross-platform compatibility
                user_input = sys.stdin.readline()
                if not user_input:  # EOF
                    break
                user_input = user_input.strip()
                
                if not user_input:
                    print(f"[{self.username}]> ", end='', flush=True)
                    continue
                
                if user_input.upper() == '/HELP':
                    self.print_help()
                elif user_input.upper() == '/QUIT' or user_input.upper() == '/EXIT':
                    self.send_message('/LEAVE')
                    self.running = False
                    break
                else:
                    self.send_message(user_input)
                
                if self.running:
                    print(f"[{self.username}]> ", end='', flush=True)
        except EOFError:
            # Handle EOF (Ctrl+D on Unix, Ctrl+Z on Windows)
            self.running = False
        except Exception as e:
            if self.running:
                print(f"\nInput error: {e}")
            self.running = False
    
    def run(self):
        """Main client loop"""
        if not self.connect():
            return
        
        print(f"Connected to {self.hostname}:{self.port}")
        print("Type '/HELP' for available commands")
        print(f"[{self.username}]> ", end='', flush=True)
        
        # Start input thread
        input_thread = threading.Thread(target=self.handle_input, daemon=True)
        input_thread.start()
        
        try:
            # Main loop just keeps the program running
            # Input and receiving are handled in separate threads
            while self.running:
                import time
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nDisconnecting...")
            self.send_message('/LEAVE')
            self.running = False
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            self.cleanup()
    
    def print_help(self):
        """Print help message"""
        help_text = """
Available Commands:
  /HELP              - Show this help message
  /LEAVE or /QUIT    - Leave the server
  /BROADCAST <msg>   - Broadcast message to all clients
  /UNICAST <user> <msg> - Send message to specific user
  /JOINGROUP <name>  - Join a group (creates if doesn't exist)
  /LEAVEGROUP <name> - Leave a group
  /GROUP <name> <msg> - Send message to group members
  /LISTUSERS         - List all connected users
  /LISTGROUPS        - List all groups
  /LISTFILES         - List files in SharedFiles folder
  /DOWNLOAD <file> [TCP|UDP] - Download a file (default: TCP)
  
Default behavior: Sending a message without a command broadcasts it to all clients.
"""
        print(help_text)
        print(f"[{self.username}]> ", end='', flush=True)
    
    def cleanup(self):
        """Clean up client resources"""
        self.running = False
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        print("Disconnected from server")

def main():
    if len(sys.argv) < 4:
        print("Usage: python client.py [username] [hostname] [port]")
        sys.exit(1)
    
    username = sys.argv[1]
    hostname = sys.argv[2]
    
    try:
        port = int(sys.argv[3])
        client = Client(username, hostname, port)
        client.run()
    except ValueError:
        print("Error: Port must be a number")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

