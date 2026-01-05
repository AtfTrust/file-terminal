import urllib.request
import urllib.parse
import json
import os
import subprocess
import sys
import readline

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
COMMANDS = ['cd', 'get', 'zip', 'ls', 'exit', 'quit', '..']

def complete(text, state):
    buffer = readline.get_line_buffer()
    if " " not in buffer.lstrip():
        options = COMMANDS + [i['name'] for i in CURRENT_ITEMS]
    else:
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
            while True:
                chunk = response.read(1024*1024)
                if not chunk: break
                out_file.write(chunk)
        print(f"{GREEN}Saved to: {local_path}{RESET}")
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
        if action == 'ls': continue
        if action == '..' or (action == 'cd' and arg == '..'):
            if current_path != ".":
                current_path = os.path.dirname(current_path)
                if not current_path: current_path = "."
            continue

        target_item = None
        
        if action.isdigit():
            idx = int(action) - 1
            if 0 <= idx < len(data): target_item = data[idx]
        else:
            if action in ['cd', 'get', 'zip']:
                search_name = arg
            else:
                search_name = cmd
            
            for item in data:
                if item['name'] == search_name:
                    target_item = item
                    break
        
        if target_item:
            if action == 'zip':
                if target_item['type'] == 'dir':
                    download_item(base_url, target_item, current_path, as_zip=True)
                else:
                    print(f"{RED}Error: Use 'get' for files.{RESET}")
                    input()
            elif target_item['type'] == 'dir':
                if action == 'get': 
                    print(f"{YELLOW}Zipping folder...{RESET}")
                    download_item(base_url, target_item, current_path, as_zip=True)
                else:
                    if current_path == ".": current_path = target_item['name']
                    else: current_path = f"{current_path}/{target_item['name']}"
            else:
                download_item(base_url, target_item, current_path, as_zip=False)
        else:
            if action not in ['cd', 'get', 'zip']:
                 print(f"{RED}Item '{cmd}' not found.{RESET}")
                 input()

if __name__ == "__main__":
    main()
