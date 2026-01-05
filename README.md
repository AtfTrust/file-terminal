# File Terminal

A lightweight, terminal-based file server and client application for easy file navigation and transfer over a local network.

## Features

- **Remote File Navigation**: Browse directories on a remote server from your terminal.
- **Rainbow File Listing**: Distinct row coloring for better readability.
- **File & Folder Downloads**:
    - Download individual files with a visual progress bar.
    - Download entire directories (automatically zipped).
- **Search**: Search for files on the server.
- **Cross-Platform**: Works on Windows, Linux, and WSL (proxies bypassed for local connections).

## Installation

Clone the repository:

```bash
git clone https://github.com/AtfTrust/file-terminal.git
cd file-terminal
```

## Usage

### 1. Start the Server

Run the server on the machine you want to share files from:

```bash
python file_server_nav.py
```
This will start an HTTP server on port 8000.

### 2. Start the Client

Run the client on your local machine:

```bash
python client.py
```

- Enter the Server IP when prompted (default is `192.168.33.61`).
- Use commands to navigate and download.

### Commands

| Command | Description |
| :--- | :--- |
| `cd <dir>` | Change directory |
| `get <file>` | Download a file or zip a folder |
| `zip <dir>` | Download a folder as a zip file |
| `..` | Go up one directory |
| `exit` / `quit` | Exit the client |

You can also simply type the **Index Number** of a file/folder to select it (navigates into folders, downloads files).

## Configuration

In `client.py`, you can modify:
- `DEFAULT_IP`: The default server IP.
- `PORT`: The server port (default 8000).

## License

[MIT License](LICENSE)
