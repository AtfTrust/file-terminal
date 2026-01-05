import http.server
import socketserver
import json
import os
import urllib.parse
import fnmatch
import shutil
import tempfile

PORT = 8000
START_DIR = "/" 

class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class NavHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        # --- 1. ZIP DIRECTORY API ---
        if parsed.path == '/zip':
            try:
                rel_path = query.get('path', ['.'])[0]
                full_path = os.path.abspath(os.path.join(START_DIR, rel_path))
                
                if not os.path.isdir(full_path):
                    self.send_error(404, "Directory not found")
                    return

                # Create a temp directory to hold the zip
                temp_dir = tempfile.mkdtemp()
                try:
                    # Create zip (shutil.make_archive adds .zip extension automatically)
                    base_name = os.path.basename(full_path)
                    if not base_name: base_name = "root"
                    
                    archive_base = os.path.join(temp_dir, base_name)
                    zip_path = shutil.make_archive(archive_base, 'zip', full_path)
                    
                    # Serve the file
                    self.send_response(200)
                    self.send_header("Content-Type", "application/zip")
                    self.send_header("Content-Disposition", f'attachment; filename="{base_name}.zip"')
                    self.send_header("Content-Length", str(os.path.getsize(zip_path)))
                    self.end_headers()
                    
                    with open(zip_path, 'rb') as f:
                        shutil.copyfileobj(f, self.wfile)
                finally:
                    # Cleanup temp files immediately
                    shutil.rmtree(temp_dir)
                    
            except Exception as e:
                # If streaming already started, this error might not show up clearly on client
                print(f"Zip Error: {e}")

        # --- 2. SEARCH API ---
        elif parsed.path == '/search':
            try:
                search_term = query.get('q', [''])[0]
                search_root = query.get('path', ['.'])[0]
                abs_search_root = os.path.abspath(os.path.join(START_DIR, search_root))
                
                results = []
                limit = 50 
                for root, dirs, files in os.walk(abs_search_root):
                    for filename in fnmatch.filter(files, f"*{search_term}*"):
                        full_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(full_path, START_DIR)
                        try: size = os.path.getsize(full_path)
                        except: size = 0
                        results.append({'name': filename, 'path': rel_path, 'type': 'file', 'size': size})
                        if len(results) >= limit: break
                    if len(results) >= limit: break
                self.send_json(results)
            except Exception as e:
                self.send_error(500, str(e))

        # --- 3. LIST API ---
        elif parsed.path == '/list':
            try:
                rel_path = query.get('path', ['.'])[0]
                target_path = os.path.abspath(os.path.join(START_DIR, rel_path))
                items = []
                if target_path != "/":
                    items.append({'name': '..', 'type': 'dir', 'size': 0})
                try:
                    for f in os.listdir(target_path):
                        if f.startswith('.'): continue
                        full_p = os.path.join(target_path, f)
                        is_dir = os.path.isdir(full_p)
                        try: size = os.path.getsize(full_p) if not is_dir else 0
                        except: size = 0
                        item_rel = os.path.relpath(full_p, START_DIR)
                        items.append({'name': f, 'path': item_rel, 'type': 'dir' if is_dir else 'file', 'size': size})
                except PermissionError: pass
                items.sort(key=lambda x: (x['type'] != 'dir', x['name']))
                self.send_json(items)
            except Exception as e:
                self.send_error(500, str(e))

        # --- 4. DOWNLOAD FILE API ---
        else:
            try:
                req_path = urllib.parse.unquote(self.path)
                if req_path.startswith('/'): req_path = req_path[1:]
                full_path = os.path.join(START_DIR, req_path)
                if os.path.isfile(full_path):
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(os.path.getsize(full_path)))
                    self.end_headers()
                    with open(full_path, 'rb') as f:
                        self.wfile.write(f.read())
                else:
                    self.send_error(404, "File not found")
            except Exception as e:
                self.send_error(500, str(e))

    def send_json(self, data):
        blob = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

print(f"[+] Serving Multi-Threaded from Root (/) on port {PORT}")
with ThreadingSimpleServer(("", PORT), NavHandler) as httpd:
    try: httpd.serve_forever()
    except KeyboardInterrupt: print("\nStopped.")
