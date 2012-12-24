from flask import render_template, g, url_for, redirect, session, request
from mycouchfe import app, forms, settings
import requests
import simplejson


def api_call(type, path, request_data=None, request_params=None):
    auth_str = 'MYC apikey="whatever"'
    token = session.get('token', None)
    if token:
        auth_str = '%s, token="%s"' % (auth_str, token)
    headers = {'Content-Type': 'application/json',
               'Authorization': auth_str}
    req_fn = getattr(requests, type.lower())
    resp = req_fn('%s%s' % (settings.API_URL, path),
                  data=simplejson.dumps(request_data or {}),
                  params=request_params,
                  headers=headers)
    return resp


def get_user(user_id=None, expand=('city',)):
    url_base = '/users/%s' % user_id if user_id else '/current_user'
    resp = api_call('get', url_base, request_params={'expand': 'city'})
    if resp.status_code == 200:
        return resp.json()


@app.route('/', methods=('GET',))
def index():
    user = get_user()
    return render_template('index.html',
        user=user)


@app.route('/login', methods=('GET', 'POST'))
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


@app.route('/logout', methods=('GET',))
def logout():
    token = session.pop('token')
    api_call('delete', '/auth')
    return redirect(url_for('index'))


@app.route('/myprofile', methods=('GET',))
def myprofile():
    user = get_user()
    return redirect(url_for('profile', user_id=user['id']))


@app.route('/myactivities', methods=('GET',))
def myactivities():
    resp = api_call('get', '/activities')
    if resp.status_code == 200:
        return render_template('activity_list.html', activities=resp.json())

@app.route('/create/activity', methods=('GET', 'POST'))
def create_activity():
    user = get_user()
    form = forms.NewActivityForm()
    if request.method == 'GET':
        cities = api_call('get', '/locations/cities').json()
        form.locality_id.choices = [
            (o.get('id'), '[%s] %s' % (o['country_code'], o['name']))
            for o in cities]
    if form.validate_on_submit():
        pass
    return render_template('new_activity.html', form=form)


@app.route('/myfriends', methods=('GET',))
def myfriends():
    user = get_user()
    if user:
        resp = api_call('get', '/connections/friendships')
        if resp.status_code == 200:
            return render_template('friend_list.html', friendships=resp.json())


@app.route('/myreferences', methods=('GET',))
def myreferences():
    user = get_user()
    if user:
        resp = api_call('get', '/connections/references')
        if resp.status_code == 200:
            return render_template('reference_list.html', references=resp.json())


@app.route('/profile/<int:user_id>', methods=('GET',))
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
