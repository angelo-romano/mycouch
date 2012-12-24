from flask import Flask
from flask.ext.bootstrap import Bootstrap

app = Flask('mycouchfe')
app.config['SECRET_KEY'] = 'devkey'
bootstrap = Bootstrap(app)

from mycouchfe import controllers
