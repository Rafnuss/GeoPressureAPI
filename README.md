# GeoPressureAPI

[![Test Server](https://github.com/Rafnuss/GeoPressureAPI/actions/workflows/test-server.yml/badge.svg)](https://github.com/Rafnuss/GeoPressureAPI/actions/workflows/test-server.yml)

## Introduction

GeoPressureAPI is a JSON API that makes it easy to compute the mismatch of a geolocator pressure timeserie with the atmospheric pressure from [ERA5-LAND reanalysis data](https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-land).

This docs describe how to use the GeoPressure API. We hope you enjoy these docs, and please don't hesitate to [file an issue](https://github.com/Rafnuss/GeoPressureAPI/issues/new) if you see anything missing.


## Pressure map

```http
POST /glp.mgravey.com/GeoPressure/v2/map/
```

### Description

With this end-point, you will be able to compute the maps of pressure mismatch from a geolocator pressure timeseries.

The input parameters are the labeled pressure timeseries (time, pressure, label) and the grid (West, South, East, North, scale). See below for details.

We return a geotiff map with one or two layers.
1. **mse**: The first layer is the mismatch between the input pressure timeseries and the reanalysis one at each location. This is computed with a [mean square error (MSE)](https://en.wikipedia.org/wiki/Mean_squared_error) where the mean error is removed. The mean error is removed because we assume no specific altitude of the geolocator, thus allowing an altitudinal shift of the pressure timeseries.
2.  **mask**: (optional) The second layer quantifies how often the pressure timeseries corresponds to altitude falling within the min and max ground elevation found in each pixel of the map. For instance, a pixel with a value of 0.9 indicates that for 90% of the timeseries, the bird was found on an elevation which exists in the range of altitude found in that pixel. The altitude value of the geolocator pressure timeseries is computed with [the barometric formula](https://en.wikipedia.org/wiki/Barometric_formula) accounting for the temporal variation of pressure (surface-pressure) and temperature (2m-temperature) based on ERA5 data. The min and max ground elevation of each pixel is computed from [SRTM-90](https://developers.google.com/earth-engine/datasets/catalog/CGIAR_SRTM90_V4). In addition, you can use the `margin` parameter to account for possible errors in pressure and vertical movement of the bird. It define a range of pressure error acceptable where the bird is still considered to be on the ground. You can not return this layer using the `includeMask` paramaters. 

In order to save computational time, you can use the `maskThreshold` parameter which will filter the mask layer and only keep pixel with a mask value above the threashold for the rest of the computation. This means that the mse layer is only computed for these pixels. 

To get these maps, you first need to call the API which will return a list of urls (one for each unique label). Then, using these urls, you can download the `geotiff` of the output map. Note that the actual calculation is only performed when you request the map (second step), making this step much longer.

The time range available to query is the same as ERA5-Land data, which is from 1981 to three months from real-time. More information can be found at the [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-land) and the [the corresponding Google Earth Engine dataset](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_HOURLY#description).

The time resolution of the ERA5-Land is 1 hours. The API will compute the match for any timestamp provided in the request by using the closest 1 hours. To avoid redundant information, downscale the timeseries to 1 hour before the request. 

### Request

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `W` | `number` | **Required**. West coordinate. -180° to 180°. |
| `S` | `number` | **Required**. South coordinate. 0° to 90°. |
| `E` | `number` | **Required**. East coordinate. -180° to 180°. |
| `N` | `number` | **Required**. North coordinate. 0° to 90°. |
| `scale` | `number` | *default: `10`*. Number of pixels per latitude, longitude. 10 for a resolution of 0.1° (~10) and 4 for a resolution of 0.25° (~30km). To avoid interpolating the ERA5 data, `scale` should be smaller than 10. Read more about `scale` on [Google earth Engine documention.](https://developers.google.com/earth-engine/guides/scale).  |
| `pressure` | `array of number` | **Required**. Atmospheric pressure to match in Pascal. |
| `time` | `array of number` | **Required**. [UNIX time](https://en.wikipedia.org/wiki/Unix_time) of the pressure data (i.e., number of second since 1-janv-1970.   |
| `label` | `array of string/number` | **Required**. Define the grouping of the pressure data. All pressure with the same label will be match together |
| `maxSample` | `number` | *default: `250`*. The computation of the mismatch is only performed on `maxSample` datapoints of pressure to reduce computational time. The samples are randomly (uniformly) selected on the timeseries.  |
| `margin` | `number` | *default: `30`*. The margin is used in the threshold map to accept some measurement error. unit in meter. (1hPa~10m) |
| `includeMask`    | `boolean` | *default: `true`*. Specify if the mask variable should be included in the download. If set to `false`, only the MSE band will be downloaded. |
| `maskThreshold`  | `float`   | default: 0. A value above 0 will filter the map to only compute the MSE at pixel where the proportion of pressure datapoint are falling at ground level. Typically a value of 0.9 can considerably reduce the computational time by only considering pixel above this threashold.|


### Responses

See example for response structure.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `status` | `success` or `error` | |
| `taskId` | `number` | Task ID. Use this ID for communication if you have any problem. |
| `labels` | `array of string/number` | List of unique labels. Same order than urls. |
| `urls` | `array of string` | List of the mismatch urls. |
| `resolution` | `number` | resolution in degree. Same resolution for latitude and longitude. |
| `size` | `array of number` | Number of pixel of the map.|
| `bbox` | `Object` | Bounding box requested. |
| `includeMask`     | `boolean`| The boolean flag indicating if the mask variable was included.  |
| `maskThreshold`   | `float`  | The threshold value used to generate the mask.                  |
| `errorMesage` | `string` | In case `status==error`, `errorMessage` provides the reason for the error |
| `advice` | `string` | In case `status==error`, `advice` provides guidance on how to solve the problem |

### URL content

Each url will with return a [`geotiff` file](https://en.wikipedia.org/wiki/GeoTIFF) with one or two bands/layers: **mse** and optionally the **mask**. Pixels not covered by the data (i.e., water) are indecated with a value of `-2`, while pixels with a **mse** below `maskThreashold` are indicated with a `-1` in the **mse**.


#### API Endpoint
```http
POST /glp.mgravey.com/GeoPressure/v2/map/
```

#### Request (POST with JSON body)
```json
{
    "W": -18,
    "S": 4,
    "E": 16,
    "N": 51,
    "time": [1572075000,1572076800,1572078600],
    "pressure": [97766,97800,97833],
    "label": [1,1,1]
}
```

#### Response:
```javascript
{
  "status" : success,
  "task_id" : 1639259414,
  "data"    : {
    "labels": [1],
    "urls": ['https://earthengine.googleapis.com/v1alpha/projects/earthengine-legacy/thumbnails/d0f8335cac1ccb4bb27da95ecf7d5718-65cde402d14f88a8a7fcf8256c8793e5:getPixels'],
    "resolution": 0.25,
    "size": [136 188],
    "bbox": {w:-18, S:4, E:16, N:51},
    "time2GetUrls": 11.61416506767273,
    "includeMask": true,
    "maskThreshold": 0.9,
  }
}
```




## Pressure timeseries
```http
POST /glp.mgravey.com/GeoPressure/v2/timeseries/
```
### Description
The second endpoint allows you to return the pressure timeseries at one specific location. This can be useful to check visually the match of the geolocator pressure with the ERA5 pressure at a specific location (e.g., most likely position according to the response of the endpoint `map`). 

If you supply the `pressure` (and `time`) of the geolocator, it will additionally return the `altitude` of the geolocator (above sea level).

The timeseries of the response will be the same as `time` if supply, otherwise, it will return on an hourly basis between `startTime` and `endTime`.

When requesting a position on water, it will move the position to the shortest point on land. The response will include `distInter >0 ` and the exact coordinates used in the computation.

### Request

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `lon` | `number` | **Required**. longitude coordinate. -180° to 180°. |
| `lat` | `number` | **Required**. latitude coordinate. 0° to 90°. |
| `pressure` | `array of number` | geolocator pressure. |
| `time` | `array of number` | **Required if pressure**. [UNIX time](https://en.wikipedia.org/wiki/Unix_time) of the pressure data (i.e., number of second since 1-janv-1970.   |
| `startTime` | `number` | **Required if NOT pressure**. [UNIX time](https://en.wikipedia.org/wiki/Unix_time) of start (i.e., number of second since 1-janv-1970.  |
| `endTime` | `number` | **Required if NOT pressure**. [UNIX time](https://en.wikipedia.org/wiki/Unix_time) of end (i.e., number of second since 1-janv-1970.  |


### Responses

See example for response structure.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `status`    | `success` or `error` | |
| `taskId`    | `number` | Task ID. Use this ID for communication if you have any problem. |
| `url`       | `string` | urls of the response timeseries |
| `distInter` | `number` | Distance interpolated from the requested coordinate to the one used. meters. |
| `lon`       | `number` | longitude coordinate used (different than requested if over water). |
| `lat`       | `number` | latitude coordinate used (different than requested if over water). |



### URL content

The url will with return a `csv` the following columns:

| date | pressure | (altitude) |
| :--- | :--- | :--- |
| ... | ... | ... |

### Example
#### API Endpoint
```http
POST /glp.mgravey.com:24853/GeoPressure/v2/timeseries/
```

#### Request (POST with JSON body)
```json
{
    "lon": 6,
    "lat": 46,
    "startTime": 1497916800,
    "endTime": 1500667800
}
```

#### Response:
```javascript
{
  "status" : success,
  "task_id" : 1639259414,
  "data"    : {
    urls: ['https://earthengine.googleapis.com/v1alpha/projects/earthengine-legacy/thumbnails/d0f8335cac1ccb4bb27da95ecf7d5718-65cde402d14f88a8a7fcf8256c8793e5:getPixels'],
    format: 'csv'
  }
}
```

## Installation

To install the server:
1. Clone this repository.
```bash
git clone https://github.com/Rafnuss/GeoPressureAPI
```
2. Add the `json` file with the key in the repository.
3. Update `bootServer.sh` with the appropriate service address.
4. Create a `logs` folder 
5. Add a route to the server if needed
```bash
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 80
sudo iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 443
```
6. Run the server
```bash
bash bootServer.sh
```
