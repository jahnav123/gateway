from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

if __name__ == '__main__':
    os.chdir('/Users/jahnavibandarupalli/gateway')
    server = HTTPServer(('0.0.0.0', 8080), CORSRequestHandler)
    print('✅ Frontend server running on http://0.0.0.0:8080')
    print('   - Main app: http://192.168.18.104:8080/front_gate.html')
    print('   - Parent approval: http://192.168.18.104:8080/parent-approve.html')
    server.serve_forever()
