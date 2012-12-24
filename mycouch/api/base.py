"""
API configuration module.
"""


def register_this(
        manager, model, resource=None, can_fetch=True,
        can_create=True, can_delete=True,
        can_update=True):
    kwargs = {
        'url_prefix': '/api',
        'methods': ['GET', 'POST', 'DELETE', 'PATCH'],
        'collection_name': (
            resource or getattr(model, '__api_resource__', None) or
            model.__name__.lower()),
    }
    manager.create_api(model, **kwargs)


def register_api(app):
    HANDLER_LIST = (
        ('auth', 'AuthHandler'),
        ('users', 'UserHandler'),
        ('users', 'UserByIDHandler'),
        ('current_user', 'CurrentUserHandler'),
        ('locations', 'LocationHandler'),
        ('locations', 'LocationByIDHandler'),
        ('activities', 'ActivityHandler'),
        ('activities', 'ActivityByIDHandler'),
        ('connections', 'ConnectionHandler'),
        ('connections', 'ConnectionByIDHandler'),
    )
    for handler_path, handler_name in HANDLER_LIST:
        handler_module = getattr(__import__(
            'mycouch.api.handlers.%s' % handler_path).api.handlers,
            handler_path)
        handler = getattr(handler_module, handler_name)
        app.add_url_rule(
            handler.__base_uri__,
            view_func=handler.as_view(handler.__resource_name__))
