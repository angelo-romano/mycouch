DEBUG = True
SECRET_KEY = 'F701vWQRO4mi5hp8G3QRG3tomagsAM1RlkNcmqmzdiQN1omUtj'
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://angelo:ciaobella@127.0.0.1:5432/mycouch'
CACHE_MEMCACHED_SERVERS = ['127.0.0.1:11211']

ELASTICSEARCH_URL = 'localhost:9200'
ELASTICSEARCH_TIMEOUT = 30  # in secs
ELASTICSEARCH_CONNECTION_TYPE = 'http'  # can be either 'http', 'thrift', None
