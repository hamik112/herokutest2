import datetime
import flask_admin as admin
import flask_login as login
import pytz

from flask import redirect, url_for, request, render_template, flash, Markup, session
from flask_admin import helpers, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.filters import BaseSQLAFilter
from flask_admin.actions import action
from pytz import timezone
from loginform import LoginForm
from wtforms import form, fields, TextAreaField
from wtforms.widgets import TextArea
from celery.result import AsyncResult
from sqlalchemy import func
from flask import jsonify

datetime_format='%m/%d %I:%M %p'
tz=timezone('US/Pacific')

# from sqlalchemy.sql import func

from tasks import GoiEbay, CallGetSessionID, FetchToken, AsinsTextToList, ScraperToCSVToEbay, ClearScraperList, DoUrJob, \
    UpdateReceiptData, Pricer, DoUrEventJob

from database import db, ActiveItem, DescriptionTemplate, ScrapedItem, db_session, User, OrderItem, SoldReceipt, \
    LineItem, DescriptionTemplate, Notification, eBayAccount, NotifyEmail, BlackList





class AdminIndexView(admin.AdminIndexView):
    @expose('/')
    # The index page
    def index(self):
        session['curview'] = 'index'
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        # if '' in session.get('accSelect'):
        #     session['accSelect'] = [db_session.query(eBayAccount.usern).filter_by(uid=login.current_user.get_id()).first()]
        boxes = {}
        chartboxesdata = {}

        datetimenow = datetime.datetime.now(tz=tz)
        datefilter = datetimenow - datetime.timedelta(days=1)
        datethirty = datetimenow - datetime.timedelta(days=30)
        ending = db_session.query(func.count(ActiveItem.ItemID)).filter(
            ActiveItem.eBayAccount.in_(session.get('accSelect'))).filter(
            func.timezone(tz.zone, ActiveItem.TimeLeft).between(datetimenow, datefilter)).scalar()
        unshipped = db_session.query(func.count(OrderItem.uid)).filter(
            OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(
            OrderItem.PrivateNotes != None).filter(OrderItem.SellerPaidStatus == 'PaidWithPayPal').filter(
            OrderItem.ShippedTime == None).scalar()
        # profittoday = db_session.query(func.sum(SoldReceipt.TotalProfit)).filter(
        #     SoldReceipt.uid == login.current_user.get_id()).filter(
        #     SoldReceipt.SoldTime > datefilter).scalar()
        unordered = db_session.query(func.count(OrderItem.uid)).filter(
            OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(
            OrderItem.PrivateNotes == None).filter(OrderItem.SellerPaidStatus == 'PaidWithPayPal').scalar()
        notshippedtwodays = db_session.query(func.count(OrderItem.uid)).filter(
            OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(
            OrderItem.PrivateNotes != None).filter(OrderItem.ShippedTime == None).filter(
            func.timezone(tz.zone, OrderItem.CreatedTime) < (datetimenow - datetime.timedelta(days=2))).scalar()

        boxes['unshipped'] = unshipped
        boxes['ending'] = ending
        boxes['unordered'] = unordered
        boxes['notshippedtwodays'] = notshippedtwodays
        soldRecDayfunc = func.date_trunc('day', SoldReceipt.SoldTime - datetime.timedelta(hours=7))

        chartdata = db_session.query(soldRecDayfunc, func.sum(SoldReceipt.TotalProfit)).join(SoldReceipt.order_item).filter(
            OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(
             func.timezone(tz.zone, SoldReceipt.SoldTime) > datethirty).order_by(soldRecDayfunc).group_by(soldRecDayfunc).all()
        chartorderdata = db_session.query(func.count(OrderItem.PrivateNotes)).join(SoldReceipt.order_item).filter(
            OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(
             func.timezone(tz.zone, SoldReceipt.SoldTime) > datethirty).order_by(soldRecDayfunc).group_by(soldRecDayfunc).all()
        #chartdata = sorted(chartdata)
        if chartdata:
            chartlabels, chartdata = zip(*chartdata)
            chartdata = [float(n) if n is not None else 0 for n in chartdata]
            chartlabels = ["{:%m/%d}".format(i) for i in chartlabels]
            chartorderdata = [int(n[0]) for n in chartorderdata]

            TotalPaidMonth = db_session.query(func.sum(SoldReceipt.TotalPaid)).join(SoldReceipt.order_item).filter(
                OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(
                SoldReceipt.TotalPurchasePrice != None).filter(
                SoldReceipt.SoldTime > datethirty).order_by(soldRecDayfunc).group_by(soldRecDayfunc).all()
            TotalPaidMonth = [n[0] for n in TotalPaidMonth]

            TotalPurchaseMonth = db_session.query(
                func.sum(SoldReceipt.TotalPurchasePrice + SoldReceipt.FinalValueFee + SoldReceipt.PaypalFee + SoldReceipt.TotalTaxFee)).join(SoldReceipt.order_item).filter(
                OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(
                SoldReceipt.TotalPurchasePrice != None).filter(
                SoldReceipt.SoldTime > datethirty).order_by(soldRecDayfunc).group_by(soldRecDayfunc).all()
            TotalPurchaseMonth = [n[0] for n in TotalPurchaseMonth]

            TotalShippedWeekQuery = db_session.query(func.count(OrderItem.uid))
            TotalShippedWeekOrdered = TotalShippedWeekQuery.filter(OrderItem.PrivateNotes != None).filter(
                OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(
                OrderItem.CreatedTime > (datetimenow - datetime.timedelta(days=7))).scalar()
            TotalShippedWeekShipped = TotalShippedWeekQuery.filter(OrderItem.ShippedTime != None).filter(
                OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(
                OrderItem.CreatedTime > (datetimenow - datetime.timedelta(days=7))).scalar()

            chartboxesdata['TotalProfitMonth'] = "%.2f" % chartdata[-1]
            chartboxesdata['TotalProfitAvg'] = "%.2f" % (sum(chartdata) / len(chartdata))
            chartboxesdata['TotalPaidMonth'] = "%.2f" % TotalPaidMonth[-1]
            chartboxesdata['TotalPaidAvg'] = "%.2f" % (sum(TotalPaidMonth) / len(TotalPaidMonth))
            chartboxesdata['TotalPurchaseMonth'] = "%.2f" % TotalPurchaseMonth[-1]
            chartboxesdata['TotalPurchaseAvg'] = "%.2f" % (sum(TotalPurchaseMonth) / len(TotalPurchaseMonth))
            chartboxesdata['TotalShippedWeekOrdered'] = TotalShippedWeekOrdered
            chartboxesdata['TotalShippedWeekShipped'] = TotalShippedWeekShipped
        else:
            chartlabels = []
            chartdata = []
            chartboxesdata = []
            chartorderdata = []

        self.header = "Dashboard"
        return render_template('index.html', admin_view=self, boxes=boxes, chartlabels=chartlabels[-16:], chartdata=chartdata[-16:],
                               chartboxesdata=chartboxesdata, chartorderdata=chartorderdata[-16:])

    @expose('/logout/')
    def logout_view(self):
        user = login.current_user
        user.authenticated = False
        db.session.add(user)
        db.session.commit()
        login.logout_user()
        return redirect(url_for('.index'))

    @expose('/lockscreen/')
    def lockscreen(self):
        return render_template('lockscreen.html', current_user=login.current_user)


    @expose('/login')
    def login(self):
        return render_template('login.html', current_user=login.current_user)


    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # # handle user login
        form = LoginForm(request.form)

        if helpers.validate_form_on_submit(form):
            user = form.get_user()
            if user:
                if user.check_password(form.password.data):
                    user.authenticated = True
                    db.session.add(user)
                    db.session.commit()
                    login.login_user(user, remember=True)
                else:
                     flash("Invalid Password.")
            else:
                flash("Invalid User.")


        if login.current_user.is_authenticated:
            return redirect(url_for('.index'))
        self._template_args['form'] = form
        return render_template('login.html', form=form)

    """ The scaper view we use to get scraped Amazon items. """
    @expose('/scrape/', methods=('GET', 'POST'))
    def scraper_view(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))

        session['curview'] = 'scraper'

        scraperListForm = ScraperViewScraperForm(request.form)
        scraperListForm.template_id.choices = [(g.id, g.TemplateName) for g in DescriptionTemplate.query.order_by('id')]

        #if request.method == 'POST' and scraperListForm.validate():
        if helpers.validate_form_on_submit(scraperListForm):
            optDict = {'templateid': scraperListForm.template_id.data, 'titleopt': scraperListForm.titleOption.data,
                       'brandopt': scraperListForm.brandOption.data,
                       'ignoreact': scraperListForm.ignoreActiveOption.data, 'maxweight': float(scraperListForm.maxWeight.data)}
            asins = scraperListForm.asin.data
            task = AsinsTextToList.delay(asins, login.current_user.eBayAccounts[0].token, login.current_user.id,
                                         optDict)
            session['listertaskid'] = task.id
            return redirect(url_for('scraper.index_view'))

        self._template_args['form'] = form
        return render_template('/pages/scrape/scrape.html', scraperListForm=scraperListForm,admin_view=self)

    # @expose('/active/')
    # def active(self):
    #     if not login.current_user.is_authenticated:
    #         return redirect(url_for('.login_view'))
    #
    #     # view = ActiveView(ActiveItem, db.session)
    #     # self._template_args['view'] = view
    #     return self.render('pages/active.html', current_user=login.current_user)
    #

    """ Temporary way to subscribe to an eBay service """
    @expose('/subscribe/<accname>')
    def subscribe(self,accname):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        session['accSelect'] = [accname]

        self.header = "Subscribe"
        # sessionID = CallGetSessionID.delay()
        sessionID = CallGetSessionID()
        url = 'https://signin.ebay.com/ws/eBayISAPI.dll?SignIn&runame=Dennis_Nguyen-DennisNg-9cec-4-evuckklo&SessID=' + sessionID
        return render_template('pages/subscribe/subscribe.html', admin_view=self, url = url, sessid=sessionID, currentacc = session.get('accSelect'))

    """ After user agree to subscription, we grab the eBay user token for communication with eBay API """
    @expose('/subscribe2/', methods=('GET', 'POST'))
    def fetchToken(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))

        sessid = request.form.get('sessid')
        tokenAndExpire = FetchToken(sessid)
        if tokenAndExpire:
            #user = login.current_user
            ebayAcc = db_session.query(eBayAccount).filter_by(usern='equatesave').first() ##fix
            ebayAcc.token = tokenAndExpire[0]
            ebayAcc.tokenExpiration = tokenAndExpire[1]
            db_session.add(ebayAcc)
            db_session.commit()
            msg = 'Success!'
        else:
            msg = 'Error getting token. Call Dennis!\n' + 'SessionID: ' + str(sessid) + '\n Token tuple: ' + str(tokenAndExpire)

        return render_template('pages/subscribe/subscribe2.html', admin_view=self, msg = msg)

    """ Later we can upload a csv file of scraped items to list on eBay. This method/page is not implemented yet. """
    @expose('/uploadcsv/')
    def uploadcsv(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))

        task = ScraperToCSVToEbay.delay(login.current_user.eBayAccounts[0].token, login.current_user.id)

        session['listertaskid'] = task.id
        return redirect(url_for('scraper.index_view'))

    """ redirect to this page to clear scraper data. """
    @expose('/clearscraper/')
    def clearscraper(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))

        t = ClearScraperList.delay(login.current_user.id)
        t.get()

        return redirect(url_for('scraper.index_view'))



    # @expose('/wabisabi/<orderid>/<azorderid>/<asin>/<quantity>/<azonprice>/<tax>')
    # def updateOrderItem(self,orderid, azorderid, asin, quantity, azonprice, tax):
    #
    #     # We use countdown here so that the database can be updated with DoUrJob routine before creating a new lineitem
    #     try:
    #         t = setLineItem.apply_async(args=[orderid, azorderid, asin, quantity, azonprice,tax])
    #         return Response(status=200, mimetype='application/json')
    #         # resp.headers['Link'] = 'http://luisrei.com'
    #
    #         # self.header = "Dashboard"
    #         # return render_template('index.html', admin_view=self)
    #
    #     except Exception, e:
    #         return Response(status=404, mimetype='application/json')

    """ For testing of tasks """
    @expose('/dourjob')
    def dourjob(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))

        t = DoUrJob.delay()
        #t = DoUrEventJob.delay()

        return redirect(url_for('.login_view'))

    """ For testing of pricing updates """
    @expose('/runpricer')
    def runpricer(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))

        t = Pricer.delay()

        return redirect(url_for('.login_view'))

    """ Top right account list list. Later we can select which eBay account to manage. """
    @expose('/acc/<accname>')
    def acc(self, accname):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))

        if accname == 'all':
            accList = []
            for q in db_session.query(eBayAccount.usern).filter_by(uid=login.current_user.get_id()).distinct():
                accList.append(q.usern)
            session['accSelect'] = accList
        elif accname == 'add':
            session['accSelect'] = None
            return redirect(url_for('ebayacc.create_view'))
        else:
            #call db here
            #accList = []
            #accList.append(str(accname))
            session['accSelect'] = [str(accname)]

        #flash('Account changed to: ' + accname)

        return redirect(url_for('.index'))

    """ Check progress on certain tasks """
    @expose('/status/<task_id>')
    def taskstatus(self, task_id):
        task = AsyncResult(task_id)
        if task.state == 'PENDING':
            # job did not start yet
            response = {
                'state': task.state,
                'current': 0,
                'total': 1,
                'status': 'Pending...'
            }
        elif task.state != 'FAILURE':
            response = {
                'state': task.state,
                'current': task.info.get('current', 0),
                'total': task.info.get('total', 1),
                'status': task.info.get('status', '')
            }
            if 'result' in task.info:
                response['result'] = task.info['result']
        else:
            # something went wrong in the background job
            response = {
                'state': task.state,
                'current': 1,
                'total': 1,
                'status': str(task.info),  # this is the exception raised
            }
        return jsonify(response)

    # @expose('/notify/clicked')
    # def notificationsClicked(self):
    #     session['lastnotifclicked'] = session.get('lastnotifcnt')
    #     return True

"""
### Filters for the order list ###
"""
class ActionViewFilter_HideEnded(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        timenow = datetime.datetime.now(tz=tz)
        if value == '1':
            return query.filter(self.column < timenow)
        else:
            return query.filter(self.column > timenow)

    def operation(self):
        return 'Ended Items'

class ActionViewFilter_UpdateFailed(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        if value == '1':
            return query.filter(self.column == False)
        else:
            return query.filter(self.column == True)

    def operation(self):
        return 'Failed Items'
"""###################################"""

class ActiveView(ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated

    @action('enditem', 'End Item', 'Are you sure you want to end selected items?')
    def action_enditem(self, itemids):
        try:
            from celery import group
            query = ActiveItem.query.filter(ActiveItem.ItemID.in_(itemids))
            token = login.current_user.eBayAccounts[0].token
            listLength = query.count()
            items = query.all()

            joblist = []
            failCount = 0
            SuccCount = 0
            for i in range(0, listLength, 7):
                chunk = items[i:i + 7]
                try:
                    #joblist = []
                    for j in chunk:
                        joblist.append(GoiEbay.delay(token, j.ItemID, 'enditem'))
                    job = group(joblist)
                    result = job.apply_async()
                    result = result.get()
                    SuccCount += sum(result)
                    joblist[:] = []
                except Exception:
                    joblist[:] = []
                    failCount += 1

            flash('%(SuccCount)s items ended. $(failCount)s failed. Results shown in a few mins.',
                           '%(SuccCount)s users were successfully approved.',)
        except Exception as e:
            if not self.handle_view_exception(e):
                raise

            flash('Failed to some items. %(error)s', 'error')

    @expose('/')
    def index_view(self):
        session['curview'] = 'active'

        datetimenow = datetime.datetime.now(tz=tz)
        datefilter = (datetimenow + datetime.timedelta(days=1))
        ended = db_session.query(ActiveItem.ItemID).filter(
            ActiveItem.eBayAccount.in_(session.get('accSelect'))).filter(
            func.timezone(tz.zone, ActiveItem.TimeLeft)< datetimenow).count()
        notupdated = db_session.query(ActiveItem.ItemID).filter(
            ActiveItem.eBayAccount.in_(session.get('accSelect'))).filter(
            ActiveItem.PriceUpdated == False).filter(func.timezone(tz.zone, ActiveItem.TimeLeft) > (datetimenow + datetime.timedelta(hours=1))).count()
        ending = db_session.query(ActiveItem.ItemID).filter(
            ActiveItem.eBayAccount.in_(session.get('accSelect'))).filter(
            func.timezone(tz.zone, ActiveItem.TimeLeft).between(datetimenow, datefilter)).count()
        newadded = db_session.query(ActiveItem.ItemID).filter(
            ActiveItem.eBayAccount.in_(session.get('accSelect'))).filter(
            func.timezone(tz.zone, ActiveItem.created_on) > datetimenow - datetime.timedelta(days=1)).count()
        self._template_args['ending'] = ending
        self._template_args['ended'] = ended
        self._template_args['notupdated'] = notupdated
        self._template_args['newadded'] = newadded

        return super(ActiveView, self).index_view()

    def get_query(self):
        #return db_session.query(ActiveItem).filter_by(uid=login.current_user.get_id())
        return db_session.query(ActiveItem).filter(ActiveItem.TimeLeft > datetime.datetime.utcnow()).filter_by(uid=login.current_user.get_id()).filter(ActiveItem.eBayAccount.in_(session.get('accSelect')))
    def get_count_query(self):
        return db_session.query(func.count(ActiveItem.uid)).filter(ActiveItem.TimeLeft > datetime.datetime.utcnow()).filter_by(uid=login.current_user.get_id()).filter(ActiveItem.eBayAccount.in_(session.get('accSelect')))

    def _Time_formatter(view, context, model, name):
        if model.TimeLeft:
            c = (model.TimeLeft - datetime.datetime.utcnow())
            time = "%sd, %.2dh: %.2dm: %.2ds" % (c.days,c.seconds//3600,(c.seconds//60)%60, c.seconds%60)
            if c.days <= 0:
                if c.days < 0:
                    return Markup("<span id='redtime'>{}</span>".format('ENDED'))
                return Markup("<span id='redtime'>{}</span>".format(time))
            return time
        return None

    def _ASIN_formatter(view, context, model, name):
        return Markup("""<a title="To Amazon Listing" data-toggle="tooltip"
                                  onclick="return !window.open(this.href, 'Amazon Order', 'width=1300,height=600')" target="_blank"
                              href="https://www.amazon.com/dp/{0}">{0}</a>""".format(model.Asin))
    def _Ops_formatter(view, context, model, name):
        return Markup("""<a title="End Item" data-toggle="tooltip"
                                  onclick="return !window.open(this.href, 'eBay End Item', 'width=1300,height=600')" target="_blank"
                              href="http://offer.ebay.com/ws/eBayISAPI.dll?VerifyStop&item={0}"><span class="fa fa-remove"></span></a>""".format(model.ItemID))
    column_formatters = {
       'TimeLeft': _Time_formatter,
        'Asin': _ASIN_formatter,
        'Ops': _Ops_formatter
    }
    column_filters = [
        ActionViewFilter_HideEnded(ActiveItem.TimeLeft, 'Ended Items', options=(('0', 'Hide'), ('1', 'Show'))),
        ActionViewFilter_UpdateFailed(ActiveItem.PriceUpdated, 'Failed Items', options=(('0', 'Hide'), ('1', 'Show')))
            ]

    column_labels = dict(eBayAccount='Acc', Quantity='Quant.', PriceUpdated=Markup("""<span class="fa fa-tasks"></span>"""),Ops=' ',AzonPrice='A-Price',TargetProfit='T-Profit',BuyItNowPrice='Price', Asin='ASIN', QuantityAvailable='Q-Avail', WatchCount='Watch.', PictureDetailsURL='Pic',SoldAmount='Q-Sold')
    page_size = 100
    can_create = False
    #can_delete = False
    list_template = 'pages/active/activelist.html'
    edit_template = 'pages/active/activeedit.html'

    column_list = (
    'Ops', 'PictureDetailsURL', 'Title', 'BuyItNowPrice', 'TargetProfit', 'AzonPrice', 'QuantityAvailable', 'Quantity',
    'SoldAmount', 'WatchCount', 'Asin', 'TimeLeft','eBayAccount','PriceUpdated')
    form_columns = ['Title', 'BuyItNowPrice', 'Quantity', 'Asin', 'PriceUpdated']
    column_searchable_list = ['Title', 'Asin', 'ItemID']
    column_editable_list = ['Title', 'BuyItNowPrice', 'QuantityAvailable']
    column_default_sort = 'TimeLeft'
    column_sortable_list = (
    'Title', 'BuyItNowPrice', 'TargetProfit', 'AzonPrice', 'QuantityAvailable', 'Quantity', 'SoldAmount', 'WatchCount',
    'TimeLeft')


    # def on_model_change(self, form, model):
    #      time.sleep(1)
    #      # return 'error'

class EndedView(ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated

    @action('enditem', 'End Item', 'Are you sure you want to relist selected items?')
    def action_relistitem(self, itemids):
        try:
            from celery import group
            query = ActiveItem.query.filter(ActiveItem.ItemID.in_(itemids))
            token = login.current_user.eBayAccounts[0].token
            listLength = query.count()
            items = query.all()

            joblist = []
            failCount = 0
            SuccCount = 0
            for i in range(0, listLength, 7):
                chunk = items[i:i + 7]
                try:
                    #joblist = []
                    for j in chunk:
                        joblist.append(GoiEbay.delay(token, j.ItemID, 'enditem'))
                    job = group(joblist)
                    result = job.apply_async()
                    result = result.get()
                    SuccCount += sum(result)
                    joblist[:] = []
                except Exception:
                    joblist[:] = []
                    failCount += 1

            flash('%(SuccCount)s items ended. $(failCount)s failed. Results shown in a few mins.',
                           '%(SuccCount)s users were successfully approved.',)
        except Exception as e:
            if not self.handle_view_exception(e):
                raise

            flash('Failed to some items. %(error)s', 'error')

    @expose('/')
    def index_view(self):
        session['curview'] = 'ended'
        datetimenow = datetime.datetime.now(tz=tz)
        datefilter = (datetimenow + datetime.timedelta(days=1))
        ended = db_session.query(ActiveItem.ItemID).filter(
            ActiveItem.eBayAccount.in_(session.get('accSelect'))).filter(
            func.timezone(tz.zone, ActiveItem.TimeLeft)< datetimenow).count()
        notupdated = db_session.query(ActiveItem.ItemID).filter(
            ActiveItem.eBayAccount.in_(session.get('accSelect'))).filter(
            ActiveItem.PriceUpdated == False).filter(func.timezone(tz.zone, ActiveItem.TimeLeft) > (datetimenow + datetime.timedelta(hours=1))).count()
        ending = db_session.query(ActiveItem.ItemID).filter(
            ActiveItem.eBayAccount.in_(session.get('accSelect'))).filter(
            func.timezone(tz.zone, ActiveItem.TimeLeft).between(datetimenow, datefilter)).count()
        newadded = db_session.query(ActiveItem.ItemID).filter(
            ActiveItem.eBayAccount.in_(session.get('accSelect'))).filter(
            func.timezone(tz.zone, ActiveItem.created_on) > datetimenow - datetime.timedelta(days=1)).count()
        self._template_args['ending'] = ending
        self._template_args['ended'] = ended
        self._template_args['notupdated'] = notupdated
        self._template_args['newadded'] = newadded

        return super(EndedView, self).index_view()

    def get_query(self):
        #return db_session.query(ActiveItem).filter_by(uid=login.current_user.get_id())
        return db_session.query(ActiveItem).filter(ActiveItem.TimeLeft < datetime.datetime.utcnow()).filter_by(uid=login.current_user.get_id()).filter(ActiveItem.eBayAccount.in_(session.get('accSelect')))
    def get_count_query(self):
        return db_session.query(func.count(ActiveItem.uid)).filter(ActiveItem.TimeLeft < datetime.datetime.utcnow()).filter_by(uid=login.current_user.get_id()).filter(ActiveItem.eBayAccount.in_(session.get('accSelect')))

    def _Time_formatter(view, context, model, name):
        if model.TimeLeft:
            c = (model.TimeLeft - datetime.datetime.utcnow())
            return "%sd, %.2dh: %.2dm: %.2ds" % (c.days,c.seconds//3600,(c.seconds//60)%60, c.seconds%60)
            # if c.days <= 0:
            #     if c.days < 0:
            #         return Markup("<span id='redtime'>{}</span>".format('ENDED'))
            #     return Markup("<span id='redtime'>{}</span>".format(time))
            #return time
        return None

    def _ASIN_formatter(view, context, model, name):
        return Markup("""<a title="To Amazon Listing" data-toggle="tooltip"
                                  onclick="return !window.open(this.href, 'Amazon Order', 'width=1300,height=600')" target="_blank"
                              href="https://www.amazon.com/dp/{0}">{0}</a>""".format(model.Asin))
    def _Ops_formatter(view, context, model, name):
        return Markup("""<a title="End Item" data-toggle="tooltip"
                                  onclick="return !window.open(this.href, 'eBay End Item', 'width=1300,height=600')" target="_blank"
                              href="http://offer.ebay.com/ws/eBayISAPI.dll?VerifyStop&item={0}"><span class="fa fa-remove"></span></a>""".format(model.ItemID))
    column_formatters = {
       'TimeLeft': _Time_formatter,
        'Asin': _ASIN_formatter,
        'Ops': _Ops_formatter
    }
    column_filters = [
        # ActionViewFilter_HideEnded(ActiveItem.TimeLeft, 'Ended Items', options=(('0', 'Hide'), ('1', 'Show'))),
        # ActionViewFilter_UpdateFailed(ActiveItem.PriceUpdated, 'Failed Items', options=(('0', 'Hide'), ('1', 'Show')))
            ]

    column_labels = dict(eBayAccount='Acc', Quantity='Quant.', PriceUpdated=Markup("""<span class="fa fa-tasks"></span>"""),Ops=' ',AzonPrice='A-Price',TargetProfit='T-Profit',BuyItNowPrice='Price', Asin='ASIN', QuantityAvailable='Q-Avail', WatchCount='Watch.', PictureDetailsURL='Pic',SoldAmount='Q-Sold')
    page_size = 100
    can_create = False
    #can_delete = False
    list_template = 'pages/ended/endedlist.html'
    edit_template = 'pages/ended/endededit.html'

    column_list = (
    'Ops', 'PictureDetailsURL', 'Title', 'BuyItNowPrice', 'TargetProfit', 'AzonPrice', 'QuantityAvailable', 'Quantity',
    'SoldAmount', 'WatchCount', 'Asin', 'TimeLeft','eBayAccount','PriceUpdated')
    form_columns = ['Title', 'BuyItNowPrice', 'Quantity', 'Asin', 'PriceUpdated']
    column_searchable_list = ['Title', 'Asin', 'ItemID']
    column_editable_list = ['Title', 'BuyItNowPrice', 'QuantityAvailable']
    column_default_sort = 'TimeLeft'
    column_sortable_list = (
    'Title', 'BuyItNowPrice', 'TargetProfit', 'AzonPrice', 'QuantityAvailable', 'Quantity', 'SoldAmount', 'WatchCount',
    'TimeLeft')


    # def on_model_change(self, form, model):
    #      time.sleep(1)
    #      # return 'error'

class BlackListView(ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated
    def __init__(self, session,**kwargs):
        super(BlackListView, self).__init__(BlackList, session, **kwargs)
    def get_query(self):
        return db_session.query(BlackList).filter(
            BlackList.uid.in_([0, login.current_user.get_id()]))
    def get_count_query(self):
        return db_session.query(func.count(BlackList.uid)).filter(
            BlackList.uid.in_([0, login.current_user.get_id()]))

    def _List_formatter(view, context, model, name):
        return Markup('<a href ="{}">Edit List<a>'.format(url_for('blacklist.edit_view', id=model.id)))

    @expose('/')
    def index_view(self):
        session['curview'] = 'scraper'
        return super(BlackListView, self).index_view()

    column_formatters = {
       'List': _List_formatter
    }

    form_columns = ['List']
    column_list = ('ListName', 'List')
    #column_editable_list = ['List']
    list_template = 'pages/scrape/blacklist.html'
    edit_template = 'pages/scrape/blacklistedit.html'

    column_labels = dict(ListName='List Name')

    edit_modal = True

    can_delete = False
    can_create = False

    #can_edit = False
    #edit_template = 'pages/active/activeedit.html'

class TemplateView(ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated
    def get_query(self):
        return db_session.query(DescriptionTemplate).filter_by(uid=login.current_user.get_id())
    def get_count_query(self):
        return db_session.query(func.count(DescriptionTemplate.uid)).filter_by(uid=login.current_user.get_id())

    @expose('/')
    def index_view(self):
        session['curview'] = 'scraper'
        return super(TemplateView, self).index_view()

    list_template = 'pages/template/templatelist.html'
    edit_template = 'pages/template/templateedit.html'
    create_template = 'pages/template/templatecreate.html'


    column_list = ('TemplateName', 'Template')

    def _Template_formatter(view, context, model, name):
        return Markup('<form><textarea class="ckeditor" name="editor1" id="editor1" rows="5">{}</textarea><script>CKEDITOR.replace( "editor1" );</script></form>'.format(model.Template))

    column_formatters = {
       'Template': _Template_formatter,
    }
    form_columns = ['TemplateName','Template']
    column_labels = dict(id='ID')
    #column_sortable_list = ('ID')

    can_delete = True

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.uid = login.current_user.get_id()


    def __init__(self, session,**kwargs):
        super(TemplateView, self).__init__(DescriptionTemplate, session, **kwargs)

class OrderViewFilter_Unshipped(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        if value == '1':
            return query.filter(self.column == None)
        else:
            return query.filter(self.column != None)

    def operation(self):
        return 'Unshipped Items'

class OrderViewFilter_Ordered(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        if value == '1':
            return query.filter(self.column != None)
        else:
            return query.filter(self.column == None)

    def operation(self):
        return 'Ordered Items'

class OrderView(ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated

    @expose('/')
    def index_view(self):
        session['curview'] = 'orders'

        datetimenow = datetime.datetime.now(tz=tz)
        datefilter = datetimenow - datetime.timedelta(days=1)
        datemonth = datetimenow - datetime.timedelta(weeks=4)
        orderstoday = db_session.query(OrderItem.Asin).filter(
            OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(
            func.timezone(tz.zone, OrderItem.CreatedTime) > datefilter).count()

        profittoday = db_session.query(func.sum(SoldReceipt.TotalProfit)).join(SoldReceipt.order_item).filter(
            OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(
            func.timezone(tz.zone, SoldReceipt.SoldTime) > datefilter).scalar()

        tpaid = db_session.query(func.sum(OrderItem.TotalPrice)).filter(
            OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(
            func.timezone(tz.zone, OrderItem.CreatedTime) > datemonth).scalar()

        notshippedtwodays = db_session.query(OrderItem.Asin).filter(
            OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(OrderItem.ShippedTime == None).filter(
            func.timezone(tz.zone, OrderItem.CreatedTime) > (datefilter - datetime.timedelta(days=1))).count()

        self._template_args['orderstoday'] = orderstoday
        self._template_args['tpaid'] = tpaid
        self._template_args['profittoday'] = profittoday
        self._template_args['notshippedtwodays'] = notshippedtwodays

        return super(OrderView, self).index_view()


    def get_query(self):
        #return db_session.query(OrderItem).filter_by(uid=login.current_user.get_id())
        return db_session.query(OrderItem).filter_by(uid=login.current_user.get_id()).filter(OrderItem.eBayAccount.in_(session.get('accSelect')))
    def get_count_query(self):
        return db_session.query(func.count(OrderItem.uid)).filter_by(uid=login.current_user.get_id()).filter(OrderItem.eBayAccount.in_(session.get('accSelect')))


    def _Shipped_formatter(view, context, model, name):
        if model.ShippedTime is not None:
            return Markup('<a class="col-md-2 fa fa-truck" title="" data-placement="top" data-toggle="tooltip" href="#/" data-original-title="{}"></a>'.format(model.ShippedTime))

    def _Sold_formatter(view, context, model, name):
        return Markup('<span class="col-md-2">{}</span>'.format(model.Quantity))
    def _TotalPrice_formatter(view, context, model, name):
        if model.TotalPrice != 0.0:
            return Markup('<span class="fa fa-usd"></span> {}'.format(model.TotalPrice))
    def _BuyerUserID_formatter(view, context, model, name):
        msg = ''
        if model.BuyerCheckoutMessage:
            msg = '<a class="fa fa-envelope" title="" data-placement="top" data-toggle="tooltip" href="#/" data-original-title="{}"></a>&nbsp&nbsp'.format(model.BuyerCheckoutMessage)
        return Markup(msg + """<a title="To eBay User" data-toggle="tooltip"
                                  onclick="return !window.open(this.href, 'eBay User', 'width=1300,height=600')" target="_blank"
                              href="http://www.ebay.com/usr/{0}">{0}</a>""".format(model.BuyerUserID))
    def _TotalProfit_formatter(view, context, model, name):
        TProfit = model.sold_receipt.TotalProfit
        if TProfit:
            return Markup('<span class="fa fa-usd"> {}</span>'.format(model.sold_receipt.TotalProfit))

    def _CreatedTime_formatter(view, context, model, name):
        return model.CreatedTime.replace(tzinfo=pytz.utc).astimezone(tz).strftime(datetime_format)

    def _Title_formatter(view, context, model, name):
        if model.CombinedOrder:
            full_title = ''
            for lineitems in model.line_item:
                full_title = full_title + "{0} x {1}<br>".format(lineitems.Quantity,lineitems.Title)

            return Markup(full_title)
        else:
            return model.Title

    column_filters = [
        OrderViewFilter_Unshipped(OrderItem.ShippedTime, 'Unshipped Items', options=(('0', 'Hide'), ('1', 'Show'))),
        OrderViewFilter_Ordered(OrderItem.PrivateNotes, 'Ordered Items', options=(('0', 'Hide'), ('1', 'Show'))),
            ]


    column_formatters = {
       'ShippedTime': _Shipped_formatter,
        'Quantity' : _Sold_formatter,
        'TotalPrice' : _TotalPrice_formatter,
        'BuyerUserID' : _BuyerUserID_formatter,
        'T-Profit' : _TotalProfit_formatter,
        'Title' : _Title_formatter,
        'CreatedTime' : _CreatedTime_formatter
    }

    column_labels = dict(SellerPaidStatus='Status', BuyerUserID='Buyer', TotalPrice='Total', Quantity='Sold'
                         , CreatedTime='Sold Time', IsMultiLeftShipping='GS', ShippedTime = 'Shipped', eBayAccount='Acc')
    page_size = 100
    can_create = False
    can_delete = True
    list_template = 'pages/orders/orderlist.html'
    edit_template = 'pages/orders/orderedit.html'

    column_list = ('SellerPaidStatus', 'ShippedTime','Quantity', 'Title', 'BuyerUserID',  'T-Profit', 'TotalPrice', 'CreatedTime', 'eBayAccount')
    column_searchable_list = ['OrderID', 'Title', 'PrivateNotes', 'Asin']
    column_default_sort = ('CreatedTime', True)


    # column_editable_list = ['Title', 'BuyItNowPrice', 'Quantity']
    # def on_model_change(self, form, model):
    #      time.sleep(5)
    #      # return 'error'

    # @action('eBaySalesRecord', 'eBay Sales Record')
    # def action_toEbaySalesRecord(self, ids):
    #     try:
    #         query = db_session.query(ScrapedItem).filter(ScrapedItem.OrderID is ids)
    #
    #     except Exception, e:
    #         if not self.handle_view_exception(e):
    #             raise

class ReceiptView(ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated
    def get_query(self):
        #return db_session.query(SoldReceipt).filter_by(uid=login.current_user.get_id())
        return db_session.query(SoldReceipt).join(SoldReceipt.order_item).filter_by(uid=login.current_user.get_id()).filter(OrderItem.eBayAccount.in_(session.get('accSelect')))
    def get_count_query(self):
        return db_session.query(func.count(SoldReceipt.uid)).join(SoldReceipt.order_item).filter_by(uid=login.current_user.get_id()).filter(OrderItem.eBayAccount.in_(session.get('accSelect')))

    @expose('/')
    def index_view(self):
        session['curview'] = 'receipt'

        datefilter = datetime.datetime.now(tz=tz) - datetime.timedelta(weeks=4)
        tprofit = db_session.query(func.sum(SoldReceipt.TotalProfit)).join(SoldReceipt.order_item).filter(
            OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(func.timezone(tz.zone, SoldReceipt.SoldTime) > datefilter).scalar()
        tamount = db_session.query(func.sum(SoldReceipt.TotalPurchasePrice)).join(SoldReceipt.order_item).filter(
            OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(func.timezone(tz.zone, SoldReceipt.SoldTime) > datefilter).scalar()
        titems = db_session.query(func.sum(SoldReceipt.ItemCount)).join(SoldReceipt.order_item).filter(
            OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(func.timezone(tz.zone, SoldReceipt.SoldTime) > datefilter).scalar()
        tsold = db_session.query(OrderItem.Asin).filter(
            OrderItem.eBayAccount.in_(session.get('accSelect'))).filter(OrderItem.SellerPaidStatus == 'PaidWithPayPal').filter(
            func.timezone(tz.zone, OrderItem.CreatedTime) > datefilter).count()


        self._template_args['tprofit_sum'] = tprofit
        self._template_args['total_sold'] = tsold
        self._template_args['total_amt'] = tamount
        self._template_args['total_items'] = titems

        return super(ReceiptView, self).index_view()

    def _OrderID_formatter(view, context, model, name):
        return Markup('<a href="/killerapp/lineitem/?search={0}" title="View line items" data-toggle="tooltip">{0}</a>'.format(model.OrderID))
    def _Status_formatter(view, context, model, name):
        if model.order_item.ShippedTime:
            return Markup('<a class="col-md-2 fa fa-truck" title="" data-placement="top" data-toggle="tooltip" href="#/" data-original-title="{}"></a>'.format(model.order_item.ShippedTime))
    def _ShippingCost_formatter(view, context, model, name):
        return model.order_item.ShippingServiceCost
    def _eBayAccount_formatter(view, context, model, name):
        return model.order_item.eBayAccount
    def _SoldTime_formatter(view, context, model, name):
        return model.SoldTime.replace(tzinfo=pytz.utc).astimezone(tz).strftime(datetime_format)

    ##Add Shipping service col later

    column_labels = dict(id='No.', OrderID='Order ID - Transaction ID', AmountPaid='Amount Paid', TotalPurchasePrice='P-Price'
                         ,TotalProfit='T-Profit', SoldTime='Sold Time', ItemCount='# Items', PaypalFee='PP Fee', FinalValueFee='FVF'
                         ,TotalTaxFee='T-Tax',TotalPaid='T-Paid',eBayAccount='Acc')

    column_formatters = {
        'OrderID': _OrderID_formatter,
        'Status': _Status_formatter,
        'S-Paid': _ShippingCost_formatter,
        'SoldTime': _SoldTime_formatter,
        'eBayAccount': _eBayAccount_formatter
    }
    column_hide_backrefs = False
    page_size = 100
    can_create = False
    list_template = 'pages/receipt/receiptlist.html'
    # edit_template = 'pages/orders/orderedit.html'
    can_edit = False
    can_delete = False

    can_export = True

    column_list = ('id','Status', 'OrderID', 'ItemCount', 'TotalPaid', 'S-Paid', 'TotalPurchasePrice', 'FinalValueFee', 'PaypalFee', 'TotalProfit', 'TotalTaxFee', 'SoldTime','eBayAccount')
    column_searchable_list = ['OrderID']
    column_default_sort = ('SoldTime', True)
    # column_editable_list = ['Title', 'BuyItNowPrice', 'Quantity']
    # def on_model_change(self, form, model):
    #      time.sleep(5)
    #      # return 'error'

class LineItemView(ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated

    page_size = 100
    #can_create = False
    list_template = 'pages/lineitem/lineitemlist.html'
    # edit_template = 'pages/orders/orderedit.html'
    #can_edit = False
    #can_delete = False
    def _ASIN_formatter(view, context, model, name):
        return Markup("""<a title="To Amazon Item" data-toggle="tooltip"
                                  onclick="return !window.open(this.href, 'Amazon Order', 'width=1300,height=600')" target="_blank"
                              href="https://www.amazon.com/dp/{0}">{0}</a>""".format(model.Asin))

    column_formatters = {
       'Asin': _ASIN_formatter,
    }
    column_labels = dict(PurchasePrice='Price')

    column_searchable_list = ['OrderID']
    column_list = ('Title','Quantity', 'PurchasePrice', 'Paid', 'Profit', 'Tax', 'Asin')

    #def after_model_change(self, form, model, is_created):
        #setLineItem.delay(model.OrderID, model.AzOrderID, model.Asin, model.Quantity, float(model.PurchasePrice), float(model.Tax))
    #def after_model_delete(self, model):
        #item = db_session.query(SoldReceipt).filter_by(OrderID=model.OrderID).first()
        #UpdateReceipt.delay(model.OrderID)

class ScraperViewScraperForm(form.Form):
    asin = fields.StringField(u'Text', widget=TextArea())
    maxWeight = fields.DecimalField()
    titleOption = fields.BooleanField()
    brandOption = fields.BooleanField()
    ignoreActiveOption = fields.BooleanField()
    template_id = fields.SelectField(u'Choose template', coerce=int)




class CKTextAreaWidget(TextArea):
    def __call__(self, field, **kwargs):
        if kwargs.get('class'):
            kwargs['class'] += " ckeditor"
        else:
            kwargs.setdefault('class', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)

class CKTextAreaField(TextAreaField):
    widget = CKTextAreaWidget()

########CUSTOM FILTER FOR SCRAPER VIEW#############
class FilterStringCountLength(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
            return query.filter(func.char_length(self.column) > 80)

    def operation(self):
        return 'is 80+ in length.'

class ScraperView(ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated

    def get_query(self):
        return db_session.query(ScrapedItem).filter_by(uid=login.current_user.get_id())

    @expose('/')
    def index_view(self):
        session['curview'] = 'scraper'
        if session.get('listertaskid'):
            task = AsyncResult(session.get('listertaskid'))
            if task.state == 'SUCCESS':
                session.pop('listertaskid', None)

        return super(ScraperView, self).index_view()

    column_list = ('Pic', 'Brand', 'Title', 'Price', 'Quantity','Asin', 'Description')

    def _Desc_formatter(view, context, model, name):
        return Markup('<form><textarea class="ckeditor" name="editor1" id="editor1" rows="5">{}</textarea><script>CKEDITOR.replace( "editor1" );</script></form>'.format(model.Description))

    def _ASIN_formatter(view, context, model, name):
        return Markup("""<a title="To Amazon Item" data-toggle="tooltip"
                                  onclick="return !window.open(this.href, 'Amazon Order', 'width=1300,height=600')" target="_blank"
                              href="https://www.amazon.com/dp/{0}">{0}</a>""".format(model.Asin))
    def _PicURL_formatter(view, context, model, name):
        #pic = '|'.join(model.PicURLs)
        #return Markup("""<img class="pics" src="{}">""".format(model.PicURLs))
        return model.PicURLs

    column_default_sort = ('Asin')
    column_formatters = {
        'Description': _Desc_formatter,
        'Asin': _ASIN_formatter,
        'Pic': _PicURL_formatter
    }
    column_searchable_list = ['Title','Asin','Brand']
    column_editable_list = ['Title', 'Price', 'Quantity']
    form_overrides = dict(Description=CKTextAreaField)

    list_template = 'pages/scrape/scraperlist.html'
    edit_template = 'pages/scrape/scrapeedit.html'

    page_size = 50
    can_create = False

    column_filters = [
        FilterStringCountLength(column=ScrapedItem.Title, name='Title')
            ]


    def __init__(self, session,**kwargs):
        super(ScraperView, self).__init__(ScrapedItem, session, **kwargs)
"""
### Accounts related views ###
"""
class UserView(ModelView):

    def is_accessible(self):
        session['curview'] = 'settings'
        if login.current_user.get_id() == 1:
            return login.current_user.is_authenticated
        else:
            return False
    def get_query(self):
        return db_session.query(User)
    #column_editable_list = ['notiemail', 'notipass']

    def on_model_change(self, form, model, is_created):
        if is_created:
            u = User(username=model.username,pw_hash=model.pw_hash,email=model.email,urole=model.urole)
            db_session.add(u)
            db_session.commit()
            return redirect(url_for('users.index_view'))

    can_create = True
    column_list = ('id', 'username', 'email', 'urole', 'authenticated', 'active')
    column_labels = dict(id='User ID #', username='Username', email='Email',urole='Privilege')


    list_template = 'pages/users/userslist.html'
    edit_template = 'pages/users/usersedit.html'
    create_template = 'pages/users/userscreate.html'
    form_columns = ['username', 'pw_hash', 'email', 'urole']

    def __init__(self, session,**kwargs):
        super(UserView, self).__init__(User, session, **kwargs)

# One Amabay account can have multiple eBay accounts
class eBayAccountView(ModelView):
    def is_accessible(self):
        session['curview'] = 'settings'
        return login.current_user.is_authenticated

    def get_query(self):
        return db_session.query(eBayAccount).filter_by(uid=login.current_user.get_id())
    def get_count_query(self):
        return db_session.query(func.count(eBayAccount.uid)).filter_by(uid=login.current_user.get_id())

    def __init__(self, session,**kwargs):
        super(eBayAccountView, self).__init__(eBayAccount, session, **kwargs)

    def on_model_change(self, form, model, is_created):
        if is_created:
            session['accSelect'] = model.usern
            model.uid = login.current_user.get_id()
    def on_model_delete(self, model):
        session['accSelect'] = [r.usern for r in db.session.query(eBayAccount.usern).filter_by(uid=login.current_user.get_id()).distinct()]

    def _token_formatter(view, context, model, name):
        if not model.token:
            return Markup("""<a href="/killerapp/subscribe/{1}">{0}</a>""".format('Click here to get a token', model.usern))
        else:
            return Markup("""<span class="fa fa-check-circle"></span>""")

    column_list = ('usern', 'token')
    column_labels = dict(usern='eBay Username')

    column_formatters = {
        'token': _token_formatter
    }
    can_edit = False
    can_create = True
    can_delete = True

    list_template = 'pages/ebayacc/ebayacclist.html'
    edit_template = 'pages/ebayacc/ebayaccedit.html'
    create_template = 'pages/ebayacc/ebayacccreate.html'

    form_columns = ['usern']

# Notification email page. For notifications of order updates, shipped, etc.
class NotifyEmailView(ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated

    def get_query(self):
        return db_session.query(NotifyEmail).filter_by(uid=login.current_user.get_id())


    def __init__(self, session,**kwargs):
        super(NotifyEmailView, self).__init__(NotifyEmail, session, **kwargs)

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.uid = login.current_user.get_id()

    can_edit = False
    list_template = 'pages/notifyemail/notifyemaillist.html'
    edit_template = 'pages/notifyemail/notifyemailedit.html'
    create_template = 'pages/notifyemail/notifyemailcreate.html'