#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
tornado 相关的公用代码
'''

import tornado
import types
import inspect
import os
import sys
import public_bz
import functools
import json
import urllib
import user_bz
import db_bz
from tornado.escape import utf8
from tornado.web import RequestHandler

from tornado import escape

from tornado.util import bytes_type, unicode_type
OK = '0'


class BaseHandler(RequestHandler):

    '''
    create by bigzhu at 15/01/29 22:53:07 自定义一些基础的方法
        设置 pg
        设定 current_user 为 cookie user_id
    modify by bigzhu at 15/01/30 09:59:46 直接返回 user_info
    modify by bigzhu at 15/01/30 10:32:37 默认返回 user_info 的拆离出去
    modify by bigzhu at 15/02/21 00:41:23 修改 js_embed 的位置到 </head> 前
    create by bigzhu at 15/03/06 17:13:21 修改 js_file 的位置到 </head> 前
    '''

    def initialize(self):
        self.pg = self.settings['pg']

    def get_current_user(self):
        return self.get_secure_cookie("user_id")

    def render(self, template_name, **kwargs):
        """Renders the template with the given arguments as the response.
        create by bigzhu at 15/02/21 01:50:52 就是为了把embedded_javascript 的位置换一下
        modify by bigzhu at 15/03/06 17:14:23 调整 js 插入的次序,早出来的先插入
        """

        html = self.render_string(template_name, **kwargs)

        # Insert the additional JS and CSS added by the modules on the page
        js_embed = []
        js_files = []
        css_embed = []
        css_files = []
        html_heads = []
        html_bodies = []
        for module in getattr(self, "_active_modules", {}).values():
            embed_part = module.embedded_javascript()
            if embed_part:
                # js_embed.append(utf8(embed_part))
                js_embed.insert(0, utf8(embed_part))
            file_part = module.javascript_files()
            if file_part:
                if isinstance(file_part, (unicode_type, bytes_type)):
                    # js_files.append(file_part)
                    js_files.insert(0, file_part)
                else:
                    js_files.extend(file_part)
            embed_part = module.embedded_css()
            if embed_part:
                css_embed.append(utf8(embed_part))
            file_part = module.css_files()
            if file_part:
                if isinstance(file_part, (unicode_type, bytes_type)):
                    css_files.append(file_part)
                else:
                    css_files.extend(file_part)
            head_part = module.html_head()
            if head_part:
                html_heads.append(utf8(head_part))
            body_part = module.html_body()
            if body_part:
                html_bodies.append(utf8(body_part))

        def is_absolute(path):
            return any(path.startswith(x) for x in ["/", "http:", "https:"])
        if js_files:
            # Maintain order of JavaScript files given by modules
            paths = []
            unique_paths = set()
            for path in js_files:
                if not is_absolute(path):
                    path = self.static_url(path)
                if path not in unique_paths:
                    paths.append(path)
                    unique_paths.add(path)
            js = ''.join('<script src="' + escape.xhtml_escape(p) +
                         '" type="text/javascript"></script>'
                         for p in paths)
            #sloc = html.rindex(b'</body>')
            sloc = html.rindex(b'</head>')
            html = html[:sloc] + utf8(js) + b'\n' + html[sloc:]
        if js_embed:
            js = b'<script type="text/javascript">\n//<![CDATA[\n' + \
                b'\n'.join(js_embed) + b'\n//]]>\n</script>'
            sloc = html.rindex(b'</head>')
            html = html[:sloc] + js + b'\n' + html[sloc:]
        if css_files:
            paths = []
            unique_paths = set()
            for path in css_files:
                if not is_absolute(path):
                    path = self.static_url(path)
                if path not in unique_paths:
                    paths.append(path)
                    unique_paths.add(path)
            css = ''.join('<link href="' + escape.xhtml_escape(p) + '" '
                          'type="text/css" rel="stylesheet"/>'
                          for p in paths)
            hloc = html.index(b'</head>')
            html = html[:hloc] + utf8(css) + b'\n' + html[hloc:]
        if css_embed:
            css = b'<style type="text/css">\n' + b'\n'.join(css_embed) + \
                b'\n</style>'
            hloc = html.index(b'</head>')
            html = html[:hloc] + css + b'\n' + html[hloc:]
        if html_heads:
            hloc = html.index(b'</head>')
            html = html[:hloc] + b''.join(html_heads) + b'\n' + html[hloc:]
        if html_bodies:
            hloc = html.index(b'</body>')
            html = html[:hloc] + b''.join(html_bodies) + b'\n' + html[hloc:]
        self.finish(html)

    def render_string(self, template_name, **kwargs):
        """Generate the given template with the given arguments.

        We return the generated byte string (in utf8). To generate and
        write a template as a response, use render() above.

        create by bigzhu at 15/02/21 01:49:51 为了设定 _getframe,也得把这个方法重载一遍.否则 template 路径会按 bz 的来找

        """
        # If no template_path is specified, use the path of the calling file
        template_path = self.get_template_path()
        if not template_path:
            frame = sys._getframe(1)
            web_file = frame.f_code.co_filename
            while frame.f_code.co_filename == web_file:
                frame = frame.f_back
            template_path = os.path.dirname(frame.f_code.co_filename)
        with RequestHandler._template_loader_lock:
            if template_path not in RequestHandler._template_loaders:
                loader = self.create_template_loader(template_path)
                RequestHandler._template_loaders[template_path] = loader
            else:
                loader = RequestHandler._template_loaders[template_path]
        t = loader.load(template_name)
        namespace = self.get_template_namespace()
        namespace.update(kwargs)
        return t.generate(**namespace)


class ModuleHandler(BaseHandler):

    '''
    create by bigzhu at 15/03/11 10:17:40 给 UI Module 使用
    '''

    def myRender(self, **kwargs):
        '''
        这个方法如果不重载,那么就会报错
        像这样重载即可:
        self.render(tornado_bz.getTName(self), **kwargs)
        也可以指定自己的 template
        '''
        raise NotImplementedError()


class UserInfoHandler(BaseHandler):

    '''
    create by bigzhu at 15/01/30 10:32:00 默认返回 user_info 的类单独拆离出来, 某些不需要返回 user_info 的可以继续用 base
    '''

    def get_user_info(self):
        if self.current_user:
            user_info = user_bz.UserOper(self.pg).getUserInfoById(self.current_user)
            if user_info:
                self.user_info = user_info[0]
                return self.user_info
            else:
                self.redirect("/logout")

    def get_template_namespace(self):
        ns = super(UserInfoHandler, self).get_template_namespace()
        ns.update({
            'user_info': self.get_user_info(),
        })

        return ns


def getURLMap(the_globals):
    '''
        根据定义的tornado.web.RequestHandler,自动生成url map
        modify by bigzhu at 15/03/06 15:53:59 在这里需要设置 lib 的 static, 用于访问 lib 的 static 文件
    '''
    url_map = []
    for i in the_globals:
        try:
            if issubclass(the_globals[i], tornado.web.RequestHandler):
                url_map.append((r'/' + i, the_globals[i]))
                url_map.append(
                    (r'/lib_static/(.*)', tornado.web.StaticFileHandler, {'path': public_bz.getLibPath() + "/static"})
                )
                # url_map.append((r"/%s/([0-9]+)" % i, the_globals[i]))
                url_map.append((r"/%s/(.*)" % i, the_globals[i]))
        except TypeError:
            continue
    return url_map


def getAllUIModules():
    '''create by bigzhu at 15/02/22 05:58:07 获取所有的 ui module
    '''
    ui_modules = []
    import ui_module
    import pkgutil
    for importer, modname, ispkg in pkgutil.iter_modules(ui_module.__path__):
        if not ispkg:
            print modname
            module = importer.find_module(modname).load_module(modname)
            ui_modules.append(module)
    return ui_modules


def getSettings():
    '''
        返回 tornado 的 settings ,有一些默认值,省得每次都设置:
            debug:  True 则开启调试模式,代码自动部署,但是有语法错误,会导致程序 cash
            ui_modules 自定义的 ui 模块,默认会引入 tornado_ui_bz
            login_url: 装饰器 tornado.web.authenticated 未登录时候,重定向的网址
    '''
    settings = {
        'static_path': os.path.join(public_bz.getExecutingPath(), 'static'),
        'debug': True,
        'cookie_secret': 'bigzhu so big',
        'autoescape': None,  # 模板自定义转义
        'login_url': "/login",
        'ui_modules': getAllUIModules()
    }
    return settings


def getTName(self, name=None):
    '''
    取得模板的名字
    与类名保持一致
    '''
    if name:
        return 'template/' + name + '.html'
    else:
        return 'template/' + self.__class__.__name__ + '.html'


def handleError(method):
    '''
    出现错误的时候,用json返回错误信息回去
    很好用的一个装饰器
    '''
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            method(self, *args, **kwargs)
        except Exception:
            self.write(json.dumps({'error': public_bz.getExpInfo()}))
            print public_bz.getExpInfoAll()
    return wrapper


def mustLoginApi(method):
    '''
    必须要登录 api
    create by bigzhu at 15/06/21 08:00:56
    '''
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if self.current_user:
            pass
        else:
            raise Exception('must login')
        return method(self, *args, **kwargs)
    return wrapper


def mustLogin(method):
    '''
    必须要登录,否则弹回登录页面
    很好用的一个装饰器
    '''
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if self.current_user:
            pass
        else:
            self.redirect("/login")
            return
        return method(self, *args, **kwargs)
    return wrapper


def addHits(method):
    '''
    记录某个微信用户点击的页面
    '''
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        openid = self.get_secure_cookie('openid')
        path = self.request.path
        if not openid:
            pass
        else:
            self.pg.db.insert('hits', openid=openid, path=path)
        return method(self, *args, **kwargs)
    return wrapper


def mustSubscribe(method):
    '''
    create by bigzhu at 15/04/08 10:25:59 wechat 使用,必须要关注
    '''
    #from wechat_sdk import WechatBasic
    from wechat_sdk.basic import OfficialAPIError

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        openid = self.get_secure_cookie("openid")
        if openid is None:
            # 连openid 都没有,首先要获取 openid
            params = {
                "appid": self.settings['appid'],
                # "redirect_uri": "http://" + self.settings['domain'] + "/setOpenid?url=/" + self.__class__.__name__,
                # "redirect_uri": "http://" + self.settings['domain'] + "/setOpenid?url=" + self.request.uri,
                "redirect_uri": "http://" + "admin.hoywe.com/" + self.settings['suburl'] + "/?url=" + self.request.uri,
                "response_type": "code",
                "scope": "snsapi_base",
            }
            auth_url = "https://open.weixin.qq.com/connect/oauth2/authorize?%s#wechat_redirect"
            auth_url = auth_url % urllib.urlencode(params)
            self.redirect(auth_url)
            return
        else:
            #exists_users = list(self.pg.db.select('wechat_user', where="openid='%s'" % openid))
            # if not exists_users:
            try:
                wechat_user_info = self.wechat.get_user_info(openid, lang='zh_CN')
            except OfficialAPIError as e:
                print public_bz.getExpInfoAll()
                self.clear_cookie(name='openid')
                error = public_bz.getExpInfo()
                if error.find('40001') != -1:
                    raise e
                else:
                    error_info = '''
                    <html>
                        <script type="text/javascript">
                        alert("微信服务器异常，请关闭后，重新打开");
                        WeixinJSBridge.call('closeWindow');
                        </script>
                    </html>
                    '''
                    self.write(error_info)
                return

            # 没有关注的,跳转到配置的关注页面
            if wechat_user_info['subscribe'] == 0:
                self.redirect('http://' + self.settings["domain"] + self.settings["subscribe"])
                return
            # else:
            #    print 'add user'
            #    self.pg.db.insert('wechat_user', **wechat_user_info)

        return method(self, *args, **kwargs)
    return wrapper


def getUserId(request):
    '''
    获取当前 user_id
    未登录则为 1
    '''
    user_id = request.current_user
    if user_id:
        pass
    else:
        user_id = 1
    return user_id


class oper(BaseHandler):

    '''
    create by bigzhu at 15/04/23 16:49:57 用来操作,做一些通用的增删改
    协议说明:
        put: update
        post: insert
        get: select
        delete: delete

    参数解释:
        t: table_name
        w: where
        s: sql(完整的原始sql,太危险暂时取消)
        v: update 或者 insert 的值
        c: 记录数,要删除的记录数
    '''
    @handleError
    def get(self):
        self.set_header("Content-Type", "application/json")
        t = self.get_argument('t')
        w = self.get_argument('w', '1=1')
        order = self.get_argument('order', None)
        if order:
            data = list(self.pg.db.select(t, where=w, order=order))
        else:
            data = list(self.pg.db.select(t, where=w))

        self.write(json.dumps({'error': '0', 'data': data}, cls=public_bz.ExtEncoder))

    @handleError
    def post(self):
        '''
        create by bigzhu at 15/04/23 17:33:09 insert 返回 id
        '''
        self.set_header("Content-Type", "application/json")
        if self.current_user:
            user_id = self.current_user
        else:
            raise Exception('必须登录才能操作')

        data = json.loads(self.request.body)
        t = data.get('t')  # table
        v = data.get('v')  # value

        v = db_bz.transTimeValueByTable(self.pg, t, v)
        # 插入的值有id就update,只能udpate一条,没有就 insert
        id = v.get('id')
        if id is not None:
            print id
            w = "id=%s" % id
            trans = self.pg.db.transaction()
            count = self.pg.db.update(t, w, **v)
            if count == 1:
                trans.commit()
                self.write(json.dumps({'error': '0'}))
                return
            else:
                trans.rollback()

        seq = t + '_id_seq'
        v['user_id'] = user_id
        id = self.pg.db.insert(t, seqname=seq, **v)
        self.write(json.dumps({'error': '0', 'id': id}))

    @handleError
    def put(self):
        '''
        create by bigzhu at 15/04/23 17:33:33 udpate数据,只要value有id, 可以不写where
        '''
        self.set_header("Content-Type", "application/json")
        if self.current_user:
            pass
        else:
            raise Exception('必须登录才能操作')
        data = json.loads(self.request.body)
        t = data.get('t')  # table
        w = data.get('w')  # where
        v = data.get('v')  # value

        v = db_bz.transTimeValueByTable(self.pg, t, v)
        if w is None:
            id = v.get('id')
            if id is None:
                raise Exception('没有足够的信息来进行update操作')
            w = "id=%s" % id

        trans = self.pg.db.transaction()
        count = self.pg.db.update(t, w, **v)
        if count == 1:
            trans.commit()
        else:
            trans.rollback()
            raise Exception('不允许update %s 条记录,请检查条件' % count)

        self.write(json.dumps({'error': '0'}))

    @handleError
    def delete(self):
        '''
        create by bigzhu at 15/04/23 17:37:36 其实只是做update
        '''
        self.set_header("Content-Type", "application/json")
        if self.current_user:
            pass
        else:
            raise Exception('必须登录才能操作')
        t = self.get_argument('t')
        w = self.get_argument('w')
        c = self.get_argument('c')

        trans = self.pg.db.transaction()
        count = self.pg.db.update(t, w, is_delete=1)
        print int(c)
        if count == int(c):
            trans.commit()
        else:
            trans.rollback()
        self.write(json.dumps({'error': '0'}))


class oper_post(BaseHandler):

    '''
    通用操作,http 协议太难用了,全用 post搞定
    create by bigzhu at 15/06/07 12:38:39
    '''
    @handleError
    def post(self):
        '''
        type: insert delete query select
        create by bigzhu at 15/06/07 12:40:20
        '''
        self.set_header("Content-Type", "application/json")
        if self.current_user:
            user_id = self.current_user
        else:
            raise Exception('必须登录才能操作')

        data = json.loads(self.request.body)
        oper_type = data.get('type')
        if oper_type == 'insert':
            v = data.get('v')
            t = data.get('t')
            v = db_bz.transTimeValueByTable(self.pg, t, v)
            # 插入的值有id就update,只能udpate一条,没有就 insert
            id = v.get('id')
            if id is not None:
                w = "id=%s" % id
                trans = self.pg.db.transaction()
                count = self.pg.db.update(t, w, **v)
                if count == 1:
                    trans.commit()
                    self.write(json.dumps({'error': OK}))
                    return
                else:
                    trans.rollback()

            seq = t + '_id_seq'
            v['user_id'] = user_id
            id = self.pg.db.insert(t, seqname=seq, **v)
            self.write(json.dumps({'error': OK, 'id': id}))
            return
        elif oper_type == 'delete':
            t = data.get('t')
            ids = data.get('ids')
            w = 'id in (%s) ' % ids
            c = data.get('c')
            trans = self.pg.db.transaction()
            count = self.pg.db.update(t, w, is_delete=1)
            if count == int(c):
                trans.commit()
            else:
                trans.rollback()
                raise Exception("按条件找到%s条,指定要删除%s条,取消删除" % (count, c))
            self.write(json.dumps({'error': '0'}))

def getAllRequestHandlers():
    '''
    create by bigzhu at 15/09/14 21:43:31 取出所有modules里的RequestHandler
    '''

    all_class = {}

    import web_bz
    for name, cls in inspect.getmembers(web_bz):
        try:
            if issubclass(cls, RequestHandler):
                all_class[cls.__name__] = cls
        except TypeError:
            pass
    return all_class

def getAllUIModuleRequestHandlers():
    '''
    create by bigzhu at 15/07/02 16:17:44 获取所有 ui module 配套的 RequestHandler
    '''
    all_class = {}
    for m in getAllUIModules():
        assert isinstance(m, types.ModuleType)
        modules = dict((n, getattr(m, n)) for n in dir(m))
        for name, cls in modules.items():
            try:
                if issubclass(cls, RequestHandler):
                    all_class[cls.__name__] = cls
            except TypeError:
                pass
    return all_class

if __name__ == '__main__':
    import web_bz
    print getAllRequestHandlers(web_bz)
