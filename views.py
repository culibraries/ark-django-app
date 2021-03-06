from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework_xml.renderers import XMLRenderer
from rest_framework.parsers import JSONParser
from django.http import HttpResponseRedirect
from rest_framework.exceptions import APIException
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
from rest_framework.exceptions import APIException


class arkMissingError(APIException):
    status_code = 400
    default_detail = 'The ARK was not found. Please make sure the submitted ARK url has been minted.'
    default_code = 'Missing ARK Error'


class arkUniqueError(APIException):
    status_code = 400
    default_detail = 'ARKs need to be unique. Please update the existing ARK or submit a new response with a unique ARK.'
    default_code = 'ARK Unique Error'


class arkValidationError(APIException):
    status_code = 400
    default_detail = "ARKs require a NAAN/Identifier. This error generated regarding '/' not within ARK submitted. No other checks are currently performed."
    default_code = 'ARK Validation Error'


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
            data = self.cleanID(request, data)
            return Response(data)
            # return CatalogData.get(database='Catalog', collection=cybercom_ark_collection, format='json')
        elif naan and ark:
            # check for ? ?? or ??? if no question marks resolve
            url = request.get_full_path()
            # build_absolute_uri()
            groups = groupby(url)
            result = [(label, sum(1 for _ in group))
                      for label, group in groups if label == '?']
            try:
                # Pull Record
                data = self.pullRecord(request, naan, ark)
                item = data['results'][0]
            except:
                raise arkMissingError()
            if not result:
                # Resolve
                # try:
                #     # Show Tombstone if ARK status is removed
                #     if item['status'].lower() == 'removed':
                #         url = url.replace('?', '')
                #         if url.strip()[-1] == '/':
                #             url = url[:-1]
                #         return HttpResponseRedirect("{0}/detail".format(url))
                # except:
                #     pass
                try:
                    return HttpResponseRedirect(item["resolve_url"])
                except:
                    raise APIException("resolve_url is not active")
            elif result[0][1] >= 2:
                # expanded response
                try:
                    url = url.replace('?', '')
                    if url.strip()[-1] == '/':
                        url = url[:-1]
                    return HttpResponseRedirect("{0}/detail".format(url))
                except:
                    raise APIException("redirect error to ark detail view")
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

    def cleanID(self, request, data):
        new_results = [{k: v for k, v in d.items() if k != '_id'}
                       for d in data['results']]
        for item in new_results:
            item.update(
                {"ark-detail": "{0}/{1}/detail".format(request.build_absolute_uri('/ark:'), item['ark'])})
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
        template = request.query_params.get('template', 'eedededdedek')
        mintark = True
        if 'ark' in request.data and request.data['ark'].strip() != '':
            mintark = False
        if mintark:
            # Mint
            ark = self.mint(request, naan, template, prefix)
        else:
            ark = request.data['ark']
            if not self.checkArk(request, ark):
                raise arkUniqueError()
        # Set Metadata
        arkMeta = self.registerARK(ark, request.data)
        # Store Metadata
        self.saveCatlog(arkMeta)
        url = request.build_absolute_uri('/ark:/')
        query = {"filter": {"ark": ark}}
        url = '{0}?query={1}'.format(url, json.dumps(query))
        if format and format != 'api':
            url = "{0}&format={1}".format(url, format)
        return HttpResponseRedirect(url)

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
        # if not arkpy.validate(ark):
        #     return False
        # Catalog URL
        try:
            naan, ark = ark.split('/')
        except:
            raise arkValidationError()
        data = self.pullRecord(request, naan, ark)
        if data['count'] > 0:
            return False
        return True

    def registerARK(self, ark, data):
        baseRecord = {"ark": ark, "resolve_url": "",
                      "retired_url": [], "metadata": {}}
        baseRecord.update(data)
        return baseRecord


class ArkDetail(APIView):
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
        return Response(data)
        # return HttpResponseRedirect(request.build_absolute_uri())

    def delete(self, request, naan=None, ark=None, format=None):
        item = self.pullRecord(request, naan, ark)
        result = MongoDataDelete(
            self.db, 'catalog', cybercom_ark_collection, item['_id'])
        return Response({"deleted_count": result.deleted_count, "_id": item['_id']})

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
        if '_id' in data:
            del data['_id']
        return data
