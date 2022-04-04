import logging
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import defaultdict
import requests
import urllib.robotparser

logger = logging.getLogger(__name__)
stopWords = ['a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', "aren't", 'as',
             'at',
             'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
             "can't", 'cannot', 'could', "couldn't", 'did', "didn't", 'do', 'does', "doesn't", 'doing', "don't", 'down',
             'during',
             'each', 'few', 'for', 'from', 'further', 'had', "hadn't", 'has', "hasn't", 'have', "haven't", 'having',
             'he', "he'd",
             "he'll", "he's", 'her', 'here', "here's", 'hers', 'herself', 'him', 'himself', 'his', 'how', "how's", 'i',
             "i'd",
             "i'll", "i'm", "i've", 'if', 'in', 'into', 'is', "isn't", 'it', "it's", 'its', 'itself', "let's", 'me',
             'more', 'most', "mustn't", 'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or',
             'other', 'ought', 'our', 'ours',
             'ourselves', 'out', 'over', 'own', 'same', "shan't", 'she', "she'd", "she'll", "she's", 'should',
             "shouldn't", 'so', 'some', 'such',
             'than', 'that', "that's", 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', "there's",
             'these', 'they', "they'd",
             "they'll", "they're", "they've", 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very',
             'was', "wasn't", 'we',
             "we'd", "we'll", "we're", "we've", 'were', "weren't", 'what', "what's", 'when', "when's", 'where',
             "where's", 'which', 'while',
             'who', "who's", 'whom', 'why', "why's", 'with', "won't", 'would', "wouldn't", 'you', "you'd", "you'll",
             "you're", "you've", 'your', 'yours', 'yourself', 'yourselves']

class Crawler:
    """
    This class is responsible for scraping urls from the next available link in frontier and adding the scraped links to
    the frontier
    """

    def __init__(self, frontier, corpus):
        self.frontier = frontier
        self.corpus = corpus
        self.subDomainURLS = defaultdict(set)

        #contains all urls that that are not traps
        self.uniqueURLS = set()
        self.crawlerTraps = set()

        #contains all urls that are valid only
        self.validLinksList = set()
        self.mostOutputLinks = 0
        self.pageOutputLinks = ""

    def start_crawling(self):
        """
        This method starts the crawling process which is scraping urls from the next available link in frontier and adding
        the scraped links to the frontier
        """
        while self.frontier.has_next_url():
            numValidLinks = 0
            subDomainUniqueURLS = set()
            url = self.frontier.get_next_url()
            logger.info("Fetching URL %s ... Fetched: %s, Queue size: %s", url, self.frontier.fetched, len(self.frontier))
            url_data = self.corpus.fetch_url(url)
            subDomainFrontier = urlparse(url_data["url"]).netloc
            if subDomainFrontier.find("www.") != -1:
                subDomainFrontier = subDomainFrontier.split("www.")[1]

            #iterates through all href found in a webpage, checks to see if valid to load into frontier
            for next_link in self.extract_next_links(url_data):
                subDomainNextLink = urlparse(next_link).netloc
                if subDomainNextLink.find("www.") != -1:
                    subDomainNextLink = subDomainNextLink.split("www.")[1]
                if subDomainNextLink == subDomainFrontier:
                    subDomainUniqueURLS.add(next_link)
                if self.is_valid(next_link):
                    numValidLinks+=1
                    if self.corpus.get_file_name(next_link) is not None:
                        self.frontier.add_url(next_link)

            #keeps track of unique subdomains
            for sdu in subDomainUniqueURLS:
                self.subDomainURLS[subDomainFrontier].add(sdu)

            #tracks pages with most valid href
            if numValidLinks > self.mostOutputLinks:
                self.mostOutputLinks = numValidLinks
                self.pageOutputLinks = url_data["url"]

            #deliverables/analyticals once frontier is empty
            if not (self.frontier.has_next_url()):
                cwordList = self.calculate_words(self.validLinksList)
                file = open("analytics.txt","w")
                file.write("###############################################\n")
                file.write("1. Counts all URLS whether valid/invalid/crawlerTrap\n")
                for k,v in self.subDomainURLS.items():
                    file.write(str(k) + ' has ' + str(len(v))+" different URLS")
                file.write("\n###############################################\n")
                file.write("2.\n")
                file.write(str(self.pageOutputLinks) + " is the page with the most valid output links of "+ str(self.mostOutputLinks)+"\n")
                file.write("\n###############################################\n")
                file.write("3.\n")
                file.write(str(self.frontier.fetched)+ " is the number of downloaded URLS")
                file.write("\nList of crawlerTraps URL: " + str(len(self.crawlerTraps)))
                for crawlerURL in self.crawlerTraps:
                    file.write("\n"+str(crawlerURL))
                file.write("\n###############################################\n")
                file.write("4.\n")
                file.write(str(cwordList[0])+" is the page with the most words.")
                file.write("\n###############################################\n")
                file.write("5. Words are assumed to be at least 3 letters and is true to isAlpha()\n")
                file.write("List of the 50 most common words:\n")
                sortedTokens = sorted(sorted(cwordList[1].items()), key=lambda item: item[1], reverse=True)
                mostCount = 0
                for tf in sortedTokens:
                    if mostCount == 50:
                        break
                    mostCount+=1
                    file.write(str(tf)+"\n")
                file.close()

    def extract_next_links(self, url_data):
        """
        The url_data coming from the fetch_url method will be given as a parameter to this method. url_data contains the
        fetched url, the url content in binary format, and the size of the content in bytes. This method should return a
        list of urls in their absolute form (some links in the content are relative and needs to be converted to the
        absolute form). Validation of links is done later via is_valid method. It is not required to remove duplicates
        that have already been fetched. The frontier takes care of that.

        Suggested library: lxml
        """
        #used below to implement beautifulsoup
        '''https://www.crummy.com/software/BeautifulSoup/bs4/doc/
           https://docs.python.org/3/library/urllib.parse.html
        '''
        outputLinks = []
        #turn document into data structure
        if url_data["content"] != None:
            soup = BeautifulSoup(url_data["content"], "lxml")
            #anchor tags
            for link in soup.find_all('a'):
                #get the hypertext ref in link
                #and combine with the base url to get absolute form
                href = link.get('href')
                absoluteURL = urljoin(url_data['url'], href)
                outputLinks.append(absoluteURL)
        return outputLinks

    def is_valid(self, url):
        """
        Function returns True or False based on whether the url has to be fetched or not. This is a great place to
        filter out crawler traps. Duplicated urls will be taken care of by frontier. You don't need to check for duplication
        in this method
        """
        #scheme://netloc/path;parameters?query#fragment"
        #parsed = (scheme="scheme", netloc = "netloc")
        parsed = urlparse(url)

        ### if not in uci.edu domain or error with no netloc
        try:
            if ("uci.edu" not in parsed.netloc):
                return False

        except:
            return False
        try:
            if ".ics.uci.edu" not in parsed.hostname or re.match(".*\.(css|js|bmp|gif|jpe?g|ico" + "|png|tiff?|mid|mp2|mp3|mp4" \
                             + "|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf" \
                             + "|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|epub|dll|cnf|tgz|sha1" \
                             + "|thmx|mso|arff|rtf|jar|csv" \
                             + "|rm|smil|wmv|swf|wma|zip|rar|gz|pdf)$", parsed.path.lower()):
                return False


            if parsed.scheme not in set(["http", "https"]):
                print("not in set http trap?")
                self.crawlerTraps.add(url)
                return False

            ### check for traps, request.head is from sites below
            '''
            https://www.kite.com/python/answers/how-to-check-if-a-string-is-a-url-in-python
            https://www.kite.com/python/docs/requests.get
            https://docs.python-requests.org/en/latest/user/quickstart/
            https://docs.python.org/3/library/urllib.robotparser.html
            https://docs.python-requests.org/en/latest/user/advanced/#body-content-workflow
            https://www.w3schools.com/python/ref_requests_head.asp
            '''
            ###fragment trap and multiple query trap
            if "#" in parsed.geturl() or "&" in parsed.geturl():
                self.crawlerTraps.add(url)
                return False

            #check for status codes
            if (self.cant_crawl(url)):
                return False

            ### regex is from site below
            '''
            https://support.archive-it.org/hc/en-us/articles/208332963-Modify-your-crawl-scope-with-a-Regular-Expression#InvalidURLs
            '''
            ###long messy strings
            if re.match(r"^.*\/[^\/]{300,}$", parsed.geturl()):
                # print("trap long text detected")
                self.crawlerTraps.add(url)
                return False
            ### repeating directories
            if re.match(r"^.*?(\/.+?\/).*?\1.*$|^.*?\/(.+?\/)\2.*$", parsed.path):
                # print("trap repeating direct")
                self.crawlerTraps.add(url)
                return False
            ### extra directories / dynamic  but must 3 in a row
            if re.match(r"^.*(\/misc|\/sites|\/all|\/themes|\/modules|\/profiles|\/css|\/field|\/node|\/theme){3}.*",
                        parsed.path):
                # print("extra directories")
                self.crawlerTraps.add(url)
                return False

            ### keep track of subdomain and its pages
            # if url not in trap, add to uniqueURL + cantcrawl wont request head again
            if url not in self.crawlerTraps:
                self.uniqueURLS.add(url)
            #print(url, len(self.uniqueURLS), len(self.crawlerTraps),len(self.validLinksList))
            return True
        except TypeError:
            print("TypeError for ", parsed)
            self.crawlerTraps.add(url)
            return False
        except:
            print("non-type error exception")
            self.crawlerTraps.add(url)
            return False

    def cant_crawl(self, url):
        try:
            #doesnt crawl traps
            if (url in self.crawlerTraps):
                return True
            else:
                #do not need to request get again if already requested before
                if url in self.uniqueURLS:
                    return False
                #check if site returns error
                #head ignores the body
                #chose 1s timeout because frontierqueue+uniqueURLS was unchanged from 1s to 1.5s
                #infinite redirect crawler trap
                #max 5 redirect links is from Google
                try:
                    checkRedirects = requests.Session()
                    checkRedirects.max_redirects = 5
                    response = checkRedirects.get(url,timeout =1, allow_redirects = True,stream=True)
                except:
                    #print("max redirects reached")
                    self.crawlerTraps.add(url)
                    return True
                if response.status_code != 200:
                    raise Exception
                response.raise_for_status()
                #checks if lowquality, if is, not valid
                #but also not considered crawlerTrap
                #if there are at least 101 *words
                #*isAlpha() and at least 3 letters and is not a stopWord and unique
                numQualityWords = self.lowQualityCheck(response)
                #print(numQualityWords)
                #too many words in url link, considered trap
                if numQualityWords == -1:
                    self.crawlerTraps.add(url)
                    raise Exception
                if numQualityWords<=100:
                    raise Exception
                self.validLinksList.add(url)
                return False

        except:
            # site cannot be reached
            if url not in self.crawlerTraps:
                self.uniqueURLS.add(url)
            return True

    def calculate_words(self, allFetched):
        #https://www.geeksforgeeks.org/beautifulsoup-scraping-paragraphs-from-html/ + beautifulsoup documentation
        global stopWords
        wordsLongestPage = 0
        longest_page = ""
        commonWords = defaultdict(int)
        for url in allFetched:
            getURL = requests.get(url)
            lxmlParse = BeautifulSoup(getURL.content, 'lxml')
            tokenList = []
            for tag in lxmlParse.find_all("p"):
                tokenList += (t.lower() for t in re.split(r'[^a-zA-Z]', tag.get_text()) if t != '' and len(t)>=3 and t not in stopWords)

            if len(tokenList)> wordsLongestPage:
                wordsLongestPage = len(tokenList)
                longest_page = url
            for word in tokenList:
                if word not in stopWords:
                    commonWords[word]+=1
        return [longest_page,commonWords]

    def lowQualityCheck(self,response):
        lxmlParse = BeautifulSoup(response.content, 'lxml')
        tokenListUnique = []
        tooMany = []
        global stopWords
        for tag in lxmlParse.find_all("p"):
            if len(tooMany)>10000:
                return -1
            tooMany += (t.lower() for t in re.split(r'[^a-zA-Z]', tag.get_text()) if t != '')
            tokenListUnique += (t.lower() for t in re.split(r'[^a-zA-Z]', tag.get_text()) if t != '' and len(t) >= 3
                                and t not in tokenListUnique )
        return len(tokenListUnique)