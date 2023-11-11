#!/usr/local/bin/python3
import math
import cgi
jsonObj = cgi.FieldStorage()
import json
import datetime


from GEE_API_server import GEE_Service

def printErrorMessage(task_id,errorMessage,adviceMessage='Double check the inputs. '):
	return (400,{"Content-type":"application/json"},json.JSONEncoder().encode({'status':'error','taskID':task_id,'errorMesage':errorMessage,'advice':adviceMessage}));

class GP_elevationPath(GEE_Service):

	def __init__(self,service_account, apiKeyFile, highvolume=False ):
		super(GP_elevationPath, self).__init__(service_account, apiKeyFile, highvolume)

	def getElevationAlongPath(self, path, distanceSampling, dataScale, percentileArray ):

		dataScale*=111139;
		distanceSampling*=111139;

		#SRTM = self.ee.Image("CGIAR/SRTM90_V4")	
		#elev=SRTM.reduceResolution(self.ee.Reducer.percentile(percentileArray),True)
		elev=self.ee.ImageCollection("COPERNICUS/DEM/GLO30").mosaic().select("DEM").reproject(crs="EPSG:4326",scale=dataScale/8).reduceResolution(self.ee.Reducer.percentile(percentileArray),True)
		def makeAsPoint(l):
			return self.ee.Geometry.Point(l);
		listPoint=self.ee.Geometry.LineString(path).coordinates()

		def polylineAsMultiline(idVal):
			idVal=self.ee.Number(idVal);
			return self.ee.Feature(self.ee.Geometry.LineString([listPoint.get(idVal),listPoint.get(idVal.add(1))], "EPSG:4326", True),{"startIndex":idVal})

		listLine=self.ee.List.sequence(0,listPoint.size().subtract(2)); 
		listLine=self.ee.FeatureCollection(listLine.map(polylineAsMultiline))

		def lineAsCollection(line):
			length=line.length()
			start=self.ee.Geometry.Point(line.geometry().coordinates().get(0))

			def getSampleFeatures(l):
				pt=self.ee.Geometry.Point(self.ee.Geometry(l).coordinates().get(0))
				return self.ee.Feature(pt,{"pathPosition":pt.distance(start).divide(length).add(line.getNumber("startIndex"))})

			return self.ee.FeatureCollection(line.geometry().cutLines(self.ee.List.sequence(0,length,distanceSampling)).geometries().map(getSampleFeatures))

		samplePoints=listLine.map(lineAsCollection).flatten()

		val=elev.unmask(0).reduceRegions(samplePoints,self.ee.Reducer.first(),dataScale)

		url=val.getDownloadURL("csv", [f"DEM_p{num}" for num in percentileArray]+["pathPosition"], "elevPath")

		return {
					'format':'csv',
					'url':url,
					'resolution':dataScale,
					'spacing':distanceSampling
				}

	def singleRequest(self, jsonObj, requestType):
		
		timeStamp=math.floor(datetime.datetime.utcnow().timestamp());
		
		with open("logs/{}.log".format(timeStamp), 'w') as f:
			f.write(json.JSONEncoder().encode(jsonObj))
		
		if len(jsonObj.keys())<1 :
			return printErrorMessage(timeStamp,'jsonObj is empty! did you send it as json my accident? ')

		if 'path' not in jsonObj.keys() and not ('lat'  in jsonObj.keys()  and 'lon' in jsonObj.keys()):
			return printErrorMessage(timeStamp,'path or lat + lon is missing, is should be an array of [lon,lat] or an array of lat and an array on lon. ')
		
		if 'scale' not in jsonObj.keys():
			return printErrorMessage(timeStamp,'scale is missing')

		if 'samplingScale' not in jsonObj.keys():
			return printErrorMessage(timeStamp,'scale is missing')
		
		

		if 'lat' in jsonObj.keys() and 'lon' in jsonObj.keys():
			path=list(zip(jsonObj["lon"],jsonObj["lat"]))

		if 'path' in jsonObj.keys():
			path=jsonObj["path"]


		try:
			scale=float(jsonObj["scale"]);
			samplingScale=scale;
		except:
			return printErrorMessage(timeStamp,'scale should be a number. '); 

		if 'samplingScale' in jsonObj.keys():
			try:
				samplingScale=float(jsonObj["samplingScale"]);
			except:
				return printErrorMessage(timeStamp,'samplingScale should be a number. '); 
		
		percentile=[10,50,90];

		if 'percentile' in jsonObj.keys():
			try:
				percentile=jsonObj["percentile"];
			except:
				return printErrorMessage(timeStamp,'samplingScale should be a number. '); 

		try:
			dic = self.getElevationAlongPath(path,samplingScale,scale,percentile);
			dic = {'status':'success', 'taskID':timeStamp,'data':dic};
			return (200,{"Content-type":"application/json"},json.JSONEncoder().encode(dic));
		except Exception as e:
			return printErrorMessage(timeStamp,str(e),"An error has occurred. Please try again, and if the problem persists, file an issue on https://github.com/Rafnuss/GeoPressureServer/issues/new?body=task_id:{}&labels=crash".format(timeStamp));
