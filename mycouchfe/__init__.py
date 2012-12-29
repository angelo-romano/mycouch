from flask import Flask
from flask.ext.bootstrap import Bootstrap

app = Flask('mycouchfe')
app.config['SECRET_KEY'] = 'devkey'
bootstrap = Bootstrap(app)

from mycouchfe import controllers

app.register_blueprint(controllers.site_blueprint)
app.register_blueprint(controllers.ajax_blueprint)

print (app.url_map)
