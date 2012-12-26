from flask import render_template, g, url_for, redirect, session, request, Blueprint
from mycouchfe import forms, settings
from mycouchfe.controllers.utils import api_call, get_user
import requests
import simplejson


site_blueprint = Blueprint('site_blueprint', __name__,
                           template_folder='templates')


@site_blueprint.route('/', methods=('GET',))
def index():
    user = get_user()
    return render_template('index.html',
        user=user)


@site_blueprint.route('/login', methods=('GET', 'POST'))
def login():
    form = forms.LoginForm()
    if form.validate_on_submit():
        reqdata = {'username': form.username.data,
                   'password': form.password.data}
        resp = api_call('post', '/auth', reqdata)
        if resp.status_code == 200:
            session['token'] = resp.json().get('token')
            return redirect(url_for('index'))
        if resp.status_code == 401:
            form.errors['username'] = ['Invalid login and/or password.']
            form.errors['password'] = ['Invalid login and/or password.']
            form.force_error = True
    return render_template('login.html', form=form)


@site_blueprint.route('/logout', methods=('GET',))
def logout():
    token = session.pop('token')
    api_call('delete', '/auth')
    return redirect(url_for('index'))


@site_blueprint.route('/register', methods=('GET', 'POST'))
def register():
    form = forms.NewUserForm()
    if form.validate_on_submit():
        pass
    return render_template('new_user.html', form=form)

@site_blueprint.route('/myprofile', methods=('GET',))
def myprofile():
    user = get_user()
    return redirect(url_for('profile', user_id=user['id']))


@site_blueprint.route('/myactivities', methods=('GET',))
def myactivities():
    resp = api_call('get', '/activities')
    if resp.status_code == 200:
        return render_template('activity_list.html', activities=resp.json())

@site_blueprint.route('/create/activity', methods=('GET', 'POST'))
def create_activity():
    user = get_user()
    form = forms.NewActivityForm()
    cities = getattr(g, 'activity_cities', None) or api_call('get', '/locations/cities').json()
    form.locality_id.choices = [
        (str(o.get('id')), '[%s] %s' % (o['country_code'], o['name']))
        for o in cities]
    print form.locality_id.choices
    if form.validate_on_submit():
        reqdata = form.get_request_data()
        resp = api_call('post', '/activities', reqdata)
        if resp.status_code == 200:
            return redirect(url_for('myprofile'))
        if resp.status_code == 401:
            pass
    print form.locality_id.data
    return render_template('new_activity.html', form=form)


@site_blueprint.route('/myfriends', methods=('GET',))
def myfriends():
    user = get_user()
    if user:
        resp = api_call('get', '/connections/friendships')
        if resp.status_code == 200:
            return render_template('friend_list.html', friendships=resp.json())


@site_blueprint.route('/myreferences', methods=('GET',))
def myreferences():
    user = get_user()
    if user:
        resp = api_call('get', '/connections/references')
        if resp.status_code == 200:
            return render_template('reference_list.html', references=resp.json())


@site_blueprint.route('/profile/<int:user_id>', methods=('GET',))
def profile(user_id):
    logged_user = get_user()
    if user_id == logged_user.get('id'):
        user = logged_user
        is_logged_user = True
    else:
        user = get_user(user_id)
        is_logged_user = False

    return render_template('user.html',
        user=user,
        is_logged_user=is_logged_user)
