from flask import Flask
from celeryconfig import make_celery
#from scripts.flask_redis import FlaskRedis


def create_app(configfile=None):
    app = Flask(__name__)

    return app

app = create_app()
celery = make_celery(app)
#celery.init_app(app)
#redis_store = FlaskRedis(app)
