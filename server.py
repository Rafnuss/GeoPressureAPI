import http.server
 
PORT = 24853
server_address = ("", PORT)

server = http.server.HTTPServer
handler = http.server.CGIHTTPRequestHandler
handler.cgi_directories = ["/","/GeoPressure/v1/","/GeoPressure"]
handler.path='glp.mgravey.com'
print("Serveur actif sur le port :", PORT)

httpd = server(server_address, handler)
httpd.serve_forever()