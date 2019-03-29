import aiohttp
import asyncio
from bs4 import BeautifulSoup
from models import Cloopen_sms
import redis
import re
import random

pool = redis.ConnectionPool(host="localhost", port=6379, db=1)
redis_client = redis.Redis(connection_pool=pool)

COOKIE = "aoa9Qst4eXsqFinUsMS44o24SEV3jVe0qYMJayh6T6Dn7c2h"
HOST = "https://github.com"

LOGIN_DATA = {
    'commit': 'Sign in',
    'utf8': '✓',
    'login': 'git-username',
    'password': 'git-password'
}

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Cookie": "user_session=%s;" % COOKIE,
    "Host": "github.com",
    "If-None-Match": "W/\"56c8a202d4b8819615f27eed44965afb\"",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"
}

PATTERN_DICT = {
    "sid": r"(accountSid|Sid)",
    "token": r"(authToken|Token|accountToken)",
    "app_id": r"appId"
}

async def fetch(session, url, method="get", **kwargs):
    print("%s:%s" % (method, url))
    if method == "get":
        method = session.get
    else:
        method = session.post
    async with method(url, data=kwargs) as response:
        return await response.text()

class Page:
    def __init__(self, soup, exclude_code="Text"):
        self.content = []
        self.totalCount = soup.select("div.pagination > a:nth-last-of-type(2)")[0].text
        self.next_url = soup.select("div.pagination > a:nth-last-of-type(1)")[0].attrs.get("href")
        self.content_urls = []
        for result in soup.select("#code_search_results > div.code-list > div.code-list-item"):
            if result.select(".d-flex > span")[-1].text.strip() == exclude_code:
                continue
            content_url = result.select(".d-flex > div > a:nth-of-type(2)")[0].attrs.get("href")
            self.content_urls.append(content_url)

async def main():
    total_count = 1
    current_count = 0
    next_page_url = "/search?p=54&q=app.cloopen.com&type=Code"
    while current_count < total_count:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            html = await fetch(session, '%s%s' % (HOST, next_page_url))
            try:
                page = Page(BeautifulSoup(html))
            except Exception as e:
                print(e)
                continue
            if total_count == 1:
                total_count = int(page.totalCount)
            next_page_url = page.next_url
            for url in page.content_urls:
                await asyncio.sleep(random.randint(10, 25))
                _html = await fetch(session, "%s%s" % (HOST, url))
                _content = {}
                try:
                    for _result in BeautifulSoup(_html).find("table").find_all("tr"):
                        _text = _result.text
                        for _key, _pattern in PATTERN_DICT.items():
                            if re.search(_pattern, _text, re.IGNORECASE):
                                match = re.search(r"[a-z0-9]{32}", _text)
                                if match:
                                    _content[_key] = match.group(0)
                except Exception as e:
                    print(e)
                    continue
                if len(_content) == 3:
                    sms = Cloopen_sms(**_content)
                    try:
                        await sms.save()
                    except:
                        pass
        current_count += 1



loop = asyncio.get_event_loop()
loop.run_until_complete(main())
