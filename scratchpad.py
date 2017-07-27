### For testing and learning ###
import amazonproduct
from amazonproduct.errors import InvalidParameterValue
import time
from lxml import html, etree, objectify
config = {
        'access_key': '###',
        'secret_key': '###',
        'associate_tag': '###',
        'locale': 'us'
}
aapi = amazonproduct.API(cfg=config)

#response = aapi.item_search('LawnAndGarden', Keywords='camp', Condition='New', Availability='Available', MerchantId='Amazon')
#response = aapi.item_search('HomeGarden', Keywords="household", Condition='New', Availability='Available', MerchantId='Amazon', Sort='salesrank', MinimumPrice='800', MaximumPrice='6000')

#HomeGarden
#LawnAndGarden
#Appliances


# for item in response:
#         #time.sleep(0.5)
#         print item.ASIN.text
def azonPriceGrab(response):
    try:
        asin = response.ASIN.text
        tree = response.Offers.Offer.OfferListing
        avail = response.Offers.Offer.OfferListing.AvailabilityAttributes.AvailabilityType.text
        availMinHours = response.Offers.Offer.OfferListing.AvailabilityAttributes.MinimumHours.text
        prime = response.Offers.Offer.OfferListing.IsEligibleForPrime.text
        if prime == '1' and avail == 'now':
            if int(availMinHours) > 48:
                # print 'More than 2 days to ship... Returning false'
                # print 'Min Hours:' + availMinHours
                return False
            #getattr(tree,'SalePrice',None)
            if hasattr(tree, 'SalePrice'):
                price = (response.Offers.Offer.OfferListing.SalePrice.FormattedPrice.text)
            else:
                price = (response.Offers.Offer.OfferListing.Price.FormattedPrice.text)
            return float((price)[1:])
        else:
            # print("First check no go. " + " Prime: " + prime + " Avail: " + avail)
            # print("Checking sold by Amazon...")
            #time.sleep(1)
            response = aapi.item_lookup(asin, ResponseGroup='Offers', MerchantId='Amazon', Condition='New')

            #t = GoiAzon.delay(asin, 'price0')
            #response = CallTaskWaitToObject(t)
            #logger.info(etree.tostring(response, encoding="us-ascii", method="xml"))

            tree = response.Items.Item.Offers.Offer.OfferListing
            avail = response.Items.Item.Offers.Offer.OfferListing.AvailabilityAttributes.AvailabilityType.text
            availMinHours = response.Items.Item.Offers.Offer.OfferListing.AvailabilityAttributes.MinimumHours.text
            #print 'Min Hours:' + availMinHours
            #print 'p ' + response.Items.Item.Offers.Offer.OfferListing.IsEligibleForPrime.text
            #if prime == '1' and avail == 'now':
            if avail == 'now':
                if int(availMinHours) > 48:
                    #print 'More than 2 days to ship... Returning false'
                    return False
                if hasattr(tree, 'SalePrice'):
                    price = response.Items.Item.Offers.Offer.OfferListing.SalePrice.FormattedPrice.text
                else:
                    price = response.Items.Item.Offers.Offer.OfferListing.Price.FormattedPrice.text
            return float((price)[1:])
            print("Second check no go" + " Prime: " + prime + " Avail: " + avail)
        return False
    except AttributeError as e:
        return False
    except Exception as e:
        return False


def test():

    list = 'B00F4NK7D8,B00RBNGOGS,B0058I16DO,B00CJIDH7Y,B00CWF7YBE,B000F95D0I,B000UUAAOG,B000BX4SBI,B0009J5NSQ,B0041D8PEK'
    try:
        response = aapi.item_lookup(list, ResponseGroup='OfferFull', Condition='New')
        #print (response.Items)
        #return azonPriceGrab(response.Items.Item)

        return (etree.tostring(response, encoding="us-ascii", method="xml"))
    except InvalidParameterValue as e:
        return (etree.tostring(e.xml, encoding="us-ascii", method="xml"))

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
    return ''.join(f)

fl = 13.71
t = test2(fl)
print t
#
# if getattr(tt.Items.Request, 'Errors', None):
#     for error in tt.Items.Request.Errors.Error:
#         if error.Code == 'AWS.InvalidParameterValue':
#             print str(error.Message)[:10]