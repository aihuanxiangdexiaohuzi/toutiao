### 今日头条图片爬取

import json
import re
import os
import pymongo  #数据库存储
import requests
from  hashlib  import md5    #用于校验下载文件
from urllib.parse import urlencode #
from bs4 import BeautifulSoup #
from requests.exceptions import RequestException #异常处理
from config import *         #自定义配置文件
from multiprocessing import Pool  #多线程库 开启貌似很卡
from json.decoder import JSONDecodeError   #json异常处理


client = pymongo.MongoClient(MONGO_URL, connect=False)
db = client[MONGO_DB]

#得到网页信息
def get_page_index(offset, keyword):
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': 1
    }
    url = 'http://www.toutiao.com/search_content/?' + urlencode(data)
    try:
        response =requests.get(url)
        if response.status_code == 200:  #判读状态码的方式确定网页读取成功
            return  response.text
    except RequestException:
        print('请求索引出错')
        return  None

#解析网页
def parse_page_index(html):
    try:
        data = json.loads(html)
        if data and 'data' in data.keys():
            for item in data.get('data'):
                yield item.get('article_url')
    except JSONDecodeError:
        pass

#得到网页细节
def get_page_detail(url):
    try:
        response =requests.get(url)
        if response.status_code == 200:
            return  response.text
    except RequestException:
        print('请求详情页出错',url)
        return  None

#解析网页细节
def parse_page_detail(html, url):
    soup = BeautifulSoup(html,'lxml')
    title = soup.select('title')[0].get_text()
    images_pattern = re.compile('var gallery = (.*?);',re.S)
    result = re.search(images_pattern, html)
    if result:
        data = json.loads(result.group(1))
        if data and 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images: download_image(image)
            return {
                'title': title,
                'url': url,
                'images': images,

            }

# 保存数据到mongodb
def save_to_mongo(result):
    if db[MONGGO_TABLE].insert(result):
        print('存储到MongoDB成功', result)
        return  True
    return  False

# 下载图片
def download_image(url):
    print('正在下载：' ,url)
    try:
        response =requests.get(url)
        if response.status_code == 200:
            save_image(response.content)
            return  response.text
    except RequestException:
        print('请求图片出错',url)
        return  None

#保存图片
def save_image(content):
    file_path = '{0}/{1}.{2}'.format(os.getcwd(), md5(content).hexdigest(),'jpg')
    if  not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(content)
            f.close()

#main方法 多线程 迭代快速抓取数据
def main(offset):
    html = get_page_index(offset,KEYWORD)
    for url in parse_page_index(html):
        html = get_page_detail(url)
        if html:
            result = parse_page_detail(html, url)
            if result: save_to_mongo(result)


if __name__ == '__main__':
    groups = [x * 20 for x in range(GROUP_START, GROUP_END + 1)]
    pool = Pool()
    pool.map(main, groups)




