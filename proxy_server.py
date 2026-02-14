from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import os

class ProxyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/'):
            # Proxy API requests to backend
            try:
                url = 'http://localhost:3000' + self.path
                with urllib.request.urlopen(url) as response:
                    self.send_response(response.status)
                    for header, value in response.headers.items():
                        if header.lower() not in ['transfer-encoding', 'connection']:
                            self.send_header(header, value)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(response.read())
            except Exception as e:
                self.send_error(500, str(e))
        else:
            # Redirect root to front_gate.html
            if self.path == '/':
                self.path = '/front_gate.html'
            # Serve static files
            super().do_GET()
    
    def do_POST(self):
        if self.path.startswith('/api/'):
            # Proxy API requests to backend
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length) if content_length > 0 else b''
                
                # Forward all headers including Authorization
                headers = {}
                for header, value in self.headers.items():
                    if header.lower() not in ['host', 'connection']:
                        headers[header] = value
                
                req = urllib.request.Request(
                    'http://localhost:3000' + self.path,
                    data=body,
                    headers=headers
                )
                
                with urllib.request.urlopen(req) as response:
                    self.send_response(response.status)
                    for header, value in response.headers.items():
                        if header.lower() not in ['transfer-encoding', 'connection']:
                            self.send_header(header, value)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
                    self.end_headers()
                    self.wfile.write(response.read())
            except urllib.error.HTTPError as e:
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(e.read())
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(405)
    
    def do_OPTIONS(self):
        # Handle CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()

if __name__ == '__main__':
    os.chdir('/Users/jahnavibandarupalli/gateway')
    server = HTTPServer(('0.0.0.0', 8080), ProxyHandler)
    print('✅ Proxy server running on http://0.0.0.0:8080')
    server.serve_forever()
