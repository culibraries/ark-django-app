from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import TemplateHTMLRenderer
import json
import os
# import requests
# import base64
import arkpy
from .permission import arkPermission
from itertools import groupby
from django.http import HttpResponseRedirect
from catalog.views import Catalog, CatalogData, CatalogDataDetail
from data_store.mongo_paginator import MongoDataPagination
from data_store.renderer import DataBrowsableAPIRenderer, mongoJSONPRenderer, mongoJSONRenderer
from rest_framework_xml.renderers import XMLRenderer
from api import config
from rest_framework.settings import api_settings
from pymongo import MongoClient
# (DB_MongoClient, database, collection, query=None, page=1, nPerPage=None, uri=''):

cybercom_ark_collection = os.getenv('ARK_CATALOG_COLLECTION', 'ark')


class arkAcknowledgement(APIView):
    """
    A view that returns CU Boulder Acknowledgement.
    """
    renderer_classes = [TemplateHTMLRenderer]

    def get(self, request, naan=None, format=None):
        return Response({}, template_name='arkAcknowledgement.html.js')


class arkMetadata(APIView):
    """
    A view that returns CU Boulder Ark Metadata.
    """
    renderer_classes = [TemplateHTMLRenderer]

    def get(self, request, naan=None, format=None):
        return Response({}, template_name='metadataAcknowledgement.html.js')


class ArkServer(APIView):
    permission_classes = (arkPermission,)
    connect_uri = config.DATA_STORE_MONGO_URI
    renderer_classes = [mongoJSONRenderer, mongoJSONRenderer, mongoJSONRenderer
                        XMLRenderer, DataBrowsableAPIRenderer]

    def __init__(self):
        self.db = MongoClient(host=self.connect_uri)

    def get(self, request, naan=None, ark=None, format=None):
        if not request.GET._mutable:
            request.GET._mutable = True
        url = request and request.build_absolute_uri() or ''
        format = format or 'json'
        if not naan:
            # return list of arks
            #request.GET['collection'] = cybercom_ark_collection
            page = int(request.query_params.get('page', '1'))
            page_size = request.query_params.get(api_settings.user_settings.get('PAGINATE_BY_PARAM', 'page_size'),
                                                 api_settings.user_settings.get('PAGINATE_BY', 10))
            try:
                page = int(request.query_params.get('page', 1))
            except:
                page = 1
            try:
                page_size = int(page_size)
            except:
                page_size = int(
                    api_settings.user_settings.get('PAGINATE_BY', 25))

            data = MongoDataPagination(
                self.db, 'catalog', cybercom_ark_collection, query={}, page=page, nPerPage=page_size, uri=url)
            return Response(data)
            # return CatalogData.get(database='Catalog', collection=cybercom_ark_collection, format='json')
        elif naan and ark:
            # check for ? ?? or ??? if no question marks resolve
            url = request.get_full_path()
            # build_absolute_uri()
            groups = groupby(url)
            result = [(label, sum(1 for _ in group))
                      for label, group in groups if label == '?']
            # Pull Record
            data = self.pullRecord(request, naan, ark)
            item = data['results'][0]
            if not result:
                # Resolve
                return HttpResponseRedirect(item["resolve_url"])
            elif result[0][1] >= 2:
                # expanded response
                return Response(item)
            # elif result[0][1] >= 3:
            #     # check for ? ?? or ??? if no question marks resolve
            #     return Response(item)
            else:
                raise Exception('Some Error.')
        else:
            data = {
                "error": "Error occured both NAAN and ARK are required for GET operations. Please "}
            return Response(data)

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
        self.saveCatlog(request)

        return ark

    def pullRecord(self, request, naan, ark):
        url = request and request.build_absolute_uri() or ''
        page = int(request.query_params.get('page', '1'))
        page_size = request.query_params.get(api_settings.user_settings.get('PAGINATE_BY_PARAM', 'page_size'),
                                             api_settings.user_settings.get('PAGINATE_BY', 10))
        try:
            page = int(request.query_params.get('page', 1))
        except:
            page = 1
        try:
            page_size = int(page_size)
        except:
            page_size = int(
                api_settings.user_settings.get('PAGINATE_BY', 25))
        query = '{"filter":{"ark":"' + naan + '/' + ark + '"}}'
        data = MongoDataPagination(
            self.db, 'catalog', cybercom_ark_collection, query=query, page=page, nPerPage=page_size, uri=url)
        # request.GET['query'] = query
        # data = CatalogData.get(request, database='Catalog',
        #                        collection=cybercom_ark_collection, format='json')

        return data

    def saveCatlog(self, request):
        data = CatalogData.post(
            request, database='Catalog', collection=cybercom_ark_collection, format='json')
        return data

    def mint(self, naan, template, prefix):
        ark = arkpy.mint(naan, template, prefix)
        while (not (self.checkArk(ark))):
            ark = arkpy.mint(naan, template, prefix)

        return ark

    def checkArk(self, request, ark):
        """
        Check if valid ARk. Plus check unique within data catalog
        """
        if not arkpy.validate(ark):
            return False
        # Catalog URL
        naan, ark = ark.split('/')
        data = json.loads(self.pullRecord(request, naan, ark))
        if data['count'] > 0:
            return False
        return True

    def registerARK(self, ark, data):
        temp = {"ark": ark, "resolve_url": "",
                "retired_url": [], "metadata": {}}
        data['ark'] = ark
        return temp.update(data)
