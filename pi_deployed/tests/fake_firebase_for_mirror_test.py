import http.server,sys
class H(http.server.BaseHTTPRequestHandler):
    def do_PUT(self):
        n=int(self.headers.get("Content-Length",0));self.rfile.read(n);self.send_response(200);self.send_header("Content-Length","0");self.end_headers()
    def log_message(self,*a):pass
http.server.ThreadingHTTPServer(("127.0.0.1",8799),H).serve_forever()
