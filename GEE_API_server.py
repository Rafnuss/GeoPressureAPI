import http.server
from http.server import SimpleHTTPRequestHandler
import os
import json
from urllib.parse import urlparse, parse_qs


class GEE_Handler (SimpleHTTPRequestHandler):
    dictionaryApp={};
    def __init__(self, request, client_address, server):
        self.dictionaryApp=server.dictionaryApp;
        super(GEE_Handler, self).__init__(request, client_address, server)

    def setDictionaryApp(self,dictionaryApp):
        self.dictionaryApp=dictionaryApp;
        print(self.dictionaryApp)

    def end_headers (self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header("Access-Control-Allow-Methods", "POST,GET,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Accept, Content-Type")
        SimpleHTTPRequestHandler.end_headers(self)

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()

    def do_GET(self):
        try:
            self.notJSON();
        except:
            self.catastrophicError();

    def do_POST(self):
        try:
            parsedUrl=urlparse(self.path);
            content_type = self.headers['Content-Type']
            if(content_type not in  'application/json'):
                self.notJSON()
            length = int(self.headers['Content-Length']);
            field_data = self.rfile.read(length);
            jsonObj = json.loads(field_data.decode('utf-8'))
            self.GEE_service(parsedUrl.path, jsonObj,'POST');
        except:
            self.catastrophicError();

    def GEE_service(self,service, jsonObj, requestType):
        status=404
        hearders={}
        val='';
        if(service in self.dictionaryApp.keys()):
            status,hearders,val=self.dictionaryApp[service].singleRequest(jsonObj,requestType)        
        self.send_response(status)
        
        for key in hearders.keys():
            try:
                self.send_header(key, hearders[key]);
                pass
            except Exception as e:
                print(e);
        self.end_headers()
        self.wfile.write(val.encode('utf-8'))

    def catastrophicError(self):
        self.send_response(500)
        self.end_headers()
        self.wfile.write("Catastrophic Error :(".encode('utf-8'))

    def notJSON(self):
        self.send_response(500)
        self.end_headers()
        self.wfile.write("Your input must be in JSON format over a POST request. It appears you're using API V2. If you intended to use API V1 (which is no longer maintained), you may do so. However, we strongly recommend using a PSOT request with JSON on the API V2 for better support".encode('utf-8'))

class GEE_server (http.server.HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, dictionaryApp):
        super(GEE_server, self).__init__(server_address, RequestHandlerClass)
        self.dictionaryApp=dictionaryApp;

class GEE_Service():

  def __init__(self,service_account, apiKeyFile, highvolume=False ):
    super(GEE_Service, self).__init__()
    import ee 
    credentials = ee.ServiceAccountCredentials(service_account, apiKeyFile)
    ee.Initialize(credentials,opt_url=('https://earthengine-highvolume.googleapis.com' if highvolume else 'https://earthengine.googleapis.com'))
    self.ee=ee
