
from celery.schedules import crontab
from celery import Celery
#from datetime import timedelta
#from scripts.flask_celery import Celery

""" todo REMOVE YOUR PASSWORD DUDE! """
def make_celery(app):
    app.config.update(
        REDIS_URL = 'redis://10.128.0.3',
        CELERY_BROKER_URL='amqp://dn00:##@##//',
        #CELERY_RESULT_BACKEND='amqp://dn00:##@##//',
        CELERY_RESULT_BACKEND='redis://##',
        CELERY_ENABLE_UTC = True,
        CELERY_TASK_SERIALIZER = 'json',
        CELERY_RESULT_SERIALIZER = 'json',

        #CELERY_SEND_EVENTS=False,
        CELERY_TASK_RESULT_EXPIRES=1800,
        CELERY_RESULT_PERSISTENT=False,
        BROKER_TRANSPORT_OPTIONS = {'confirm_publish': True},
        #CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml'],

        CELERY_ACCEPT_CONTENT = ['json'],

        CELERYBEAT_SCHEDULE = {
        #  # 'updateActive': {
        #  #     'task': 'abay.tasks.updateActive',
        #  #     'schedule': timedelta(seconds=10)
        #  #  },
        #  # 'updateSold': {
        #  #     'task': 'abay.tasks.updateSold',
        #  #     'schedule': timedelta(seconds=120)
        #  # },
        #  #    'endJob': {
        #  #    'task': 'abay.tasks.endJob',
        #  #    'schedule': timedelta(seconds=10)
        # # },
        # #  'CompleteSale': {
        # #     'task': 'abay.tasks.CompleteSale',
        # #     'schedule': timedelta(seconds=5)
        # #  }

        'DoUrJob': {
            'task': 'abay.tasks.DoUrJob',
            'schedule': crontab(minute='*/30') #*/10
         },
        'DoUrEventJob': {
            'task': 'abay.tasks.DoUrEventJob',
            'schedule': crontab(minute='*/2') #*/10
         },
        'Pricer': {
            'task': 'abay.tasks.Pricer',
            'schedule': crontab(minute=0, hour='*/2') #*/10
         },
        'PurgeNotifications': {
            'task': 'abay.tasks.PurgeNotifications',
            'schedule': crontab(minute=0, hour='*/3') #*/10
         }
         },

    #
    # CELERYBEAT_SCHEDULE = {
    #     # 'updateActive': {
    #     #     'task': 'tasks.updateActive',
    #     #     'schedule': timedelta(seconds=5)
    #     #   }
    #     # 'endJob': {
    #     #     'task': 'tasks.endJob',
    #     #     'schedule': timedelta(seconds=10)
    #     # }
        ONCE_DEFAULT_TIMEOUT = 60 * 5,
        CELERY_IMPORTS = ('abay.scripts.CallEbay','abay.scripts.ListingBuilder'),

    #SQLALCHEMY_DATABASE_URI = 'sqlite:///tmp/test.db'
        #CELERYD_TASK_SOFT_TIME_LIMIT = 60

    CELERY_ROUTES = {'abay.tasks.DoUrJob': {'queue': 'DoUrJobDriver'},
                     'abay.tasks.GoiEbay': {'queue': 'GoiEbay'},
                     'abay.tasks.GoiAzon': {'queue': 'GoiAzon'},
                     'abay.tasks.GetSetPricer': {'queue': 'GetSetPricer'},
                     'abay.tasks.SetEbayPricing': {'queue': 'SetEbayPricing'},
                     'abay.tasks.Pricer': {'queue': 'PricerDriver'},
                     'abay.tasks.updateActive': {'queue': 'DoUrJob'},
                     'abay.tasks.DoUrEventJob': {'queue': 'DoUrJobDriver'},
                     'abay.tasks.updateActiveEventDriver': {'queue': 'DoUrJob'}
                     }
    )


    celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    return celery

