# GeoPressureServer

## Introduction

GeoPressureServer is a JSON API that makes it easy to compute the mismatch of a geolocator pressure timeserie with the atmospheric pressure from [ERA5-LAND reanalysis data](https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-land).

This docs describe how to use the [GeoPressureServer](http://glp.mgravey.com/GeoLocPressure/) API. We hope you enjoy these docs, and please don't hesitate to [file an issue](https://github.com/Rafnuss/GeoPressureServer/issues/new) if you see anything missing.

## Description

With this api, you will be able to compute the maps of pressure mismatch from a geolocator pressure timeseries.

**Input**
The input parameters are the labeled pressure timeseries (time, pressure, label) and the grid (West, South, East, North, scale).

**Ouput**
We return a maps with two layers.
1. The [mean square error (MSE)](https://en.wikipedia.org/wiki/Mean_squared_error) between the input pressure timeseries and the reanalysis one at each location, 
2. A mask of whether the altitude equivalent to the pressure measurement is within the min and max altitude found in each grid cell. The altitude equivalent is computed with [the barometric formula](https://en.wikipedia.org/wiki/Barometric_formula) accounting for the temperature variation from ERA5 data. The min and max altitude of each pixel is computed from the [SRTM-30](https://developers.google.com/earth-engine/datasets/catalog/CGIAR_SRTM90_V4).

To get these map, you first need to call the API which will return a list of urls (one for each unique label). Then, using these urls, you can download the geotiff of the output map. Note that the actual calculation is only performed when you request the map (second step), making this step much longer.

The time range available to query is the same as ERA5-Land data, which is from 1981 to three months from real-time. More information can be found at the [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-land) and the [the corresponding Google Earth Engine dataset](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_HOURLY#description).

## Pressure map

### Request

```http
GET http://glp.mgravey.com/GeoPressure/v1/map.py/?
```

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `W` | `number` | **Required**. West coordinate. -180° to 180°. |
| `S` | `number` | **Required**. South coordinate. 0° to 90°. |
| `E` | `number` | **Required**. East coordinate. -180° to 180°. |
| `N` | `number` | **Required**. North coordinate. 0° to 90°. |
| `scale` | `number` | (*default=10*) Number of pixel per latitude, longitude. 10 for a resultion of 0.1° (~10) and 4 for a resolution of 0.25° (~30km). To avoid interpolating the ERA5 data, `scale` should be smaller than 10. Read more about `scale` on [Google earth Engine documention.](https://developers.google.com/earth-engine/guides/scale).  |
| `pressure` | `array of number` | **Required**. Atmospheric pressure to match in Pascal. |
| `time` | `array of number` | **Required**. [UNIX time](https://en.wikipedia.org/wiki/Unix_time) of the pressure data (i.e., number of second since 1-janv-1970.   |
| `label` | `array of string/number` | **Required**. Define the grouping of the pressure data. All pressure with the same label will be match together |


## Responses

See example for response structure.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `status` | `success` or `error` | |
| `task_id` | `number` | . |
| `labels` | `array of string/number` | List of unique labels. Same order than urls. |
| `urls` | `array of string` | List of the mismatch urls. |
| `resolution` | `number` |  |
| `size` | `array of number` | |
| `bbox` | `array of number` | |


## Example

```http
GET http://glp.mgravey.com/GeoPressure/v1/map.py/?W=-18&S=4&E=16&N=51&time=[1572075000,1572076800,1572078600]&pressure=[97766,97800,97833]&label=[1,1,1]
```

```javascript
{
  "status" : success,
  "task_id" : 1639259414,
  "data"    : 
    labels: [1],
    urls: ['https://earthengine.googleapis.com/v1alpha/projects/earthengine-legacy/thumbnails/d0f8335cac1ccb4bb27da95ecf7d5718-65cde402d14f88a8a7fcf8256c8793e5:getPixels'],
    resolution: ,
    size: [],
    bbox: [],
  }
}
```
