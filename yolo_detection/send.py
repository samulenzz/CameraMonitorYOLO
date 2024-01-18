import os
import urllib.parse
import urllib.request

# 第三方服务server酱推送
key = ''  # server酱的key
def sc_send(text, desp='', key='[SENDKEY]'):
    postdata = urllib.parse.urlencode({'text': text, 'desp': desp}).encode('utf-8')
    url = f'https://sctapi.ftqq.com/{key}.send'
    req = urllib.request.Request(url, data=postdata, method='POST')
    with urllib.request.urlopen(req) as response:
        result = response.read().decode('utf-8')
    return result

sc_send('检测提醒', '仅提醒6点后第一次响应', key)
