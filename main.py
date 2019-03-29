# coding=utf-8
from base64 import b64encode
from models import Cloopen_sms
import json
import datetime
import logging, hashlib
import aiohttp
import random
import asyncio

class Cloopen:
    URL = 'https://app.cloopen.com:8883/2013-12-26'

    def __init__(self, sid, token, appid, template_ids=None):
        self.sid = sid
        self.token = token
        self.appid = appid
        self.template_ids = None
        if template_ids:
            self.template_ids = json.loads(template_ids)
        self.balance = 0.0

    async def load_valid_template_ids(self):
        """加载可用短信模板"""
        resp = await self.query_sms_template('')
        if resp['statusCode'] == '000000':
            self.template_ids = [d['id'] for d in resp['TemplateSMS'] if d['status'] == '1']
            return self.template_ids

    async def send_sms(self, recvr, template_id):
        return await self._send_request("/Accounts/%s/SMS/TemplateSMS?sig=" % self.sid, {"to": recvr,
                                                                                         "appId": self.appid,
                                                                                         "templateId": template_id,
                                                                                         "datas": [
                                                                                             "%s" % random.randint(
                                                                                                 1000, 9999),
                                                                                             "3"]}, method="post")

    async def query_sms_template(self, template_id):
        """
        查询短信模板
        :param template_id 模板Id，不带此参数查询全部可用模板
        """
        return await self._send_request('/Accounts/' + self.sid + '/SMS/QuerySMSTemplate?sig=',
                                        {'appId': self.appid, 'templateId': template_id}, method="post")

    async def query_account_info(self):
        return await self._send_request("/Accounts/" + self.sid + "/AccountInfo?sig=")

    async def _send_request(self, path, body={}, method="get"):
        # 生成sig
        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        signature = self.sid + self.token + ts
        sig = hashlib.md5(signature.encode('utf-8')).hexdigest().upper()
        path += sig
        # basic authsig
        async with aiohttp.ClientSession(headers={
            'Authorization': b64encode((self.sid + ':' + ts).encode()).strip().decode(),
            'Accept': 'application/json',
            'Content-Type': 'application/json;charset=utf-8'
        }) as session:
            if method == "get":
                method = session.get
            else:
                method = session.post
            async with method(Cloopen.URL + path, json=body) as resp:
                text = await resp.text()
                return json.loads(text)

    def __str__(self, *args, **kwargs):
        return 'Account: {sid: %s, token: %s, appid: %s, template_ids: %s, balance: %.2f}' % \
               (self.sid, self.token, self.appid, str(self.template_ids), self.balance)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.sid == other.sid
        return False

    def __hash__(self, *args, **kwargs):
        return hash(self.sid)


# def search_all(keyword, max_page=10, greenlet_count=3):
#     """
#     通过协程并发搜索
#     :param max_page 最大页数
#     :param greenlet_count 协程数量
#     """
#     paging = client.search_code(keyword)
#     total_page = min(max_page, paging.totalCount / 20)
#     tasks = queue.Queue()
#     for i in range(1, total_page + 1):
#         tasks.put(i)
#     accounts = set()
#
#     def _search():
#         while not tasks.empty():
#             try:
#                 page_no = tasks.get()
#                 logging.info('正在搜索第%d页' % page_no)
#                 contents = map(lambda x: x.decoded_content.decode('utf-8'), paging.get_page(page_no))
#                 accounts.update({Cloopen(*p) for p in map(extract, contents) if p})
#             except Exception as err:
#                 logging.error(err)
#                 break
#
#     gevent.joinall([gevent.spawn(_search) for _ in range(greenlet_count)])
#     return accounts
#
#
# def extract(content):
#     """
#     从搜索结果中抽取字段
#     """
#
#     # 提取主要字段
#     def search_field(keyword_and_pattern):
#         keyword, pattern = keyword_and_pattern
#         for line in content.split('\n'):
#             if re.search(keyword, line, re.IGNORECASE):
#                 match = re.search(pattern, line)
#                 if match:
#                     return match.group(0)
#
#     account_sid, account_token, appid = map(search_field, [('sid', '[a-z0-9]{32}'),
#                                                            ('token', '[a-z0-9]{32}'),
#                                                            ('app.?id', '[a-z0-9]{32}')])
#     if all([account_sid, account_token, appid]):
#         return account_sid, account_token, appid



# def run(account, recvr):
#     while True:
#         resp = account.send_sms(recvr, random.choice(account.template_ids))
#         if resp['statusCode'] == '000000':
#             global sent_count
#             sent_count += 1
#             # cloopen规定同一个手机号发送间隔为30s
#             gevent.sleep(30)
#         else:
#             logging.error('协程: [' + hex(id(gevent.getcurrent())) + "]发送消息失败: " + resp['statusMsg'])
#             break


async def collect_accounts():
    for cloopen_sms in (await Cloopen_sms.filter(is_actived=1)):
        if cloopen_sms.template_ids:
            continue
        account = Cloopen(sid=cloopen_sms.sid, token=cloopen_sms.token, appid=cloopen_sms.app_id,
                          template_ids=cloopen_sms.template_ids)
        # info = await account.query_account_info()
        info = {
            'statusCode': '000000'
        }
        try:
            if info['statusCode'] == '000000':
                balance = 1
                # balance = float(info['Account']['balance'])
                if balance > 0:
                    account.balance = balance
                    template_ids = await account.load_valid_template_ids()
                    if template_ids:
                        cloopen_sms.template_ids = json.dumps(template_ids)
                    else:
                        cloopen_sms.is_actived = 0
                else:
                    cloopen_sms.is_actived = 0
                await cloopen_sms.save()
                print("get template_ids", template_ids)
        except Exception as e:
            print(e)
        await asyncio.sleep(30)

PAGE_SIZE = 10


async def get_send_sms_group():
    datas = await Cloopen_sms.filter(is_actived=1)
    return list(filter(lambda data: data.template_ids is not None, datas))


async def send_sms(revcr: str):
    datas = await Cloopen_sms.filter(is_actived=1)
    while len(datas) > 0:
        data = random.choice(datas)
        account = Cloopen(sid=data.sid, token=data.token, appid=data.app_id, template_ids=data.template_ids)
        resp = await account.send_sms(revcr, random.choice(account.template_ids))
        if resp["statusCode"] != "000000":
            data.is_actived = 0
            await data.save()
            datas.remove(data)
        else:
            print(resp)
        await asyncio.sleep(60 ** 2)

    # while True:
    #     resp = await account.send_sms(revcr, random.choice(account.template_ids))
    #     if resp["statusCode"] != "000000":
    #         cloopen_sms.is_actived = 0
    #         await cloopen_sms.save()
    #     else:
    #         print(resp)
    #     await asyncio.sleep(60 ** 60)
    # print(resp)

    # while True:
    #     if size == 0:
    #         datas = await Cloopen_sms.filter(is_actived=1)
    #         accounts = filter(lambda data: data.template_ids is not None, datas[page_idx: min(page_idx + PAGE_SIZE, len(page_idx))])
    #         size = len(accounts)
    #     else:
    #
    #         size -= 1
    #         for cloopen_sms in accounts:
    #             if not cloopen_sms.template_ids:
    #                 continue
    #             account = Cloopen(sid=cloopen_sms.sid, token=cloopen_sms.token, appid=cloopen_sms.app_id,
    #                               template_ids=cloopen_sms.template_ids)
phone_num = ""
loop = asyncio.get_event_loop()
loop.run_until_complete(send_sms(phone_num))
# loop.run_until_complete(collect_accounts())
# accounts = loop.run_until_complete(get_send_sms_group())
# loop.run_until_complete(asyncio.wait([send_sms(accounts[__], phone_num) for __ in range(0, len(accounts))]))
