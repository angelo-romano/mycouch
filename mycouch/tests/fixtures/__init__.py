from sqlalchemy.inspection import inspect
from mycouch import db, models
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
        for key, val in entry.iteritems():
            setattr(this_instance, key, val)
        resp.append(this_instance)
    return resp


def import_fixture(fixture):
    return json_loads(_import_fixture(fixture))


def export_all_fixtures():
    model_list = [o for o in models.__dict__.itervalues()
                  if isinstance(o, type) and issubclass(o, db.Model)]
    resp = []
    for model in model_list:
        resp += _export_fixture(model)
    return json_dumps(resp)
