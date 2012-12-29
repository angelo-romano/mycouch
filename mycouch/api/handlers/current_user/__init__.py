from flask.views import MethodView
from mycouch.api.auth import login_required
from mycouch.api.utils import get_logged_user
from mycouch.api.handlers.users import UserByIDHandler


class CurrentUserHandler(MethodView):
    __base_uri__ = '/current_user'
    __resource_name__ = 'current_user'

    @login_required()
    def get(self):
        user = get_logged_user()
        if not user:
            return ('NOT AUTHENTICATED', 401, [])
        return UserByIDHandler._get(user)

    @login_required()
    def patch(self):
        user = get_logged_user()
        if not user:
            return ('NOT AUTHENTICATED', 401, [])
        return UserByIDHandler._patch(user)
