#!/usr/bin/env python3
import os
from GEE_API_server import GEE_Handler, GEE_server
from map import *
from timeseries import *

PORT = 24853
server_address = ("", PORT)

server = GEE_server
handler = GEE_Handler;
print("Serveur actif sur le port :", PORT)

#["/","/GeoPressure/v1/","/GeoPressure"]
httpd = server(server_address, handler,{'/GeoPressure/v1/timeseries/':GP_timeseries_v1(os.environ['GEE_API_ADDRESS'],'../gee-api-key.json'),
										'/GeoPressure/v1/map/':GP_map_v1(os.environ['GEE_API_ADDRESS'],'../gee-api-key.json')})
#Dont need httpS
# httpd.socket = ssl.wrap_socket (httpd.socket,
#         keyfile="../ssl/privkey.pem",
#         certfile='../ssl/fullchain.pem', server_side=True)
httpd.serve_forever()