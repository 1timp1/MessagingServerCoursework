================================================================================
INSTANT MESSENGER - USAGE INSTRUCTIONS
================================================================================

This instant messenger system consists of a server (server.py) and client (client.py)
program written in Python 3.13. The system uses TCP for messaging and supports
both TCP and UDP for file downloads.

================================================================================
SETUP
================================================================================

1. Ensure Python 3.13 is installed on your system
2. The server will automatically create a "SharedFiles" folder if it doesn't exist
3. Alternatively, set the SERVER_SHARED_FILES environment variable to specify
   a custom path for the shared files folder

Example (Windows):
    set SERVER_SHARED_FILES=C:\MySharedFiles

Example (Linux/Mac):
    export SERVER_SHARED_FILES=/path/to/shared/files

================================================================================
STARTING THE SERVER
================================================================================

Command:
    python server.py [port]

Example:
    python server.py 12000

The server will:
- Start listening on the specified port
- Display connection information when clients connect
- Create a "SharedFiles" folder if it doesn't exist
- Print the absolute path of the SharedFiles folder on startup

================================================================================
STARTING A CLIENT
================================================================================

Command:
    python client.py [username] [hostname] [port]

Example:
    python client.py John 127.0.0.1 12000

This will:
- Connect a client named "John" to the server at 127.0.0.1:12000
- Display a welcome message from the server
- Create a folder named "John" for downloaded files
- Show an input prompt: [John]>

================================================================================
BASIC FUNCTIONALITY
================================================================================

1. CONNECTION HANDLING:
   - When a client connects, the server prints: "Connection from IP:PORT"
   - The client receives a welcome message from the server
   - Multiple clients can connect simultaneously
   - When a client joins, all other clients see: "[username] has joined"
   - When a client leaves (via /LEAVE or /QUIT), all others see: "[username] has left"
   - Unexpected disconnections are handled gracefully

2. DEFAULT MESSAGING:
   - Simply type a message and press Enter to broadcast it to all other clients
   - Format displayed: "username: message"

================================================================================
MESSAGING COMMANDS
================================================================================

/BROADCAST <message>
    Explicitly broadcast a message to all other clients
    Example: /BROADCAST Hello everyone!
    Format displayed: "[BROADCAST] username: message"

/UNICAST <username> <message>
    Send a private message to a specific user
    Requires at least 2 clients to be connected
    Example: /UNICAST John Hello John!
    Format displayed: "[UNICAST] username: message"
    If the target user is not found, you'll receive an error message

/JOINGROUP <group_name>
    Join a named group (creates the group if it doesn't exist)
    Example: /JOINGROUP TeamA
    You'll receive confirmation: "Joined group 'TeamA'"

/LEAVEGROUP <group_name>
    Leave a named group
    Example: /LEAVEGROUP TeamA
    You'll receive confirmation: "Left group 'TeamA'"

/GROUP <group_name> <message>
    Send a message to all members of a specific group (multicast)
    Only members of the group will receive the message
    Example: /GROUP TeamA Meeting at 3pm
    Format displayed: "[GROUP:TeamA] username: message"

/LISTUSERS
    Display all currently connected users
    Example output: "Connected users (3): John, Alice, Bob"

/LISTGROUPS
    Display all existing groups and their members
    Example output:
        TeamA (2 members): John, Alice
        TeamB (1 members): Bob

================================================================================
FILE DOWNLOADING
================================================================================

/LISTFILES
    Access the SharedFiles folder and list all available files
    The server responds with:
    - A success message including the number of files
    - A list of all files in the folder
    Example output:
        "Successfully accessed SharedFiles folder. Number of files: 3"
        "Files in SharedFiles:
        file1.txt
        image.jpg
        video.mp4"

/DOWNLOAD <filename> [TCP|UDP]
    Download a file from the SharedFiles folder
    - The file will be saved in a folder named after your username
    - You can specify TCP (default) or UDP protocol
    - The file size (in bytes) will be displayed after download
    Examples:
        /DOWNLOAD file1.txt
        /DOWNLOAD file1.txt TCP
        /DOWNLOAD image.jpg UDP
    
    Download process:
    1. Server sends file information (filename and size)
    2. File data is transferred via the selected protocol
    3. Server sends completion message with file size
    4. Client displays: "File 'filename' downloaded successfully (size bytes)"
    
    Note: Downloaded files are saved in a folder named after your username.
    For example, if your username is "John", files are saved in "./John/"

================================================================================
OTHER COMMANDS
================================================================================

/HELP
    Display a list of all available commands

/LEAVE or /QUIT or /EXIT
    Gracefully disconnect from the server
    All other clients will see: "[username] has left"

================================================================================
USAGE EXAMPLES
================================================================================

Example 1: Basic Chat
    Server: python server.py 12000
    Client1: python client.py Alice 127.0.0.1 12000
    Client2: python client.py Bob 127.0.0.1 12000
    
    Alice types: Hello Bob!
    Bob sees: "Alice: Hello Bob!"
    
    Bob types: Hi Alice!
    Alice sees: "Bob: Hi Alice!"

Example 2: Unicast Message
    Client1: /UNICAST Bob This is private
    Only Bob receives: "[UNICAST] Alice: This is private"

Example 3: Group Messaging
    Client1: /JOINGROUP TeamA
    Client2: /JOINGROUP TeamA
    Client3: /JOINGROUP TeamB
    
    Client1: /GROUP TeamA Meeting at 3pm
    Only Client1 and Client2 receive the message (both in TeamA)
    Client3 does not receive it (not in TeamA)

Example 4: File Download
    Client1: /LISTFILES
    Server responds with file list
    
    Client1: /DOWNLOAD document.pdf TCP
    File is downloaded to ./Alice/document.pdf
    Client1 sees: "File 'document.pdf' downloaded successfully (12345 bytes)"
    
    Client2: /DOWNLOAD image.jpg UDP
    File is downloaded to ./Bob/image.jpg via UDP protocol

================================================================================
TECHNICAL DETAILS
================================================================================

Protocol Usage:
- TCP: Used for all messaging and default file downloads
- UDP: Optional protocol for file downloads (specify with /DOWNLOAD command)

Message Format:
- All messages are sent with a 4-byte length prefix followed by the message data
- Messages are UTF-8 encoded strings

File Transfer:
- TCP files: Sent in 4096-byte chunks with length prefixes
- UDP files: Sent in 1024-byte chunks with chunk numbers
- File information (name and size) is always sent via TCP first

Connection Handling:
- Server uses select() for non-blocking I/O
- Clients use threading for receiving messages while allowing input
- Graceful disconnection handling prevents server crashes

Error Handling:
- Invalid commands show usage instructions
- File not found errors are displayed to the client
- Connection errors are handled gracefully

================================================================================
NOTES
================================================================================

1. The server must be started before clients can connect
2. All file operations are relative to the directory where the programs are run
3. The SharedFiles folder is created automatically if it doesn't exist
4. Download folders (named by username) are created automatically
5. The system supports any file type (text, images, audio, video, etc.)
6. Multiple clients can download the same file simultaneously
7. Group names are case-sensitive
8. Usernames must be unique per connection (not enforced, but recommended)
9. The server continues running even if all clients disconnect
10. Use Ctrl+C to stop the server or client

================================================================================
TROUBLESHOOTING
================================================================================

Problem: "Connection refused" error
Solution: Ensure the server is running and the port number is correct

Problem: "Address already in use" error
Solution: The port is already in use. Choose a different port or close the
          program using that port

Problem: File download fails
Solution: 
- Check that the file exists in SharedFiles folder
- Ensure you have write permissions in your download directory
- For UDP downloads, ensure firewall allows UDP traffic

Problem: Messages not received
Solution:
- Check that you're using the correct messaging command
- For unicast, verify the target username is correct
- For group messages, ensure you've joined the group

Problem: Server crashes when client disconnects
Solution: This should not happen. The code handles disconnections gracefully.
          If it occurs, check Python version (must be 3.13)

================================================================================
END OF README
================================================================================


