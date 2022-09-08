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

class GP_map_v1(GEE_Service):
	def getMSE_Map(self, time, pressure, label, W, S, E, N, boxSize, sclaeFcator=10, mode='full',maxSample=250,margin=30):
		
		def makeFeature(li):
			li=self.ee.List(li);
			return self.ee.Feature(None,{'system:time_start':self.ee.Number(li.get(0)).multiply(1000),'pressure':li.get(1),'label':li.get(2)})
		
		val=self.ee.List([time, pressure, label]).unzip();
		fc=self.ee.FeatureCollection(val.map(makeFeature));

		def makeFeatureLabel(labelId):
			return self.ee.Feature(None,{'label':labelId});

		listLabel=fc.aggregate_array('label').distinct();

		ERA5=self.ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY");
		endERA5=ERA5.filterDate('2022','2100').aggregate_max('system:time_start').getInfo();

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
			

			ERA5_stat=ERA5.aggregate_stats('system:time_start');
			if(self.ee.Number(end).gt(endERA5).getInfo()):
				return None;

			ERA5_pressur=ERA5.filterDate(self.ee.Date(start).advance(-1,'hour'),self.ee.Date(end).advance(1,'hour')).select(['surface_pressure','temperature_2m']);

			# if(ERA5_pressur.size().getInfo()<1):
			# 	return None;
			era5_llabelFeature=self.ee.Join.saveBest(matchKey='bestERA5',measureKey='diff').apply(labelFeature,ERA5_pressur,self.ee.Filter.maxDifference(3600*1000,leftField='system:time_start',  rightField='system:time_start' ));

			def getpresurMap(ft):
				return self.ee.Image(ft.get('bestERA5'));

			meanMapPressure=self.ee.ImageCollection(era5_llabelFeature.map(getpresurMap)).select('surface_pressure').mean();

			def getError(ft):
				error=self.ee.Image(ft.get('bestERA5')).select('surface_pressure').subtract(meanMapPressure).subtract(self.ee.Number(ft.get('pressure')).subtract(presureMeanSesnor)).toFloat();
				altIm=self.ee.Image('projects/earthimages4unil/assets/PostDocProjects/rafnuss/min_max_elevation');
				dh = self.ee.Image(ft.get('bestERA5')).select('temperature_2m').divide(Lb).multiply(self.ee.Image.constant(self.ee.Number(ft.get('pressure'))).divide(self.ee.Image(ft.get('bestERA5')).select('surface_pressure')).pow(-R*Lb/g0/M).subtract(1));
				isPossible=dh.gte(altIm.select('elevation_min').add(-margin)).And(dh.lte(altIm.select('elevation_max').add(margin))).toFloat();
				return error.multiply(error).addBands(isPossible).rename(['error','isPossible']);

			agregatedMap=self.ee.ImageCollection(era5_llabelFeature.map(getError)).mean().updateMask(ERA5_pressur.first().mask())
			if 'full' not in mode:
				agregatedMap=agregatedMap.updateMask(agregatedMap.select('isPossible').gte(0.90)); # I hardcode 90% you can change if you want
			if 'redcued' in mode:
				agregatedMap=agregatedMap.select('error')

			#agregatedMap=agregatedMap.addBands(agregatedMap.mask());

			return agregatedMap.set('label',labelFeature.get('label'))

		#listLabel_py=listLabel.getInfo();
		listLabel_py=list(set(label));# maybe less robust, but clearly much faster
		urls={}

		for label in listLabel_py:
				im=runMSEmatch(fc.filter(self.ee.Filter.equals('label',label)));
				if im:
					urls[label]=im.getDownloadURL({"name":'label',"dimensions":boxSize,"format":"GEO_TIFF", "region":self.ee.Algorithms.GeometryConstructors.BBox(W,S,E,N)});# ZIPPED_GEO_TIFF
				else:
					urls[label]=None;

		return {'format':'GEOTIFF',
				'labels':listLabel_py,
				'urls':[urls[label] for label in listLabel_py],
				'resolution':1/sclaeFcator,
				'bbox':{'W':W,'S':S,'E':E,'N':N},
				'size':boxSize
				}




	def singleRequest(self, form, requestType):

		timeStamp=math.floor(datetime.datetime.utcnow().timestamp());
		with open("logs/{}.log".format(timeStamp), 'w') as f:
			f.write(json.JSONEncoder().encode(form))
		
		if 'W' not in form.keys() or 'S' not in form.keys() or 'E' not in form.keys() or 'N' not in form.keys() :
			return printErrorMessage(timeStamp,'W,S,E or N is missing the bounding box is mendatory!')

		if('time' not in form.keys() or 'pressure' not in form.keys() or 'label' not in form.keys()):
			return printErrorMessage(timeStamp,'time, pressure and label are mendatory!')

		try:
			if isinstance(form["W"], list):
				W=float(form["W"][0]);
			else:
				W=float(form["W"]);
		except:
			return printErrorMessage(timeStamp,'W is not a float number');

		try:
			if isinstance(form["S"], list):
				S=float(form["S"][0]);
			else:
				S=float(form["S"]);
		except:
			return printErrorMessage(timeStamp,'S is not a float number');

		try:
			if isinstance(form["E"], list):
				E=float(form["E"][0]);
			else:
				E=float(form["E"]);
		except:
			return printErrorMessage(timeStamp,'E is not a float number');

		try:
			if isinstance(form["N"], list):
				N=float(form["N"][0]);
			else:
				N=float(form["N"]);
		except:
			return printErrorMessage(timeStamp,'N is not a float number');




		scale=10;
		if 'scale' in form.keys():
			try:
				if isinstance(form["scale"], list):
					scale=float(form["scale"][0]);
				else:
					scale=float(form["scale"]);
			except:
				return printErrorMessage(timeStamp,'scale should be a number');return 

		maxSample=250;
		if 'maxSample' in form.keys():
			try:
				if isinstance(form["maxSample"], list):
					maxSample=int(form["maxSample"][0]);
				else:
					maxSample=int(form["maxSample"]);
			except:
				return printErrorMessage(timeStamp,'maxSample should be a number');

		margin=30;
		if 'margin' in form.keys():
			try:
				if isinstance(form["margin"], list):
					margin=float(form["margin"][0]);
				else:
					margin=float(form["margin"]);
			except:
			  return printErrorMessage(timeStamp,'margin is not a float number');

		mode='full;'
		if 'mode' in form.keys():
			if isinstance(form["mode"], list):
				mode=form["mode"][0];
			else:
				mode=form["mode"];

		sizeLon=(E-W)*scale;
		sizeLat=(N-S)*scale;

		if math.fabs(sizeLon-round(sizeLon))>0.001:
			return printErrorMessage(timeStamp,'(E-W)*scale should be an integer');

		if math.fabs(sizeLat-round(sizeLat))>0.001:
			return printErrorMessage(timeStamp,'(N-S)*scale should be an integer');

		sizeLon=round(sizeLon);
		sizeLat=round(sizeLat);

		time=form["time"];
		pressure=form["pressure"];
		label=form["label"];

		if(isinstance(time[0], str)):
			time=json.JSONDecoder().decode(time[0])
		if(isinstance(pressure[0], str)):
			pressure=json.JSONDecoder().decode(pressure[0])
		if(isinstance(label[0], str)):
			label=json.JSONDecoder().decode(label[0])


		if(len(time)!=len(pressure) or len(time)!=len(label)):
			return printErrorMessage(timeStamp,'presure time and label need to have the same length!');

		try:
			dic = self.getMSE_Map(time, pressure, label,W,S,E,N,[sizeLon, sizeLat], scale,mode,maxSample,margin);
			dic = {'status':'success', 'taskID':timeStamp,'data':dic};
			return (200,{"Content-type":"application/json"},json.JSONEncoder().encode(dic));
		except Exception as e:
			return printErrorMessage(timeStamp,str(e),"An error has occurred. Please try again, and if the problem persists, file an issue on https://github.com/Rafnuss/GeoPressureServer/issues/new?body=task_id:{}&labels=crash".format(timeStamp));
