#!/usr/bin/env python
#encoding=utf-8
'''
vimwiki 中用来查找 wiki 词
'''
import fnmatch
import sys
import os
import time
import re

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

NOT_IN = ['search', 'site', 'wiki_index']  # 添加wiki显示时忽略的文件名

class SearchWiki:
    def __init__(self, wiki_name):
        self.wiki_name = wiki_name
        self.mergered_all = {}
        self.mergered_all_sorted = []
        self.wikis_time = {}

    def getHtmlNameList(self, html_path):
        '''
        取wiki生成的html文件夹下的所有html文件名
        '''
        html_list = []
        for html in os.listdir(html_path):
            html = os.path.basename(html)
            html = html.rsplit('.', 1)
            html = html[0]
            html_list.append(html)
        return html_list

    def search(self, path='.', html_path='.'):
        '''
        找到wiki文件名,并加上时间
        '''
        html_list = self.getHtmlNameList(html_path)
        pattern = re.compile(r'^\.') # 匹配以.开头的隐藏文件
        for wiki in os.listdir(path):
            path_wiki = path + '/' + wiki
            if os.path.isdir(path_wiki):  #过滤掉目录
                continue
            if( fnmatch.fnmatchcase(wiki.upper(), ('*%s*' % self.wiki_name).upper()) ): # 测试两个字符串是否匹配,大小写敏感
                modify_time = time.localtime(os.path.getctime(path_wiki))  # os.path.getmtime(f)获取文件的最后修改时间
                m = pattern.search(wiki)
                if m is None:  # 隐藏的文件不要参与查找
                    wiki = wiki.rsplit('.', 1)
                    wiki = wiki[0]
                    if wiki in NOT_IN:  # 过滤掉黑名单中的wiki名
                        continue
                    if wiki in html_list:
                        self.wikis_time[wiki] = modify_time

    def mergerByYear(self):
        '''按年份来归并'''
        for i in self.wikis_time:
            year = str(self.wikis_time[i].tm_year)
            mergered_wikis_dic = self.mergered_all.get(year)
            if mergered_wikis_dic is None:
                dic = {i: self.wikis_time[i]}
                self.mergered_all[year] = dic
            else:
                mergered_wikis_dic[i] = self.wikis_time[i]

    def sortByTime(self):
        '''按时间排序'''
        for i in self.mergered_all:
            wikis_time = self.mergered_all[i]
            wikis_time_sorted = sorted(wikis_time.items(), key=lambda by: by[1], reverse=True)
            self.mergered_all[i] = wikis_time_sorted

    def sortByYear(self):
        self.mergered_all_sorted = sorted(self.mergered_all.items(), key=lambda by: by[0], reverse=True)


if __name__ == '__main__':
    pass
