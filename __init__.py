import flask_admin as admin
import flask_login as login

from flask import Flask,render_template, session
from flask.signals import request_finished, request_started
from database import User, ActiveItem, db_session, OrderItem, SoldReceipt, ScrapedItem, DescriptionTemplate, BlackList,db, LineItem, Notification, eBayAccount
from flask_adminlte import AdminLTE
from views import AdminIndexView, ActiveView, OrderView, ReceiptView, ScraperView, TemplateView, BlackListView, UserView, LineItemView, eBayAccountView, NotifyEmailView, EndedView
from scripts.files.descriptiontemplate import template

app = Flask(__name__)
AdminLTE(app)

app.config['SECRET_KEY'] = 'IfYouCanReadThisItAintASecret'

import datetime as dt

@app.route('/')
def index():
    return render_template("redir.html")

def init_login():
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

init_login()


admin = admin.Admin(app,
    'aBay',
    index_view=AdminIndexView(url='/killerapp'), template_mode="bootstrap3")

admin.add_view(ActiveView(ActiveItem, db_session,endpoint="active"))
admin.add_view(EndedView(ActiveItem, db_session,endpoint="ended"))
admin.add_view(OrderView(OrderItem, db_session,endpoint="orders"))
admin.add_view(ReceiptView(SoldReceipt, db_session,endpoint="receipts"))
admin.add_view(LineItemView(LineItem, db_session,endpoint="lineitem"))
admin.add_view(ScraperView(db_session,endpoint="scraper"))
admin.add_view(TemplateView(db_session,endpoint="template"))
admin.add_view(BlackListView(db_session,endpoint="blacklist"))
admin.add_view(UserView(db_session,endpoint="users"))
admin.add_view(eBayAccountView(db_session,endpoint="ebayacc"))
admin.add_view(NotifyEmailView(db_session,endpoint="notifyemail"))


@app.template_filter()
def timepast(value):
    c = (dt.datetime.utcnow() - value.updated_on)
    return "%.2dh%.2dm" % (c.seconds//3600,(c.seconds//60)%60)

""" Pass notifications to template """
@app.context_processor
def inject_notifications():
    accList = [r.usern for r in db.session.query(eBayAccount.usern).filter_by(uid=login.current_user.get_id()).distinct()]
    # if 'accSelect' not in session or session.get('accSelect') is None:
    #     session['accSelect'] = accList
    #
    query = db.session.query(Notification.msg, Notification.icon, Notification.link, Notification.updated_on,
                             Notification.uid).filter_by(
        uid=login.current_user.get_id()).order_by(Notification.updated_on.desc())

    return dict(notif=query.filter_by(type=0).limit(10).all(), tasks=query.filter_by(type=1).limit(10).all(),
                acc=accList)

""" no cache so we can see the latest info """
def expire_session(sender, response, **extra):
    db_session.expire_all()
request_finished.connect(expire_session, app)

""" Pass account list to template """
def accList_inject(sender):
    if not session.get('accSelect'):
        session['accSelect'] = [r.usern for r in db.session.query(eBayAccount.usern).filter_by(uid=login.current_user.get_id()).distinct()]
request_started.connect(accList_inject, app)

# @app.after_request
# def add_header(r):
#     """
#     Add headers to both force latest IE rendering engine or Chrome Frame,
#     and also to cache the rendered page for 10 minutes.
#     """
#     r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#     r.headers["Pragma"] = "no-cache"
#     r.headers["Expires"] = "0"
#     r.headers['Cache-Control'] = 'public, max-age=0'
#     return r

# import abay.views
#db.session.rollback()
#db.create_all()
#
#db.session.add(User('dn','De1414919','dtnguy90@gmail.com','admin'))
# # db.session.add(User('dn1','de1414919','dtnguy90@gmail.com','admin'))
#db_session.add(DescriptionTemplate(Template=template,uid=1,TemplateName='equatesave default'))
#db.session.commit()
# db_session.add(Notifications(uid=1,icon='fa fa-warning danger',msg='Test notification',link='http://google.com'))
# db_session.add(Notifications(uid=1,icon='fa fa-cart',msg='Test notification2',link='http://amazon.com'))
# db_session.add(Notifications(uid=1,type=1,icon='fa fa-cart',msg='Task Running test',link='TaskID'))
#db_session.add(BlackList(ListName='brand'))
#db_session.add(BlackList(ListName='title', uid=1))
#db_session.commit()



