from flask import render_template, g, url_for, redirect, session, request
from mycouchfe import app, forms, settings, serializers
import requests
import simplejson


def api_call(type, path, request_data=None, request_params=None,
             get_json=False):
    auth_str = 'MYC apikey="whatever"'
    token = session.get('token', None)
    if token:
        auth_str = '%s, token="%s"' % (auth_str, token)
    headers = {'Content-Type': 'application/json',
               'Authorization': auth_str}
    req_fn = getattr(requests, type.lower())
    resp = req_fn('%s%s' % (settings.API_URL, path),
                  data=serializers.json_dumps(request_data or {}),
                  params=request_params,
                  headers=headers)
    if get_json:
        if resp.status_code == 200:
            resp = resp.json() if resp is not None else {}
            return resp
        else:
            raise ValueError('Invalid status code: got %s' % resp.status_code)
    return resp


def get_user(user_id=None, expand=('city',)):
    url_base = '/users/%s' % user_id if user_id else '/current_user'
    resp = api_call('get', url_base, request_params={'expand': 'city'})
    if resp.status_code == 200:
        return resp.json()
    elif not user_id and 'token' in session:
        # force logout in case of failure
        session.pop('token')
