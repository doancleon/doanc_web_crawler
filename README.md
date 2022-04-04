# Web Crawler
Contributors: Cleon Doan
### Background
This project takes multiple local files (CORPUS) directing to a web page and checks for hyperlink references (HREF) to later browse. 
This web crawler is capable of crawling web pages in the ics.uci.edu domain and will track and ignore broken URLs or crawler traps (definition listed below).

If a URL is valid and accessible, the crawler will download the URL and analytically track valid outlinks (valid HREF of the web pages) and the number of words (excluding 50 common stop words) existing on the webpage.

### Libraries used: 
- BeautifulSoup
- Requests
- URL.LIB
- LXML (parser)

### Description
Main must be runned with a local path to an existing CORPUS as system argument[1]. 

corpus.py code is responsible for mapping a URL to a local file name.  
frontier.py code holds a queue of URLS to be crawled. While crawling, the frontier queue will be loaded with new URLs taken from the valid HREF outlinks of a crawled web page.

crawler.py will crawl webpages from the frontier and will be responsible for extracting all HREF links from the web page to queue it into the frontier.  
After the frontier is cleared, crawler.py will calculate and return an analytical.txt file that tracks all non-crawler trap URLs, the page with the most valid outlinks, the number of downloaded URLs, the number of crawler traps and its URLs, the page with the most words, and the top 50 most common words (definition for words listed below).

### Self Definitions and Assumptions
Web pages that do not return a 200 HTTP status code are considered invalid and will not be crawled again, but is not counted as a crawler trap.  
Crawler traps are pages with long URLs, repeating directories, extra/dynamic pages, and if the redirection lasts longer than 5 redirects or 1 second.   
Low quality pages are pages with too many words (>10000) or too little unique words (<101) and are considered crawler traps.  
Words parsed from a web page are transformed with isAlpha(), has a length >3, and is not in the stopWord dictionary (in crawler.py).

### Some weaknesses
This crawler handles URls with repeating fragments or the "multiple query trap" by crawling the URL without the fragment included.
