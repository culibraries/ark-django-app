from data_store.renderer import DataBrowsableAPIRenderer, mongoJSONPRenderer, mongoJSONRenderer


class customMongoJSONRenderer(mongoJSONRenderer):
    def get_default_renderer(self, view):
        return mongoJSONRenderer()
