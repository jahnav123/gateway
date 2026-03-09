from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import urllib.error
import os

class ProxyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/'):
            self.proxy_request('GET')
        else:
            if self.path == '/':
                self.path = '/front_gate.html'
            super().do_GET()
    
    def do_POST(self):
        if self.path.startswith('/api/'):
            self.proxy_request('POST')
        else:
            self.send_error(405)
            
    def do_OPTIONS(self):
        # Handle CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()

    def proxy_request(self, method):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            
            # Forward all headers including Authorization
            headers = {}
            for header, value in self.headers.items():
                if header.lower() not in ['host', 'connection']:
                    headers[header] = value
            
            # Construct the backend URL (keep the /api/ part)
            url = 'http://localhost:3000' + self.path
            
            req = urllib.request.Request(
                url,
                data=body,
                headers=headers,
                method=method
            )
            
            with urllib.request.urlopen(req) as response:
                self.send_response(response.status)
                for header, value in response.headers.items():
                    if header.lower() not in ['transfer-encoding', 'connection', 'access-control-allow-origin']:
                        self.send_header(header, value)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response.read())
                
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            print(f"Proxy Error: {e}")
            self.send_error(500, str(e))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    # Use current directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
    server = HTTPServer(('0.0.0.0', port), ProxyHandler)
    print(f'✅ Proxy server running on http://0.0.0.0:{port}')
    server.serve_forever()
