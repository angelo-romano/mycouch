import inspect

from mycouch.lib.search import base


def _get_searchable_value(class_or_instance):
    searchable = getattr(class_or_instance, '__searchable__', False)

    if not searchable:
        return

    if not isinstance(searchable, basestring):
        if inspect.isclass(class_or_instance):
            searchable = class_or_instance.__name__.lower()
        else:
            searchable = class_or_instance.__class__.__name__.lower()

    return searchable


def index(instance, alternate_serializer=None):
    """
    Index a specific model instance accordingly.

    :param instance:
    :param alternate_serializer:
    """
    searchable = _get_searchable_value(instance)

    if not searchable:  # not a valid searchable class!
        return

    if alternate_serializer:
        serialized = alternate_serializer(instance)
    else:
        serialized = instance.serialized

    base.put((searchable,), instance.id, serialized)


ADDITIONAL_RANKINGS = {
    'City': "_score * doc['rating'].value",
    'MinorLocality': "_score * doc['rating'].value",
}


def query(model, query_field=None, query_string=None, max_distance=None,
          limit=None, fields=None, order_by=None):
    searchable = _get_searchable_value(model)

    if not searchable:  # not a valid searchable class!
        return

    kwargs = {}
    query_paradigms = []
    query = {}

    # if custom score query, handles it in a special way
    additional_ranking_formula = ADDITIONAL_RANKINGS.get(model.__name__)
    if additional_ranking_formula:
        query_paradigms.append(
            ('custom_score', {'script': additional_ranking_formula}))

    # custom distance + custom filter constraints
    if max_distance or fields:
        filtered = {}
        # maximum distance
        if max_distance:
            km, coordinates = max_distance
            latitude, longitude = coordinates
            filtered.update({
                "geo_distance": {
                    "distance": "%skm" % km,
                    "coordinates": [longitude, latitude],  # lon, lat (GeoJSON)
                },
            })
        # additional filters
        if fields:
            for (key, val) in fields.iteritems():
                if not val:
                    continue
                if isinstance(val, tuple) and len(val) == 2:
                    # we consider 2-tuples as ranges here
                    if 'range' not in filtered:
                        filtered['range'] = {}
                    filtered['range'][key] = {'from': val[0], 'to': val[1]}
                elif isinstance(val, (list, set, frozenset)):
                    if 'terms' not in filtered:
                        filtered['terms'] = {}
                    filtered['terms'][key] = list(val)
                else:
                    if 'term' not in filtered:
                        filtered['term'] = {}
                    filtered['term'][key] = val
        #filtered['match_all'] = {}
        query_paradigms.append(('filtered', {'filter': filtered}))

    # preparing query
    if query_string:
        if query_field:
            # using wildcard-based search against a specific field
            query = {query_field: query_string.lower()}
            query_paradigms.append(('wildcard', query))
        else:
            # no specific field - old query string system
            query = {'query': query_string}
            query_paradigms.append(('query_string', query))
    else:
        query_paradigms.append(('match_all', {}))

    # depth-based query build-up
    query_dict = {"query": {}}
    query_dict_cur = query_dict['query']
    for idx in xrange(len(query_paradigms)):
        key, reldict = query_paradigms[idx]
        query_dict_cur[key] = reldict
        if (idx + 1) < len(query_paradigms):  # not the last call!
            query_dict_cur[key]['query'] = {}
            query_dict_cur = query_dict_cur[key]['query']

    search_resp = base.query((searchable,), query=query_dict)
    search_resp = [o['_source'] for o in search_resp['hits']['hits']]
    if not search_resp:
        return

    objects = dict(
        (o.id, o)
        for o in model.query.filter(
            model.id.in_([o['id'] for o in search_resp])).all())
    resp = []
    for this_entry in search_resp:
        this_obj = objects.get(this_entry['id'])
        if this_obj:
            resp.append((this_entry, this_obj))

    # custom ordering
    if order_by:
        if order_by[0] not in ('+', '-'):
            raise ValueError(
                'Invalid "order_by" value, must begin with a +/-.')
        field_name = order_by[1:]
        field_reverse = (order_by[0] == '-')
        resp.sort(key=lambda x: getattr(x[1], field_name, None),
                  reverse=field_reverse)

    # custom limit
    if limit:
        resp = resp[:limit]

    return resp
