from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from time import sleep
from random import randint
class asinScraper:
    def __init__(self):
        self.driver = webdriver.Firefox()
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

    def runCategoryResults(self, url, num=500):
        cnt = 0
        # keyword = keyword.replace(' ', '+')
        # url = self.categoryURL[category].format(keyword)
        try:
            self.driver.get(url)
            print url
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
                    sleep(randint(1,5))
        except Exception,e:
            print str(e)


    def runSearchResults(self, url, num=500):
        cnt = 0
        # keyword = keyword.replace(' ', '+')
        # url = self.categoryURL[category].format(keyword)
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
                    print('end')
                sleep(randint(1,5))
        except Exception,e:
            print str(e)


    def checkByXpath(self,path):
        try:
            t = self.driver.find_element_by_xpath(path)
            return t
        except NoSuchElementException:

            return False


def main():
    scrape = asinScraper()
    #scrape.runSearchResults("novelty", "HomeAndKitchen", 50)
    #scrape.runCategoryResults('https://www.amazon.com/gp/search/ref=sr_nr_p_n_is-min-purchase-_0?fst=as%3Aoff&rh=n%3A1055398%2Cn%3A%211063498%2Cn%3A284507%2Cn%3A289913%2Cn%3A289940%2Cp_72%3A1248915011%2Cp_85%3A2470955011%2Cp_n_is-min-purchase-required%3A5016683011&bbn=289940&ie=UTF8&qid=1466157877&rnid=5016682011')
    scrape.runSearchResults(url='https://www.amazon.com/s/ref=sr_nr_p_n_condition-type_0?fst=as%3Aoff&rh=n%3A228013%2Cp_72%3A1248909011%2Cp_n_date_first_available_absolute%3A1249048011%2Cp_85%3A2470955011%2Cp_n_condition-type%3A6358196011&bbn=228013&ie=UTF8&qid=1467362621&rnid=6358194011')
if __name__ == "__main__":
    main()

