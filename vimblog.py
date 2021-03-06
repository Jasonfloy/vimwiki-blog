#!/usr/bin/env python
# -*- coding: utf-8 -*-
import tornado.ioloop
import tornado.web
import json
import time
from search_vimwiki import SearchWiki

from os.path import expanduser
import tornado_bz
import sys
import public_bz
from tornado_bz import BaseHandler

home = expanduser("~")

HTML_PATH = home + '/Dropbox/knowledge/html/'
WIKI_PATH = home + '/Dropbox/knowledge/data/'
CLICK_COUNT = home + '/click_count'
click_path = home + '/click/'
click_count = {}

key_names = {}
key_names_sorted = []

new_key_names = []

SITE = 'site'
black_keys = ['11', u'香港']

SHOW_COUNT = 15  # 首页显示几个详情


def popSome():
    '''
    过滤掉关键字黑名单black_keys中的关键字
    '''
    global key_names
    for black_key in black_keys:
        if black_key in key_names:
            key_names.pop(black_key)


def getKeyNames():
    try:
        f = open('./key_name', 'a+')
        global key_names
        global key_names_sorted
        content = f.read()
        if content != '':
            key_names = json.loads(content)
            popSome()
            key_names_sorted = sorted(key_names.items(), key=lambda by: by[1], reverse=True)
        f.close()
    except IOError:
        print public_bz.getExpInfoAll()


def getClickCount():
    try:
        f = open(CLICK_COUNT, 'a+')
        global click_count
        content = f.read()
        if content != '':
            click_count = json.loads(content)
        f.close()
    except IOError:
        print public_bz.getExpInfoAll()


def save(file_name, content):
    f = open(file_name, 'w+')
    print >>f, json.dumps(content)
    f.close()


def saveKeyNames():
    global key_names
    save('key_name', key_names)


def saveClickCount():
    global click_count
    save(CLICK_COUNT, click_count)


def increase(dic, name):
    if name in dic:
        dic[name] += 1
    else:
        if name.strip() != "":
            dic[name] = 1
    return dic


def refreshKeyNamesCount(name, count):
    global key_names
    # if key_names[name] % 5 == 0:
    if count != 0:
        key_names[name] = count
        saveKeyNames()
    # 需要排序
    global key_names_sorted
    key_names_sorted = sorted(key_names.items(), key=lambda by: by[1], reverse=True)


def addClickCount(name):
    global click_count
    click_count = increase(click_count, name)  # 点击数增加1次
    count_path = click_path + name
    save(count_path, click_count[name])  # 点击次数写入以[name]命名的文件
    if click_count[name] % 5 == 0:
        saveClickCount()
    return click_count[name]


def getList(name):
    seartch_wiki = SearchWiki(name)
    seartch_wiki.search(WIKI_PATH, HTML_PATH)
    seartch_wiki.mergerByYear()
    seartch_wiki.sortByTime()
    seartch_wiki.sortByYear()
    global new_key_names
    if name not in black_keys:
        if seartch_wiki.mergered_all_sorted:
            new_key_names = seartch_wiki.mergered_all_sorted[0][1][:SHOW_COUNT]
    return seartch_wiki.mergered_all_sorted


def getHtmlContent(name):
    '''
    取得对应名字的 html 文件的内容
    '''
    try:
        name_file = open(HTML_PATH + name + '.html', 'r')
        content = name_file.read()
        name_file.close()
        return content
    except IOError:
        # print public_bz.getExpInfoAll() # vimwiki中每个生成的html都默认会调一个style.css来,所以这里总是会读不存在的文件style.css.html所以报错
        return '0'


def getLen(lists):
    count = 0
    for l in lists:
        count += len(l[1])
    return count


class list(BaseHandler):

    '''
    显示 blog 列表
    '''

    def get(self, name='*'):
        lists = getList(str(name))
        if name == '*':
            title = 'zpf'
        else:
            title = name
            refreshKeyNamesCount(name, getLen(lists))
        global key_names
        global key_names_sorted
        global click_count

        self.render(tornado_bz.getTName(self),
                    title=title,
                    lists=lists,
                    key_names=key_names_sorted,
                    click_count=click_count,
                    time=time
                    )


def getTenContent(name):
    ten_names = getList(name)[0][1][:SHOW_COUNT]
    lists = []
    for i in ten_names:
        c = public_bz.storage()
        c.name = i[0]
        c.time = i[1]
        c.content = getHtmlContent(c.name)
        lists.append(c)
    return lists


class main(BaseHandler):

    '''
    首页,显示blog列表
    '''

    def get(self, name='*'):
        title = 'zpf'
        lists = getTenContent(name)

        self.render(tornado_bz.getTName(self), title=title, lists=lists, time=time)


class about(BaseHandler):

    '''
    关于我的介绍页面
    '''

    def get(self):
        self.render(tornado_bz.getTName(self, 'about'))


class blog(BaseHandler):

    '''
    显示单条blog 的详细内容
    '''

    def get(self, name):
        if name is None:
            name = 'index'
        html = name.rsplit('.', 1)
        if len(html) > 1 and html[1] == 'html':
            name = html[0]
        content = getHtmlContent(name)
        global key_names
        global key_names_sorted
        global new_key_names
        count = addClickCount(name)

        self.render(tornado_bz.getTName(self),
                    title=name,
                    content=content,
                    key_names=key_names_sorted,
                    new_key_names=new_key_names,
                    count=count
                    )


class roottxt(BaseHandler):

    '''
    阿里妈妈验证
    '''

    def get(self):
        self.write('756973118a848cc29e3952eee7f79daa')


'''
url_map = [
    (r'/root.txt', roottxt),
    (r'/', main),
    (r'/list', list),
    (r'/rss', rss),
    (r'/blog/(.*)', blog),
    (r'/list/(.*)', list),
    (r'/(.*)', blog),
]

settings = tornado_bz.getSettings()
settings['debug'] = False
application = tornado.web.Application(url_map, **settings)

'''

if __name__ == "__main__":
    pg = None
    the_class = tornado_bz.getAllUIModuleRequestHandlers()
    the_class.update(globals().copy())

    getKeyNames()
    getClickCount()

    if len(sys.argv) == 2:
        port = int(sys.argv[1])
    else:
        port = 8888
    print port

    url_map = tornado_bz.getURLMap(the_class)
    url_map.append((r'/', main))
    url_map.append((r'/static/(.*)', tornado.web.StaticFileHandler, {'path': "./static"}))

    settings = tornado_bz.getSettings()

    settings["pg"] = pg

    application = tornado.web.Application(url_map, **settings)

    application.listen(port)
    ioloop = tornado.ioloop.IOLoop().instance()
    tornado.autoreload.start(ioloop)
    ioloop.start()
