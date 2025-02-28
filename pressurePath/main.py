import functions_framework
from pressurePath import *
import os

#'/GeoPressure/v2/map/':
hightVolumeEndpoint=True;

process=GP_pressurePath(os.environ.get('GEE_API_ADDRESS'),'../gee-api-key.json',hightVolumeEndpoint)

@functions_framework.http
def pressurePath(request):
    defaultHeaders={'Access-Control-Allow-Origin': '*',
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Access-Control-Allow-Headers": "Accept, Content-Type"}

    if request.method == "OPTIONS":
        return ("", 204, defaultHeaders)

    if request.method == "POST":
        request_json = request.get_json(silent=True)
        if request_json:
            try:
                code,typeResponse,response=process.singleRequest(request_json,None)
                return (response,code, { **defaultHeaders, **typeResponse})
            except Exception as e:
                print(e)
                return ("Catastrophic Error :(".encode('utf-8'),500,);
        else:
            return("Your input must be in JSON format over a POST request. It appears you're using API V2. If you intended to use API V1 (which is no longer maintained), you may do so. However, we strongly recommend using a PSOT request with JSON on the API V2 for better support".encode('utf-8'),500);

    else:
        return ({
              "error": "Method Not Allowed",
              "message": "This endpoint only supports POST requests."
            },405)
    