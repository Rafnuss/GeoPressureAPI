#!/usr/local/bin/python3
import math
import cgi
form = cgi.FieldStorage()
import json
import datetime
import os
import asyncio

from GEE_API_server import GEE_Service

def printErrorMessage(task_id,errorMessage,adviceMessage='Double check the inputs'):
		return (400,{"Content-type":"application/json"},json.JSONEncoder().encode({'status':'error','taskID':task_id,'errorMesage':errorMessage,'advice':adviceMessage}));

class GP_timeseries_v1(GEE_Service):

	

	def boundingTimeCollection(self,timeStart,timeEnd,coordinates):
		def reduce2aPixel(im):
			return im.addBands(self.ee.Image.constant(self.ee.Number(im.get('system:time_start')).divide(1000)).rename('time').toLong()).sample(region=self.ee.Geometry.Point(coordinates), scale=10, numPixels=1);
		ERA5_pressur=self.ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY").filterDate(timeStart,self.ee.Date(timeEnd).advance(1,'hour')).select(['surface_pressure'],['pressure']);
		fc=ERA5_pressur.map(reduce2aPixel).flatten()
		url=self.ee.FeatureCollection(fc).getDownloadURL(selectors=['time','pressure'])
		return url;

	def expliciteTimeCollection(self,time,pressure,coordinates):
		def makeFeature(li):
			li=self.ee.List(li);
			return self.ee.Feature(None,{'system:time_start':self.ee.Number(li.get(0)).multiply(1000),'pressure':li.get(1)})

		val=self.ee.List([time, pressure]).unzip();
		fc=self.ee.FeatureCollection(val.map(makeFeature));

		start=fc.aggregate_min('system:time_start');
		end=fc.aggregate_max('system:time_start');
		ERA5=self.ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY");

		ERA5_pressur=ERA5.filterDate(start,self.ee.Date(end).advance(1,'hour')).select(['surface_pressure','temperature_2m']);

		era5_llabelFeature=self.ee.Join.saveBest(matchKey='bestERA5',measureKey='diff').apply(fc,ERA5_pressur,self.ee.Filter.maxDifference(3600*1000,leftField='system:time_start',  rightField='system:time_start' ));

		def getAltitude(ft):
			#standard temperature lapse rate [K/m] = -0.0065 [K/m]
			Lb = -0.0065;
			#universal gas constant = 8.31432 [N * m / mol /K]
			R = 8.31432;
			#gravitational acceleration constant = 9.80665 [m/s^2]
			g0 = 9.80665;
			#molar mass of Earth s air = 0.0289644 [kg/mol]
			M = 0.0289644;
			#standard temperature (temperature at sea level) [K]
			T0 = 273.15+15;

			altIm=self.ee.Image('projects/earthimages4unil/assets/PostDocProjects/rafnuss/Geopot_ERA5');
			dh = self.ee.Image(ft.get('bestERA5')).select('temperature_2m').divide(Lb).multiply(self.ee.Image.constant(self.ee.Number(ft.get('pressure'))).divide(self.ee.Image(ft.get('bestERA5')).select('surface_pressure')).pow(-R*Lb/g0/M).subtract(1)).add(altIm).rename('altitude');
			return dh.addBands(self.ee.Image(ft.get('bestERA5')).select('surface_pressure').rename('pressure')).addBands(self.ee.Image.constant(self.ee.Number(ft.get('system:time_start'))).rename('time').divide(1000).toLong()).sample(region=self.ee.Geometry.Point(coordinates), scale=10, numPixels=1);

		agregatedMap=self.ee.FeatureCollection(era5_llabelFeature.map(getAltitude)).flatten();
		url=agregatedMap.getDownloadURL(selectors=['time','pressure','altitude'])
		return url;

	def checkPosition(self,coordinates):
		lon,lat=coordinates;
		print(lon,lat)
		ERA5=self.ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY");
		land=ERA5.first().select(0).mask();
		radius=1000000;
		geometry=self.ee.Geometry.Point(coordinates);
		isLand=list(land.reduceRegion(self.ee.Reducer.first(),geometry,1).getInfo().values())[0];
		if(not isLand):
			land=land.focalMin(1,'circle','pixels')
			aoi=self.ee.FeatureCollection(self.ee.Feature(geometry)).distance(radius).addBands(self.ee.Image.pixelLonLat()).updateMask(land);
			best=aoi.reduceRegion(self.ee.Reducer.min(3),geometry.buffer(radius),land.geometry().projection().nominalScale().multiply(0.1)).getInfo();
			return (best['min1'],best['min2'],best['min'],True);
		else:
			return (lon, lat,0,False);

	def singleRequest(self, form, requestType):
		timeStamp=math.floor(datetime.datetime.utcnow().timestamp());
		with open("logs/{}.log".format(timeStamp), 'w') as f:
			f.write(json.JSONEncoder().encode(form))
		
		if('lon' not in form.keys() or 'lat' not in form.keys() ):
			return printErrorMessage(timeStamp,'lon and lat are mendatory!')

		try:
			if isinstance(form["lon"], list):
				lon=float(form["lon"][0]);
			else:
				lon=float(form["lon"]);
		except:
			return printErrorMessage(timeStamp,'lon is not a float number');

		try:
			if isinstance(form["lat"], list):
				lat=float(form["lat"][0]);
			else:
				lat=float(form["lat"]);
		except:
			return printErrorMessage(timeStamp,'lat is not a float number');

		informedTimeSeries=False;
		if('time' in form.keys() and 'pressure' in form.keys()):
			informedTimeSeries=True;
		else:
			if 'startTime' not in form.keys() or 'endTime' not in form.keys() :
				return printErrorMessage(timeStamp,'startTime and endTime OR time and pressure arrays are mendatory!')

		if(informedTimeSeries):
			time=form["time"];
			pressure=form["pressure"];
			if(isinstance(time[0], str)):
				time=json.JSONDecoder().decode(time[0])
			if(isinstance(pressure[0], str)):
				pressure=json.JSONDecoder().decode(pressure[0])

		else:
			try:
				if isinstance(form["startTime"], list):
					timeStart=int(form["startTime"][0]);
				else:
					timeStart=int(form["startTime"]);
			except:
				return printErrorMessage(timeStamp,'startTime is not a int number');

			try:
				if isinstance(form["endTime"], list):
					timeEnd=int(form["endTime"][0]);
				else:
					timeEnd=int(form["endTime"]);
			except:
				return printErrorMessage(timeStamp,'endTime is not a int number');

			timeStart=timeStart*1000;
			timeEnd=timeEnd*1000;

		try:
			lon,lat,dist,change=self.checkPosition([lon, lat]);
			if informedTimeSeries:
				url=self.expliciteTimeCollection(time,pressure,[lon, lat]);
			else:
				url=self.boundingTimeCollection(timeStart,timeEnd,[lon, lat]);
			dic = {'status':'success', 'taskID':timeStamp,'data':{'format':'csv','url':url,'lon':lon,'lat':lat,'distInter':dist}};
			return (200,{"Content-type":"application/json"},json.JSONEncoder().encode(dic));
		except Exception as e:
			return printErrorMessage(timeStamp,str(e),"An error has occurred. Please try again, and if the problem persists, file an issue on https://github.com/Rafnuss/GeoPressureServer/issues/new?body=task_id:{}&labels=crash".format(timeStamp));
