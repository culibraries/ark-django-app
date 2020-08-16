
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer  # , #JSONPRenderer


class DataBrowsableAPIRenderer(BrowsableAPIRenderer):
    # template = 'rest_framework/queue_run_api.html'
    def get_context(self, data, accepted_media_type, renderer_context):
        context = super(DataBrowsableAPIRenderer, self).get_context(
            data, accepted_media_type, renderer_context)
        # if context['request'].method.upper() == 'GET':
        #    context['content']=data
        temp = []
        i = 0
        crumbs = ['Ark Root', 'NAAN', 'Name', 'Detail']
        for k, v in context['breadcrumblist']:
            temp.append((crumbs[i], v))
            i = i + 1
        context['breadcrumblist'] = temp

        return context
