import http.server
import socketserver
import os
import socket
import threading
import json
import re
import requests
import shutil
import subprocess
import time
import sys
import cgi
import io
from datetime import datetime

PORT = 8010
current_dir = os.path.abspath(os.path.dirname(__file__))

class CustomedServer(http.server.SimpleHTTPRequestHandler):
    def extract_params(self, st, params = {}):
        if not "&" in st:
            words = [st[2:]]
        else:
            words = st[2:].split("&")
        for word in words:
            if not "=" in word:
                continue
            else:
                k, v = word.split("=")
                params[k] = v
        return params

    def _set_headers(self):
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.end_headers()
        
    def do_HEAD(self):
        self._set_headers()

    def do_GET(self):
        self._set_headers()
        files = os.listdir(current_dir)
        if "index.htm" in files or "index.html" in files:
            htmlfile = os.path.join(current_dir, "index.htm")
            if "index.html" in files:
                htmlfile = os.path.join(current_dir, "index.html")
            with open(htmlfile, "r") as fp:
                data = fp.read()        
                self.wfile.write(data.encode())
        self.GET = self.extract_params(str(self.query))
        self.get_request(self.query)

    def post_data(self):
            boundary = self.headers.get_boundary()
            remainbytes = int(self.headers['content-length'])
            line = str(self.rfile.readline())
            remainbytes -= len(line)
            if not boundary in line:
                return {}
            fied_values = {}
            filenames = {}
            statuses = []
            while remainbytes > 0:
                filename = None
                line = str(self.rfile.readline())
                remainbytes -= len(line)
                fn = re.findall(r'Content-Disposition.*name="(\w+)"', str(line))
                if not fn:
                    return {}
                path = self.translate_path(self.path)
                namevalue = fn[0]
                if "; filename=" in str(line):
                    fn = re.findall(r'Content-Disposition.*name="\w+"; filename="(.*)"', str(line))
                    if fn:
                        if fn[0]:
                            filename = os.path.join(path, fn[0])
                            filenames[namevalue] = filename
                            line = self.rfile.readline() #content type
                            remainbytes -= len(line)
                out = None
                if filename:
                    out = io.BytesIO()
                preline = self.rfile.readline()
                remainbytes -= len(preline)
                start = 0
                while remainbytes > 0:
                    line = self.rfile.readline()
                    remainbytes -= len(line)
                    if boundary.encode() in line:
                        preline = preline[0:-1]
                        if preline.decode("utf-8") .endswith('\r'):
                            preline = preline[0:-1]
                        if out:
                            out.write(preline)
                            fied_values[namevalue] = out
                            statuses.append(True)
                        else:
                            fied_values[namevalue] = preline.decode("utf-8") 
                        break
                    else:
                        if start == 0:
                            start +=1 
                        else:                      
                            if out:
                                out.write(preline)
                        preline = line
            return fied_values

    def do_POST(self):
        self._set_headers()
        self.POST = self.post_data()
        self.post_request()

    def handle_one_request(self):
        try:
            self.raw_requestline = self.rfile.readline(65537)
            
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(414)
                return
            if not self.raw_requestline:
                self.close_connection = 1
                return
            if not self.parse_request():
                # An error code has been sent, just exit
                return
            mname = 'do_' + self.command
            if not hasattr(self, mname):
                self.send_error(501, "Unsupported method (%r)" % self.command)
                return
            self.query = self.path
            method = getattr(self, mname)
            method()
            self.wfile.flush() #actually send the response if not already done.
        except socket.timeout as e:
            #a read or a write timed out.  Discard this connection
            self.log_error("Request timed out: %r", e)
            self.close_connection = 1
            return

    def redirect(self, path):
        self.send_response(301)
        new_path = '%s%s'%('http://localhost:'+str(PORT), path)
        self.send_header('Location', new_path)
        self.end_headers()
            
class MyServer(CustomedServer):
    appname = None

    def get_request(self, request):
        MyServer.appname.handle_get_request(self, request)

    def post_request(self):
        MyServer.appname.handle_post_request(self)

    def http_response(self, st):
        if isinstance(st, str):
            self.wfile.write(st.encode())
        else:
            self.wfile.write(st)

    def save_file(self, filename, destination):
        destination = os.path.join(self.translate_path(self.path), destination)
        if not destination.endswith("/"):
            with open(destination, "wb") as dest:
                dest.write(filename.getbuffer())
            return 0
        return -1

    def run_as_server(self):
        MyServer.appname = type(self)
        with socketserver.TCPServer(("localhost", self.port), MyServer) as server:
            print("Local Server started at port {} ".format(self.port))
            """
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            server.server_close()
            """

        #execute as thread
            t = threading.Thread(target=server.serve_forever, args=(), daemon=True)
            t.start()
            input("")

class Application(MyServer):   
    def __init__(self, port = 8010):
        self.port = port

    @staticmethod
    def handle_get_request(request, kwords):
        pass

    @staticmethod
    def handle_post_request(request):
        data = request.POST
        code = data["code"]
        n = data["data"]
        f1 = data["filename"]
        f2 = data["filename2"]
        status1 = request.save_file(data["filename"], "../postdata/rgukt1")  
        status2 = request.save_file(data["filename2"], "../postdata/rgukt2")  

if __name__ == "__main__":
    app = Application(port=8011)
    app.run_as_server()
