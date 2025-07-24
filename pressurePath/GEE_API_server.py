"""
GeoPressure API - Google Earth Engine Service Base Class

This module provides a base class for Google Earth Engine services used across
the GeoPressure API. It handles authentication, initialization, and provides
a consistent interface for Earth Engine operations.

Author: GeoPressure Team
"""

import ee


class GEE_Service:
    """
    Google Earth Engine Service Base Class

    Provides a standardized interface for Google Earth Engine services across
    the GeoPressure API. Handles service account authentication and Earth Engine
    initialization with support for both standard and high-volume endpoints.

    Features:
    - Service account authentication
    - High-volume endpoint support for production workloads
    - Consistent Earth Engine interface across all modules
    - Error handling for authentication failures
    """

    def __init__(self, service_account, apiKeyFile, highvolume=False):
        """
        Initialize Google Earth Engine service with authentication.

        Sets up Earth Engine authentication using service account credentials
        and initializes the Earth Engine client with appropriate endpoint.

        Args:
            service_account (str): Google Earth Engine service account email
            apiKeyFile (str): Path to service account JSON key file
            highvolume (bool): Use high-volume Earth Engine endpoint for production
                             (default: False for standard endpoint)

        Raises:
            Exception: If Earth Engine authentication or initialization fails

        Note:
            High-volume endpoint is recommended for production workloads that
            require higher request rates and computational capacity.
        """
        super(GEE_Service, self).__init__()

        try:
            # Create service account credentials from key file
            credentials = ee.ServiceAccountCredentials(service_account, apiKeyFile)

            # Select appropriate Earth Engine endpoint
            endpoint_url = (
                "https://earthengine-highvolume.googleapis.com"
                if highvolume
                else "https://earthengine.googleapis.com"
            )

            # Initialize Earth Engine with credentials and endpoint
            ee.Initialize(credentials, opt_url=endpoint_url)

            # Store Earth Engine instance for use by subclasses
            self.ee = ee

        except Exception as e:
            raise Exception(
                f"Failed to initialize Google Earth Engine service: {str(e)}"
            )
