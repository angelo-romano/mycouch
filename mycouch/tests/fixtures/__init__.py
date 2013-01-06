import os.path
from functools import wraps
from sqlalchemy.inspection import inspect
from mycouch import db, models
from mycouch.core.db import Base
from mycouch.core.serializers import json_loads, json_dumps


def _export_fixture(model, filters=None):
    if not model.query:
        return []
    if filters:
        instances = model.query.filter_by(**filters)
    else:
        instances = model.query.all()

    resp = []

    fields = [o.name for o in inspect(model).columns]

    for entry in instances:
        this_dict = dict((k, getattr(entry, k)) for k in fields)
        this_dict['_model'] = model.__name__
        resp.append(this_dict)

    return resp


def export_fixture(model, filters=None):
    return json_dumps(_export_fixture(model, filters))


def _import_fixture(fixture):
    imported_fixtures = fixture
    if not isinstance(imported_fixtures, list):
        imported_fixtures = [imported_fixtures]
    resp = []
    for entry in imported_fixtures:
        model = entry.pop('_model')
        model = getattr(models, model, None)
        if not model:
            continue

        this_instance = model()
        this_instance.populate_from_json(entry)
        resp.append(this_instance)
        db.session.add(this_instance)
    db.session.commit()
    return resp


def _remove_fixture(fixture):
    imported_fixtures = fixture
    if not isinstance(imported_fixtures, list):
        imported_fixtures = [imported_fixtures]
    res_list = set(o.get('_model') for o in imported_fixtures)
    res_list = map(lambda x: getattr(models, x, None), res_list)
    db.session.rollback()
    for model in res_list:
        query = ('TRUNCATE TABLE %s CASCADE;' % model.__tablename__)
        db.session.execute(query)
        db.session.commit()


def import_fixture(fixture):
    return json_loads(_import_fixture(fixture))


def export_all_fixtures():
    model_list = [o for o in models.__dict__.itervalues()
                  if isinstance(o, type) and issubclass(o, Base)]
    resp = []
    for model in model_list:
        resp += _export_fixture(model)
    return json_dumps(resp)


def import_fixtures_from_files(filelist):
    for this_file in filelist:
        with open(this_file, 'r') as fh:
            file_content = json_loads(fh.read())
        _import_fixture(file_content)


def remove_fixtures_from_files(filelist):
    for this_file in reversed(filelist):
        with open(this_file, 'r') as fh:
            file_content = json_loads(fh.read())
        _remove_fixture(file_content)


def with_fixtures(*filelist):
    filelist = [os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), '%s.json' % f)) for f in filelist]

    def decorator(fn):
        @wraps(fn)
        def fn2(*args, **kwargs):
            import_fixtures_from_files(filelist)

            try:
                resp = fn(*args, **kwargs)
            except:
                remove_fixtures_from_files(filelist)
                raise
            else:
                remove_fixtures_from_files(filelist)
                return resp

        return fn2
    return decorator


def with_base_fixtures(fn):
    return with_fixtures('country', 'city', 'user')(fn)
