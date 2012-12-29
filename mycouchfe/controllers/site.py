from flask import render_template, g, url_for, redirect, session, request, Blueprint
from functools import wraps
from mycouchfe import forms, settings
from mycouchfe.controllers.utils import api_call, get_user
import requests
import simplejson


class SiteResponse(object):
    def __init__(self, template=None, redirect_to=None, **kwargs):
        self._template = template
        self._redirect_to = redirect_to
        self._context = kwargs

    def as_flask(self):
        if self._redirect_to:
            return redirect(self._redirect_to)
        elif self._template:
            return render_template(self._template, **self._context)


site_blueprint = Blueprint('site_blueprint', __name__,
                           template_folder='templates')


def route_with_user(url, methods):
    def decorator(fn):
        @site_blueprint.route(url, methods=methods or ('GET',))
        @wraps(fn)
        def fn2(*args, **kwargs):
            user = get_user()
            resp = fn(user, *args, **kwargs)
            resp._context['logged_user'] = user
            return resp.as_flask()
        return fn2
    return decorator


@route_with_user('/', methods=('GET',))
def index(user):
    return SiteResponse(template='index.html')


@route_with_user('/login', methods=('GET', 'POST'))
def login(user):
    form = forms.LoginForm()
    if form.validate_on_submit():
        reqdata = {'username': form.username.data,
                   'password': form.password.data}
        resp = api_call('post', '/auth', reqdata)
        if resp.status_code == 200:
            session['token'] = resp.json().get('token')
            return redirect(url_for('site_blueprint.index'))
        if resp.status_code == 401:
            form.errors['username'] = ['Invalid login and/or password.']
            form.errors['password'] = ['Invalid login and/or password.']
            form.force_error = True
    return SiteResponse(template='login.html', form=form)


@route_with_user('/logout', methods=('GET',))
def logout(user):
    token = session.pop('token')
    api_call('delete', '/auth')
    return SiteResponse(redirect_to=url_for('site_blueprint.index'))


@route_with_user('/register', methods=('GET', 'POST'))
def register(user):
    form = forms.NewUserForm()
    if form.validate_on_submit():
        resp = api_call('post', '/user', form.as_dict())

        if resp.status_code == 200:
            session['token'] = resp.json().get('token')
            return redirect(url_for('site_blueprint.index'))
        if resp.status_code == 401:
            form.errors['username'] = ['Unexpected error.']
    return SiteResponse(template='new_user.html', form=form)


@route_with_user('/myprofile', methods=('GET',))
def myprofile(user):
    return SiteResponse(redirect_to=url_for(
        'site_blueprint.profile', user_id=user['id']))


@route_with_user('/myactivities', methods=('GET',))
def myactivities(user):
    resp = api_call('get', '/activities')
    if resp.status_code == 200:
        return SiteResponse(template='activity_list.html', activities=resp.json())


@route_with_user('/create/activity', methods=('GET', 'POST'))
def create_activity(user):
    form = forms.NewActivityForm()
    cities = getattr(g, 'activity_cities', None) or api_call('get', '/locations/cities').json()
    form.locality_id.choices = [
        (str(o.get('id')), '[%s] %s' % (o['country_code'], o['name']))
        for o in cities]
    if form.validate_on_submit():
        reqdata = form.get_request_data()
        resp = api_call('post', '/activities', reqdata)
        if resp.status_code == 200:
            return SiteResponse(redirect_to=url_for('site_blueprint.myprofile'))
        if resp.status_code == 401:
            pass
    return SiteResponse(template='new_activity.html', form=form)


@route_with_user('/myfriends', methods=('GET',))
def myfriends(user):
    if user:
        resp = api_call('get', '/connections/friendships')
        if resp.status_code == 200:
            return SiteResponse(template='friend_list.html', friendships=resp.json())


@route_with_user('/myreferences', methods=('GET',))
def myreferences(user):
    if user:
        resp = api_call('get', '/connections/references')
        if resp.status_code == 200:
            return SiteResponse(template='reference_list.html', references=resp.json())


@route_with_user('/city/<int:city_id>', methods=('GET',))
def city(user, city_id):
    city = api_call('get', '/locations/cities/%s' % city_id, get_json=True)
    groups = api_call('get', '/groups', request_params={
        'f:city_id': city_id, 'f:parent_group_id': None})

    return SiteResponse(
        template='city.html',
        city=city)


@route_with_user('/profile/<int:user_id>', methods=('GET',))
def profile(user, user_id):
    if user_id == user.get('id'):
        selected_user = user
        is_logged_user = True
    else:
        selected_user = get_user(user_id)
        is_logged_user = False
    references = api_call('get', '/connections/references/%s' % user_id, get_json=True)
    friendships = api_call('get', '/connections/friendships/%s' % user_id, get_json=True)

    return SiteResponse(
        template='user.html',
        user=selected_user,
        references=references,
        friendships=friendships,
        is_logged_user=is_logged_user)
