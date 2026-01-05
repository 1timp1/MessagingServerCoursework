#!/usr/bin/env python3
"""
Instant Messenger Server
Python 3.13 implementation using socket library
"""

import socket
import select
import sys
import os
import threading
import struct

class Server:
    def __init__(self, port):
        self.port = port
        self.host = ''  # Listen on all interfaces
        self.clients = {}  # Dictionary: {socket: {'username': str, 'address': tuple}}
        self.groups = {}  # Dictionary: {group_name: [socket1, socket2, ...]}
        self.server_socket = None
        self.shared_files_path = os.getenv('SERVER_SHARED_FILES', 'SharedFiles')
        
        # Create SharedFiles directory if it doesn't exist
        if not os.path.exists(self.shared_files_path):
            os.makedirs(self.shared_files_path)
    
    def start(self):
        """Start the server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"Server started on port {self.port}")
            print(f"SharedFiles folder: {os.path.abspath(self.shared_files_path)}")
            
            while True:
                # Use select to check for new connections and messages
                readable, _, exceptional = select.select(
                    [self.server_socket] + list(self.clients.keys()),
                    [],
                    [self.server_socket] + list(self.clients.keys())
                )
                
                for sock in readable:
                    if sock == self.server_socket:
                        # New client connection
                        self.accept_client()
                    else:
                        # Message from existing client
                        self.handle_client_message(sock)
                
                # Handle exceptional conditions
                for sock in exceptional:
                    if sock == self.server_socket:
                        print("Server socket error")
                        break
                    else:
                        self.remove_client(sock)
                        
        except KeyboardInterrupt:
            print("\nServer shutting down...")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.cleanup()
    
    def accept_client(self):
        """Accept a new client connection"""
        try:
            client_socket, address = self.server_socket.accept()
            print(f"Connection from {address[0]}:{address[1]}")
            
            # Send welcome message
            welcome_msg = "Welcome to the Instant Messenger Server!"
            self.send_message(client_socket, welcome_msg)
            
            # Receive username
            username = self.receive_message(client_socket)
            if username:
                self.clients[client_socket] = {
                    'username': username,
                    'address': address
                }
                # Broadcast join message to all other clients
                join_msg = f"{username} has joined"
                self.broadcast_message(join_msg, exclude_socket=client_socket)
                print(f"{username} ({address[0]}:{address[1]}) has joined")
        except Exception as e:
            print(f"Error accepting client: {e}")
    
    def handle_client_message(self, sock):
        """Handle incoming message from a client"""
        try:
            message = self.receive_message(sock)
            if not message:
                # Client disconnected
                self.remove_client(sock)
                return
            
            if sock not in self.clients:
                return
            
            username = self.clients[sock]['username']
            print(f"Message from {username}: {message}")
            
            # Parse command
            parts = message.strip().split(' ', 2)
            command = parts[0].upper()
            
            if command == '/LEAVE':
                self.remove_client(sock)
            elif command == '/BROADCAST':
                if len(parts) > 1:
                    broadcast_msg = f"[BROADCAST] {username}: {parts[1]}"
                    self.broadcast_message(broadcast_msg, exclude_socket=sock)
            elif command == '/UNICAST':
                if len(parts) >= 3:
                    target_username = parts[1]
                    unicast_msg = f"[UNICAST] {username}: {parts[2]}"
                    self.unicast_message(unicast_msg, target_username, exclude_socket=sock)
                else:
                    self.send_message(sock, "Usage: /UNICAST <username> <message>")
            elif command == '/JOINGROUP':
                if len(parts) > 1:
                    group_name = parts[1]
                    self.join_group(sock, group_name)
                else:
                    self.send_message(sock, "Usage: /JOINGROUP <group_name>")
            elif command == '/LEAVEGROUP':
                if len(parts) > 1:
                    group_name = parts[1]
                    self.leave_group(sock, group_name)
                else:
                    self.send_message(sock, "Usage: /LEAVEGROUP <group_name>")
            elif command == '/GROUP':
                if len(parts) >= 3:
                    group_name = parts[1]
                    group_msg = f"[GROUP:{group_name}] {username}: {parts[2]}"
                    self.send_group_message(group_msg, group_name, exclude_socket=sock)
                else:
                    self.send_message(sock, "Usage: /GROUP <group_name> <message>")
            elif command == '/LISTFILES':
                self.list_files(sock)
            elif command == '/DOWNLOAD':
                if len(parts) > 1:
                    filename = parts[1]
                    protocol = parts[2].upper() if len(parts) > 2 else 'TCP'
                    self.handle_file_download(sock, filename, protocol)
                else:
                    self.send_message(sock, "Usage: /DOWNLOAD <filename> [TCP|UDP]")
            elif command == '/LISTUSERS':
                self.list_users(sock)
            elif command == '/LISTGROUPS':
                self.list_groups(sock)
            else:
                # Default: broadcast message
                broadcast_msg = f"{username}: {message}"
                self.broadcast_message(broadcast_msg, exclude_socket=sock)
                
        except Exception as e:
            print(f"Error handling client message: {e}")
            self.remove_client(sock)
    
    def send_message(self, sock, message):
        """Send a message to a client socket"""
        try:
            message_bytes = message.encode('utf-8')
            message_len = len(message_bytes)
            # Send length as 4-byte integer, then message
            sock.sendall(struct.pack('!I', message_len))
            sock.sendall(message_bytes)
        except Exception as e:
            print(f"Error sending message: {e}")
            raise
    
    def receive_message(self, sock):
        """Receive a message from a client socket"""
        try:
            # Receive message length (4 bytes)
            length_data = sock.recv(4)
            if len(length_data) < 4:
                return None
            message_len = struct.unpack('!I', length_data)[0]
            
            # Receive message
            message = b''
            while len(message) < message_len:
                chunk = sock.recv(message_len - len(message))
                if not chunk:
                    return None
                message += chunk
            
            return message.decode('utf-8')
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None
    
    def broadcast_message(self, message, exclude_socket=None):
        """Broadcast message to all clients except exclude_socket"""
        for sock in list(self.clients.keys()):
            if sock != exclude_socket:
                try:
                    self.send_message(sock, message)
                except:
                    self.remove_client(sock)
    
    def unicast_message(self, message, target_username, exclude_socket=None):
        """Send message to a specific user"""
        target_socket = None
        for sock, info in self.clients.items():
            if info['username'] == target_username and sock != exclude_socket:
                target_socket = sock
                break
        
        if target_socket:
            try:
                self.send_message(target_socket, message)
            except:
                self.remove_client(target_socket)
        elif exclude_socket:
            self.send_message(exclude_socket, f"User '{target_username}' not found")
    
    def join_group(self, sock, group_name):
        """Add client to a group"""
        if group_name not in self.groups:
            self.groups[group_name] = []
        
        if sock not in self.groups[group_name]:
            self.groups[group_name].append(sock)
            username = self.clients[sock]['username']
            self.send_message(sock, f"Joined group '{group_name}'")
            print(f"{username} joined group '{group_name}'")
        else:
            self.send_message(sock, f"Already in group '{group_name}'")
    
    def leave_group(self, sock, group_name):
        """Remove client from a group"""
        if group_name in self.groups:
            if sock in self.groups[group_name]:
                self.groups[group_name].remove(sock)
                username = self.clients[sock]['username']
                self.send_message(sock, f"Left group '{group_name}'")
                print(f"{username} left group '{group_name}'")
                
                # Remove empty groups
                if not self.groups[group_name]:
                    del self.groups[group_name]
            else:
                self.send_message(sock, f"Not in group '{group_name}'")
        else:
            self.send_message(sock, f"Group '{group_name}' does not exist")
    
    def send_group_message(self, message, group_name, exclude_socket=None):
        """Send message to all clients in a group"""
        if group_name in self.groups:
            for sock in self.groups[group_name]:
                if sock != exclude_socket:
                    try:
                        self.send_message(sock, message)
                    except:
                        self.remove_client(sock)
        else:
            if exclude_socket:
                self.send_message(exclude_socket, f"Group '{group_name}' does not exist")
    
    def list_files(self, sock):
        """List files in SharedFiles folder"""
        try:
            files = os.listdir(self.shared_files_path)
            file_count = len(files)
            success_msg = f"Successfully accessed SharedFiles folder. Number of files: {file_count}"
            self.send_message(sock, success_msg)
            
            if files:
                file_list = "\n".join(files)
                self.send_message(sock, f"Files in SharedFiles:\n{file_list}")
            else:
                self.send_message(sock, "SharedFiles folder is empty")
        except Exception as e:
            self.send_message(sock, f"Error accessing SharedFiles: {e}")
    
    def handle_file_download(self, sock, filename, protocol='TCP'):
        """Handle file download request"""
        filepath = os.path.join(self.shared_files_path, filename)
        
        if not os.path.exists(filepath):
            self.send_message(sock, f"ERROR: File '{filename}' not found")
            return
        
        if not os.path.isfile(filepath):
            self.send_message(sock, f"ERROR: '{filename}' is not a file")
            return
        
        file_size = os.path.getsize(filepath)
        
        if protocol.upper() == 'TCP':
            self.send_file_tcp(sock, filepath, filename, file_size)
        elif protocol.upper() == 'UDP':
            self.send_file_udp(sock, filepath, filename, file_size)
        else:
            self.send_message(sock, f"ERROR: Invalid protocol '{protocol}'. Use TCP or UDP")
    
    def send_file_tcp(self, sock, filepath, filename, file_size):
        """Send file using TCP"""
        try:
            # Send file info
            info_msg = f"DOWNLOAD_START:{filename}:{file_size}"
            self.send_message(sock, info_msg)
            
            # Send file data
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    # Send chunk length then chunk
                    sock.sendall(struct.pack('!I', len(chunk)))
                    sock.sendall(chunk)
            
            # Send completion message
            self.send_message(sock, f"DOWNLOAD_COMPLETE:{filename}:{file_size}")
            print(f"File '{filename}' ({file_size} bytes) sent via TCP")
        except Exception as e:
            self.send_message(sock, f"ERROR: Failed to send file: {e}")
    
    def send_file_udp(self, sock, filepath, filename, file_size):
        """Send file using UDP"""
        try:
            # Get client address
            client_address = self.clients[sock]['address']
            
            # Create UDP socket
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Send file info via TCP first
            info_msg = f"DOWNLOAD_START_UDP:{filename}:{file_size}"
            self.send_message(sock, info_msg)
            
            # Send UDP port info
            udp_port = self.port + 1
            self.send_message(sock, f"UDP_PORT:{udp_port}")
            
            # Read and send file in chunks via UDP
            chunk_size = 1024  # Smaller chunks for UDP
            with open(filepath, 'rb') as f:
                chunk_num = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Send chunk number and data
                    header = struct.pack('!II', chunk_num, len(chunk))
                    udp_socket.sendto(header + chunk, (client_address[0], udp_port))
                    chunk_num += 1
            
            # Send completion via TCP
            self.send_message(sock, f"DOWNLOAD_COMPLETE_UDP:{filename}:{file_size}")
            udp_socket.close()
            print(f"File '{filename}' ({file_size} bytes) sent via UDP")
        except Exception as e:
            self.send_message(sock, f"ERROR: Failed to send file via UDP: {e}")
    
    def list_users(self, sock):
        """List all connected users"""
        usernames = [info['username'] for info in self.clients.values()]
        user_list = f"Connected users ({len(usernames)}): {', '.join(usernames)}"
        self.send_message(sock, user_list)
    
    def list_groups(self, sock):
        """List all groups"""
        if self.groups:
            group_list = []
            for group_name, members in self.groups.items():
                member_names = [self.clients[s]['username'] for s in members if s in self.clients]
                group_list.append(f"{group_name} ({len(member_names)} members): {', '.join(member_names)}")
            self.send_message(sock, "\n".join(group_list))
        else:
            self.send_message(sock, "No groups exist")
    
    def remove_client(self, sock):
        """Remove a client from the server"""
        if sock in self.clients:
            username = self.clients[sock]['username']
            address = self.clients[sock]['address']
            
            # Remove from all groups
            for group_name in list(self.groups.keys()):
                if sock in self.groups[group_name]:
                    self.groups[group_name].remove(sock)
                    if not self.groups[group_name]:
                        del self.groups[group_name]
            
            # Remove from clients
            del self.clients[sock]
            
            # Close socket
            try:
                sock.close()
            except:
                pass
            
            # Broadcast leave message
            leave_msg = f"{username} has left"
            self.broadcast_message(leave_msg)
            print(f"{username} ({address[0]}:{address[1]}) has left")
    
    def cleanup(self):
        """Clean up server resources"""
        for sock in list(self.clients.keys()):
            try:
                sock.close()
            except:
                pass
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print("Server closed")

def main():
    if len(sys.argv) < 2:
        print("Usage: python server.py [port]")
        sys.exit(1)
    
    try:
        port = int(sys.argv[1])
        server = Server(port)
        server.start()
    except ValueError:
        print("Error: Port must be a number")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


