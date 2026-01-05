import urllib.request
import urllib.parse
import json
import os
import subprocess
import sys
import readline
import time
import glob

# --- CONFIG ---
DEFAULT_IP = "192.168.33.61"
PORT = 8000

# ANSI Colors
CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
GREY = "\033[90m"     
RESET = "\033[0m"
BOLD = "\033[1m"

# Global list for tab-completion
CURRENT_ITEMS = []
COMMANDS = ['cd', 'get', 'put', 'zip', 'help', '?', 'exit', 'quit', '..']

def complete(text, state):
    buffer = readline.get_line_buffer()
    line_stripped = buffer.lstrip()
    
    options = []
    
    # Check if we are typing a command (first word)
    if " " not in line_stripped:
        options = COMMANDS + [i['name'] for i in CURRENT_ITEMS]
        matches = [s for s in options if s.startswith(text)]
    else:
        # We are typing an argument
        cmd_parts = line_stripped.split()
        cmd = cmd_parts[0]
        
        if cmd == 'put':
            # Local file completion
            # Expand ~user directories if present, though glob handles some
            path_prefix = os.path.expanduser(text)
            
            # Use glob to find matches
            # If text is empty, list current dir
            # If text ends with /, list that dir
            search_pat = path_prefix + "*"
            glob_matches = glob.glob(search_pat)
            
            # We need to append / to directories to make navigation continuous
            matches = []
            for m in glob_matches:
                if os.path.isdir(m):
                    matches.append(m + "/")
                else:
                    matches.append(m)
        else:
            # Remote item completion
            options = [i['name'] for i in CURRENT_ITEMS]
            matches = [s for s in options if s.startswith(text)]

    try:
        return matches[state]
    except IndexError:
        return None

readline.set_completer(complete)
readline.parse_and_bind("tab: complete")
readline.set_completer_delims(' \t\n')

try:
    win_user = subprocess.check_output(["cmd.exe", "/c", "echo %USERNAME%"], stderr=subprocess.DEVNULL).decode().strip()
    DOWNLOAD_DIR = f"/mnt/c/Users/{win_user}/Downloads"
except:
    DOWNLOAD_DIR = "."

def clear_screen():
    print("\033c", end="")

def get_server_ip():
    val = input(f"Server IP [{DEFAULT_IP}]: ").strip()
    return val if val else DEFAULT_IP

def fetch_list(base_url, rel_path):
    try:
        # Create a proxy-free opener to avoid local network issues
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        
        params = urllib.parse.urlencode({'path': rel_path})
        url = f"{base_url}/list?{params}"
        # print(f"DEBUG: Fetching {url}")
        
        with opener.open(url, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
        return None

def download_item(base_url, item, current_path, as_zip=False):
    if as_zip:
        print(f"\n{YELLOW}Zipping and Downloading: {BOLD}{item['name']}{RESET}")
        if current_path == ".": server_path = item['name']
        else: server_path = f"{current_path}/{item['name']}"
        params = urllib.parse.urlencode({'path': server_path})
        url = f"{base_url}/zip?{params}"
        filename = f"{item['name']}.zip"
    else:
        print(f"\nDownloading: {BOLD}{item['name']}{RESET}")
        if current_path == ".": server_path = item['name']
        else: server_path = f"{current_path}/{item['name']}"
        url = f"{base_url}/{urllib.parse.quote(server_path)}"
        filename = item['name']

    local_path = os.path.join(DOWNLOAD_DIR, filename)
    
    try:
        # Create a proxy-free opener for downloads too
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        
        with opener.open(url, timeout=60) as response, open(local_path, 'wb') as out_file:
            total_size = int(response.getheader('Content-Length') or 0)
            downloaded = 0
            start_time = time.time()
            
            while True:
                chunk = response.read(1024*1024) # 1MB chunks
                if not chunk: break
                out_file.write(chunk)
                
                downloaded += len(chunk)
                if total_size > 0:
                    percent = downloaded / total_size * 100
                    elapsed = time.time() - start_time
                    speed = downloaded / (elapsed if elapsed > 0 else 1) / (1024*1024) # MB/s
                    
                    # Create a simple progress bar
                    bar_len = 30
                    filled_len = int(bar_len * downloaded // total_size)
                    bar = '=' * filled_len + '-' * (bar_len - filled_len)
                    
                    print(f"\r{YELLOW}[{bar}] {percent:.1f}% | {downloaded/(1024*1024):.1f}MB / {total_size/(1024*1024):.1f}MB | {speed:.2f} MB/s{RESET}", end="")
            
            print() # Newline after done
            
        print(f"{GREEN}Saved to: {local_path}{RESET}")
    except Exception as e:
        print(f"{RED}Failed: {e}{RESET}")
    
    input(f"{GREY}[Press Enter]{RESET}")

def show_help():
    print(f"\n{BOLD}Available Commands:{RESET}")
    print(f"  {BOLD}cd <dir/id>{RESET}       : Change directory (or use index number)")
    print(f"  {BOLD}get <file/id...>{RESET}  : Download file(s) or folder(s) (supports ranges like 1-5)")
    print(f"  {BOLD}put <local_file>{RESET}  : Upload a local file to current remote directory")
    print(f"  {BOLD}zip <dir/id...>{RESET}  : Download folder(s) as .zip file")
    print(f"  {BOLD}..{RESET}               : Go up one directory")
    print(f"  {BOLD}exit / quit{RESET}      : Exit the application")
    print(f"  {BOLD}help / ?{RESET}         : Show this help message")
    print(f"\n  {GREY}Tip: You can simply type the index number to enter a folder or download a file.{RESET}")
    input(f"{GREY}[Press Enter]{RESET}")

def upload_file(base_url, local_path_arg, remote_dir):
    # Try to resolve the local file path
    # 1. Expand User (~/)
    expanded_arg = os.path.expanduser(local_path_arg)
    
    candidates = [
        expanded_arg,                                        # Expanded path
        local_path_arg,                                      # As provided
        os.path.join(DOWNLOAD_DIR, local_path_arg),          # In the download folder
        os.path.abspath(expanded_arg)                        # Absolute
    ]
    
    local_path = None
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(c):
            local_path = c
            break
            
    if not local_path:
        print(f"\n{RED}Error: Local file '{local_path_arg}' not found.{RESET}")
        print(f"{GREY}Checked locations:{RESET}")
        print(f"  - {os.getcwd()}")
        print(f"  - {DOWNLOAD_DIR}")
        print(f"\n{YELLOW}Tip: Provide the full path or move the file to your Downloads folder.{RESET}")
        return

    filename = os.path.basename(local_path)
    file_size = os.path.getsize(local_path)
    
    print(f"\nUploading: {BOLD}{filename}{RESET} ({file_size} bytes)")
    
    try:
        # Create a proxy-free opener
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        
        params = urllib.parse.urlencode({'path': remote_dir, 'name': filename})
        url = f"{base_url}/upload?{params}"
        
        with open(local_path, 'rb') as f:
            data = f.read() # Read entire file into memory for simplicity (stream for large files if needed)
            
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Length', str(len(data)))
        
        with opener.open(req, timeout=60) as response:
            if response.status == 200:
                print(f"{GREEN}Upload successful!{RESET}")
            else:
                print(f"{RED}Upload failed: {response.read().decode()}{RESET}")
                
    except Exception as e:
         print(f"{RED}Failed: {e}{RESET}")
    
    input(f"{GREY}[Press Enter]{RESET}")

MAGENTA = "\033[95m"
CYAN_DARK = "\033[36m"
GREEN_DARK = "\033[32m"
MAGENTA_DARK = "\033[35m"
BLUE_DARK = "\033[34m"
YELLOW_DARK = "\033[33m"

ROW_COLORS = [CYAN, GREEN, MAGENTA, BLUE, YELLOW]

def main():
    global CURRENT_ITEMS
    server_ip = get_server_ip()
    base_url = f"http://{server_ip}:{PORT}"
    current_path = "home/lifemm" 
    
    while True:
        clear_screen()
        print(f"{GREY}Remote: {server_ip} | Local: {DOWNLOAD_DIR}{RESET}")
        print(f"{BOLD}Path: /{BLUE}{current_path}{RESET}")
        print("-" * 60)
        
        data = fetch_list(base_url, current_path)
        if data is None:
            input("Connection lost. Press Enter to retry...")
            continue
            
        CURRENT_ITEMS = data 
        print(f" {BOLD}{'#':<3}{RESET} | {'Type':<5} | {'Size':<10} | Name")
        print("-" * 60)

        if not data: print(" (Empty Directory)")
        
        for i, item in enumerate(data):
            # --- COLOR CYCLING LOGIC ---
            color = ROW_COLORS[i % len(ROW_COLORS)]
            
            # Index uses the row color
            idx_str = f"{color}{i+1:<3}{RESET}"
            
            if item['type'] == 'dir':
                # Directories: BOLD + Row Color
                ftype = f"{BOLD}{color}[DIR]{RESET}"
                size = "" 
                name_disp = f"{BOLD}{color}{item['name']}{RESET}"
            else:
                # Files: Normal Row Color
                ftype = f"{color}     {RESET}"
                size = f"{color}{str(item['size']):<10}{RESET}"
                name_disp = f"{color}{item['name']}{RESET}"
                
            print(f" {idx_str} | {ftype} | {size} | {name_disp}")

        print("-" * 60)

        display_path = current_path if current_path != "." else "/"
        try:
            cmd = input(f"{GREEN}remote:{BLUE}/{display_path}{RESET}$ ").strip()
        except EOFError: break 

        if not cmd: continue
        parts = cmd.split(" ", 1)
        action = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        if action in ['exit', 'quit', 'q']: break
        if action in ['help', '?']:
            show_help()
            continue
        if action == '..' or (action == 'cd' and arg == '..'):
            if current_path != ".":
                current_path = os.path.dirname(current_path)
                if not current_path: current_path = "."
            continue

        if action == 'put':
            if not arg:
                print(f"{RED}Usage: put <local_file_path>{RESET}")
                input()
            else:
                upload_file(base_url, arg, current_path)
            continue

        target_items = []
        
        # Helper to get item by Index or Name
        def get_item_by_ref(ref):
            if ref.isdigit():
                idx = int(ref) - 1
                if 0 <= idx < len(data): return data[idx]
            else:
                for item in data:
                    if item['name'] == ref: return item
            return None

        # PARSE TARGETS
        if action.isdigit():
             # Single direct index access -> cd (dir) or get (file) logic handled dynamically later
             t = get_item_by_ref(action)
             if t: target_items.append(t)
        
        elif action in ['get', 'zip']:
            # Handle multiple arguments: "1 2 3" or "1-5" or "file.txt"
            # Args are in 'arg' string. We need to split properly.
            # Special case: filenames with spaces? For now assuming space-separated IDs or filenames without spaces if multiple context.
            
            raw_tokens = arg.split()
            for token in raw_tokens:
                if '-' in token and token.replace('-', '').isdigit():
                    # Range 1-5
                    start, end = map(int, token.split('-'))
                    for i in range(start, end + 1):
                        t = get_item_by_ref(str(i))
                        if t and t not in target_items: target_items.append(t)
                else:
                    # Single item (ID or Name)
                    t = get_item_by_ref(token)
                    if t and t not in target_items: target_items.append(t)
        
        elif action == 'cd':
             t = get_item_by_ref(arg)
             if t: target_items.append(t)
             
        else:
             # Try to match command as a filename directly (fallback for implicit 'cd' or 'get'?? No, current logic is strict)
             # But legacy logic allowed "foldername" to cd.
             t = get_item_by_ref(cmd)
             if t: target_items.append(t)

        
        if not target_items:
             if action not in ['cd', 'get', 'zip', 'put']:
                  print(f"{RED}Item '{cmd}' not found.{RESET}")
                  input()
             continue

        # PROCESS TARGETS
        for target_item in target_items:
            # Smart Default Action if just typed number/name
            current_action = action
            if current_action.isdigit() or current_action not in ['cd', 'get', 'zip']:
                 if target_item['type'] == 'dir': current_action = 'cd'
                 else: current_action = 'get'

            if current_action == 'zip':
                if target_item['type'] == 'dir':
                    download_item(base_url, target_item, current_path, as_zip=True)
                else:
                    print(f"{RED}Error: Use 'get' for files ({target_item['name']}).{RESET}")
                    
            elif current_action == 'get':
                if target_item['type'] == 'dir':
                    print(f"{YELLOW}Zipping folder: {target_item['name']}{RESET}")
                    download_item(base_url, target_item, current_path, as_zip=True)
                else:
                    download_item(base_url, target_item, current_path, as_zip=False)
                    
            elif current_action == 'cd':
                if target_item['type'] == 'dir':
                    if current_path == ".": current_path = target_item['name']
                    else: current_path = f"{current_path}/{target_item['name']}"
                    # CD only supports one target realistically, so break after first success
                    break 
                else:
                     print(f"{RED}Error: '{target_item['name']}' is not a directory.{RESET}")

if __name__ == "__main__":
    main()
