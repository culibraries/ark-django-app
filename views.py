from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import TemplateHTMLRenderer
import json
import os
import requests
import base64
from .permission import arkPermission
from itertools import groupby
from django.http import HttpResponseRedirect
from django.template import loader

cybercom_token = os.getenv('CYBERCOM_TOKEN')
cybercom_catalog_url = os.getenv(
    'ARK_CATALOG_URL', "/api/catalog/data/catalog/ark/")
cybercom_ark_collection='ark'
from catalog.views import Catalog, CatalogData,CatalogDataDetail 

class arkAcknowledgement
    """
    A view that returns CU Boulder Acknowledgement.
    """
    renderer_classes = [TemplateHTMLRenderer]

    def get(self, request,naan=None, format=None):
        return Response({}, template_name='arkAcknowledgement.html.js')



class ArkServer(APIView):
    permission_classes = (arkPermission)

    def get(self, request, naan=None, ark=None, format=None):
        if not request.GET._mutable:
            request.GET._mutable = True
        if not naan:
            # return list of arks
            #request.GET['collection'] = cybercom_ark_collection
            return CatalogData.get(request,database='Catalog',collection=cybercom_ark_collection,format='json')
        elif naan and ark:
            # check for ? ?? or ??? if no question marks resolve
            url=request.build_absolute_uri()
            groups=groupby(url)
            result=[(label, sum(1 for _ in group)) for label, group in groups if label=='?']
            query = '{"format":{"ark":"' + naan + '/' +  ark + '"}'
            request.GET['query'] = query
            data=CatalogData.get(request,database='Catalog',collection=cybercom_ark_collection,format='json')
            item= json.loads(data['results'][0])
            if not result:
                #Resolve
                return HttpResponseRedirect(item["resolve_url"]) 
            elif result[0][1] == 1:
                #min response
                return Response(item)
            elif result[0][1] == 2:
                #expanded response
                return Response(item)
            elif result[0][1] => 3:
            # check for ? ?? or ??? if no question marks resolve
                return Response(item)
        else:
            data= {"error":"Error occured both NAAN and ARK are required for GET operations. Please "}
            return Response(data)


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
        # NAAN - set default to CU Boulder if NAAN not provided
        # This option is to allow multiple ARK registration with different NAAN
        naan = naan or '47540'
        #naan = request.query_params.get('naan', '47540')
        # prefix - default ''
        prefix = request.query_params.get('prefix', '')
        # template - default 'eeddeeddeeddeeeek'
        template = request.query_params.get('template', 'eeddeeddeeddeeeek')

        # Mint
        ark = self.mint(naan, template, prefix)
        # Set Metadata
        arkMeta = self.registerARK(ark, request.data)
        # Store Metadata
        headers = {"Content-Type": "application/json",
                   "Authorization": "Token {0}".format(cybercom_token)}

        return ark
    def saveCatlog(self, request,data):
        data=CatalogData.post(request,database='Catalog',collection=cybercom_ark_collection,format='json')

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
