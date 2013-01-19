import rawes
from mycouch import settings
from mycouch.lib.search.mappers import MAPPERS_BY_RESOURCE


BASE_URI = '/mycouch_resources'


rawes_conn = rawes.Elastic(
    url=settings.ELASTICSEARCH_URL,
    path='',  # can be customized in the future
    timeout=settings.ELASTICSEARCH_TIMEOUT,
    connection_type=settings.ELASTICSEARCH_CONNECTION_TYPE)


def map_data(data, resource_name):
    # location
    if 'latitude' in data and 'longitude' in data:
        # per GeoJSON (lon, lat)
        data['coordinates'] = [data.get('longitude'), data.get('latitude')]
    return data


def create_mapper(resource_path):
    mapping = MAPPERS_BY_RESOURCE.get(resource_path[-1])
    print mapping, resource_path, resource_path[-1]
    if mapping:
        mapping = {resource_path[-1]: mapping}
        print 'mapping2', rawes_conn.put(
            '%s/%s/_mapping' % (BASE_URI, '/'.join(resource_path)),
            data=mapping)


def delete_mapper(resource_path):
    rawes_conn.delete(
        '%s/%s/_mapping' % (BASE_URI, '/'.join(resource_path)))


def get_mapper(resource_path):
    return rawes_conn.get(
        '%s/%s/_mapping' % (BASE_URI, '/'.join(resource_path)))


def create_index():
    # this will create a new index!
    rawes_conn.put(
        BASE_URI,
        data={
            "settings": {
                "number_of_shards": 3,
                "number_of_replicas": 1},
        })


def delete_index():
    # this will delete the whole index!
    # to be used only for tests purposes
    rawes_conn.delete(BASE_URI)


def put(resource_path, resource_id, data):
    rawes_conn.put(
        '%s/%s/%s' % (BASE_URI, '/'.join(resource_path), resource_id),
        data=map_data(data, resource_path[-1]))


def get(resource_path, resource_id):
    return rawes_conn.get(
        '%s/%s/%s' % (BASE_URI, '/'.join(resource_path), resource_id))


def query(resource_path, query=None, limit=None):
    kwargs = {}
    if limit:
        kwargs['size'] = limit

    if kwargs:
        kwargs['params'] = kwargs

    if not query:
        data = {'query': {'match_all': {}}}
    else:
        data = query

    #if filters:
    #    data['filter'] = filters
    #    data = {
    #        'query': {
    #            'filtered': data,
    #        },
    #    }
    base_uri = '%s/%s/_search' % (BASE_URI, '/'.join(resource_path))
    resp = rawes_conn.get(
        base_uri, data=data)
    return resp


def update(resource_path, resource_id, data):
    rawes_conn.post(
        '%s/%s/%s/_update' % (BASE_URI, '/'.join(resource_path), resource_id),
        data=map_data(data))


def delete(resource_path, resource_id):
    rawes_conn.delete(
        '%s/%s/%s' % (BASE_URI, '/'.join(resource_path), resource_id))
