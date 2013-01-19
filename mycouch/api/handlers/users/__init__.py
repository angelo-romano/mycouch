from flask import request
from flask.views import MethodView
from mycouch.api.auth import login_required, get_request_token
from mycouch.api.utils import (
    jsonify, get_logged_user, build_error_dict, get_filter_dict,
    model_by_id, parse_search_fields)
from mycouch.lib.search import query
from mycouch.models import User, UserProfileDetails
from functools import wraps


def only_this_user(fn):
    @wraps(fn)
    def fn2(cls, user, *args, **kwargs):
        logged_user = get_logged_user()
        if user.id != logged_user.id:
            return ('', 401, [])
        else:
            return fn(cls, user, *args, **kwargs)
    return fn2


user_by_id = model_by_id(User)


class UserHandler(MethodView):
    __base_uri__ = '/users'
    __resource_name__ = 'users'

    def get(self):
        """
        Currently not implemented.
        """
        ALLOWED_FILTERS = frozenset([
            'city_id', 'gender', 'age',
            'n_refs', 'n_friends', 'has_details',
            'can_host', 'keywords'])
        search_dict = parse_search_fields()
        if search_dict.get('fields'):
            # only some filters are allowed
            search_dict['fields'] = dict(
                (k, v) for k, v in search_dict['fields'].iteritems()
                if k in ALLOWED_FILTERS)
        resp = query(User, **search_dict)
        return jsonify([obj.serialized for _, obj in resp] if resp else [])

    def post(self):
        """
        Creates a new account.
        """
        # TODO: improved password handling?
        params = dict(
            first_name=request.json.get('first_name'),
            last_name=request.json.get('last_name'),
            birth_date=request.json.get('birth_date'),
            email=request.json.get('email'),
            gender=request.json.get('gender'),
            username=request.json.get('username'),
            password=request.json.get('password'))

        optional_params = dict(
            city_id=request.json.get('city_id'))

        missing_fields = [k for (k, v) in params.iteritems() if not v]
        if missing_fields:
            return (jsonify(build_error_dict([
                'No value specified for "%s".' % field
                for field in missing_fields])), 400, [])

        params.update(optional_params)
        user = User(**params)
        user.save(commit=True)
        return UserByIDHandler._get(user)


class UserByIDHandler(MethodView):
    __base_uri__ = '/users/<int:id>'
    __resource_name__ = 'users_one'

    @classmethod
    @user_by_id
    def _get(cls, user):
        expand_rels = request.args.get('expand')
        if expand_rels:
            expand_rels = filter(lambda o: o.lower().strip(),
                                 expand_rels.split(','))
            user.force_serialize(expand_rels)
        resp = user.serialized
        resp['token'] = get_request_token()
        return jsonify(resp)

    @classmethod
    @user_by_id
    @only_this_user
    def _delete(cls, user):
        user.is_active = False
        user.save(commit=True)
        return ('DELETED', 203, [])

    @classmethod
    @user_by_id
    @only_this_user
    def _patch(cls, user):
        params = dict(
            first_name=request.json.get('first_name'),
            last_name=request.json.get('last_name'),
            birth_date=request.json.get('birth_date'),
            email=request.json.get('email'),
            gender=request.json.get('gender'),
            city_id=request.json.get('city_id'))

        # password handling
        password = request.json.get('password')
        if password:
            user.set_and_encrypt_password(password)

        # "normal" param handling
        for (key, val) in params.iteritems():
            if val is None:
                continue

            curval = getattr(user, key, None)
            if curval != val:
                setattr(user, key, val)

        # profile details are stored in a different table
        profile_details = request.json.get('details')
        if profile_details:
            detail_object = user.details
            for (key, val) in profile_details.iteritems():
                if key not in ('websites', 'profile_details', 'sections'):
                    continue

                if val and not detail_object:
                    # detail entry not present, must be created
                    detail_object = UserProfileDetails(user_id=user.id)
                    setattr(detail_object, key, val)
                else:
                    if not detail_object:
                        continue  # no need to create a new entry for now

                    # update existing entry if needed
                    curval = getattr(detail_object, key, None)
                    if curval != val:
                        setattr(detail_object, key, val)

            if detail_object:
                # save details here (commit comes later)
                detail_object.save()

        user.save(commit=True)
        return jsonify(user.serialized)

    @login_required()
    def get(self, id):
        return self._get(id)

    @login_required()
    def delete(self, id):
        return self._delete(id)

    @login_required()
    def patch(self, id):
        return self._patch(id)
