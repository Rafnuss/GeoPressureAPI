#!/usr/local/bin/python3
import math
import cgi
jsonObj = cgi.FieldStorage()
import json
import datetime
import os
import asyncio
import numpy
import time as tm
from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ThreadPoolExecutor

from GEE_API_server import GEE_Service



def printErrorMessage(task_id,errorMessage,adviceMessage='Double check the inputs. '):
	return (400,{"Content-type":"application/json"},json.JSONEncoder().encode({'status':'error','taskID':task_id,'errorMesage':errorMessage,'advice':adviceMessage}));

class GP_map_v2(GEE_Service):

	def __init__(self,service_account, apiKeyFile, highvolume=False ):
		super(GP_map_v2, self).__init__(service_account, apiKeyFile, highvolume)
		self.endERA5=1;
		self.endERA5=self.ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY").filterDate('2022','2100').aggregate_max('system:time_start').getInfo();

		self.ERA5Scheduler = BackgroundScheduler()
		self.ERA5Scheduler.add_job(self.updateERA5, 'interval', hours=1)
		self.ERA5Scheduler.start()

	def updateERA5():
		self.endERA5 = self.ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY").filterDate(self.endERA5-1,'2100').aggregate_max('system:time_start').getInfo();
	
	def getMSE_Map(self, time, pressure, label, W, S, E, N, boxSize, sclaeFcator=10, includeMask=True, maxSample=250,margin=30,maskThreashold=0.9):
		
		def makeFeature(li):
			li=self.ee.List(li);
			return self.ee.Feature(None,{'system:time_start':self.ee.Number(li.get(0)).multiply(1000),'pressure':li.get(1),'label':li.get(2)})
		
		val=self.ee.List([time, pressure, label]).unzip();
		fc=self.ee.FeatureCollection(val.map(makeFeature));

		def makeFeatureLabel(labelId):
			return self.ee.Feature(None,{'label':labelId});

		listLabel=fc.aggregate_array('label').distinct();

		def runMSEmatch(labelFeature):

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

			labelFeature=labelFeature.randomColumn("random").sort("random").limit(maxSample);

			presureMeanSesnor=labelFeature.aggregate_mean('pressure');
			start=labelFeature.aggregate_min('system:time_start');
			end=labelFeature.aggregate_max('system:time_start');
			
			ERA5=self.ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY");

			ERA5_pressur=ERA5.filterDate(self.ee.Date(start).advance(-1,'hour'),self.ee.Date(end).advance(1,'hour')).select(['surface_pressure','temperature_2m']);

			era5_llabelFeature=self.ee.Join.saveBest(matchKey='bestERA5',measureKey='diff').apply(labelFeature,ERA5_pressur,self.ee.Filter.maxDifference(3600*1000,leftField='system:time_start',  rightField='system:time_start' ));

			def getpresurMap(ft):
				return self.ee.Image(ft.get('bestERA5'));

			meanMapPressure=self.ee.ImageCollection(era5_llabelFeature.map(getpresurMap)).select('surface_pressure').mean();

			def getError(ft):
				error=self.ee.Image(ft.get('bestERA5')).select('surface_pressure').subtract(meanMapPressure).subtract(self.ee.Number(ft.get('pressure')).subtract(presureMeanSesnor)).toFloat();
				altIm=self.ee.Image('projects/earthimages4unil/assets/PostDocProjects/rafnuss/min_max_elevation');
				dh = self.ee.Image(ft.get('bestERA5')).select('temperature_2m').divide(Lb).multiply(self.ee.Image.constant(self.ee.Number(ft.get('pressure'))).divide(self.ee.Image(ft.get('bestERA5')).select('surface_pressure')).pow(-R*Lb/g0/M).subtract(1));
				isPossible=dh.gte(altIm.select('elevation_min').add(-margin)).And(dh.lte(altIm.select('elevation_max').add(margin))).toFloat();
				return error.multiply(error).addBands(isPossible).rename(['mse','probAlt']);

			agregatedMap=self.ee.ImageCollection(era5_llabelFeature.map(getError)).mean().updateMask(ERA5_pressur.first().mask())
			
			if(maskThreashold>0):
				agregatedMap=agregatedMap.addBands(agregatedMap.select('mse').updateMask(agregatedMap.select('probAlt').gte(maskThreashold)),None,True);
				
			if not includeMask:
				agregatedMap=agregatedMap.select('mse')

			return agregatedMap.set('label',labelFeature.get('label'))

		#listLabel_py=listLabel.getInfo();
		listLabel_py=list(set(label));# maybe less robust, but clearly much faster
		urls={}

		ims={}
		for label in listLabel_py:
			ims[label]=runMSEmatch(fc.filter(self.ee.Filter.equals('label',label)));

		bbox=self.ee.Algorithms.GeometryConstructors.BBox(W,S,E,N);

		def getEEUrl(label):
			start_time = tm.time()
			if ims[label]:
				urls[label] = ims[label].getDownloadURL({"name": 'label', "dimensions": boxSize, "format": "GEO_TIFF", "region": bbox})
			else:
				urls[label] = None
			end_time = tm.time()

		start_time = tm.time()
		with ThreadPoolExecutor(max_workers=25) as executor:
			executor.map(getEEUrl, listLabel_py)
		end_time = tm.time()

		return {'format':'GEOTIFF',
				'labels':listLabel_py,
				'urls':[urls[label] for label in listLabel_py],
				'resolution':1/sclaeFcator,
				'bbox':{'W':W,'S':S,'E':E,'N':N},
				'size':boxSize,
				'time2GetUrls':end_time-start_time,
				'includeMask':includeMask,
				'maskThreashold':maskThreashold
				}

	def singleRequest(self, jsonObj, requestType):
		
		timeStamp=math.floor(datetime.datetime.utcnow().timestamp());
		
		with open("logs/{}.log".format(timeStamp), 'w') as f:
			f.write(json.JSONEncoder().encode(jsonObj))
		
		if len(jsonObj.keys())<1 :
			return printErrorMessage(timeStamp,'jsonObj is empty! did you send it as json my accident? ')

		if 'W' not in jsonObj.keys() or 'S' not in jsonObj.keys() or 'E' not in jsonObj.keys() or 'N' not in jsonObj.keys() :
			return printErrorMessage(timeStamp,'W, S, E or N are missing the bounding box is mandatory. ')

		if('time' not in jsonObj.keys() or 'pressure' not in jsonObj.keys() or 'label' not in jsonObj.keys()):
			return printErrorMessage(timeStamp,'time, pressure and label are mandatory. ')
		
		try:
			W=float(jsonObj["W"]);
		except:
			return printErrorMessage(timeStamp,'W is not a float number. ');

		try:
			S=float(jsonObj["S"]);
		except:
			return printErrorMessage(timeStamp,'S is not a float number. ');

		try:
			E=float(jsonObj["E"]);
		except:
			return printErrorMessage(timeStamp,'E is not a float number. ');

		try:
			N=float(jsonObj["N"]);
		except:
			return printErrorMessage(timeStamp,'N is not a float number. ');

		scale=10;
		if 'scale' in jsonObj.keys():
			try:
				scale=float(jsonObj["scale"]);
			except:
				return printErrorMessage(timeStamp,'scale should be a number. ');return 

		maxSample=250;
		if 'maxSample' in jsonObj.keys():
			try:
				maxSample=int(jsonObj["maxSample"]);
			except:
				return printErrorMessage(timeStamp,'maxSample should be a number. ');

		margin=30;
		if 'margin' in jsonObj.keys():
			try:
				margin=float(jsonObj["margin"]);
			except:
			  return printErrorMessage(timeStamp,'margin is not a float number. ');

		includeMask=True
		if 'includeMask' in jsonObj.keys():
			includeMask=jsonObj["includeMask"];

		maskThreashold=0.9
		if 'maskThreashold' in jsonObj.keys():
			maskThreashold=jsonObj["maskThreashold"];

		sizeLon=(E-W)*scale;
		sizeLat=(N-S)*scale;

		if math.fabs(sizeLon-round(sizeLon))>0.001:
			return printErrorMessage(timeStamp,'(E-W)*scale should be an integer. ');

		if math.fabs(sizeLat-round(sizeLat))>0.001:
			return printErrorMessage(timeStamp,'(N-S)*scale should be an integer. ');

		sizeLon=round(sizeLon);
		sizeLat=round(sizeLat);

		time=jsonObj["time"];
		pressure=jsonObj["pressure"];
		label=jsonObj["label"];

		if(len(time)!=len(pressure) or len(time)!=len(label)):
			return printErrorMessage(timeStamp,'presure time and label need to have the same length. ');

		try:
			if(numpy.array(time).max()*1000>self.endERA5):
				return (416,{"Content-type":"application/json"},json.JSONEncoder().encode({'status':'error','taskID':timeStamp,'errorMesage':"ERA-5 data not available from {}. Request only pressure with earlier date.".jsonObjat(datetime.datetime.utcfromtimestamp(self.endERA5/1000)),"lastERA5":self.endERA5}));
			dic = self.getMSE_Map(time, pressure, label, W, S, E, N, [sizeLon, sizeLat], scale, includeMask, maxSample, margin, maskThreashold);
			dic = {'status':'success', 'taskID':timeStamp,'data':dic};
			return (200,{"Content-type":"application/json"},json.JSONEncoder().encode(dic));
		except Exception as e:
			return printErrorMessage(timeStamp,str(e),"An error has occurred. Please try again, and if the problem persists, file an issue on https://github.com/Rafnuss/GeoPressureServer/issues/new?body=task_id:{}&labels=crash".jsonObjat(timeStamp));
