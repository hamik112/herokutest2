import os
import logging
import imaplib
import email
import re
import traceback
import urllib2
import time
import amazonproduct

from datetime import timedelta, datetime
from celery.utils.log import get_task_logger
from logging.handlers import RotatingFileHandler
from scripts.logger import TlsSMTPHandler
from scripts import CallEbay, AbayLibs
from scripts.ListingBuilder import ListingBuilder
from lxml import etree, objectify
from celery import chain
from amazonproduct.errors import InvalidParameterValue


# import sys
# reload(sys)
# sys.setdefaultencoding('utf-8')
# from decimal import Decimal
# celery = Celery('tasks')
# celery.config_from_object('celeryconfig')


from database import ActiveItem, ListingStat, User, OrderItem, SoldReceipt, ScrapedItem, DescriptionTemplate, db_session, db, LineItem, Notification, eBayAccount, NotifyEmail
from app import celery

from scripts.flask_celery import single_instance

# from views import flash
from sqlalchemy.orm.exc import NoResultFound, StaleDataError
from celery import group

#import amazonproduct.processors.objectify as obj

logger = get_task_logger(__name__)
logger.setLevel(logging.DEBUG)


APP_ROOT = os.path.dirname(os.path.abspath(__file__))   # refers to application_top
APP_FILES = os.path.join(APP_ROOT, 'scripts/files')
APP_STATIC = os.path.join(APP_ROOT, 'static')

formatter = logging.Formatter(
    "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
handler = RotatingFileHandler('app.log', maxBytes=10000000, backupCount=5)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)
emailLog = TlsSMTPHandler(("smtp.gmail.com", 587), '###', ['###'], 'Task Error', ('###', '###'))
emailLog.setLevel(logging.WARNING)
logger.addHandler(emailLog)


#####Instance0
config = {
            'access_key': '###',
            'secret_key': '###',
            'associate_tag': '###',
            'locale': 'us'
        }

# # ######Instance1
# config = {
#             'access_key': 'AKIAI6VTFZ6KCMGZA4PQ',
#             'secret_key': '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',
#             'associate_tag': 'abay01-20',
#             'locale': 'us'
#         }

api = amazonproduct.API(cfg=config)

#NotiStrings = AbayLibs.NotiStrings
# from scripts.celery_once import QueueOnce

# db_session = db.session

class SqlAlchemyTask(celery.Task):
    """An abstract Celery Task that ensures that the connection the the
    database is closed on task completion"""
    abstract = True

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.info('End Task()')

        db_session.remove()

def PricerCallTaskWaitToObject(task):
    try:
        while not task.ready():
            time.sleep(0.3)
        tt = task.get()
        return ('True', objectify.fromstring(tt))
    except InvalidParameterValue as e:
        return ('False', str(e))

def CallTaskWaitToObject(task):
    #try:
    while not task.ready():
        time.sleep(0.3)
    tt = task.get()
    return objectify.fromstring(tt)
    # except InvalidParameterValue as e:
    #     return InvalidParameterValue(e)

# def UpdateActiveCallTaskWaitToObject(task):
#     #try:
#     while not task.ready():
#         time.sleep(0.7)
#     tt = task.get()
#     return objectify.fromstring(tt)
#     # except InvalidParameterValue as e:
#     #     return InvalidParameterValue(e)

""" Wrapper for tasks """
@celery.task(base=SqlAlchemyTask, time_limit=580)
def DoUrJob():
    try:
        #users = db_session.query(User).join(User.eBayAccounts).filter(eBayAccount.token.isnot(None)).all()
        for u in db_session.query(User).join(User.eBayAccounts).filter(eBayAccount.token.isnot(None)):
            for e in u.eBayAccounts:
                try:
                    updateActiveDriver(u.id,e.usern,e.token)
                except Exception, e:
                    logger.error('Error occured in DoUrJob()|Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))
                    continue
    except Exception, e:
        db_session.rollback()
        logger.error('Error occured in DoUrJob()|Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))
    except StaleDataError as e:
        db_session.rollback()
        logger.error('Error occured in updateActiveDriver(), StaleDataError|Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))

""" Wrapper for tasks """
@celery.task(base=SqlAlchemyTask, time_limit=179)
def DoUrEventJob():
    logger.info('Start DoUrEventJob')
    users = db_session.query(User).join(User.eBayAccounts).filter(eBayAccount.token.isnot(None))
    for u in users:
            for e in u.eBayAccounts:
                try:
                    updateActiveEventDriver.delay(u.id, e.usern, e.token, 2)
                except Exception, e:
                    logger.error('Error occured in DoUrEventJob()|Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))
                    continue
    ##updateEventDriver(3)
    updateSold()
    CompleteSale()
    endJob()
    updateSold()
    for u in users:
            for e in u.eBayAccounts:
                try:
                    updateActiveEventDriver.delay(u.id, e.usern, e.token, 2)
                except Exception, e:
                    logger.error('Error occured in DoUrEventJob()|Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))
                    continue
    purgeEnded()

@celery.task(base=SqlAlchemyTask, time_limit=179, max_retries=2, default_retry_delay=1)
def updateActiveEventDriver(uid,usern,token,mins):
    try:
        logger.info('Start updateActiveEventDriver')
        t = GoiEbay.delay(token, mins, 'getSellerEvents')
        response = CallTaskWaitToObject(t)
        if hasattr(response.ItemArray, 'Item'):
            for item in response.ItemArray.Item:
                title = item.Title.pyval
                logger.info('Working: ' + title)
                itemId = item.ItemID.pyval
                #Asin = getattr(item, 'SKU', None)
                BuyItNowPrice = item.SellingStatus.CurrentPrice.pyval
                Quantity = int(getattr(item, 'Quantity', 0))
                SoldAmount = int(getattr(item.SellingStatus, 'QuantitySold', 0))
                WatchCount = int(getattr(item, 'WatchCount', 0))
                QuantityAvailable = Quantity - SoldAmount
                #pic = item.PictureDetails.GalleryURL.pyval
                TimeLeft = item.ListingDetails.EndTime.pyval
                # TimeLeft = item.TimeLeft.pyval

                ##if db.session.query(ActiveItem.ItemID).filter_by(ItemID=itemId).scalar() is None:
                theItem = ActiveItem(uid=uid, Title=title, ItemID=itemId, BuyItNowPrice=BuyItNowPrice,
                                     Quantity=Quantity,
                                     SoldAmount=SoldAmount, TimeLeft=TimeLeft, WatchCount=WatchCount,
                                     eBayAccount=usern,
                                     QuantityAvailable=QuantityAvailable)
                db_session.merge(theItem)

                t = db_session.query(ListingStat).filter_by(ItemID=itemId).first()
                if int(QuantityAvailable) != 0:
                    if t is not None:
                        t.PurgeZeroNextDate = None
                else:
                    if t is None:
                        # nextZeroPurgeDate = TimeLeft + timedelta(days=30)

                        theListing = ListingStat(uid=uid, ItemID=itemId,
                                                 PurgeZeroNextDate=TimeLeft + timedelta(days=30))
                        db_session.add(theListing)
            response = None
            del response
            db_session.commit()
        logger.info('End updateActiveEventDriver')
    except Exception, e:
        db_session.rollback()
        if updateActive.request.retries > 1:
            logger.error('Error occured in updateEventDriver() Retrying... |Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))
            return Exception(str(e))
        raise updateActive.retry(exc=e)


def updateActiveDriver(uid,usern,token):
    try:
        currentdt = datetime.utcnow()
        logger.info("DoUrJob::: starting: " + usern)
        # UpdateActive
        t = updateActive.delay(uid, usern, 1, token)
        while not t.ready():
            time.sleep(0.3)

        totalPages, totalEntries = t.get()
        jobList = []
        chunk = 5
        for x in range(2, totalPages, chunk):
            for i in range(x, x + chunk):
                logger.info("DoUrJob::: page: " + str(i))
                jobList.append(updateActive.s(uid, usern, i, token))
                if i == totalPages:
                    logger.info("DoUrJob::: end")
                    break

            job = group(jobList)
            task = job.apply_async()
            jobList[:] = []
            while not task.ready():
                time.sleep(0.3)

        #purgeActive()

        logger.info("DoUrJob::: end: " + usern)

    except Exception, e:
        #logger.error('Error occured in updateActiveDriver()|Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))
        return Exception(str(e))


# @celery.task(base=SqlAlchemyTask)
# def DoUrJob():
#     #chain(updateActive(),updateSold(), CompleteSale(), endJob(), updateActive(), updateSold())
#     #chain(CompleteSale())
#     #Notify.delay(1, 'dourjob', msg='Database updated')
#

""" Task used to call eBay.
# Params:
# token: the eBay user token
# param: paramater for certain tasks. Page # etc.
# job: (String) job name
"""
@celery.task(base=SqlAlchemyTask, bind=True, max_retries=2, default_retry_delay=1)
def GoiEbay(self,token, param, job):
    try:
        if job == 'rePrice':
            #param[0] = itemID
            #param[1] = newprice
            #param[3] = quantity
            t = CallEbay.rePrice(token,param[0],param[1],param[2])
            logger.info('tttt' + str(t))
            if not t == 'Success' and not t == 'Warning':
                raise Exception("Repricing failed. ItemID: " + str(param[0]))
            return (True, 'Success')
        elif job == 'getSellerEvents':
            #param = page number
            t = CallEbay.GetSellerEvents(token,param)
            if t:
                return etree.tostring(t)
            else:
                return False
        elif job == 'setQuantity':
            #param[0] = itemID
            #param[1] = quantity
            t = CallEbay.setQuantity(token,param[0],param[1])
            if not t == 'Success' and not t == 'Warning':
                raise Exception("Set Quantity failed. ItemID: " + str(param[0]))
            return (True, 'Success')
        elif job == 'getActive':
            #param = page number
            t = CallEbay.GetActiveItems(token, param)
            if t:
                return etree.tostring(t)
            else:
                return False
        elif job == 'uploadPic':
            t = CallEbay.picsUpload(token,param[1].split('|'))
            if not t:
                raise Exception("uploadPic failed. ItemID: " + str(param[0]))
            #logger.info('ttttttt \n' + str(t))
            return (param[0], t)
        elif job == 'enditem':
            ##param[0] = the itemid
            ##token = token
            t = CallEbay.endFixedPrice(param, token)
            if not t:
                return False
            #logger.info('ttttttt \n' + str(t))
            return True
        elif job == 'FVFLineItem':
            ##param[0] = OrderID (LineItem)
            ##token = token
            FVF = CallEbay.GetFinalValueFee(param, token)
            if not FVF:
                return False
            #logger.info('ttttttt \n' + str(t))
            return FVF
        elif job == 'FVFCombined':
            ##param[0] = OrderID (LineItem)
            ##token = token
            FVF = CallEbay.GetFinalValueFeeCombined(param, token)
            if not FVF:
                return False
            #logger.info('ttttttt \n' + str(t))
            return FVF
        else:
            raise Exception('job not defined...')


    except Exception as e:
        logger.error('Error occured in GoiEbay()|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
        if GoiEbay.request.retries > 1:
            return (False, str(e))
        raise GoiEbay.retry(exc=e)
"""
# Task used to call Amazon
# Params:
# asinliststring: the list of ASINs, seperated by (,)
# job: (String) job name
"""
@celery.task(base=SqlAlchemyTask, bind=True, max_retries=2, default_retry_delay=5)
def GoiAzon(self, asinliststring, job):
    try:
        time.sleep(1.1)
        # response = None
        if job == 'scrape':
            asinstr = ','.join(asinliststring)
            response = api.item_lookup(asinstr, ResponseGroup='EditorialReview,ItemAttributes,OfferFull,Images',
                                       Condition='New')
            return etree.tostring(response, encoding="us-ascii", method="xml")
        elif job == 'price':  ##Fix later for pricer
            try:
                asinstr = ','.join(asinliststring)
                response = api.item_lookup(asinstr, ResponseGroup='OfferFull', Condition='New')
                return etree.tostring(response, encoding="us-ascii", method="xml")
            except InvalidParameterValue as e:
                return etree.tostring(e.xml, encoding="us-ascii", method="xml")
        elif job == 'price0':
            response = api.item_lookup(asinliststring, ResponseGroup='Offers', MerchantId='Amazon', Condition='New')
            return etree.tostring(response, encoding="us-ascii", method="xml")
        return False

    except Exception as e:
        logger.error('Error occured in GoiAzon()|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
        if GoiAzon.request.retries > 1:
            return False
        raise GoiAzon.retry(exc=e)


""" Validation of asin """
def determineExceptionAsin(string):
    try:
        asinPattern = "([A-Z0-9]{10})"
        asin = re.search(asinPattern, string)
        return asin.group(1)
    except Exception:
        return False



# @celery.task(base=SqlAlchemyTask, bind=True, max_retries=10, default_retry_delay=6)
# def GoiEbay(self, asin, job):
#     try:
#         time.sleep(1.1)
#         response = None
#         if job == 'scrape':
#             response = api.item_lookup(asin, ResponseGroup='EditorialReview,ItemAttributes,OfferFull,Images', Condition='New')
#         elif job == 'price': ##Fix later for pricer
#             response = api.item_lookup(asin, ResponseGroup='OfferFull', Condition='New')
#
#         return etree.tostring(response, encoding="us-ascii", method="xml")
#
#     except Exception as e:
#         logger.error('Error occured in GoiEbay()|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
#         raise GoiAzon.retry(exc=e)

"""  Update prices in the active items list """
@celery.task(base=SqlAlchemyTask, bind=True, max_retries=2, default_retry_delay=6, time_limit=3600)
def Pricer(self):
    try:
        #users = db_session.query(User.id, User.token).filter(User.token.isnot(None)).all()
        ##MAKe for multiple users
        #uid = 1
        #user = db_session.query(User.token).filter_by(id=uid).first()
        #token = user.token

        users = db_session.query(User).join(User.eBayAccounts).filter(eBayAccount.token.isnot(None)).all()
        for user in users:
            for ee in user.eBayAccounts:
                query = db_session.query(ActiveItem.ItemID, ActiveItem.Asin
                                          ).filter_by(uid=user.id).filter_by(eBayAccount=ee.usern).filter(ActiveItem.Asin != None).filter(ActiveItem.TimeLeft > datetime.utcnow())

                listLength = query.count()
                query = query.all()

                setEbayAsinList = []
                ItemIDDict = {}
                chunklength = 10
                maxRunningTasks = 70

                # We split active items list into chunks of 10
                for i in range(0, listLength, chunklength):
                    chunk = query[i:i + chunklength]
                    #logger.info('Working on chunk' + str(i) + ':' + str(i+10))
                    #asins = []
                    for q in chunk:
                        if q.Asin[0] != '!':
                            setEbayAsinList.append(str(q.ItemID))
                            #asins.append(q.Asin)
                            ItemIDDict[q.Asin] = str(q.ItemID)

                    #t = GetSetPricer.delay(token,list(ItemIDDict.keys()),ItemIDDict)
                    t = chain(GetSetPricer.s(list(ItemIDDict.keys()),ItemIDDict,user.id), SetEbayPricing.s(ee.token, user.id)).apply_async()
                    ItemIDDict.clear()
                    # This if statement is for the task to pause when we have 70 tasks running in the queue. This way, the task queue doesn't get overloaded
                    if i % maxRunningTasks is 0 or (i + chunklength) >= listLength:
                        logger.info(maxRunningTasks + ' Tasks of ' + chunklength + ' items queued... Waiting for finish... ' + str(i) + '/' + str(listLength))
                        # pause the task input
                        while not t.ready():
                            time.sleep(0.3)
                        #tt = t.get()
                        #db_session.flush()
                        #logger.info('SetEbayPricingList:' + str(setEbayAsinList))
                        #tt = SetEbayPricing.delay(token,setEbayAsinList)
                        #setEbayAsinList[:] = []
                        #while not tt.ready():
                        #    time.sleep(1)
                        # if (i + 10) >= listLength:
                        #     logger.info('Final Wait')
                        #     while not tt.ready():
                        #         time.sleep(1)
                        #db_session.commit()


                    #db_session.flush()

                setEbayAsinList[:] = []
                ItemIDDict.clear()
                #db_session.commit()
                Notify.delay(1,'pricer')

    except Exception as e:
        db_session.rollback()
        logger.error('Error occured in GetPricer()|Error: ' + str(e) + '\n123 ' + str(traceback.print_exc()))
        #raise GoiAzon.retry(exc=e)

""" Send pricing information to eBay API
# Params
# itemIDList: List of eBay item ids to be updated
# token: user eBay token
# uid: local user id to access user details
"""
@celery.task(base=SqlAlchemyTask, bind=True, max_retries=2, default_retry_delay=6)
def SetEbayPricing(self, itemIDList, token, uid):
    try:
        #logger.info('SetEbayPricingList:' + str(itemIDList))
        db_session.flush()
        # query = db_session.query(ActiveItem.AzonPrice, ActiveItem.TargetProfit, ActiveItem.PriceUpdated,
        #                          ActiveItem.PriceUpdated, ActiveItem.CustomTargetPrice, ActiveItem.BuyItNowPrice,
        #                          ActiveItem.QuantityAvailable, ActiveItem.ItemID
        #                          ).filter_by(uid=uid).filter(ActiveItem.PriceUpdated == False)

        query = db_session.query(ActiveItem.Title,ActiveItem.AzonPrice, ActiveItem.TargetProfit, ActiveItem.PriceUpdated,
                                 ActiveItem.PriceUpdated, ActiveItem.CustomTargetPrice, ActiveItem.BuyItNowPrice,
                                 ActiveItem.QuantityAvailable, ActiveItem.ItemID
                                 ).filter(ActiveItem.ItemID.in_(itemIDList))
        itemIDList = None

        # todo Get these constants outta here
        EBAY_FEE = 0.10
        PAYPAL_FEE = 0.029
        PAYPAL_FEE_30 = 0.30
        AZON_TAX = 0.005

        newQuant = 2

        logger.info('Starting set ebay price, len of query: + ' + str(query.count()))
        query = query.all()
        for item in query:
            try:
                logger.info(item.Title + '--' + str(item.QuantityAvailable))
                if item.AzonPrice:
                    logger.info('item.AzonPrice if')
                    azonTax = float(item.AzonPrice) * AZON_TAX
                    sellPrice = (float(item.AzonPrice) + azonTax) + float(item.TargetProfit)
                    finalSellPrice = (((sellPrice * EBAY_FEE) + ((sellPrice * PAYPAL_FEE) + PAYPAL_FEE_30)) + sellPrice)
                    finalSellPrice = "%.2f" % finalSellPrice
                    #finalSellPrice = roundAbout(float(finalSellPrice))

                    if float(item.BuyItNowPrice) != float(finalSellPrice):
                        logger.info('bitnp : ' + str(item.BuyItNowPrice) + ' fsp:' + str(finalSellPrice))
                        if item.QuantityAvailable != 0:
                            logger.info('avail not 0')
                            t = GoiEbay.delay(token, (item.ItemID, finalSellPrice, item.QuantityAvailable), 'rePrice')
                            while not t.ready():
                                time.sleep(0.3)
                            logger.info('GoiEbay--- ' + str(item.ItemID) + '--' + str(finalSellPrice))
                            res = t.get()
                            if res[0]:
                                logger.info('Setting the Item--- ' + str(item.ItemID) + '--' + str(finalSellPrice))
                                theItem = ActiveItem(ItemID=item.ItemID,
                                                     BuyItNowPrice=finalSellPrice,
                                                     PriceUpdated=True)
                                item = db_session.merge(theItem)
                                #db_session.add(item)
                                #Notify.delay(uid, 'reprice', link=item.ItemID)
                            else:
                                Notify.delay(uid, 'reprice', msg='Item reprice failed: ' + item.ItemID, link=item.ItemID)
                                raise Exception('Reprice Failed: ' + res[1])
                        else:
                            logger.info('avail 0')
                            t = GoiEbay.delay(token, (item.ItemID, finalSellPrice, newQuant), 'rePrice')
                            while not t.ready():
                                time.sleep(0.3)
                            res = t.get()
                            if res[0]:
                                theItem = ActiveItem(ItemID=item.ItemID,
                                                     BuyItNowPrice=finalSellPrice,
                                                     PriceUpdated=True,
                                                     QuantityAvailable=newQuant)
                                item = db_session.merge(theItem)
                                #db_session.add(item)
                                #Notify.delay(uid, 'reprice', link=item.ItemID)
                            else:
                                Notify.delay(uid, 'reprice', msg='Item set quantity failed: ' + item.ItemID, link=item.ItemID)
                                raise Exception('Reprice Failed: ' + res[1])
                    else:
                        if item.QuantityAvailable == 0:
                            logger.info('avail == 0')
                            t = GoiEbay.delay(token, (item.ItemID, finalSellPrice, newQuant), 'rePrice')
                            while not t.ready():
                                time.sleep(0.3)
                            res = t.get()
                            if res[0]:
                                theItem = ActiveItem(ItemID=item.ItemID,
                                                         BuyItNowPrice=finalSellPrice,
                                                         PriceUpdated=True,
                                                         QuantityAvailable=newQuant)
                                item = db_session.merge(theItem)
                                #db_session.add(item)
                                #Notify.delay(uid, 'reprice', link=item.ItemID)

                            else:
                                Notify.delay(uid, 'reprice', msg='Item reprice failed: ' + item.ItemID, link=item.ItemID)
                                raise Exception('Reprice Failed: ' + res[1])
                        else:
                            logger.info('avail != 0')
                            theItem = ActiveItem(ItemID=item.ItemID, PriceUpdated=True)
                            item = db_session.merge(theItem)
                            #db_session.add(item)

                else:
                    logger.info('item.AzonPrice not if')
                    if item.QuantityAvailable != 0:
                        logger.info('item.QuantityAvailable not 0')
                        t = GoiEbay.delay(token, (item.ItemID, 0), 'setQuantity')
                        while not t.ready():
                            time.sleep(0.3)
                        res = t.get()
                        if res[0]:
                                theItem = ActiveItem(ItemID=item.ItemID,
                                                         PriceUpdated=True,
                                                         QuantityAvailable=0)
                                item = db_session.merge(theItem)
                                #db_session.add(item)
                                #Notify.delay(uid, 'reprice', link=item.ItemID)
                        else:
                            Notify.delay(uid, 'reprice', msg='Item reprice failed: ' + item.ItemID, link=item.ItemID)
                            raise Exception('Reprice Failed: ' + res[1])
                    else:
                        logger.info('Reached end------------------------')
                        theItem = ActiveItem(ItemID=item.ItemID,
                                                PriceUpdated=True,
                                            )
                        item = db_session.merge(theItem)
                        #db_session.add(item)
            except Exception as e:
                logger.error('Error occured in SetEbayPricing() ITEM LOOP|Error: ' + str(item.ItemID) + '\n\n' + str(e))
                pass

        db_session.commit()

    except Exception as e:
        db_session.rollback()
        logger.error('Error occured in SetEbayPricing() MAIN|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
        #raise GoiAzon.retry(exc=e)

"""
# This is where we get the pricing info from Amazon API
# Params:
# asins: ASIN list to get their price
# itemIDDict: dict of IDs to be updated. We also store ASINS that are invalid as to skip them to avoid unnecessary API calls
# returns: itemIDDict list that has been updated.
"""
@celery.task(base=SqlAlchemyTask, bind=True, max_retries=2, default_retry_delay=6)
def GetSetPricer(self,asins,ItemIDDict,uid):
    try:

        # for attempt in range(10):
        #     try:
        #         # asinstr = ','.join(asins)
        #         logger.info('tryng--- ' + str(asins))
        #         t = GoiAzon.delay(asins, 'price')
        #         response = CallTaskWaitToObject(t)
        #     except InvalidParameterValue as e:
        #         logger.info('INvalids Exception??--- ' + str(e))
        #         exceptedAsin = determineExceptionAsin(str(e))
        #         if exceptedAsin:
        #             logger.info('determineExceptionAsin--- ' + str(exceptedAsin))
        #             asins.remove(exceptedAsin)
        #             nonAsinsList.append(exceptedAsin)
        #             continue
        #         else:
        #             raise Exception("determineExceptionAsin returned False : " + str(e))
        #             #logger.info('determineExceptionAsin encountered an error--- ' + str(e))
        #             #break
        #     else:
        #         logger.info('theeelisttttt--- ' + str(asins))
        #         break
        # else:
        #     raise Exception("Could't get AzonPrice response")

        # if not response[0]:
        #         exceptedAsin = determineExceptionAsin(response[1])
        #         logger.info('determineExceptionAsin--- ' + exceptedAsin)
        #         asins.remove(exceptedAsin)
        #         nonAsinsList.append(exceptedAsin)
        #         continue
        #     else:
        #         logger.info('theeelisttttt--- ' + str(asins))
        #         response = response[1]
        #         break

        # t = GoiAzon.delay(asins, 'price')
        # (asinlist, response) = PricerCallTaskWaitToObject(t)
        # logger.info('WOorking on list: ---'+ str(asinlist))

        #nonAsinsList = []

        logger.info('tryng--- ' + str(asins[0] + '---- Start'))
        t = GoiAzon.delay(asins, 'price')
        logger.info('tryng--- ' + str(asins[0] + '---- waiting task'))
        response = CallTaskWaitToObject(t)

        logger.info('tryng--- ' + str(asins[0] + '---- starting errors task'))

        if getattr(response.Items.Request, 'Errors', None):
            try:
                for error in response.Items.Request.Errors.Error:
                    if error.Code == 'AWS.InvalidParameterValue':
                        exceptedAsin = determineExceptionAsin(str(error.Message))
                        if exceptedAsin:
                            logger.info('determineExceptionAsin--- ' + str(exceptedAsin))
                            # asins.remove(exceptedAsin)
                            # nonAsinsList.append(exceptedAsin)
                            theItem = ActiveItem(ItemID=ItemIDDict[exceptedAsin], AzonPrice=None,
                                                     PriceUpdated=False)
                            t = db_session.merge(theItem)
                            #db_session.add(t)
                        else:
                            logger.error('Error occured in GetSetPricer() ASIN NO EXIST|Error: ' + str(error.Message))
            except Exception as e:
                logger.error('Error occured in GetSetPricer() OUTER|Error: ' + str(e))
                pass

        logger.info('tryng--- ' + str(asins[0] + '---- errors done task'))


        #logger.info('Nonasins----' + str(nonAsinsList))
        logger.info('tryng--- ' + str(asins[0] + '---- start items loop'))
        for item in response.Items.Item:
            try:
                azonPrice = azonPriceGrab(item)
                if azonPrice:
                    theItem = ActiveItem(ItemID=ItemIDDict[item.ASIN], AzonPrice=azonPrice,
                                         TargetProfit=float(determineAutoTargetProfit(azonPrice)),
                                         PriceUpdated=False)
                else:
                    theItem = ActiveItem(ItemID=ItemIDDict[item.ASIN], AzonPrice=None,
                                         PriceUpdated=False)
                t = db_session.merge(theItem)
                #db_session.add(t)

            except Exception as e:
                logger.error(
                    'Error occured in GetPricer() ITEM LOOP|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
                pass
        logger.info('tryng--- ' + str(asins[0] + '---- end items loop'))

        response = None
        del response
        db_session.commit()
        logger.info('tryng--- ' + str(asins[0] + '----commit'))

        return list(ItemIDDict.values())

    except Exception as e:
        db_session.rollback()
        logger.error('Error occured in GetSetPricer()|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
        raise GetSetPricer.retry(exc=e)

""" Method to calculate the price with target profit
# todo custom pricing
"""
def determineAutoTargetProfit(azonPrice):
    if azonPrice < 17.00:
        PROFIT_MARGIN = 2.45 #2.05
    elif azonPrice < 24.00:
        PROFIT_MARGIN = (0.085 * azonPrice) + 0.95 #.55
    else:
        PROFIT_MARGIN = (0.085 * azonPrice) + 0.95

    return "%.2f" % PROFIT_MARGIN

# Round price with sigfig of 2
def roundAbout(f):
    f = list(str("%.2f" % f))
    i = f.index('.')
    if f[i-1] < f[i+1]:
        f[i-1] = str(int(f[i-1]) + 1)
        f[i+1] = f[i-1]
        f[i+2] = f[i-1]
    else:
        f[i+1] = f[i-1]
        f[i+2] = f[i-1]
    return float(''.join(f))

"""
# Method to grab amazon pricing
# Params
# respons: the Amazon API response populated item details
"""
def azonPriceGrab(response):
    try:
        asin = response.ASIN.text
        tree = response.Offers.Offer.OfferListing
        avail = response.Offers.Offer.OfferListing.AvailabilityAttributes.AvailabilityType.text
        availMinHours = response.Offers.Offer.OfferListing.AvailabilityAttributes.MinimumHours.text
        prime = response.Offers.Offer.OfferListing.IsEligibleForPrime.text
        if prime == '1' and avail == 'now':
            if int(availMinHours) > 48:
                return False
            #getattr(tree,'SalePrice',None)
            if hasattr(tree, 'SalePrice'):
                price = (response.Offers.Offer.OfferListing.SalePrice.FormattedPrice.text)
            else:
                price = (response.Offers.Offer.OfferListing.Price.FormattedPrice.text)
            return float((price)[1:])
        else:
            t = GoiAzon.delay(asin, 'price0')
            response = CallTaskWaitToObject(t)
            tree = response.Items.Item.Offers.Offer.OfferListing
            avail = response.Items.Item.Offers.Offer.OfferListing.AvailabilityAttributes.AvailabilityType.text
            availMinHours = response.Items.Item.Offers.Offer.OfferListing.AvailabilityAttributes.MinimumHours.text

            if avail == 'now':
                if int(availMinHours) > 48:
                    #print 'More than 2 days to ship... Returning false'
                    return False
                if hasattr(tree, 'SalePrice'):
                    price = response.Items.Item.Offers.Offer.OfferListing.SalePrice.FormattedPrice.text
                else:
                    price = response.Items.Item.Offers.Offer.OfferListing.Price.FormattedPrice.text
                return float((price)[1:])

        return False
    except AttributeError as e:
        #logger.error('Error occured in GoiEbay()|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
        return False
    except Exception as e:
        return False

"""
# Method to update currently listed items on eBay
# Params
# uid: Local user id
# usern: eBay account user name (for notification purposes)
# page: the pagination in the response (eBay API sends back responses in pages)
# token: the eBay user token
# returns: token of number of pages in the response and number of items
"""
@celery.task(base=SqlAlchemyTask, bind=True, time_limit=45, max_retries=3, default_retry_delay=1)
def updateActive(self, uid, usern, page, token):
    try:
        #logger.info('Starting updateActive()')
        #response = CallEbay.GetActiveItems(token, page)
        t = GoiEbay.delay(token, page, 'getActive')
        response = CallTaskWaitToObject(t)
        currentdt = datetime.utcnow()

        totalNumberOfPages = response.ActiveList.PaginationResult.TotalNumberOfPages.pyval
        totalNumberOfEntries = response.ActiveList.PaginationResult.TotalNumberOfEntries.pyval
        logger.info('TotalnuberoFpages: ' + str(totalNumberOfPages))
        activeList = response.ActiveList.ItemArray.Item
        for item in activeList:
            title = item.Title.pyval
            itemId = item.ItemID.pyval
            Asin = getattr(item, 'SKU', None)
            BuyItNowPrice = item.SellingStatus.CurrentPrice.pyval
            Quantity = int(getattr(item, 'Quantity', 0))
            QuantityAvailable = int(getattr(item, 'QuantityAvailable', 0))
            WatchCount = int(getattr(item, 'WatchCount', 0))
            pic = item.PictureDetails.GalleryURL.pyval
            TimeLeft = AbayLibs.parse_duration(item.TimeLeft.text)
            #TimeLeft = item.TimeLeft.pyval

            ##if db.session.query(ActiveItem.ItemID).filter_by(ItemID=itemId).scalar() is None:
            theItem = ActiveItem(uid=uid, Title=title, ItemID=itemId, Asin=str(Asin), BuyItNowPrice=BuyItNowPrice,
                                 Quantity=Quantity,
                                 QuantityAvailable=QuantityAvailable, TimeLeft=TimeLeft, WatchCount=WatchCount,
                                 PictureDetailsURL=pic,
                                 eBayAccount=usern,
                                 SoldAmount=(Quantity-QuantityAvailable))
            t = db_session.merge(theItem)
            #db_session.add(t)

            #t = ListingStat.query.filter_by(ItemID=itemId).first()
            t = db_session.query(ListingStat).filter_by(ItemID=itemId).first()
            if int(QuantityAvailable) != 0:
                if t is not None:
                    t.PurgeZeroNextDate = None
            else:
                if t is None:
                    #nextZeroPurgeDate = TimeLeft + timedelta(days=30)

                    theListing = ListingStat(uid=uid, ItemID=itemId,
                                             PurgeZeroNextDate=TimeLeft + timedelta(days=30))
                    db_session.add(theListing)


        #purgeActive(uid)

        response = None
        del response

        db_session.commit()
        #logger.info('End updateActive()')
        return (totalNumberOfPages,totalNumberOfEntries)

    except Exception, e:
        db_session.rollback()
        if updateActive.request.retries > 2:
            logger.error('Error occured in updateActive() Retrying... |Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))
            return Exception(str(e))
        raise updateActive.retry(exc=e)

# @celery.task(base=SqlAlchemyTask, bind=True)
# def updateActive(self):
#     try:
#         logger.info('Starting updateActive()')
#         users = db_session.query(User).join(User.eBayAccounts).filter(eBayAccount.token.isnot(None)).all()
#
#         ItemsFromEbayList = []
#         for u in users:
#             for e in u.eBayAccounts:
#                 page = 1
#                 response = CallEbay.GetActiveItems(str(e.token), page)
#
#                 # t = NgoiEbay.delay(str(u.token), page)
#                 # while not t.ready():
#                 #     time.sleep(1)
#                 # tt = t.get()
#                 # #logger.error(str(type(response)))
#                 # response = json.loads(tt, 'utf8')
#
#                 totalNumberOfPages = response.reply.ActiveList.PaginationResult.TotalNumberOfPages
#                 for x in range(2, int(totalNumberOfPages) + 2):
#                     activeList = response.reply.ActiveList.ItemArray.Item
#
#                     for item in activeList:
#                         ItemsFromEbayList.append(item.ItemID)
#                         title = item.Title
#                         itemId = item.ItemID
#                         #Asin = item.SKU
#                         Asin = getattr(item, 'SKU', None)
#                         BuyItNowPrice = item.SellingStatus.CurrentPrice.value
#                         Quantity = getattr(item, 'Quantity', 0)
#                         QuantityAvailable = getattr(item, 'QuantityAvailable', 0)
#                         WatchCount = getattr(item, 'WatchCount', 0)
#                         pic = item.PictureDetails.GalleryURL
#                         TimeLeft = AbayLibs.parse_duration(item.TimeLeft)
#
#                         ##if db.session.query(ActiveItem.ItemID).filter_by(ItemID=itemId).scalar() is None:
#                         theItem = ActiveItem(uid = u.id, Title= title, ItemID = itemId, Asin = Asin, BuyItNowPrice=BuyItNowPrice, Quantity=Quantity,
#                                               QuantityAvailable=QuantityAvailable,TimeLeft=TimeLeft,WatchCount=WatchCount, PictureDetailsURL = pic,
#                                              eBayAccount=e.usern)
#                         t = db_session.merge(theItem)
#                         db_session.add(t)
#
#                         t = ListingStat.query.filter_by(ItemID=itemId).first()
#                         if int(QuantityAvailable) != 0:
#                             if t is not None:
#                                 t.PurgeZeroNextDate = None
#                         else:
#                             if t is None:
#                                 theListing = ListingStat(uid=u.id,ItemID = itemId, PurgeZeroNextDate = (datetime.now() + timedelta(days=30)))
#                                 db_session.add(theListing)
#
#                     response = CallEbay.GetActiveItems(str(e.token), x)
#
#                 purgeActive(u.id, ItemsFromEbayList)
#                 ItemsFromEbayList[:] = []
#
#
#                 db_session.commit()
#
#
#         logger.info('End updateActive()')
#     except Exception, e:
#         db_session.rollback()
#         logger.error('Error occured in updateActive()|Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))
"""
# Method for removing of ended or expired items on eBay before they can be relisted
# We don't want items that arent selling to be relisted ( waste of moneys )
"""
def purgeEnded():
    try:
        purgeTime = timedelta(days=30)
        items = db_session.query(ActiveItem).filter(
            (ActiveItem.TimeLeft < (datetime.utcnow() - purgeTime))).all()

        for i in items:
            # ls = db_session.query(ListingStat).filter_by(ItemID=i.ItemID).first()
            # db_session.delete(ls)
            db_session.delete(i)

        #db_session.flush()

        # items = db_session.query(ActiveItem).filter(
        #      ActiveItem.updated_on < currentdt).all()
        # for j in items:
        #     # ls = db_session.query(ListingStat).filter_by(ItemID=i.ItemID).first()
        #     # db_session.delete(ls)
        #     j.TimeLeft = datetime.utcnow()

        db_session.commit()

    except Exception, e:
        db_session.rollback()
        logger.error('Error occured in purgeActive()|Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))


# def purgeActive(uid, ItemsFromEbayList):
#     try:
#         purgeTime = timedelta(days=1)
#         items = db_session.query(ActiveItem).filter(
#             (ActiveItem.TimeLeft < (datetime.utcnow() - purgeTime))).all()
#
#         for i in items:
#             # ls = db_session.query(ListingStat).filter_by(ItemID=i.ItemID).first()
#             # db_session.delete(ls)
#             db_session.delete(i)
#
#         db_session.flush()
#         time = datetime.now()
#         itemsNotInList = db_session.query(ActiveItem).filter_by(uid=uid).filter(ActiveItem.ItemID.notin_(ItemsFromEbayList)).filter(ActiveItem.TimeLeft >= time).all()
#         for i in itemsNotInList:
#             #time = datetime.now()
#             i.TimeLeft = time
#
#
#     except Exception, e:
#         db_session.rollback()
#         logger.error('Error occured in purgeActive()|Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))
#
#
"""
# Method to grab sold items details
@celery.task(base=SqlAlchemyTask, bind=True)
"""
def updateSold(self):
    #from database import OrderItem
    try:
        logger.info('Starting updateSold()')
        #users = db_session.query(User.id, User.token).filter(User.token.isnot(None)).all()
        users = db_session.query(User).join(User.eBayAccounts).filter(eBayAccount.token.isnot(None)).all()

        for u in users:
            for e in u.eBayAccounts:
                page = 1
                response = CallEbay.GetSoldItems(str(e.token), page)
                totalNumberOfPages = response.reply.SoldList.PaginationResult.TotalNumberOfPages

                for x in range(2, int(totalNumberOfPages) + 2):
                    soldList = response.reply.SoldList.OrderTransactionArray.OrderTransaction

                    for order in soldList:
                        theOrder = getattr(order, 'Order', None)

                        if theOrder: #If order has multiple line items
                            CombinedOrder = True

                            OrderID = order.Order.OrderID
                            TotalPrice = getattr(order.Order, 'Total', 0.0)
                            if TotalPrice:
                                TotalPrice =order.Order.Total.value

                            Title = "Multiple Items: {}".format(str(len(order.Order.TransactionArray.Transaction)))

                            Quantity = 0
                            for trans in order.Order.TransactionArray.Transaction:
                                Quantity = Quantity + int(trans.QuantityPurchased)

                            trans = order.Order.TransactionArray.Transaction[0]
                            SellerPaidStatus = trans.SellerPaidStatus
                            CreatedTime = trans.CreatedDate
                            BuyerUserID = trans.Buyer.UserID
                            ShippedTime = getattr(trans, 'ShippedTime', None)
                            IsMultiLegShipping = getattr(trans, 'IsMultiLegShipping', False)
                            PrivateNotes = None
                            Asin = None

                            ShippingService = None
                            ShippingServiceCost = getattr(trans.Item.ShippingDetails.ShippingServiceOptions,
                                                          'ShippingServiceCost', 0.0)
                            if ShippingServiceCost:
                                ShippingServiceCost = trans.Item.ShippingDetails.ShippingServiceOptions.ShippingServiceCost.value

                            theItem = OrderItem(uid=u.id, Title=Title, OrderID=OrderID, SellerPaidStatus=SellerPaidStatus,
                                                CreatedTime=CreatedTime, BuyerUserID=BuyerUserID,
                                                TotalPrice=TotalPrice, IsMultiLegShipping=IsMultiLegShipping,
                                                Quantity=Quantity,
                                                PrivateNotes=PrivateNotes, ShippedTime=ShippedTime, Asin=Asin,
                                                CombinedOrder=CombinedOrder, ShippingService=ShippingService,
                                                ShippingServiceCost=ShippingServiceCost, eBayAccount=e.usern)

                            order_item = db_session.merge(theItem)
                            db_session.add(updateReceipt(order_item, u.id, e.usern))

                            totalPrivateNotes = None
                            for trans in order.Order.TransactionArray.Transaction:
                                addLineItem(trans,OrderID)
                                if not totalPrivateNotes:
                                    totalPrivateNotes = getattr(trans.Item, 'PrivateNotes', None)

                            order_item.PrivateNotes = totalPrivateNotes

                            addTotalLineItem(totalPrivateNotes, trans, OrderID, TotalPrice, Quantity)

                        else:
                            CombinedOrder = False

                            SellerPaidStatus = order.Transaction.SellerPaidStatus
                            CreatedTime = order.Transaction.CreatedDate
                            BuyerUserID = order.Transaction.Buyer.UserID
                            Quantity = order.Transaction.QuantityPurchased
                            Title = order.Transaction.Item.Title
                            OrderID = order.Transaction.OrderLineItemID

                            PrivateNotes = getattr(order.Transaction.Item, 'PrivateNotes', None)
                            #TransactionID = order.Transaction.TransactionID
                            ShippedTime = getattr(order.Transaction, 'ShippedTime', None)
                            TotalPrice = getattr(order.Transaction, 'TotalPrice', 0.0)
                            if TotalPrice:
                                TotalPrice = order.Transaction.TotalPrice.value
                            Asin = getattr(order.Transaction.Item, 'SKU', None)
                            IsMultiLegShipping = getattr(order.Transaction, 'IsMultiLegShipping', False)
                            if IsMultiLegShipping:
                                IsMultiLegShipping = True

                            ShippingService = None
                            ShippingServiceCost = getattr(order.Transaction.Item.ShippingDetails.ShippingServiceOptions,
                                                          'ShippingServiceCost', 0.0)
                            if ShippingServiceCost:
                                ShippingServiceCost = order.Transaction.Item.ShippingDetails.ShippingServiceOptions.ShippingServiceCost.value

                            theItem = OrderItem(uid=u.id, Title=Title, OrderID=OrderID, SellerPaidStatus=SellerPaidStatus,
                                                CreatedTime=CreatedTime, BuyerUserID=BuyerUserID,
                                                TotalPrice=TotalPrice, IsMultiLegShipping=IsMultiLegShipping,
                                                Quantity=Quantity,
                                                PrivateNotes=PrivateNotes, ShippedTime=ShippedTime, Asin=Asin,
                                                CombinedOrder=CombinedOrder, ShippingService=ShippingService,
                                                ShippingServiceCost=ShippingServiceCost, eBayAccount=e.usern)

                            order_item = db_session.merge(theItem)
                            db_session.add(updateReceipt(order_item, u.id, e.usern))
                            addLineItem(order.Transaction,OrderID)


                        # o = db_session.merge(theItem)
                        # db_session.add(updateReceipt(o, u.id))

                        #theItem.BuyerCheckoutMessage = BuyerCheckoutMessage
                        ###Address



                    response = CallEbay.GetSoldItems(str(e.token), page)

                db_session.commit()

        logger.info('Ending updateSold()')
    except Exception, e:
        db_session.rollback()
        logger.error('Error occured in updateSold()|Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))

# def updateLineItems(item, TransactionArray, uid):
#     db_session.flush()
#     for Transaction in TransactionArray:
#         l = LineItem(Paid=Transaction.TotalPrice,
#                      Asin=Transaction.Item.SKU, Quantity=Transaction.QuantityPurchased,
#                         Title=Transaction.Item.Title
#                                                 )
#         item.LineItems.append(l)
"""
# In an eBay order, we can have multiple eBay items. One Line Item == one eBay item in an order.
"""
def addLineItem(trans, orderID):
    db_session.flush()
    Asin = trans.Item.SKU
    lineitem = db_session.query(LineItem).filter_by(OrderID=orderID).filter_by(Asin=Asin).scalar()
    PrivateNotes = getattr(trans.Item, 'PrivateNotes', None)
    if not lineitem:
        Price = getattr(trans, 'TotalTransactionPrice', 0.0)
        if Price:
            Price = trans.TotalTransactionPrice.value

        l = LineItem(OrderID=orderID,Paid=Price,
                         Asin=Asin, Quantity=trans.QuantityPurchased,
                            Title=trans.Item.Title,SellerPaidStatus=trans.SellerPaidStatus,
                     PrivateNotes=PrivateNotes, OrderLineItemID=trans.OrderLineItemID)
        db_session.add(l)
    else:
        lineitem.PrivateNotes = PrivateNotes
        lineitem.SellerPaidStatus = trans.SellerPaidStatus
"""
# Temporary row of item details to show the total amount calculated from other LineItems
"""
def addTotalLineItem(privateNotes, trans, orderID, totalPrice, totalQuant):
    db_session.flush()
    Asin = 'None'
    lineitem = db_session.query(LineItem).filter_by(OrderID=orderID).filter_by(Asin=Asin).scalar()
    #PrivateNotes = privateNotes
    if not lineitem:
        Price = totalPrice
        l = LineItem(OrderID=orderID,Paid=Price,
                         Asin=Asin, Quantity=totalQuant,
                            Title='Total',SellerPaidStatus=trans.SellerPaidStatus,
                     PrivateNotes=privateNotes, OrderLineItemID=trans.OrderLineItemID)
        db_session.add(l)
    else:
        lineitem.PrivateNotes = privateNotes
        lineitem.SellerPaidStatus = trans.SellerPaidStatus

# Method to update receipt of orders. Sometimes an order is changed. We need to update that with this method.
def updateReceipt(theItem, uid, usern):
    #ss = SoldReceipt.query.filter_by(OrderID=theItem.OrderID).first()
    #dd = getattr(ss, 'id', None)

    #
    # if theItem.SellerPaidStatus in AbayLibs.PaidValues:
    #     sReceipt = SoldReceipt(PaypalFee=PPFee,OrderID=theItem.OrderID, TotalPaid=theItem.TotalPrice, SoldTime=theItem.CreatedTime, uid=uid)
    # elif theItem.SellerPaidStatus in AbayLibs.NotPaidValues:
    #     sReceipt = SoldReceipt(PaypalFee=0,OrderID=theItem.OrderID, TotalPaid=0, SoldTime=theItem.CreatedTime, uid=uid)
    # elif theItem.SellerPaidStatus in AbayLibs.PendingPaid:
    #     sReceipt = SoldReceipt(PaypalFee=0,OrderID=theItem.OrderID, TotalPaid=0, SoldTime=theItem.CreatedTime, uid=uid) #change soldtime to updated
    #
    # db_session.add(db_session.merge(sReceipt))
    #

    db_session.flush()
    PPFee = ((float(theItem.TotalPrice) * 0.029) + 0.30)

    rec = db_session.query(SoldReceipt).filter_by(OrderID=theItem.OrderID).first()

    if not rec:
        if theItem.SellerPaidStatus in AbayLibs.PaidValues:
            sReceipt = SoldReceipt(PaypalFee=PPFee,OrderID=theItem.OrderID, TotalPaid=theItem.TotalPrice,
                                   SoldTime=theItem.CreatedTime, uid=uid, CombinedOrder=theItem.CombinedOrder,
                                   ItemCount = theItem.Quantity)
        elif theItem.SellerPaidStatus in AbayLibs.NotPaidValues:
            sReceipt = SoldReceipt(PaypalFee=0,OrderID=theItem.OrderID, TotalPaid=0, SoldTime=theItem.CreatedTime,
                                   uid=uid, CombinedOrder=theItem.CombinedOrder,ItemCount = theItem.Quantity)
        elif theItem.SellerPaidStatus in AbayLibs.PendingPaid:
            sReceipt = SoldReceipt(PaypalFee=0,OrderID=theItem.OrderID, TotalPaid=0, SoldTime=theItem.CreatedTime,
                                   uid=uid, CombinedOrder=theItem.CombinedOrder, ItemCount = theItem.Quantity) #change soldtime to updated

        db_session.add(sReceipt)
        Notify.delay(uid, 'neworder', link=theItem.OrderID)
    else:
        if theItem.SellerPaidStatus in AbayLibs.PaidValues:
            rec.PaypalFee = PPFee
            rec.TotalPaid = theItem.TotalPrice
        elif theItem.SellerPaidStatus in AbayLibs.NotPaidValues:
            rec.PaypalFee = 0
            rec.TotalPaid = 0
            rec.TotalProfit = 0
            rec.TotalPurchasePrice = 0
            rec.FinalValueFee = 0
            rec.TotalTaxFee = 0
        elif theItem.SellerPaidStatus in AbayLibs.PendingPaid:
            rec.PaypalFee = 0
            rec.TotalPaid = 0
            rec.TotalProfit = 0
            rec.TotalPurchasePrice = 0
            rec.FinalValueFee = 0
            rec.TotalTaxFee = 0

    return theItem

# def insert_or_updateReceipt(r):
#     receipt = SoldReceipt.query.get(r.OrderID).first()
#     if receipt:
#
"""
# Method to end items in certain categories. If the item has relisted twice with 0 sold, we end that item.
# We also update locally to reflect those changes.
"""
@celery.task(base=SqlAlchemyTask, bind=True)
def endJob(self):
    try:
        logger.info('Starting endJob()')

        durEnding = timedelta(minutes=15)
        users = db_session.query(User).join(User.eBayAccounts).filter(eBayAccount.token.isnot(None)).all()
        #users = db_session.query(User.id, User.token).filter(User.token.isnot(None)).all()

        for u in users:
            for ee in u.eBayAccounts:
                #app.logger.info('Started endJob() for: ' + u.username)
                zero = db_session.query(ListingStat.PurgeZeroNextDate, ListingStat.ItemID).filter_by(uid=u.id).filter(
                (ListingStat.PurgeZeroNextDate < (datetime.now() + durEnding))).all()
                for item in zero:
                    try:
                        q = db_session.query(ActiveItem).filter_by(ItemID=item.ItemID).filter(ActiveItem.QuantityAvailable == 0).first()
                        if q is not None:
                            response = CallEbay.endFixedPrice(str(item.ItemID), str(ee.token))
                            #if response is 'Success':
                            #db_session.delete(item)
                            q.TimeLeft = datetime.utcnow()
                            # else:
                    except Exception as e:
                        logger.error('Error occured in ListingStat loop endjob()|Error: ' + str(e))
                        continue

                db_session.commit()
                # req = db_session.query(ActiveItem).filter_by(uid=u.id).filter(
                # (ActiveItem.TimeLeft < (datetime.now() + durEnding))).all()
                currentdt = datetime.utcnow()
                req = db_session.query(ActiveItem).filter_by(uid=u.id).filter(
                (ActiveItem.TimeLeft).between(currentdt, currentdt + durEnding)).all()
                endcnt = 0

                for item in req:
                    try:
                        if db_session.query(ListingStat).filter_by(ItemID=item.ItemID).scalar() is None:
                            if item.WatchCount > 3:
                                theListing = ListingStat(uid=u.id,ItemID = item.ItemID, LastPurgeDate = (item.TimeLeft + timedelta(days=30)), LastPurgeWatchCount = item.WatchCount,
                                                         LastPurgeQuantity=item.SoldAmount)
                                db_session.add(theListing)
                            #elif item.Quantity is item.QuantityAvailable:
                            elif item.SoldAmount == 0:
                                response = CallEbay.endFixedPrice(str(item.ItemID), str(ee.token))
                                #if response is 'Success':

                                #db_session.delete(item)
                                item.TimeLeft = datetime.utcnow()
                                endcnt += 1
                                # else:
                                #     raise Exception('Ending item not successful')

                                #f.write('--' + str(item.ItemID) + '--' + str(item.Title) +'\n')
                            else:
                                 theListing = ListingStat(uid=u.id,ItemID = item.ItemID, LastPurgeDate = (item.TimeLeft + timedelta(days=30)), LastPurgeWatchCount = item.WatchCount,
                                                 LastPurgeQuantity = item.SoldAmount)
                                 db_session.add(theListing)
                        else:
                            theListing = db_session.query(ListingStat).filter_by(ItemID=item.ItemID).filter(ListingStat.LastPurgeDate < (datetime.now() + durEnding)).first()
                            if theListing:
                                if ((item.WatchCount - theListing.LastPurgeWatchCount) < 3) and theListing.LastPurgeQuantity == item.SoldAmount:
                                    response = CallEbay.endFixedPrice(str(item.ItemID), str(ee.token))
                                    #if response is 'Success':
                                    db_session.delete(theListing)
                                    #db_session.delete(item)
                                    item.TimeLeft = datetime.utcnow()
                                    endcnt += 1
                                    # else:
                                    #     raise Exception('Ending item not successful in past purge date')
                                else:
                                    theListing.user = u.username
                                    theListing.LastPurgeDate = item.TimeLeft + timedelta(days=30)
                                    theListing.LastPurgeQuantity = item.SoldAmount
                                    theListing.LastPurgeWatchCount = item.WatchCount
                            # else:
                            #     print('Listing doesnt exist in listing stats')
                        db_session.commit()

                    except Exception as e:
                        logger.error('Error occured in endJob() active item end loop|Error: ' + str(e))
                        continue

                if endcnt > 0:
                    Notify.delay(u.id,'endcount', msg=endcnt)

        logger.info('End endJob()')
            ###Add update of db here, or update when notified of item delete
    except Exception, e:
        db_session.rollback()
        logger.error('Error occured in endJob()|Error: ' + str(e))
        pass
    except StaleDataError as e:
        db_session.rollback()
        logger.error('Error occured in endJob() StaleDataError|Error: ' + str(e))
"""
### Methods for grabbing eBay user tokens ###
"""
@celery.task(base=SqlAlchemyTask, bind=True)
def CallGetSessionID(self):
    try:
        logger.info('Starting callGetSessionID()')
        sessID = CallEbay.GetSessionID()
        logger.info('End callGetSessionID()')
        return sessID
    except Exception, e:
        logger.error('Error occured in callGetSessionID()|Error: ' + str(e))

@celery.task(base=SqlAlchemyTask)
def FetchToken(sessid):
    try:
        logger.info('Starting FetchToken()')
        tokenAndExpire = CallEbay.FetchTokenRequest(sessid)
        logger.info('End FetchToken()')
        return tokenAndExpire
    except Exception, e:
        logger.error('Error occured in FetchToken()|Error:: ' + str(e))
#################################
"""
# Method for grabbing shipping information from Amazon shipping page.
"""
def parse(url):

    shippingxPath = '//div[@class="a-box"]/div[1]/div/div/div/text()'
    orderIDPattern = "Tracking #: (.*)"
    CarrierPattern = "Carrier: (.*),"

    f = urllib2.urlopen(url)
    html = etree.parse(f, etree.HTMLParser())
    shippingInfo = html.xpath(shippingxPath)[0].strip()
    #print etree.tostring(html, encoding='utf8', method='xml')
    carrier = re.search(CarrierPattern, shippingInfo)
    tracknum = re.search(orderIDPattern, shippingInfo)
    return (determineCarrier(carrier.group(1)), tracknum.group(1))

def determineCarrier(c):
    c = c.lower()
    if c in 'ups':
        return 'UPS'
    elif c in 'usps':
        return 'USPS'
    elif c in 'fedex':
        return 'FedEx'
    elif c in 'ups surepost':
        return 'UPS'
    elif c in 'amzl us':
        return 'Other'
    elif c in 'ontrac':
        return 'ONTRAC'
    elif c in 'parcelpool':
        return 'USPS'
    elif c in 'prestige':
        return 'Prestige'
    else:
        raise Exception('Carrier Type not Found: ' + c)

"""
# Wrapper Method to update shipping information from the notificaiton email
"""
@celery.task(base=SqlAlchemyTask, bind=True)
def CompleteSale(self):
    logger.info('Starting CompleteSale()')
       # users = db_session.query(User).join(User.eBayAccounts).filter(eBayAccount.token.isnot(None)).all()

    #users = db_session.query(User.notiemail, User.notipass, User.id, User.token).filter(User.notiemail.isnot(None)).all()
    users = db_session.query(User).join(User.eBayAccounts).filter(eBayAccount.token.isnot(None)).all()
    for user in users:
        for em in user.NotifyEmails:
            try:
                #processList = []
                #item = []
                mail = imaplib.IMAP4_SSL('imap.gmail.com')
                (rv, capabilities) = mail.login(em.usern,em.pw)
                mail.list()

                ProcessTracking(em.uid,mail)
                ProcessConfirmation(mail)

                logger.info('End CompleteSale()')

            except Exception, e:
                db_session.rollback()
                logger.error('Error occured in completeSale() - Attempt to log in|Error: ' + str(e))
                    # ... exit or deal with failure...

            finally:
                mail.logout()
"""
# We call this to regex out the carrier and tracking number from Amazon shipping page
# Params
# uid: local user id
# mail: eMail object
"""
def ProcessTracking(uid, mail):
        trackURLPattern = "(www.amazon.com%2Fgp%2Fcss%2Fshiptrack.*packageId.{4}|www.amazon.com\\/gp\\/css\\/shiptrack.*packageId.\\S)"
        subjectOrderIDPattern = "(\\d{3}-\\d{7}-\\d{7})"
        mail.select('AmazonShipped')
        (rv, messages) = mail.search(None, '(UNSEEN)')

        if rv == 'OK':
            msgs = messages[0].split()
            for num in msgs:
                orderid=None
                for attempt in range(2):
                    try:
                        #print attempt
                        strr = []
                        typ, data = mail.fetch(num,'(RFC822.HEADER BODY.PEEK[])')
                        for response_part in data:
                             if isinstance(response_part, tuple):
                                 msg = email.message_from_string(response_part[1])
                                 for part in msg.walk():
                                     charset = part.get_content_charset()
                                     if part.get_content_type() == 'text/plain':
                                        strr.append(part.get_payload(decode=True))

                        strr = ''.join(strr)
                        strr = unicode(strr, str(charset), "ignore").encode('utf8', 'replace').strip()
                        logger.info(strr)
                        mm = re.search(subjectOrderIDPattern, strr)
                        m = re.search(trackURLPattern, strr, re.DOTALL)
                        #processList.append((num,mm.group(1),'https://' + m.group(1)))
                        s = parse('https://' + m.group(1))
                        logger.info('S()' + str(s))
                        logger.info('Smm()' + str(mm.group(1)))
                        #ids = db_session.query(OrderItem.OrderID).filter_by(PrivateNotes=mm.group(1)).first()
                        ids = db_session.query(LineItem).filter_by(
                            PrivateNotes=mm.group(1)).first()
                        token = db_session.query(eBayAccount.token).filter_by(usern=ids.order_item.eBayAccount).first().token

                        if ids is not None and token is not None:
                            orderid = ids.OrderID
                            if ids.order_item.CombinedOrder: ##This is a fix for multiple line items, All line items updated to same tracking
                                #logger.info('token: ' +  token[:10] + ' orderid: ' + orderid)
                                j = CallEbay.CompleteSaleCombined(orderid, s[0], s[1], token)
                            else:
                                j = CallEbay.CompleteSale(ids.OrderLineItemID, s[0], s[1], token)
                            if j is True:
                                mail.store(num, '+FLAGS', '\Seen')
                                #logger.info('Shipping updated|OrderLineItemID: ' + ids.OrderLineItemID + ', OrderID: ' + ids.OrderID)
                                Notify.delay(uid,'processetracking', link=ids.OrderID)
                            else:
                                raise Exception('CompleteSale call Failure')
                        else:
                            raise Exception('OrderID not found in OrderItem table' + '\nOrderID: ' + mm.group(1))

                    except Exception, e:

                        #logger.error('Error occured in ProcessTracking() - Fetching mail and parse loop|Error: ' + str(e))
                        #raise Exception ##Failed to get regex
                        continue
                    else:
                        break
                else:
                    Notify.delay(uid,'processetracking', msg='Email parse failed: ', link=orderid)
                    logger.error('Error occured in ProcessTracking() - Outer Fetching mail, skipping to next|Error: ' + str(e))
                    continue
            ###Parse the the link, return tuple of shipper and track num, call ebay complete sale, if Ack Success, mark email as read
        else:
            raise Exception('Failed to get messages')
"""
# To regex out details from an email after we ordered the item on Amazon for updates in the db.
# Params
# Mail : mail object
"""
def ProcessConfirmation(mail):
        OrderIDPattern = "#(\\d{3}-\\d{7}-\\d{7})"
        BeforeTax = "Before.Tax:.\\$(\\d*.\\d*)"
        Tax = "Estimated.Tax:.*\\$(\\d*.\\d*)"

        mail.select('AmazonOrderConfirm')
        (rv, messages) = mail.search(None, '(UNSEEN)')

        if rv == 'OK':
            msgs = messages[0].split()
            for num in msgs:
                for attempt in range(2):
                    try:
                        #print attempt
                        strr = []
                        typ, data = mail.fetch(num,'(RFC822.HEADER BODY.PEEK[])')
                        for response_part in data:
                             if isinstance(response_part, tuple):
                                 msg = email.message_from_string(response_part[1])
                                 for part in msg.walk():
                                     charset = part.get_content_charset()
                                     if part.get_content_type() == 'text/plain':
                                        strr.append(part.get_payload(decode=True))

                        strr = ''.join(strr)
                        strr = unicode(strr, str(charset), "ignore").encode('utf8', 'replace').strip()
                        logger.info(strr)
                        #orderids = re.findall(OrderIDPattern, strr)
                        triplet = {}
                        for (orderid, beforetax, tax) in re.findall('|'.join([OrderIDPattern, BeforeTax, Tax]), strr):
                            #logger.info(orderid + '---' + beforetax + '---' + tax)
                            if orderid:
                                triplet['OrderID'] = orderid
                            elif beforetax:
                                triplet['BeforeTax'] = beforetax
                            elif tax:
                                triplet['Tax'] = tax
                                logger.info(triplet)
                                #t = updateLineItem.delay(triplet['OrderID'], float(triplet['BeforeTax']), float(triplet['Tax']))
                                # if not t.get():
                                #     raise Exception('UpdateLineItem Error')
                                ####CHANGE TO CHAIN()
                                #UpdateReceiptData.delay(triplet['OrderID'])
                                #UpdateReceiptData.apply_async(args=[triplet['OrderID']], countdown=20)
                                t = chain(updateLineItem.s(triplet['OrderID'], float(triplet['BeforeTax']), float(triplet['Tax'])), UpdateReceiptData.s(triplet['OrderID'])).apply_async()

                                if len(msgs) < 10:
                                    logger.info('less than 10 messages, we will wait')
                                    while not t.ready():
                                        time.sleep(1)
                                    if not t.successful():
                                        raise Exception('Email Processing not successful')

                                triplet.clear()

                        mail.store(num, '+FLAGS', '\Seen')
                        db_session.commit()
                    except Exception, e:
                        logger.error('Error occured in ProcessConfirmation() - Fetching mail and parse loop|Error: ' + str(e))
                        #raise Exception ##Failed to get regex
                        continue
                    else:
                        break
                else:
                    #send error
                    #break
                    continue
            ###Parse the the link, return tuple of shipper and track num, call ebay complete sale, if Ack Success, mark email as read
        else:
            raise Exception('Failed to get messages')


# @celery.task
# def scrape(keys,cat,cnt):
#     scrape = AsinScraper.AsinScraper()
#     scrape.runSearchResults(keys,cat,cnt)

#### SCRAPER FUNCTIONS #####
"""
# Convert text input from frontend into a python List. We also check if the ASIN is already in the local list.
# This method also called Lister() to build the scraped items list into the database for view.
# Params
# asins: input asin list
# token: user eBay token
# id: local user id
# optDict: options selected at the frontend
"""
@celery.task(base=SqlAlchemyTask, bind=True)
def AsinsTextToList(self, asins, token, id, optDict):
    try:
        logger.info('Options :' + str(optDict))
        asins = asins.strip().split()
        asins = set(asins)
        for idx, a in enumerate(asins):
            try:
                if not optDict['ignoreact']:
                    actives = db_session.query(ActiveItem).filter_by(Asin=a).scalar()
                    if actives is not None:
                        logger.info('Already exists in active')
                    else:
                        s = ScrapedItem(Asin=a, uid=id)
                        db_session.merge(s)
                        #db_session.add(t)
                else:
                    s = ScrapedItem(Asin=a, uid=id)
                    db_session.merge(s)
                    #db_session.add(t)

            except Exception, e:
                db_session.rollback()
                logger.warning('Error occured in AsinsTextToList()|Error: ' + str(e))
                pass

        db_session.flush()
        try:
            t = Lister(self, token, id, optDict)
            return t
        except:
            raise Exception('Lister error')

    except Exception, e:
        db_session.rollback()
        logger.error('Error occured in AsinsTextToList()|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
        return {'current': 99, 'total': 100, 'status': 'Task Failed!',
                'result': 'FAILURE'}

#
# def Lister(task,token,id):
#     import time
#     try:
#         if token is None:
#             raise Exception("No user token for this user.")
#
#
#         Builder = ListingBuilder()
#         asins = db_session.query(ScrapedItem).filter_by(uid=id).filter(ScrapedItem.Listed == False).filter(ScrapedItem.Title == None).all()
#         DTemplate = db_session.query(DescriptionTemplate).get(1)
#         for idx, asin in enumerate(asins):
#             try:
#                 #time.sleep(1)
#                 t = GoiAzon.delay(asin.Asin, 'scrape')
#                 response = CallTaskWaitToObject(t)
#
#                 #time.sleep(1)
#                 ListingDict = Builder.Build(asin.Asin,token,DTemplate.Template,response)
#
#                 if ListingDict:
#                     s = ScrapedItem(Asin=asin.Asin,Title=ListingDict['Title'],Price=ListingDict['Price'], Quantity=ListingDict['Quantity'],
#                                     MPN=ListingDict['MPN'],Brand=ListingDict['Brand'],Category=ListingDict['Category'],
#                                     UPC=ListingDict['UPC'],Description=ListingDict['Description'],PicURLs=ListingDict['PicURLs'])
#                     t = db_session.merge(s)
#                     db_session.add(t)
#                     #logger.error('Title ' + ListingDict['Description'])
#
#
#                 else:
#                     raise Exception('ListingDict returns None')
#
#                 task.update_state(state='PROGRESS',
#                           meta={'current': idx, 'total': len(asins),
#                                 'status': str(asin.Asin)})
#
#             except Exception, e:
#                     logger.info('Error occured in Lister() in asin loop|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
#                     db_session.delete(asin)
#                     time.sleep(1)
#                     pass
#
#
#         db_session.commit()
#         logger.info('Lister Task ends')
#
#     except Exception, e:
#         db_session.rollback()
#         logger.error('Error occured in Lister()|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
#         return {'current': 99, 'total': 100, 'status': 'Task Failed!',
#                 'result': 'FAILURE'}
"""
# Call APIs to build a list of scraped items. Here we grab the description, pricing, etc and build a list with the chosen custom template.
# Updates the database directly
# Params
# task: the task that is generating the list (passed from AsinsTextToList())
# uid: local user id
# optDict: options selected at the front end
"""
def Lister(task,token,uid, optDict):
    import time
    try:
        if token is None:
            raise Exception("No user token for this user.")

        Builder = ListingBuilder()
        #asins = db_session.query(ScrapedItem).filter_by(uid=id).filter(ScrapedItem.Listed == False).filter(ScrapedItem.Title == None).all()
        DTemplate = db_session.query(DescriptionTemplate).get(optDict['templateid']) #Change to selection later
        asins = []
        for q in db_session.query(ScrapedItem).filter_by(uid=uid).filter(ScrapedItem.Listed == False).filter(ScrapedItem.Title == None).all():
            asins.append(q.Asin)

        idx = 0
        asinLength = len(asins)


        for i in range(0, asinLength, 10):
            chunk = asins[i:i + 10]
            #asinstr = ','.join(chunk)
            #time.sleep(1)
            t = GoiAzon.delay(chunk, 'scrape')
            response = CallTaskWaitToObject(t)
            #logger.info('ASIN!!!!!! ' + asinstr)

            for item in response.Items.Item:
                try:
                    logger.info('Working on: ' + str(item.ASIN.text))
                    title = item.ItemAttributes.Title.text
                    if not optDict['titleopt']:
                        if AbayLibs.isInTitleBlackList(uid, title):
                            logger.info('Title has blacklisted keywords')
                            s = ScrapedItem(Asin=item.ASIN.text, Title='Title is blacklisted: ' + title)
                            db_session.merge(s)
                            #db_session.add(t)
                            continue
                    logger.info('max weight: ' + str((optDict['maxweight'] * 100)))
                    logger.info('weight: ' + item.ItemAttributes.PackageDimensions.Weight.text)
                    ListingDict = Builder.Build(item.ASIN,token,DTemplate.Template,item, optDict['brandopt'], optDict['maxweight'] * 100)

                    if ListingDict[0]:
                        ListingDict = ListingDict[1]
                        s = ScrapedItem(Asin=item.ASIN.text,Title=ListingDict['Title'],Price=ListingDict['Price'], Quantity=ListingDict['Quantity'],
                                            MPN=ListingDict['MPN'],Brand=ListingDict['Brand'],Category=ListingDict['Category'],
                                            UPC=ListingDict['UPC'],Description=ListingDict['Description'],PicURLs=ListingDict['PicURLs'])
                        db_session.merge(s)
                        #db_session.add(t)
                        logger.info('ADDED... ' + str(item.ASIN))
                    else:
                        s = ScrapedItem(Asin=item.ASIN.text, Title='Error: ' + ListingDict[1])
                        db_session.merge(s)
                        #db_session.add(t)
                        logger.info('ListingDict returns None: ' + str(item.ASIN.text))
                        #continue

                    task.update_state(state='PROGRESS',
                                meta={'current': idx, 'total': asinLength,
                                        'status': item.ASIN.text})
                    idx = idx + 1

                except Exception, e:
                        logger.info('Error occured in Lister() in asin loop|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
                        #item = db_session.query(ScrapedItem).filter_by(uid=id).filter(ScrapedItem.Asin == item.ASIN.text).first()
                        #.delete(item)
                        #time.sleep(1)
                        continue

            db_session.commit()

        logger.info('Lister Task ends')
        return {'current': 100, 'total': 100, 'status': 'Task completed!',
                        'result': 'COMPLETED'}

    except Exception as e:
        db_session.rollback()
        logger.info('Error occured in Lister()|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
        return {'current': 99, 'total': 100, 'status': 'Task Failed!',
                'result': 'FAILURE'}

# @celery.task(base=SqlAlchemyTask, bind=True)
# def ScraperToCSVToEbay(self, token, id):
#     try:
#         import csv
#         csvtemplate = 'csvtemplate.csv'
#         outfilename = 'output.csv'
#         csv_file = csv.DictReader(open(os.path.join(APP_FILES, csvtemplate), 'rb+'), delimiter=',', quotechar='"')
#         output_file = csv.DictWriter(open(os.path.join(APP_STATIC, outfilename), 'wb+'), delimiter=',', fieldnames=csv_file.fieldnames)
#
#         output_file.writeheader()
#
#         asins = db_session.query(ScrapedItem).filter_by(uid=id).filter(ScrapedItem.Listed == False).all()
#
#         for line in csv_file:
#             for idx, asin in enumerate(asins):
#                 try:
#                     pics = CallEbay.picsUpload(token,asin.PicURLs.split('|')) #Make this group task
#                     PicUrls = '|'.join(pics)
#
#                     title = asin.Title
#                     if len(title) > 80:
#                         title = title[:78] + '..'
#
#                     line['*Title'] = title
#                     line['*StartPrice'] = asin.Price
#                     line['CustomLabel'] = asin.Asin
#                     line['*Description'] = asin.Description.replace('\r', ' ').replace('\n',' ').decode('unicode-escape').encode('utf8')
#                     line['*Quantity'] = asin.Quantity
#                     line['*Category'] = asin.Category
#                     line['C:MPN'] = asin.MPN
#                     line['C:Brand'] = asin.Brand
#                     line['Product:UPC'] = asin.UPC
#                     line['PicURL'] = PicUrls
#
#                     output_file.writerow(line)
#
#                     asin.Listed = True
#                     # t = db_session.merge(asin)
#                     # db_session.add(t)
#
#                     self.update_state(state='PROGRESS',
#                           meta={'current': idx, 'total': len(asins),
#                                 'status': asin.Asin})
#
#                 except Exception, e:
#                     logger.error('Error occured in ScraperToCSVToEbay()-CSV output|Error: ' + str(e))
#                     asin.Listed = False
#                     pass
#
#         db_session.commit()
#
#         #flash("Output.csv ready for download.")
#
#         #ZipCSVFile(outfilename)
#
#         return {'current': 100, 'total': 100, 'status': 'Task completed!',
#                 'result': 'COMPLETED'}
#
#     except Exception, e:
#         db_session.rollback()
#         logger.error('Error occured in ScraperToCSVToEbay()|Error: ' + str(e))
#         return {'current': 99, 'total': 100, 'status': 'Task Failed!',
#                 'result': 'FAILURE'}
#
"""
# Build a downloadable CSV list from the database. We upload this csv to eBay for listing of items
# Params
# token: eBay user token
# id: local user id
"""
@celery.task(base=SqlAlchemyTask, bind=True)
def ScraperToCSVToEbay(self, token, id):
    try:
        #from celery import group
        import csv
        csvtemplate = 'csvtemplate.csv'
        outfilename = 'output.csv'
        csv_file = csv.DictReader(open(os.path.join(APP_FILES, csvtemplate), 'rb+'), delimiter=',', quotechar='"')
        output_file = csv.DictWriter(open(os.path.join(APP_STATIC, outfilename), 'wb+'), delimiter=',', fieldnames=csv_file.fieldnames)

        output_file.writeheader()

        asins = db_session.query(ScrapedItem).filter_by(uid=id).filter(ScrapedItem.Listed == False).filter(ScrapedItem.Price != None)
        listLength = asins.count()
        asins = asins.all()
        joblist = []
        asinPicDict = {}

        for line in csv_file:
            #for idx, asin in enumerate(asins):
            for i in range(0, listLength, 10):
                chunk = asins[i:i + 10]
                try:
                    #joblist = []
                    for j in chunk:
                        joblist.append(GoiEbay.s(token, (j.Asin, j.PicURLs), 'uploadPic'))

                    job = group(joblist)
                    result = job.apply_async()

                    result = result.get()

                    #asinPicDict = {}
                    for item in result:
                        asinPicDict[item[0]] = item[1]

                    for asin in chunk:
                        try:
                            PicUrls = '|'.join(asinPicDict[asin.Asin])

                            title = asin.Title
                            if len(title) > 80:
                                title = title[:78] + '..'

                            line['*Title'] = title
                            line['*StartPrice'] = asin.Price
                            line['CustomLabel'] = asin.Asin
                            line['*Description'] = asin.Description.replace('\r', ' ').replace('\n',' ').decode('unicode-escape').encode('utf8')
                            line['*Quantity'] = asin.Quantity
                            line['*Category'] = asin.Category
                            line['C:MPN'] = asin.MPN
                            line['C:Brand'] = asin.Brand
                            line['Product:UPC'] = asin.UPC
                            line['PicURL'] = PicUrls

                            logger.info('ttttWRITING.....')
                            output_file.writerow(line)

                            #asin.Listed = True
                            # t = db_session.merge(asin)
                            # db_session.add(t)

                        except Exception, e:
                            logger.error('Error occured in ScraperToCSVToEbay()-chunk loop|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
                            #asin.Listed = False
                            continue

                    joblist[:] = []
                    asinPicDict.clear()

                    self.update_state(state='PROGRESS',
                            meta={'current': i, 'total': listLength,
                                    'status': 'In progress...'})


                except Exception, e:
                    logger.error('Error occured in ScraperToCSVToEbay()-CSV output|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
                    #asin.Listed = False
                    continue

        #db_session.commit()

        #flash("Output.csv ready for download.")

        #ZipCSVFile(outfilename)


        return {'current': 100, 'total': 100, 'status': 'Task completed!',
                'result': 'COMPLETED'}

    except Exception, e:
        #db_session.rollback()
        logger.error('Error occured in ScraperToCSVToEbay()|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
        return {'current': 99, 'total': 100, 'status': 'Task Failed!',
                'result': 'FAILURE'}



"""
# Create a zip of the csv File for download
# Param
# file_name: name of the file
"""
@celery.task(base=SqlAlchemyTask, bind=True)
def ZipCSVFile(self, file_name):
    import zipfile
    try:
        zip_path = os.path.join(APP_STATIC, 'zippedcsv.zip')
        file_path = os.path.join(APP_STATIC, file_name)

        if os.path.exists(zip_path):
            os.unlink(zip_path);

        zip_file = zipfile.ZipFile(zip_path, 'w')
        zip_file.write(file_path, file_name)
        zip_file.close()

        #PrepareToSend(zip_path)

    except Exception, e:
        db_session.rollback()
        logger.error('Error occured in ZipCSVFile()|Error: ' + str(e))


# @celery.task(base=SqlAlchemyTask, bind=True)
# @single_instance
# def PrepareToSend(zip_path):
#     try:
#
#     except Exception, e:
#         logger.error('Error occured in PrepareToSend()|Error: ' + str(e))
"""
# Called to clear the scraper view
# Param
# id : local user id
"""
@celery.task(base=SqlAlchemyTask, bind=True)
def ClearScraperList(self, id):
    try:
        sql = 'DELETE FROM scraped_item WHERE uid = {}'.format(id)
        db.engine.execute(sql)

    except Exception, e:
        db_session.rollback()
        logger.error('Error occured in ClearScraperList()|Error: ' + str(e))

"""
# Called to update an individual item in an order
# Param
# azorderid: Amazon order id
# beforetax: price before tax
# tax: calcualted tax
# returns: boolean
"""
@celery.task(base=SqlAlchemyTask, bind=True, max_retries=2, default_retry_delay=360)
def updateLineItem(self, azorderid, beforetax, tax):
    try:
        item = db_session.query(LineItem).filter_by(PrivateNotes=azorderid).first()
        if item:
            if item.order_item.CombinedOrder:
                item = db_session.query(LineItem).filter_by(PrivateNotes=azorderid).filter_by(Title='Total').first()
            #logger.info(str(azorderid)+ '-' + str(beforetax) + '-' + str(tax))
            TProfit = (float(item.Paid) - beforetax - tax)
            item.Profit = float(TProfit)
            item.PurchasePrice = beforetax
            item.Tax = tax
            #UpdateReceipt(item)
            db_session.commit()
            Notify.delay(item.order_item.uid, 'liupdated', link=item.OrderID)
            return True
        else:
            raise NoResultFound

            ##item.TotalPaid <- in the futurechange when more than 1 lineitems in an order

            #db_session.commit()

    # Retries if it cant find SoldReceipt (10 mins for the DoUrJob reoutine to update db)
    except NoResultFound as exc:
        if updateLineItem.request.retries > 1:
            raise Exception('NoResultFound for azonorderID: ' + str(azorderid))
        raise updateLineItem.retry(exc=exc)

    except Exception, e:
        db_session.rollback()
        logger.error('Error occured in updateLineItem()|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
        return False

"""
# Called to update a receipt of an order. Sometimes an order changes and we need to reflect those changes inthe database.
# Param
# empty: Boolean if receipt is populated or not
# azonorderid: Amazon order id
"""
@celery.task(base=SqlAlchemyTask, bind=True, max_retries=2, default_retry_delay=3)
def UpdateReceiptData(self,empty, azonorderid):
    try:
        if empty:
            lineitem = db_session.query(LineItem.OrderID).filter_by(PrivateNotes=azonorderid).order_by(LineItem.id.desc()).first()
            order_item = db_session.query(OrderItem).filter_by(OrderID=lineitem.OrderID).first()
            li = order_item.line_item
            item = order_item.sold_receipt
            # token = db_session.query(User.token).filter_by(id=item.uid).first().token
            token = db_session.query(eBayAccount.token).filter_by(usern=order_item.eBayAccount).first().token

            TotalPurchasePrice = 0
            TotalProfit = 0
            TotalTax = 0
            #lenn = len(li)
            lenn = 0
            if order_item.CombinedOrder:
                lineitem = db_session.query(LineItem.OrderID, LineItem.PurchasePrice, LineItem.Profit, LineItem.Tax,
                                        LineItem.Title,LineItem.Quantity).filter_by(PrivateNotes=azonorderid).filter_by(Title='Total').first()

                FVF = GoiEbay.delay(token, lineitem.OrderID, 'FVFCombined').get()

                TotalPurchasePrice = float(lineitem.PurchasePrice)
                TotalProfit = float(lineitem.Profit)
                TotalTax = float(lineitem.Tax)
                lenn = lineitem.Quantity
            else:
                FVF = GoiEbay.delay(token, item.OrderID, 'FVFLineItem').get()
                for i in li:
                    TotalPurchasePrice = float(TotalPurchasePrice) + (float(i.PurchasePrice))
                    TotalProfit = float(TotalProfit) + float(i.Profit)
                    TotalTax = float(TotalTax) + float(i.Tax)
                    lenn = lenn + 1


            item.ItemCount = lenn
            #logger.info('Test')

            if lenn > 0:
                #token = db_session.query(User.token).filter_by(id=item.uid).first().token
                #FVF = CallEbay.GetFinalValueFee(item.OrderID, token)
                if FVF:
                    item.FinalValueFee = FVF
                else:
                    item.FinalValueFee = 0

                item.TotalPurchasePrice = TotalPurchasePrice
                item.TotalTaxFee = TotalTax
                item.TotalProfit = ((TotalProfit) - float(FVF) - float(item.PaypalFee)) + float(order_item.ShippingServiceCost)
            else:
                item.TotalPurchasePrice = 0.0
                item.TotalTaxFee = 0.0
                item.TotalProfit = 0.0
                #item.FinalValueFee = 0.0

            db_session.commit()
        else:
            raise Exception('UpdateLineItem returned False')
    except Exception as e:
        db_session.rollback()
        logger.error('Error occured in UpdateReceiptData()|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))

"""
# Called delete old notifications
"""
@celery.task(base=SqlAlchemyTask)
def PurgeNotifications():
    try:
        rowsdeleted = db_session.query(Notification).filter(
            Notification.updated_on < datetime.utcnow() - timedelta(hours=72)).delete()
        db_session.commit()
        #Notify.delay(item.order_item.uid, 'notipurged', link=item.OrderID)
    except Exception as e:
        db_session.rollback()
        logger.error('Error occured in PurgeNotifications()|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))

"""
# Called to add a notification to the database which shows up in the front end.
# Params
# uid: local user id
# notitype: String type of notification
# msg : custom message
# link : custom link
"""
@celery.task(base=SqlAlchemyTask)
def Notify(uid,notitype,msg=None,link='#'):
    try:

        if notitype in 'dourjob':
            icon = 'fa fa-tasks'
        elif notitype in 'processetracking':
            icon = 'fa fa-truck'
            if not msg:
                msg = 'New tracking updated: ' + str(link)
            else:
                msg += str(link)
            link = '/killerapp/orders/?search=' + str(link)
        elif notitype in 'pricer':
            icon = 'fa fa-dollar'
            msg = 'Pricer finished running'
        elif notitype in 'reprice':
            icon = 'fa fa-dollar'
            if not msg:
                msg = 'Item repriced: ' + str(link)
            link = '/killerapp/active/?search=' + str(link)
        elif notitype in 'neworder':
            icon = 'fa fa-shopping-cart'
            msg = 'New order made'
            link = '/killerapp/orders/?search=' + str(link)
        elif notitype in 'endcount':
            icon = 'fa fa-trash'
            msg = 'Purger: ' + str(msg) + ' items ended'
        elif notitype in 'liupdated':
            icon = 'fa fa-calculator'
            msg = 'Order prices calculated: ' + str(link)
            link = '/killerapp/orders/?search=' + str(link)
        else:
            raise Exception('Notify doesnt exist: ' + notitype)

        db_session.add(Notification(uid=uid,icon=icon,msg=msg,link=link))
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error('Error occured in Notify()|Error: ' + str(e) + '\n ' + str(traceback.print_exc()))
