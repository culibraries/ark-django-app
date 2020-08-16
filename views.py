from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework_xml.renderers import XMLRenderer
from rest_framework.parsers import JSONParser
from django.http import HttpResponseRedirect
from rest_framework.settings import api_settings
import json
import os
import arkpy
from pymongo import MongoClient
from itertools import groupby
from api import config
# Permissions
from .permission import arkPermission
from .renderer import DataBrowsableAPIRenderer
# Leverage Data Store code
from data_store.mongo_paginator import MongoDataPagination, MongoDataSave, MongoDataInsert, MongoDataDelete, MongoDataGet
from data_store.renderer import mongoJSONPRenderer, mongoJSONRenderer

# Default ARK collection
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
        return Response({}, template_name='arkMetadata.html.js')


class ArkServer(APIView):
    permission_classes = (arkPermission,)
    connect_uri = config.DATA_STORE_MONGO_URI
    renderer_classes = [mongoJSONRenderer, DataBrowsableAPIRenderer,
                        XMLRenderer]

    def __init__(self):
        self.db = MongoClient(host=self.connect_uri)

    def get(self, request, naan=None, ark=None, format=None):
        if not request.GET._mutable:
            request.GET._mutable = True
        url = request and request.build_absolute_uri() or ''
        format = format or 'json'
        if not naan:
            # return list of arks
            # request.GET['collection'] = cybercom_ark_collection
            query = request.query_params.get('query', None)
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
                self.db, 'catalog', cybercom_ark_collection, query=query, page=page, nPerPage=page_size, uri=url)
            data = self.cleanID(data)
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
                return HttpResponseRedirect("{0}/detail".format(url.replace('?', '')))
                # Response(item)
            # elif result[0][1] >= 3:
            #     # check for ? ?? or ??? if no question marks resolve
            #     return Response(item)
            else:
                raise Exception('Some Error.')
        else:
            data = {
                "error": "Error occured both NAAN and ARK are required for GET operations. Please "}
            return Response(data)

    def cleanID(self, data):
        new_results = [{k: v for k, v in d.items() if k != '_id'}
                       for d in data['results']]
        data['results'] = new_results
        return data

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
        # naan = request.query_params.get('naan', '47540')
        # prefix - default ''
        prefix = request.query_params.get('prefix', '')
        # template - default 'eeddeeddeeddeeeek'
        template = request.query_params.get('template', 'eeddeeddeeddeeeek')

        # Mint
        ark = self.mint(request, naan, template, prefix)
        # Set Metadata
        arkMeta = self.registerARK(ark, request.data)
        # Store Metadata
        self.saveCatlog(arkMeta)

        return Response(arkMeta)

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
        return data

    def saveCatlog(self, recorddata):
        data = MongoDataInsert(
            self.db, 'catalog', cybercom_ark_collection, recorddata)
        return data

    def mint(self, request, naan, template, prefix):
        ark = arkpy.mint(naan, template, prefix)
        while (not (self.checkArk(request, ark))):
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
        data = self.pullRecord(request, naan, ark)
        if data['count'] > 0:
            return False
        return True

    def registerARK(self, ark, data):
        baseRecord = {"ark": ark, "resolve_url": "",
                      "retired_url": [], "metadata": {}}
        baseRecord.update(data)
        return baseRecord


class ArkServerDetail(APIView):
    permission_classes = (arkPermission,)
    # model = dataStore
    renderer_classes = [DataBrowsableAPIRenderer,
                        mongoJSONRenderer, XMLRenderer]
    parser_classes = [JSONParser]
    connect_uri = config.DATA_STORE_MONGO_URI

    def __init__(self):
        self.db = MongoClient(host=self.connect_uri)

    def get(self, request, naan=None, ark=None, format=None):
        try:
            item = self.pullRecord(request, naan, ark)
            data = MongoDataGet(self.db, 'catalog',
                                cybercom_ark_collection, item['_id'])
            data = self.cleanID(data)
            return Response(data)
        except:
            return HttpResponseRedirect(request.build_absolute_uri('/ark:/'))

    def put(self, request, naan=None, ark=None, format=None):
        item = self.pullRecord(request, naan, ark)
        data = MongoDataSave(
            self.db, 'catalog', cybercom_ark_collection, item['_id'], request.data)
        data = self.cleanID(data)
        return Response(data)

    def delete(self, request, naan=None, ark=None, format=None):
        item = self.pullRecord(request, naan, ark)
        result = MongoDataDelete(
            self.db, 'catalog', cybercom_ark_collection, item['_id'])
        return Response({"deleted_count": result.deleted_count, "_id": id})

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
        return data['results'][0]

    def cleanID(self, data):
        data.pop('_id', None)
        return data
