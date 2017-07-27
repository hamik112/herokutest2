
""" Generate a custom template with obtained values from API calls
"""
import amazonproduct
from AbayLibs import getFinalPriceWithResponse, isInBrandBlackList
import CallEbay
from celery.utils.log import get_task_logger
from bs4 import BeautifulSoup#, NavigableString
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import traceback
logger = get_task_logger(__name__)



class ListingBuilder:
    # def __init__(self):
    #     self.config = {
    #         'access_key': '###',
    #         'secret_key': '###',
    #         'associate_tag': '###',
    #         'locale': 'us'
    #     }
    #     self.api = amazonproduct.API(cfg=self.config)

    def toRoundedFloat(self, n):
        return str(float(n)/100)

    def Build(self,asin,token,template,response, brandOpt, maxWeight):
        try:
            #response = self.api.item_lookup(asin, ResponseGroup='EditorialReview,ItemAttributes,OfferFull,Images', Condition='New')


            Title = response.ItemAttributes.Title.text
            #Title = Title.decode('unicode-escape').encode('utf8')


            ###Bullets###
            feat = ''
            try:
                for f in response.ItemAttributes.Feature:
                        feat = feat + '<li>' + f + '</li>'

                Description = response.EditorialReviews.EditorialReview.Content.text
            except:
                #raise Exception("Failed getting Description for: " + str(asin))
                return (False,"Can't get description")


            #Description = Description.decode('unicode-escape').encode('utf8')
            #feat = feat.decode('unicode-escape').encode('utf8')

            ###Description html###
            UPC = 'Does not apply'
            MPN = 'Does not apply'
            Brand = 'Does not apply'

            soup = BeautifulSoup(str(template), 'html.parser')
            TableTag = soup.find("table", { "class" : "metainfo" })
            ulTag = soup.find('ul')
            pTag = soup.find("div", { "class" : "para" })

            pTag.append(BeautifulSoup(Description.decode('utf-8', 'ignore'), 'html.parser'))
            ulTag.append(BeautifulSoup(feat.decode('utf-8', 'ignore'), 'html.parser'))

            hTag = soup.find("div", { "class" : "title" })
            hTag.append(BeautifulSoup(Title.decode('utf-8', 'ignore'), 'html.parser'))

            ###Price###
            Price = getFinalPriceWithResponse(response)
            if Price:
                Quantity = 1
            else:
                #raise Exception("Can't get price for:" + asin)
                return (False,"Can't get price")

            ###Attributes###
            ItemAttributes = response.ItemAttributes

            try:
                if getattr(ItemAttributes.PackageDimensions, 'Weight', None):
                    weight = float(ItemAttributes.PackageDimensions.Weight.text)
                    if weight >= maxWeight:
                        #raise Exception('Item is overweight... Returning None')
                        return (False,"Shipping overweight: " + str(weight/100) + " lbs")
            except:
                pass

            try:
                if ItemAttributes.Brand != 'null':
                    Brand = ItemAttributes.Brand.text
                    brandString = '<tr><td class="first">Brand</td><td class="second" style="color:#000">' + Brand + '</td></tr>'
                    TableTag.append(BeautifulSoup(brandString, 'html.parser'))
            except:
                pass

            if not brandOpt:
                if isInBrandBlackList(Brand):
                    #raise Exception('Brand is in the brand blacklist')
                    return (False,"Brand blacklisted, " + Brand)

            try:
                if ItemAttributes.ItemDimensions is not None:
                    width = ItemAttributes.ItemDimensions.Width.text
                    height = ItemAttributes.ItemDimensions.Height.text
                    length = ItemAttributes.ItemDimensions.Length.text
                    dimensionString = '<tr><td class="first">Dimensions</td><td class="second" style="color:#000">' + self.toRoundedFloat(length) + ' x ' + self.toRoundedFloat(width) + ' x ' + self.toRoundedFloat(height) + ' inches.</td></tr>'
                    TableTag.append(BeautifulSoup(dimensionString, 'html.parser'))
            except:
                pass

            try:
                if getattr(ItemAttributes.ItemDimensions, 'Weight', None):
                    weight = self.toRoundedFloat(ItemAttributes.ItemDimensions.Weight.text)
                    weightString = '<tr><td class ="first">Weight</td><td class="second" style="color:#000">' + weight + ' pounds</td></tr>'
                    TableTag.append(BeautifulSoup(weightString, 'html.parser'))
            except:
                pass

            try:
                if ItemAttributes.UPC != 'null':
                    UPC = ItemAttributes.UPC.text
                    # weightString = '<tr><td class ="first">UPC</td><td class="second" style="color:#000">' + UPC + '</td></tr>'
                    # tableTag.append(BeautifulSoup(weightString, 'html.parser'))
                    UPC = UPC.decode('unicode-escape')
            except:
                pass

            try:
                if ItemAttributes.MPN != 'null':
                    MPN = ItemAttributes.MPN.text
                    quantityString = '<tr><td class="first">MPN</td><td class="second" style="color:#000">' + MPN + '</td></tr>'
                    TableTag.append(BeautifulSoup(quantityString, 'html.parser'))
                    MPN = MPN.decode('unicode-escape')
            except:
                pass
            try:
                if ItemAttributes.Color != 'null':
                    colorString = '<tr><td class="first">Color</td><td class="second" style="color:#000">' + ItemAttributes.Color.text + '</td></tr>'
                    if colorString is not 'null' or None:
                        TableTag.append(BeautifulSoup(colorString, 'html.parser'))
            except:
                pass
            try:
                if ItemAttributes.PackageQuantity != 'null':
                    quantityString = '<tr><td class="first">Package Quantity</td><td class="second" style="color:#000">' + ItemAttributes.PackageQuantity.text + '</td></tr>'
                    TableTag.append(BeautifulSoup(quantityString, 'html.parser'))
            except:
                pass

            ImageSet = []
            img = response.ImageSets.ImageSet
            for i in img:
                ImageSet.append(i.LargeImage.URL.text)

            #ImageSet = ImageSet[::-1]
            ##Quick fix for image order, first image always first now

            ImageSet.insert(0, ImageSet.pop(len(ImageSet)-1))
            PicURLs = '|'.join(ImageSet)


            CatList = CallEbay.CatList(token,str(Title).decode('unicode_escape').encode('ascii','ignore').replace('&', '')[:349])
            if CatList:
                Category = CatList[0]

            ###Conversion to 2 dec###
            Price = "%.2f" % float(Price)



            soup = str(soup).replace('\r', ' ').replace('\n',' ').decode('unicode-escape').encode('ascii','ignore').encode('utf8').encode('raw-unicode-escape')
            Brand = Brand.decode('unicode-escape').encode('utf8')[:50]
            MPN = MPN.decode('unicode-escape').encode('utf8')[:60]

            tup = {'ASIN': asin, 'Title': Title[:300], 'Price': Price, 'MPN': MPN, 'Brand': Brand, 'Category': Category,
                   'UPC': UPC, 'Quantity': Quantity, 'Description': soup, 'PicURLs': PicURLs}

            return (True,tup)


        except Exception, e:
            #raise Exception(str(e))
            logger.info('Error occured in ListingBuilder()|Error: ' + traceback.format_exc( ))
            return (False,"Exception: " + str(e))
        except ValueError as e:
            logger.info('Price ValueError')
            return (False,"Exception ValueError: " + str(e))
