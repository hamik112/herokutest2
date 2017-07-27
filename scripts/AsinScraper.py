from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from time import sleep
from random import randint
#from pyvirtualdisplay import Display
# from ..database import ScrapedItem, db

""" Test file for scraper. Not in use """
class AsinScraper:
    def __init__(self):
        self.display = Display(visible=0, size=(800, 600))
        self.display.start()
        self.driver = webdriver.PhantomJS('./phantomjs')
        self.xpaths = { 'ulist' : '//*[@id="s-results-list-atf"]',
               'stock' : "//*[@id='{0}']/div/div[4]/div[2]/div/span",
                   'next' : "//*[@id='pagnNextString']",
                   'getitby' : "get it by",
                   'itemListClass' : 's-result-item celwidget',
             }
        self.xpathsres = { 'ulist' : '//*[@id="atfResults"]',
               'stock' : "//*[@id='{0}']/div/div[4]/div[2]/div/span",
                   'next' : "//*[@id='pagnNextString']",
                   'getitby' : "get it by",
                   'itemListClass' : 's-result-item celwidget',
             }
        self.xpathNum = 0

        self.categoryURL = { 'HomeAndKitchen' : "https://www.amazon.com/gp/search/ref=sr_nr_p_36_5?rnid="
                                                "386465011&keywords={0}&rh=n%3A1055398%2Cp_6%"
                                                "3AATVPDKIKX0DER%2Cp_85%3A2470955011%2Cp_72%"
                                                "3A1248915011%2Ck%3Afun%2Cp_n_is-min-purchase-required%"
                                                "3A5016683011&qid=1465633637&low-price=&high-price=100&x=0&y=0" }

        self.list = []

    def runCategoryResults(self, keyword,category, num = 1000):
        cnt = 0
        keyword = keyword.replace(' ', '+')
        url = self.categoryURL[category].format(keyword)
        try:
            while 1:
                    t = self.driver.find_elements_by_xpath('//*[@id="atfResults"]/ul/li')
                    for child in t:
                        try:
                            t = child.get_attribute('id')
                            #print t
                            stockString = child.find_element_by_xpath(self.xpaths['stock'].format(t)).text
                            #print stockString
                            if self.xpaths['getitby'] in stockString.lower()[:9]:
                                tt = child.get_attribute('data-asin')
                                print tt
                                self.list.append(tt)
                                cnt = cnt + 1
                                if cnt + 1 > num:
                                    exit()

                        except NoSuchElementException:
                            pass

                    next  = self.driver.find_element_by_xpath(self.xpaths['next'])
                    if next is not None:
                        next.click()
                    else:
                        break
                    sleep(randint(10,30))
        except Exception,e:
            print str(e)


    def runSearchResults(self,keyword,category, num=1000):
        cnt = 0
        keyword = keyword.replace(' ', '+')
        url = self.categoryURL[category].format(keyword)
        try:
            self.driver.get(url)
            print url

            while 1:
                t = self.driver.find_elements_by_xpath('//*[@id="s-results-list-atf"]/li')
                for child in t:
                    try:
                        t = child.get_attribute('id')
                        #print t
                        stockString = child.find_element_by_xpath(self.xpathsres['stock'].format(t)).text
                        #print stockString
                        if self.xpaths['getitby'] in stockString.lower()[:9]:
                            tt = child.get_attribute('data-asin')
                            print tt
                            #self.list.append(tt)
                            # t = ScrapedItem(Asin=str(tt))
                            # db.session.add(t)
                            # db.session.commit()
                            cnt = cnt + 1
                            if cnt + 1 > num:
                                exit()

                    except NoSuchElementException:
                        pass

                next  = self.driver.find_element_by_xpath(self.xpaths['next'])
                if next is not None:
                    next.click()
                else:
                    break
                    print('end')
                sleep(randint(10,40))
        except Exception,e:
            print str(e)


    def checkByXpath(self,path):
        try:
            t = self.driver.find_element_by_xpath(path)
            return t
        except NoSuchElementException:

            return False

def main():
    scrape = AsinScraper()
    scrape.runSearchResults("fun times", "HomeAndKitchen", 2)

if __name__ == "__main__":
    main()

