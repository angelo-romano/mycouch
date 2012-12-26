from flask import (
    render_template, g, url_for, redirect, session,
    request, Blueprint, jsonify)
from mycouchfe import forms
from mycouchfe.controllers.utils import api_call, get_user


ajax_blueprint = Blueprint('ajax_blueprint', __name__,
                           url_prefix='/ajax')


@ajax_blueprint.route('/login', methods=('POST',))
def login():
    data = request.json
    reqdata = {'username': data.get('username'),
               'password': data.get('password')}
    api = api_call('post', '/auth', reqdata, request_params={'expand': 'city'})
    resp = {}
    error_list = []
    if api.status_code == 200:
        json = api.json()
        session['token'] = json.get('token')
        resp.update({
            'username': json.get('username'),
            'id': json.get('id'),
            'first_name': json.get('first_name'),
            'last_name': json.get('last_name'),
            'city': json.get('city').get('name'),
            'city_id': json.get('city_id'),
            'country': json.get('country'),
            'country_code': json.get('country_code'),
        })
    elif api.status_code == 401:
        error_list.append('Not authorized.')
    else:
        error_list.append('Unexpected error.')
    resp['errors'] = error_list
    return jsonify(resp)


@ajax_blueprint.route('/logout', methods=('GET',))
def logout():
    session.pop('token')
    api_call('delete', '/auth')
    return redirect(url_for('index'))


@ajax_blueprint.route('/register', methods=('GET', 'POST'))
def register():
    form = forms.NewUserForm()
    if form.validate_on_submit():
        pass
    return render_template('new_user.html', form=form)


@ajax_blueprint.route('/myprofile', methods=('GET',))
def myprofile():
    user = get_user()
    return redirect(url_for('profile', user_id=user['id']))


@ajax_blueprint.route('/myactivities', methods=('GET',))
def myactivities():
    resp = api_call('get', '/activities')
    if resp.status_code == 200:
        return render_template('activity_list.html', activities=resp.json())


@ajax_blueprint.route('/create/activity', methods=('GET', 'POST'))
def create_activity():
    form = forms.NewActivityForm()
    cities = (getattr(g, 'activity_cities', None) or
              api_call('get', '/locations/cities').json())
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


@ajax_blueprint.route('/myfriends', methods=('GET',))
def myfriends():
    user = get_user()
    if user:
        resp = api_call('get', '/connections/friendships')
        if resp.status_code == 200:
            return render_template('friend_list.html', friendships=resp.json())


@ajax_blueprint.route('/myreferences', methods=('GET',))
def myreferences():
    user = get_user()
    if user:
        resp = api_call('get', '/connections/references')
        if resp.status_code == 200:
            return render_template('reference_list.html',
                                   references=resp.json())


@ajax_blueprint.route('/profile/<int:user_id>', methods=('GET',))
def profile(user_id):
    logged_user = get_user()
    if user_id == logged_user.get('id'):
        user = logged_user
        is_logged_user = True
    else:
        user = get_user(user_id)
        is_logged_user = False

    return render_template(
        'user.html',
        user=user,
        is_logged_user=is_logged_user)
