from ebaysdk.trading import Connection as Trading
from celery.utils.log import get_task_logger
from PIL import Image, ImageDraw, ImageFont
import urllib, cStringIO, io, traceback
#import os, io
# import config
import logging
# (appid, certid, devid, token) = config.init_options()
logger = get_task_logger(__name__)
logger.setLevel(logging.DEBUG)
import datetime

""" Custom Methods to call eBay API. Amazon APIs are called by a library """

def GetActiveItems(token, x):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)

        include = {
            "ActiveList": {
                "Include": "true",
                "Pagination": {
                    "PageNumber": x
                            }
                        },
            "IncludeWatchCount" : "true",

              # "RequesterCredentials": { "eBayAuthToken": token }
            }

        api.execute('GetMyeBaySelling', include)
        # activeList = api.response.reply.ActiveList.ItemArray.Item
        # for i in activeList:
        #     print i.PictureDetails.GalleryURL

        #return api.response.json()
        if api.response.reply.Ack == 'Success':
            return api.response.dom()
        else:
            return False

    except Exception, e:
        logger.error('Error occured in GetActiveItems()|Error:  ' + str(e))
        pass


def GetSellerList(token, x):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)

        include = {
            "Pagination": {
                    "PageNumber": x,
                    "EntriesPerPage": 200
                            },
            "GranularityLevel": 'Coarse',
            #"UserID": "liquid-audio",
            "AdminEndedItemsOnly": True,
            "StartTimeFrom" : datetime.datetime.utcnow() - datetime.timedelta(days=30),
            "StartTimeTo" : datetime.datetime.utcnow(),
            "IncludeWatchCount" : "true",

            }

        api.execute('GetSellerList', include)
        # activeList = api.response.reply.ActiveList.ItemArray.Item
        # for i in activeList:
        #     print i.PictureDetails.GalleryURL

        return api.response.json()

    except Exception, e:
        logger.error('Error occured in GetActiveItems()|Error:  ' + str(e))
        return str(e)
        pass

def GetSellerEvents(token,mins):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)
        currentdt = datetime.datetime.utcnow()
        include = {
            "DetailLevel": "ReturnAll",
            "ModTimeFrom ": currentdt - datetime.timedelta(minutes=mins),
            "IncludeWatchCount": True
            }

        api.execute('GetSellerEvents', include)
        # activeList = api.response.reply.ActiveList.ItemArray.Item
        # for i in activeList:
        #     print i.PictureDetails.GalleryURL

        if api.response.reply.Ack == 'Success':
            return api.response.dom()
        else:
            return False

    except Exception, e:
        #logger.error('Error occured in GetActiveItems()|Error:  ' + str(e))
        #return str(e)
        pass

def GetSoldItems(token,x ):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)

        include = {
          "SoldList": { "Include": "true",
                        "IncludeNotes" : "true" ,
                        #"Sort" : "starttimedescending",
                    "Pagination": {
                    "PageNumber": x
                            },
                    "DurationInDays": 30
                     },

              # "RequesterCredentials": { "eBayAuthToken": token }
            }

        api.execute('GetMyeBaySelling', include)

        # soldList = api.response.reply.SoldList.OrderTransactionArray.OrderTransaction
        # for i in soldList:
        #     print i.Transaction.TotalPrice

        return api.response
    except Exception, e:
        logger.error('Error occured in GetActiveItems()|Error:  ' + str(e))
        pass


def GetOrders(token,x):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)

        include = {
         "Include": "true",
                        "IncludeNotes" : "true" ,
                        "IncludeFinalValueFee" : "true",
                        "NumberOfDays" : "30",
                        "SortingOrder" : "Ascending",
                    "Pagination": {
                    "PageNumber": x
                            },
                     }



        api.execute('GetOrders', include)

        # soldList = api.response.reply.SoldList.OrderTransactionArray.OrderTransaction
        # for i in soldList:
        #     print i.Transaction.TotalPrice

        return api.response
    except Exception, e:
        logger.error('Error occured in GetOrders()|Error:  ' + str(e))
        pass


def endFixedPrice(itemid, token):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)

        include = {
          "EndingReason" : "NotAvailable",
          "ItemID" : itemid,
            # "RequesterCredentials": { "eBayAuthToken": token }
            }

        api.execute('EndFixedPriceItem', include)

        # soldList = api.response.reply.SoldList.OrderTransactionArray.OrderTransaction
        # for i in soldList:
        #     print i.Transaction.TotalPrice

        #return api.response.reply.Ack
        if api.response.reply.Ack == 'Success':
            return True
        else:
            return False
    except Exception, e:
        logger.error('Error occured in GetActiveItems()|Error:  ' + str(e))
        pass

def GetSessionID():
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml')

        include = {
          "RuName": "Dennis_Nguyen-DennisNg-9cec-4-evuckklo"
            }

        api.execute('GetSessionID', include)

        # soldList = api.response.reply.SoldList.OrderTransactionArray.OrderTransaction
        # for i in soldList:
        #     print i.Transaction.TotalPrice

        return api.response.reply.SessionID
    except Exception, e:
        logger.error('Error occured in GetActiveItems()|Error:  ' + str(e))
        pass

def FetchTokenRequest(sessid):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml')

        include = {
          "SessionID": sessid
            }

        api.execute('FetchToken', include)
        reply = api.response.reply
        if reply:
            tup = (reply.eBayAuthToken, reply.HardExpirationTime)
            return tup
        else:
            return None
    except Exception, e:
        logger.error('Error occured in GetActiveItems()|Error:  ' + str(e))
        pass

def CompleteSale(orderlineitemid, carrier, tracknum, token):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)

        include = {
          "OrderLineItemID": orderlineitemid,
          "Shipment": {
            "ShipmentTrackingDetails": {
              "ShipmentTrackingNumber": tracknum,
              "ShippingCarrierUsed": carrier
            }
          }
            }

        api.execute('CompleteSale', include)
        if api.response.reply.Ack == 'Success':
            return True
        else:
            return False
    except Exception, e:
        logger.error('Error occured in GetActiveItems()|Error:  ' + str(e))
        pass

def CompleteSaleCombined(orderid, carrier, tracknum, token):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)

        include = {
          "OrderID": orderid,
          "Shipment": {
            "ShipmentTrackingDetails": {
              "ShipmentTrackingNumber": tracknum,
              "ShippingCarrierUsed": carrier
            }
          }
            }

        api.execute('CompleteSale', include)
        if api.response.reply.Ack == 'Success':
            return True
        else:
            return False
    except Exception, e:
        logger.error('Error occured in GetActiveItems()|Error:  ' + str(e))
        pass

def GetFinalValueFee(orderlineitemid, token):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)

        include = {
          "IncludeFinalValueFees": True,
          "ItemTransactionIDArray": {
                "ItemTransactionID": {
                    "OrderLineItemID": orderlineitemid,
                    }
                }
            }

        api.execute('GetOrderTransactions', include)
        reply = api.response.reply

        if reply.Ack == 'Success':
            FVF = getattr(reply.OrderArray.Order.TransactionArray.Transaction, 'FinalValueFee', None)
            if FVF:
                return float(FVF.value)
            else:
                raise Exception("Couldn't find Final Value Fee")
        else:
            raise Exception("Ack Failure")
    except Exception, e:
        logger.error('Error occured in GetFinalValueFee()|Error:  ' + str(e))
        pass

def GetFinalValueFeeCombined(orderid, token):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)

        include = {
          "IncludeFinalValueFees": True,
          "OrderIDArray": {
                "OrderID": orderid,
                }
            }

        api.execute('GetOrderTransactions', include)
        reply = api.response.reply
        if reply.Ack == 'Success':
            FVF = 0
            for trans in reply.OrderArray.Order.TransactionArray.Transaction:
                FVF = FVF + float(getattr(trans.FinalValueFee, 'value', 0))

            return float(FVF)
        else:
            raise Exception("Ack Failure")
    except Exception, e:
        logger.error('Error occured in GetFinalValueFee()|Error:  ' + str(e))
        pass

def CatList(token,query):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)
        CatListString = []
        CatIDList = []
        include = {
                  "Query": query
                    }

        api.execute('GetSuggestedCategories', include)
        catArray = api.response.reply.SuggestedCategoryArray.SuggestedCategory

        for item in catArray:
            #parentCatID = item.Category.CategoryParentID
            #parentCatName = item.Category.CategoryParentName
            #catName = item.Category.CategoryName
            catID = item.Category.CategoryID

            #parentString = parentCatID + parentCatName
            #catString = str(parentString) + ' [' + catID + ', ' + catName + ']'
            #CatListString.append(catString)

            CatIDList.append(catID)

        # for i, v in enumerate(CatListString):
        #     print '[' + str(i) + ']', v
        return CatIDList

    except Exception, e:
        logger.error('Error occured in CatList()|Error:  ' + str(e))
        pass


# def picsUpload(token, picURLs, process=True):
#     try:
#         api = Trading(config_file='abay/scripts/ebay.yaml', token=token)
#
#         picURLList = []
#
#         for url in picURLs:
#             UploadSiteHostedPicturesRequest = {
#             "WarningLevel": "High",
#             "ExternalPictureURL": url,
#             "PictureSet":'Supersize',
#             "PictureName": "Item Picture"
#             }
#
#             response = api.execute('UploadSiteHostedPictures', UploadSiteHostedPicturesRequest)
#             picURLList.append(response.reply.SiteHostedPictureDetails.FullURL)
#
#         return picURLList
#
#     except Exception ,e:
#         logger.error('Error occured in picsUpload()|Error:  ' + str(e))

def picsUpload(token, picURLs, process=True, brand=None):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)

        picURLList = []
        i = 0
        for url in picURLs:
            try:
                if process:
                    img = processPic(url, brand)
                    with io.BytesIO() as fp:
                        img.save(fp, "JPEG", quality=90)
                        files = {'file': ('EbayImage', fp.getvalue())}
                        pictureData = {
                            "WarningLevel": "Low",
                            "PictureSet": 'Supersize',
                            "PictureName": "ItemPicture"
                        }

                        response = api.execute('UploadSiteHostedPictures', pictureData, files=files)
                        picURLList.append(response.reply.SiteHostedPictureDetails.FullURL)
                        img.close()
                        i += 1
                        if i >= 12:
                            break
                # UploadSiteHostedPicturesRequest = {
                # "WarningLevel": "High",
                # "ExternalPictureURL": url,
                # "PictureSet":'Supersize',
                # "PictureName": "Item Picture"
                # }

                # response = api.execute('UploadSiteHostedPictures', UploadSiteHostedPicturesRequest)
                # picURLList.append(response.reply.SiteHostedPictureDetails.FullURL)
            except Exception as e:
                logger.error('Error occured in picsUpload() inside loop|Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))
                continue

        return picURLList

    except Exception as e:
        logger.error('Error occured in picsUpload()|Error:  ' + str(e) + '\n ' + str(traceback.print_exc()))

def processPic(url,brand = None):
    file = cStringIO.StringIO(urllib.urlopen(url).read())
    img = Image.open(file)
    img_w, img_h = img.size
    newImage = Image.new('RGB', (img_w,img_h))
    #bg_w, bg_h = newImage.size
    #offset = ((bg_w - img_w) / 2, (bg_h - img_h) / 2)
    newImage.paste(img, (0,0))
    del img
    #newImage.resize((int(img_w*1.5), int(img_h*1.5)), Image.ANTIALIAS)

    if brand is not None:
        font = ImageFont.truetype("arial.ttf", 12)
        draw = ImageDraw.Draw(newImage)
        draw.text((5, newImage.size[1]- 20),'Images credited to: ' + brand + u'\N{COPYRIGHT SIGN}',(100,0,0),font=font)

    return newImage.resize((int(img_w*1.5), int(img_h*1.5)), Image.ANTIALIAS)



def rePrice(token, itemID, newPrice, quantity):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)

        Item = {
            "Item": {
                "ItemID": itemID,
                "StartPrice": newPrice,
                "Quantity": quantity
            }
        }

        api.execute('ReviseFixedPriceItem', Item)

        return api.response.reply.Ack

    except Exception as e:
        logger.error('Error occured in rePrice()|Error:  ' + str(e))

def setQuantity(token, itemID, quantity):
    try:
        api = Trading(config_file='abay/scripts/ebay.yaml', token=token)

        Item = {
            "Item": {
                "ItemID": itemID,
                "Quantity": quantity
            }
        }

        api.execute('ReviseFixedPriceItem', Item)

        return api.response.reply.Ack

    except Exception as e:
        logger.error('Error occured in rePrice()|Error:  ' + str(e))



def main():
    tt = 'AgAAAA**AQAAAA**aAAAAA**fiVLVw**nY+sHZ2PrBmdj6wVnY+sEZ2PrA2dj6wHkoahAJaBqQudj6x9nY+seQ**0icDAA**AAMAAA**396dRmMG91ia1sJRg4j+bmG6jjSM7CTymxH3pj43BkRBarw8yxUKdgH9FdYC64Kf5oSH2pAiaOP3W+npn641h+duoK72chwNcTIAnjr9EgiSb5HRjXvDZLFuQCFC7MePiOpTlgaXbpWfqV+djgVcC8QE6P3MMj1Sd2c6rKBmHrdx46G4bkh80cSQrBjRhJ6LzTQp2ls1LhgFXbZ7O9B6yWhkyCIP1WtrGGB0f+xwL/a/XQb2Dm4NlGLlAC7VliQC/6YSXT9cY5h4wPJQp7KxLnv9pQozT+4UxeYYbJHF8J2YWXzPXybiEE0+XIkbuj9n5fMeu52gGD/pvqw/Ps6Tm/twwHYW7zNHBWFSVSOMC06BqFUbVgnDp2X5xFL8nJtMrz4tgd/SvyVgGP3u+Crk4hl0jwYs7YWFM6ebVhjj6fcy3zYHMzacjbzv0P8vNQgTad3lka05FMz8II09dv1wVNxC4eJWIA9crMecNRH7nU1QKJMehrsETz9V3g3HDcg6j3L69skeSkl4R/6egXbvY8qIgTD+x+GfowIoIRHHjemHtzI5j+NajJBuSJCTvKqvLoykaZwAC+drKNuqdjBEPrzKRqgjEYLa4oPigOmIYxWdc2BFUJQRbze95GhxG+QBwaSt2GHkWWmWQQgcFC4LycKJAXLoOgseIqHmASTU5murp5T2V8BjbwSNeGzG90kQOxUNjIiP4BDsU4b78LtvdkbbJDx8AZ5oKPsUunUIYmZ8zLNByWM6xdrB3Ith+A8T'
   # t = GetFinalValueFee('262456289137-1840576721016',tt)
    t = GetSellerEvents(tt,60)
    print t


if __name__ == '__main__':
    main()
