from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import json
import os
import requests
import base64
from .permission import arkPermission

cybercom_token = os.getenv('CYBERCOM_TOKEN')
cybercom_catalog_url = os.getenv(
    'ARK_CATALOG_URL', "/api/catalog/data/catalog/ark/")
cybercom_ark_collection='ark'
from catalog.views import Catalog, CatalogData,CatalogDataDetail 

class ArkServer(APIView):
    permission_classes = (arkPermission)

    def get(self, request, naan=None, ark=None, format=None):
        request.data['collection']=cybercom_ark_collection
        return Catalog.get(request,database='Catalog')
        # if naan and ark:

        # response = redirect(cybercom_catalog_url)
        # return response
        # return True

    def post(self, request, naan=None, ark=None, format=None):
        """
        Mint Ark with data stored in data catalog 
        ARGS: naan - defaults to CU Boulder
              prefix - defaults ''
              template - default 'eeddeeddeeddeeeek'

        """
        # NAAN - default to CU Boulder
        #naan = request.query_params.get('naan', '47540')
        # prefix - default ''
        prefix = request.query_params.get('prefix', '')
        # template - default 'eeddeeddeeddeeeek'
        template = request.query_params.get('template', 'eeddeeddeeddeeeek')

        # Mint
        ark = self.mint(naan, template, prefix)
        # Set Metadata
        arkMeta = registerARK(ark, request.data)
        # Store Metadata
        headers = {"Content-Type": "application/json",
                   "Authorization": "Token {0}".format(cybercom_token)}

        return ark

    def mint(self, naan, template, prefix):
        ark = arkpy.mint(naan, template, prefix)
        while !(self.checkArk(ark)):
            ark = arkpy.mint(naan, template, prefix)
        return ark

    def checkArk(self, request, ark):
        """
        Check if valid ARk. Plus check unique within data catalog
        """
        if not arkpy.validate(ark):
            return False
        # Catalog URL
        base_url = "/".join(request.build_absolute_url.split('/')[:3])
        query = '{"filter":{"ark":"' + ark + '"}'
        url = "{0}{1}?query={2}&format=json".format(
            base_url, cybercom_catalog_url, query)
        req = requests.get(url)
        data = req.json()
        if data['count'] > 0:
            return False
        return True

    def registerARK(self, ark, data):
        temp = {"ark": ark, "resolve_url": "", "retired_url": [],"metadata":{}}
        data['ark'] = ark
        return temp.update(data)
