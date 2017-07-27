import datetime
import compat
#import time

from abay import BlackList, db_session

PaidValues = ['PaidWithPayPal','MarkedAsPaid','Paid','PaidCOD','PaidWithEscrow','PaidWithPaisaPay','PaidWithPaisaPayEscrow']
NotPaidValues = ['Refunded','EscrowPaymentCancelled','NotPaid','PaisaPayNotPaid','BuyerHasNotCompletedCheckout']
PendingPaid = ['PaymentPending','PaymentPendingWithEscrow','PaymentPendingWithPaisaPay', 'PaymentPendingWithPaisaPayEscrow', 'PaymentPendingWithPayPal']


#NotiStrings = ['task', 'sales made', 'orders marked ship', 'orders purchased', 'price update failed']


# -*- coding: utf-8 -*-

# Copyright (c) 2014, Brandon Nielsen
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license.  See the LICENSE file for details.
""" Modified for business logic """

class compat():
    import sys

    PY2 = sys.version_info[0] == 2

    if PY2:
        range = xrange
    else:
        range = range

def parse_duration(durstring):
    if durstring[0] != 'P':
        raise ValueError('String is not a valid ISO8601 duration.')

        #durationstr can be of the form PnYnMnDTnHnMnS or PnW

    #Make sure only the lowest order element has decimal precision
    if durstring.count('.') > 1:
        raise ValueError('String is not a valid ISO8601 duration.')
    elif durstring.count('.') == 1:
        #There should only ever be 1 letter after a decimal if there is more
        #then one, the string is invalid
        lettercount = 0;

        for character in durstring.split('.')[1]:
            if character.isalpha() == True:
                lettercount += 1

            if lettercount > 1:
                raise ValueError('String is not a valid ISO8601 duration.')

    #Parse the elements of the duration
    if durstring.find('T') == -1:
        if durstring.find('Y') != -1:
            years = _parse_duration_element(durstring, 'Y')
        else:
            years = 0

        if durstring.find('M') != -1:
            months = _parse_duration_element(durstring, 'M')
        else:
            months = 0

        if durstring.find('W') != -1:
            weeks = _parse_duration_element(durstring, 'W')
        else:
            weeks = 0

        if durstring.find('D') != -1:
            days = _parse_duration_element(durstring, 'D')
        else:
            days = 0

        #No hours, minutes or seconds
        hours = 0
        minutes = 0
        seconds = 0
    else:
        firsthalf = durstring[:durstring.find('T')]
        secondhalf = durstring[durstring.find('T'):]

        if  firsthalf.find('Y') != -1:
            years = _parse_duration_element(firsthalf, 'Y')
        else:
            years = 0

        if firsthalf.find('M') != -1:
            months = _parse_duration_element(firsthalf, 'M')
        else:
            months = 0

        if durstring.find('W') != -1:
            weeks = _parse_duration_element(durstring, 'W')
        else:
            weeks = 0

        if firsthalf.find('D') != -1:
            days = _parse_duration_element(firsthalf, 'D')
        else:
            days = 0

        if secondhalf.find('H') != -1:
            hours = _parse_duration_element(secondhalf, 'H')
        else:
            hours = 0

        if secondhalf.find('M') != -1:
            minutes = _parse_duration_element(secondhalf, 'M')
        else:
            minutes = 0

        if secondhalf.find('S') != -1:
            seconds = _parse_duration_element(secondhalf, 'S')
        else:
            seconds = 0

        #Note that weeks can be handled without conversion to days
        totaldays = years * 365 + months * 30 + days

        return datetime.datetime.today() + datetime.timedelta(weeks=weeks, days=totaldays, hours=hours, minutes=minutes, seconds=seconds)

def _parse_duration_element(durationstr, elementstr):
    #Extracts the specified portion of a duration, for instance, given:
    #durationstr = 'T4H5M6.1234S'
    #elementstr = 'H'
    #
    #returns 4
    #
    #Note that the string must start with a character, so its assumed the
    #full duration string would be split at the 'T'

    durationstartindex = 0
    durationendindex = durationstr.find(elementstr)

    for characterindex in compat.range(durationendindex - 1, 0, -1):
        if durationstr[characterindex].isalpha() == True:
            durationstartindex = characterindex
            break

    durationstartindex += 1

    if ',' in durationstr:
        #Replace the comma with a 'full-stop'
        durationstr = durationstr.replace(',', '.')

    return float(durationstr[durationstartindex:durationendindex])

def getReversePrice(Total):
    EBAY_FEE = 0.10
    PAYPAL_FEE = 0.029
    PAYPAL_FEE_30 = 0.30
    AZON_TAX = 0.005

    Total = float(Total)

    if Total < 21.84:
        PROFIT_MARGIN = 2.05
    elif Total < 30.23:
        PROFIT_MARGIN = (0.085 * Total) + 0.55
    else:
        PROFIT_MARGIN = (0.085 * Total) + 0.35


    azonTax = (Total) * (AZON_TAX)
    sellPrice = (Total + azonTax) + (PROFIT_MARGIN)

    finalSellPrice = (((sellPrice * EBAY_FEE) - ((sellPrice * PAYPAL_FEE) - PAYPAL_FEE_30)) - sellPrice)
    finalSellPrice = finalSellPrice + 0.28
    finalSellPrice = "%.2f" % finalSellPrice
    return float(finalSellPrice)


class calculateSellPrice():
    def __init__(self):
        self.EBAY_FEE = 0.10
        self.PAYPAL_FEE = 0.029
        self.PAYPAL_FEE_30 = 0.30
        self.AZON_TAX = 0.005

        self.finalPrice = 0.0

    def getCalcPrice(self,azonPrice):
        return self.calc(azonPrice)

    def calc(self, azonPrice):

        # if azonPrice < 15.00:
        #     PROFIT_MARGIN = self.PROFIT_MARGIN_10_15
        # elif azonPrice < 20.00:
        #     PROFIT_MARGIN = self.PROFIT_MARGIN_15_20
        # elif azonPrice < 25.00:
        #     PROFIT_MARGIN = self.PROFIT_MARGIN_20_25
        # elif azonPrice < 30.00:
        #     PROFIT_MARGIN = self.PROFIT_MARGIN_25_30
        # elif azonPrice < 35.00:
        #     PROFIT_MARGIN = self.PROFIT_MARGIN_30_35
        # elif azonPrice < 40.00:
        #     PROFIT_MARGIN = self.PROFIT_MARGIN_35_40
        # elif azonPrice < 45.00:
        #     PROFIT_MARGIN = self.PROFIT_MARGIN_40_45
        # elif azonPrice < 50.00:
        #     PROFIT_MARGIN = self.PROFIT_MARGIN_45_50
        # elif azonPrice < 55.00:
        #     PROFIT_MARGIN = self.PROFIT_MARGIN_50_55
        # else:
        #     PROFIT_MARGIN = self.PROFIT_MARGIN_DEFAULT
        #

        if azonPrice < 17.00:
            PROFIT_MARGIN = 2.05
        elif azonPrice < 24.00:
            PROFIT_MARGIN = (0.085 * azonPrice) + 0.55
        else:
            PROFIT_MARGIN = (0.085 * azonPrice) + 0.35

        azonTax = (azonPrice) * (self.AZON_TAX)
        sellPrice = (azonPrice + azonTax) + (PROFIT_MARGIN)

        finalSellPrice = (((sellPrice * self.EBAY_FEE) + ((sellPrice * self.PAYPAL_FEE) + self.PAYPAL_FEE_30)) + sellPrice)
        #finalSellPrice = "%.2f" % round(finalSellPrice, 0)
        #final = float(finalSellPrice) - .02
        finalSellPrice = "%.2f" % finalSellPrice
        final = str(finalSellPrice)
        self.finalPrice = final
        return self.finalPrice

def getFinalPriceWithResponse(resp):
    t = azonPriceGrab(responsee=resp)
    if t:
        z = calculateSellPrice()
        return z.getCalcPrice(t)
    else:
        return False

def azonPriceGrab(responsee=None,asin=None):
    import amazonproduct
    config = {
        'access_key': '###',
        'secret_key': '###',
        'associate_tag': '###',
        'locale': 'us'
    }
    api = amazonproduct.API(cfg=config)

    try:
        # ##Call if p is an asin
        # if isinstance(p, str):
        #     response = api.item_lookup(p, ResponseGroup='Offers', Condition='New')
        #     asin = p
        # else:
        #     response = p
        #     asin = response.Items.Item.ASIN.text
        if responsee is not None:
            response = responsee
            asin = response.ASIN.text
        elif asin is not None:
            response = api.item_lookup(asin, ResponseGroup='Offers', Condition='New')
            response = response.Items.Item
            asin = asin

        tree = response.Offers.Offer.OfferListing
        avail = response.Offers.Offer.OfferListing.AvailabilityAttributes.AvailabilityType.text
        availMinHours = response.Offers.Offer.OfferListing.AvailabilityAttributes.MinimumHours.text
        prime = response.Offers.Offer.OfferListing.IsEligibleForPrime.text
        if prime == '1' and avail == 'now':
            if int(availMinHours) > 48:
                # print 'More than 2 days to ship... Returning false'
                # print 'Min Hours:' + availMinHours
                return False
            price = getattr(tree, 'SalePrice', None)
            if price is not None:
                price = (response.Offers.Offer.OfferListing.SalePrice.FormattedPrice.text)
            else:
                price = (response.Offers.Offer.OfferListing.Price.FormattedPrice.text)
            price = (price)[1:]
            return float(price)
        else:
            # print("First check no go. " + " Prime: " + prime + " Avail: " + avail)
            # print("Checking sold by Amazon...")
            #time.sleep(1)
            response = api.item_lookup(asin, ResponseGroup='Offers', MerchantId='Amazon', Condition='New')
            tree = response.Items.Item.Offers.Offer.OfferListing
            avail = response.Items.Item.Offers.Offer.OfferListing.AvailabilityAttributes.AvailabilityType.text
            availMinHours = response.Items.Item.Offers.Offer.OfferListing.AvailabilityAttributes.MinimumHours.text
            #print 'Min Hours:' + availMinHours
            #prime = response.Items.Item.Offers.Offer.OfferListing.IsEligibleForPrime.text
            #if prime == '1' and avail == 'now':
            if avail == 'now':
                if int(availMinHours) > 48:
                    #print 'More than 2 days to ship... Returning false'
                    return False

                price = getattr(tree, 'SalePrice', None)
                if price is not None:
                    price = response.Items.Item.Offers.Offer.OfferListing.SalePrice.FormattedPrice.text
                else:
                    price = response.Items.Item.Offers.Offer.OfferListing.Price.FormattedPrice.text
                price = (price)[1:]
                return float(price)
            #print("Second check no go" + " Prime: " + prime + " Avail: " + avail)

        #return runAzonScraper(productURL)

        #print("Can't find any price... Setting price and quant to 0")
        #setStockQuant(opts,ebayProductID,0)
        return False
    except AttributeError as e:
        #return runAzonScraper(productURL)
        #print("Can't find price for this item...")
        #print("Setting price to 300 and quant to 0")
        #setStockQuant(opts,ebayProductID,0)
        return False


def isInBrandBlackList(brand):
    #fname = 'files/brandblacklist.txt'
    brand=brand.lower()
    bl = db_session.query(BlackList.List).filter_by(ListName='brand').first()
    list = bl.List.splitlines()
    for item in list:
        if all(word in brand.split() for word in item.split()):
            return True

def isInTitleBlackList(uid,brand):
    brand=brand.lower()
    bl = db_session.query(BlackList.List).filter_by(uid=uid).filter_by(ListName='title').first()
    list = bl.List.splitlines()
    for item in list:
        if all(word in brand.split() for word in item.split()):
            return True

# if __name__ == '__main__':
#     t = calculateSellPrice()
#     price = 15
#     finalp = t.getCalcPrice(price)
#     revp = getReversePrice(price)
#     print 'In' + finalp
#     print 're' + revp