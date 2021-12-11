# GeoPressureServer

## Introduction

GeoPressureServer is a JSON API that makes it easy to compute the mismatch of a geolocator pressure timeserie with reanalysis data.

This docs describe how to use the [GeoPressureServer](http://glp.mgravey.com/GeoLocPressure/) API. We hope you enjoy these docs, and please don't hesitate to [file an issue](https://github.com/Rafnuss/GeoPressureServer/issues/new) if you see anything missing.


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
| `urls` | `array of string` | List of urls. |
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
    urls: [''],
    resolution: ,
    size: [],
    bbox: [],
  }
}
```
