import functions_framework
from pressurePath import *
import os
import json
import tempfile

hightVolumeEndpoint=True;

# Replace these with your actual key and client email values
gee_api_key_content = os.environ.get('GEE_API_KEY').encode('utf-8').decode('unicode_escape')
gee_api_address = os.environ.get('GEE_API_ADDRESS').encode('utf-8').decode('unicode_escape')  # should contain your client email

# Prepare the JSON content as a dictionary
key_data = {
    "private_key": gee_api_key_content,
    "client_email": gee_api_address,
    "token_uri": "https://oauth2.googleapis.com/token"
}

# Create a temporary JSON file with the key content
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
    json.dump(key_data, tmp_file)
    tmp_file.flush()
    process=GP_pressurePath(gee_api_address,tmp_file.name,hightVolumeEndpoint)

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
    