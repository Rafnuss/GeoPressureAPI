#!/usr/bin/env python3.9
import os
from GEE_API_server import GEE_Handler, GEE_server
from map import *
from timeseries import *
import os

PORT = 24854
server_address = ("", PORT)

os.makedirs("./logs", exist_ok = True) 

server = GEE_server
handler = GEE_Handler;
print("Serveur actif sur le port :", PORT)

hightVolumeEndpoint=True;

#["/","/GeoPressure/v1/","/GeoPressure"]
httpd = server(server_address, handler,{'/GeoPressure/v2/timeseries/':GP_timeseries_v2(os.environ['GEE_API_ADDRESS'],'../gee-api-key.json',hightVolumeEndpoint),
										'/GeoPressure/v2/map/':GP_map_v2(os.environ['GEE_API_ADDRESS'],'../gee-api-key.json',hightVolumeEndpoint)})

#https is handle by nginx
httpd.serve_forever()

## nginx config 

# server {
#     listen 80;
#     listen 24853;
#     listen 443 ssl http2;
#     fastcgi_read_timeout 1200;
#     proxy_read_timeout 1200;
#     server_name DOMAIN_NAME;

#     ssl_certificate /etc/letsencrypt/live/**/fullchain.pem; # managed by Certbot
#     ssl_certificate_key /etc/letsencrypt/live/**/privkey.pem; # managed by Certbot

#     include /etc/letsencrypt/options-ssl-nginx.conf;

#     location / {
#         proxy_pass       http://localhost:24854;
#     }
# }