#!/usr/local/bin/python3
import math
import cgi
jsonObj = cgi.FieldStorage()
import json
import datetime
import os
numCores = os.cpu_count()
from concurrent.futures import ThreadPoolExecutor


from GEE_API_server import GEE_Service

def printErrorMessage(task_id,errorMessage,adviceMessage='Double check the inputs. '):
	return (400,{"Content-type":"application/json"},json.JSONEncoder().encode({'status':'error','taskID':task_id,'errorMesage':errorMessage,'advice':adviceMessage}));

class GP_pressurePath(GEE_Service):

	def __init__(self,service_account, apiKeyFile, highvolume=False ):
		super(GP_pressurePath, self).__init__(service_account, apiKeyFile, highvolume);
		Era5Land = self.ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")
		Era5=self.ee.ImageCollection("ECMWF/ERA5/HOURLY");

		indexFilter = self.ee.Filter.equals(leftField= 'system:index',rightField= 'system:index');

		simpleJoin = self.ee.Join.saveFirst("match");
		simpleJoined = simpleJoin.apply(Era5, Era5Land, indexFilter);

		def combineBands(im):
			land=self.ee.Image(im.get("match"))
			commonBands=land.bandNames().filter(self.ee.Filter.inList('item',im.bandNames()))
			return im.addBands(self.ee.ImageCollection([im,land]).select(commonBands).mosaic(),None,True)

		self.ERA5Combined=self.ee.ImageCollection(simpleJoined).map(combineBands)


	def getPresureAlongPath(self, path, time, pressure, variable,nbChunk=10,dataset="both"):
		def makeFeature(li):
			li=self.ee.List(li);
			return self.ee.Feature(self.ee.Geometry.Point(li.get(2)),{'system:time_start':self.ee.Number(li.get(0)).multiply(1).multiply(1000),'pressure':li.get(1)})

		val=self.ee.List([time, pressure, path] if pressure else [time, [0]*len(time), path] ).unzip();
		def runComputation4Chunk(i,val):

			def unmaskIm(image):
				return image.unmask(100,True)

			chunkSize=(size//nbChunk)+1;
			localVal=val.slice(i*chunkSize,min((i+1)*chunkSize,size))
			fc=self.ee.FeatureCollection(localVal.map(makeFeature));
			start=fc.aggregate_min('system:time_start');
			end=fc.aggregate_max('system:time_start');
			if dataset.lower()=="single-levels":
				ERA5=self.ee.ImageCollection("ECMWF/ERA5/HOURLY");
			elif dataset.lower()=="land":
				ERA5=self.ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")
			else:
				ERA5=self.ERA5Combined;


			ERA5_pressur=ERA5.filterDate(start,self.ee.Date(end).advance(1,'hour'))#.select(['surface_pressure','temperature_2m']);
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
				return dh.addBands(self.ee.Image(ft.get('bestERA5'))).addBands(self.ee.Image.constant(self.ee.Number(ft.get('system:time_start')).divide(1000)).rename('time').toLong()).sample(region=ft.geometry(), scale=1, numPixels=1, dropNulls=False).first().set("ERA5_ID",self.ee.Image(ft.get('bestERA5')).get("system:index"));

			agregatedMap=self.ee.FeatureCollection(era5_llabelFeature.map(getAltitude))

			def toJson(key,val):
				return agregatedMap.aggregate_array(val);
			print(agregatedMap.getInfo())
			js=self.ee.Dictionary.fromLists(list(set(["time"]+(["altitude"] if pressure else []) +variable)), list(set(["time"]+(["altitude"] if pressure else []) +variable))).map(toJson)

			results[i]=js.getInfo()

		size=len(path);
		results=[None]*nbChunk;

		with ThreadPoolExecutor(max_workers=numCores*3) as executor:
			executor.map(runComputation4Chunk,list(range(nbChunk)),[val]*nbChunk)	

		print(results)
		results=[x for x in results if x is not None]
		
		return {key: [item for d in results for item in d[key]] for key in results[0]}
		# url=agregatedMap.getDownloadURL(selectors=['time']+variable)
		# return url;

	def singleRequest(self, jsonObj, requestType):
		
		timeStamp=math.floor(datetime.datetime.utcnow().timestamp());
		
		with open("logs/{}.log".format(timeStamp), 'w') as f:
			f.write(json.JSONEncoder().encode(jsonObj))
		
		if len(jsonObj.keys())<1 :
			return printErrorMessage(timeStamp,'jsonObj is empty! did you send it as json my accident? ')

		if 'path' not in jsonObj.keys() and not ('lat'  in jsonObj.keys()  and 'lon' in jsonObj.keys()):
			return printErrorMessage(timeStamp,'path or lat + lon is missing, is should be an array of [lon,lat] or an array of lat and an array on lon. ')
		
		if 'time' not in jsonObj.keys():
			return printErrorMessage(timeStamp,'time should be an array ')
		
		if 'variable' not in jsonObj.keys():
			return printErrorMessage(timeStamp,'variable should be an array of ERA-5 band name ')

		if 'lat' in jsonObj.keys() and 'lon' in jsonObj.keys():
			path=list(zip(jsonObj["lon"],jsonObj["lat"]))

		if 'path' in jsonObj.keys():
			path=jsonObj["path"]

		dataset="both";
		if 'dataset' in jsonObj.keys():
			if isinstance(jsonObj["dataset"], list):
				dataset=jsonObj["dataset"][0]
			else:
				dataset=jsonObj["dataset"]

		workers=10;
		if 'workers' in jsonObj.keys():
			if isinstance(jsonObj["workers"], list):
				workers=int(jsonObj["workers"][0])
			else:
				workers=int(jsonObj["workers"])

		time=jsonObj["time"]
		pressure=None;
		if 'pressure' in jsonObj.keys():
			pressure=jsonObj["pressure"]
		variable=jsonObj["variable"]

		if((pressure and len(path)!=len(pressure)) or len(path)!=len(time)):
			return printErrorMessage(timeStamp,'pressure, time and path should have the same length')
		
		try:
			dic = self.getPresureAlongPath(path,time, pressure,variable,workers,dataset);
			dic = {'status':'success', 'taskID':timeStamp,'data':dic};
			return (200,{"Content-type":"application/json"},json.JSONEncoder().encode(dic));
		except Exception as e:
			import traceback 
			traceback.print_exc() 
			return printErrorMessage(timeStamp,str(e),"An error has occurred. Please try again, and if the problem persists, file an issue on https://github.com/Rafnuss/GeoPressureServer/issues/new?body=task_id:{}&labels=crash".format(timeStamp));
