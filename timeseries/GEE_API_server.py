class GEE_Service():

  def __init__(self,service_account, apiKeyFile, highvolume=False ):
    super(GEE_Service, self).__init__()
    import ee 
    credentials = ee.ServiceAccountCredentials(service_account, apiKeyFile)
    ee.Initialize(credentials,opt_url=('https://earthengine-highvolume.googleapis.com' if highvolume else 'https://earthengine.googleapis.com'))
    self.ee=ee
