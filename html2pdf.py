'''
python 包
https://pypi.org

1. python之使用 wkhtmltopdf 和 pdfkit 批量加载html生成pdf，适用于博客备份和官网文档打包
https://www.cnblogs.com/my8100/p/7738366.html

2. Python 爬虫：把廖雪峰教程转换成 PDF 电子书
https://foofish.net/python-crawler-html2pdf.html
http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000

3. CondaHTTPError: HTTP 000 CONNECTION FAILED
https://blog.csdn.net/ada0915/article/details/78529877

https://github.com/lzjun567/crawler_html2pdf

create by lu.qiulian
2018-05-27
@description
    http://www.liaoxuefeng.com有权限控制，以下方法无法爬取数据

'''

####################################################################################################
####################################################################################################
import requests
from lxml import html
import urllib


def getHtml1(url):
    page = requests.Session().get(url)
    return page.text


def getHtml2(url):
    html = urllib.request.urlopen(url).read()
    return html


url = 'https://movie.douban.com/' #需要爬数据的网址
url = 'http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000'
####################################################################################################
####################################################################################################


import os
import sys
import time
import traceback
import re
from urllib.parse import urlparse
from urllib.parse import urljoin
import urllib.request
import threading
# queue模块详解 https://www.cnblogs.com/CongZhang/p/5274486.html
import queue

import requests
# scrapy选择器 https://github.com/scrapy/scrapy
# http://www.w3school.com.cn/xpath/xpath_syntax.asp
# a = sel.xpath("//section[@class='page__content']/node()[position()<4]").extract()
from scrapy import Selector
import pdfkit

s = requests.Session()
# s.headers.update({'user-agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 9_3_5 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Mobile/13G36 MicroMessenger/6.5.12 NetType/4G'})
s.headers.update({'user-agent':'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'})
# s.headers.update({'Referer':'https://servicewechat.com/wx55b926152a8c3bef/14/page-frame.html'})
s.verify = False
s.mount('http://', requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000))
s.mount('https://', requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000))
import copy
sp = copy.deepcopy(s)
proxies = {'http': 'http://127.0.0.1:1080', 'https': 'https://127.0.0.1:1080'}
sp.proxies = proxies

from urllib3.exceptions import InsecureRequestWarning
from warnings import filterwarnings
filterwarnings('ignore', category = InsecureRequestWarning)

html_template = u"""
<!DOCTYPE html>

<html>
    <head>
        <meta charset="utf-8" />
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    </head>
    <body>
        <!-- <center><h1>{title}</h1></center> -->
        {content}
    </body>
</html>
"""

# wkhtmltopdf 的使用 https://wkhtmltopdf.org/usage/wkhtmltopdf.txt

options = {
    'page-size': 'A4',  # Letter
    'minimum-font-size': 25,  ###
    # 'image-dpi':1500, ###

    'margin-top': '0.1in',  # 0.75in
    'margin-right': '0.1in',
    'margin-bottom': '0.1in',
    'margin-left': '0.1in',
    'encoding': 'UTF-8',  # 支持中文
    'custom-header': [
        ('Accept-Encoding', 'gzip')
    ],
    'cookie': [
        ('cookie-name1', 'cookie-value1'),
        ('cookie-name2', 'cookie-value2'),
    ],
    'outline-depth': 10,
}

# 验证 re.findall(pattern, s)
# <img alt="_images/chapt3_img05_IDE_open.png" class="align-center" src="_images/chapt3_img05_IDE_open.png">

# http://linux.vbird.org/linux_basic/0105computers.php
# 只能通过网页源代码 或 resp.text 确认tag img内部是否存在换行 \n, F12看不出来
# 通过findall 修改 (".*?>) 为 (") 或(".*?alt)或(".*?style)确认问题，所以要加 re.S
# <div style="text-align:center;"><img src="/linux_basic/0105computers/chipset_z87.jpg" alt="Intel晶片架構" title="Intel晶片架構" style="border: 1px solid black;" /><br />
# 圖 0.2.1、Intel晶片架構</div>
# <div style="text-align:center; margin: 0 auto 0 auto; "><img src="/linux_basic/0105computers/computer01.gif" alt="計算器的功能" title="計算器的功能"
    # style="border: 0px solid black; padding: 0px " /></div>

pattern_img_scr = re.compile(r'(<img\s+[^>]*?src\s*=\s*")(?P<src>.*?)(".*?>)', re.S)  #最后不能简写成 " ，否则结果缺 "

# <a class="reference external" href="http://code.google.com/p/selenium/issues/detail?id=1008">issue 1008</a>
# text为空，也能匹配到 m.group(4)=''
pattern_a_href = re.compile(r'(<a\s+[^>]*?href\s*=\s*")(?P<href>.*?)(".*?>)(?P<text>.*?)(</a>)', re.S)

# http://linux.vbird.org/linux_desktop/0110linuxbasic.php
# 07年的网页，tag head 不符合规范
# 错误：<span class="text_head0">第一章、架設伺服器前的準備工作</span> #要变h1
# 错误：<span class="text_h1">1.1 前言： Linux 有啥功能</span>    #要变h2
# 更正：<h1>第七章、Linux 磁碟與檔案系統管理</h1>
# 复杂嵌套:<span class="text_head0"><span class="text_head_en">Linux </span>基礎</span>
# 这里只处理最普通情况
pattern_span_head = re.compile(r'<span\s+class\s*=\s*"text_h(?:ead)?(\d)">([^<]*?)</span>') #(?:xxx)数量词 不分组版本


class HTMLtoPDF(object):

    def __init__(self, seed_url, proxy=False, pdf='', page=1, font_size=25,
                 css_links='div[class="wy-menu wy-menu-vertical"] a::attr(href)',
                 css_content='div.rst-content', xpath_content='', threads_count=30):

        self.seed_url = seed_url
        self.session = sp if proxy else s

        options['minimum-font-size'] = font_size

        self.pdf = pdf
        self.netloc = urlparse(seed_url).netloc
        print(self.netloc)

        self.folder = os.path.join(sys.path[0], '{}({})'.format(self.netloc, self.pdf))
        self.folder_temp = os.path.join(sys.path[0], 'temp')
        for f in [self.folder, self.folder_temp]:
            if not os.path.isdir(f):
                os.mkdir(f)

        self.css_content = css_content
        self.css_links = css_links
        self.xpath_content = xpath_content

        self.threads_count = threads_count
        # self.lock = threading.Lock()
        self.links_queue = queue.Queue()
        self.links_seen = []

        for p in range(1, page + 1):
            url = re.sub(r'page=\d+', 'page=%s' % p, self.seed_url)  # 本来无page，原样返回
            self.links_queue.put((str(len(self.links_seen)), url))
            self.links_seen.append(url)
            self.get_links(url)
        self.links_queue_size = self.links_queue.qsize()
        self.htmls_saved = []

    def get_links(self, url):
        print(url)
        encoding, text = self.load_page(url)
        sel = Selector(text=text)


        # [u'#selenium-documentation',
        # u'00_Note_to-the-reader.jsp',
        # u'01_introducing_selenium.jsp',
        # u'01_introducing_selenium.jsp#test-automation-for-web-applications',

        links = [re.sub(r'#.*$', '', i) for i in sel.css(self.css_links).extract()]
        print(links)

        for link in links:  # set(links) 会导致乱序,使用urls_seen 去重
            link_abs = urljoin(url, link)
            if link_abs not in self.links_seen:
                self.links_queue.put((str(len(self.links_seen)), link_abs))
                self.links_seen.append(link_abs)

    def run(self):
        threads = []
        for i in range(self.threads_count):
            t = threading.Thread(target=self.save_html)
            threads.append(t)

        for t in threads:
            t.setDaemon(True)
            t.start()

        self.links_queue.join()
        print('load done')

        def func(filename):
            _, filename = os.path.split(filename)
            return int(filename[:filename.index('_')])

        self.htmls_saved.sort(key=lambda x: func(x))
        output = u'myout_{}({}) {}.pdf'.format(self.netloc, self.pdf, time.strftime('%Y%m%d_%H%M%S'))
        try:
            pdfkit.from_file(self.htmls_saved, output, options=options)
        except Exception as err:
            print('{}'.format(self.htmls_saved))

        print(output)

    def save_html(self):
        while True:
            try:
                (num, url) = self.links_queue.get()
                meta_encoding, text = self.load_page(url)
                # http://linux.vbird.org/linux_desktop/index.php
                # meta charset 是 big5
                # pdfkit 已经设置 utf-8，所以temp文件需要编码为 utf-8
                # 用于浏览的保存页面，如果编码为 utf-8，不符合meta charset 冲突，
                # 需要通过firefox手动指定编码

                encoding_to = meta_encoding if meta_encoding else 'utf-8'

                text = self.modify_text(url, text)  ######################## 含有原始 <html meta charset
                # text = self.modify_content2(url, text)
                # text1 = text

                title, content = self.parse_page(url, text)

                filename_cn = u'{}_{}.html'.format(num, re.sub(r'[^\u4e00-\u9fa5\w\s()_-]', '', title))  # ur
                filename = u'{}_{}_{}.html'.format(num, re.sub(r'[^\w\s()_-]', '', title), int(time.time()))  # os.path.abspath('en/abc.html')合成路径 不能是 /en。。

                with open(os.path.join(self.folder, filename_cn), 'wb') as fp:
                    fp.write(text.encode(encoding_to, 'replace'))
                f = os.path.join(self.folder_temp, filename)
                with open(f, 'wb') as fp:
                    fp.write(content.encode('utf-8', 'replace'))
                    # fp.write(html_template.format(content=content, title=title).encode('utf-8','replace'))  #没必要补充 <html>
                    self.htmls_saved.append(f)
                    print('{}/{} {} {}'.format(len(self.htmls_saved), self.links_queue_size, url, title))

                self.links_queue.task_done()
            except Exception as err:
                print('####################{} {} {}'.format(url, err, traceback.format_exc()))

    def load_page(self, url):
        resp = self.session.get(url)
        # http://linux.vbird.org/linux_desktop/index.php
        # meta charset 是 big5
        meta_encoding = None
        if resp.encoding == 'ISO-8859-1':

            def get_encodings(html):
                reg = r'<meta.*?charset=["\']*(.+?)["\'>]'
                charset = re.compile(reg)
                html = html.decode('UTF-8')  # python3
                encodings = re.findall(charset, html)
                return encodings;

            encodings = get_encodings(resp.content)
            # encodings = requests.utils.get_encodings_from_content(resp.content)  # re.compile(r'<meta.*?charset
            if encodings:
                resp.encoding = encodings[0]
                meta_encoding = resp.encoding
            else:
                resp.encoding = resp.apparent_encoding  # models.py  chardet.detect(self.content)['encoding']
            # print('ISO-8859-1 changed to %s' % resp.encoding)

        return (meta_encoding, resp.text)



    def modify_text(self, url, text):
        # m.group(1)='abc' SyntaxError: can't assign to function call 不能直接赋值

        # https://doc.scrapy.org/en/latest/topics/firebug.html
        # ../_images/firebug1.png
        # 异常 urljoin(self.seed_url, src)

        # r'(<img\s+[^>]*?src\s*=\s*")(?P<src>.*?)(".*?>)'
        def func_src(m):
            src = m.group('src')  # 别名
            if not src.startswith('http'):
                src = urljoin(url, src)
            # print u'{}{}{}'.format(m.group(1), src, m.group(3))
            return u'{}{}{}'.format(m.group(1), src, m.group(3))

        text = re.sub(pattern_img_scr, func_src, text)

        def func_head(m):
            # re.compile(r'<span class="text_h.*?(\d)">(.*?)</span>', re.S)
            # 错误：<span class="text_head0">第一章、架設伺服器前的準備工作</span>
            # 更正：<h1>第七章、Linux 磁碟與檔案系統管理</h1>
            return u'<h{num}>{word}</h{num}>'.format(num=int(m.group(1)) + 1, word=m.group(2))

        text = re.sub(pattern_span_head, func_head, text)

        # re.compile(r'(<a\s+[^>]*?href\s*=\s*")(?P<href>.*?)(".*?>)(?P<text>.*?)(</a>)')
        def func_href(m):
            href = m.group('href')
            text = m.group('text')
            if not href.startswith('#'):
                if not href.startswith('http'):
                    href = urljoin(url, href)
                # text = u'{text} ({href})'.format(text=text, href=href)
            return u'{g1}{href}{g3}{text}{g5}'.format(g1=m.group(1), g3=m.group(3), g5=m.group(5), href=href, text=text)

            # m.string是content全文。。。也不能 return m

        text = re.sub(pattern_a_href, func_href, text)

        return text

    def parse_page(self, url, text):
        sel = Selector(text=text)
        title = sel.css('head title::text').extract_first() or ''  # 固定css, 匹配不到 extract()返回[],extract_first()返回None

        if(self.xpath_content != ''):
            xpath_contents = self.xpath_content.split(',')
            content = []
            for _ in xpath_contents:
                content += sel.xpath(_.strip()).extract()
            content = "".join(content)
        else:
            content = sel.css(self.css_content).extract_first() or ''  # 'div.rst-content'

        return title, content

    def clean_content(self, content):
        # <a class="headerlink" href="#check" title="Permalink to this headline">¶</a>  headline 自带图形
        content = content.replace(u'>\xb6<', u'><')

        # selenium LanguagePreference
        sel = Selector(text=content)
        # content = content.replace(sel.css('div#codeLanguagePreference').extract_first(), '') #可能是None
        for div in sel.css('div#codeLanguagePreference').extract():
            content = content.replace(div, '')

        for lang in ['java', 'csharp', 'ruby', 'php', 'perl', 'javascript']:
            for div in sel.css('div.highlight-%s' % lang).extract():
                # print len(content)
                content = content.replace(div, '')

        # liaoxuefeng comment
        content = content.replace('<h3>Comments</h3>', '')
        content = content.replace('<h3>Make a comment</h3>', '')

        # http://lxml.de/
        for div in sel.css('div.sidemenu').extract():
            content = content.replace(div, '')

        return content

    # 未使用，下面解释了，extract() 执行 Serialize 导致 tag 内部 \n 丢失，replace(tag, tag_new) 失效
    def modify_content2(self, url, content):
        sel = Selector(text=content)

        # 修改图片链接为绝对链接，否则pdf无法图片
        # <img alt="_images/chapt3_img05_IDE_open.png" class="align-center" src="_images/chapt3_img05_IDE_open.png">

        # http://linux.vbird.org/linux_desktop/0110linuxbasic.php
        # <img src="0110linuxbasic/computer_fllow.png" border=1
        # title="電腦組成示意圖" alt="電腦組成示意圖">

        for i in sel.css('img[src]'):
            tag = i.extract()
            src = i.xpath('./@src').extract_first()
            if not src.startswith('http'):
                src_abs = urljoin(url, src)
                # print src, src_abs
                tag_new = tag.replace(src, src_abs)

                # In [392]: sel.extract?
                # Signature: sel.extract()
                # Docstring:
                # Serialize and return the matched nodes in a single unicode string.
                # Percent encoded content is unquoted.
                # File:      c:\program files\anaconda2\lib\site-packages\parsel\selector.py
                # Type:      instancemethod
                # Serialize。。。。。。。。。。
                # print tag  #换行被自动省略，后面的replace 失效。。。
                # print tag_new
                # <img src="0110linuxbasic/computer_fllow.png" border="1" title="電腦組成示意圖" alt="電腦組成示意圖">
                # <img src="http://linux.vbird.org/linux_desktop/0110linuxbasic/computer_fllow.png" border="1" title="電腦組成示意圖" alt="電腦組成示意圖">

                content = content.replace(tag, tag_new)  # 可能alt(同src...)

        # a href 的text添加href信息
        # <a class="reference external" href="http://code.google.com/p/selenium/issues/detail?id=1008">issue 1008</a>
        for i in sel.css('a[href]'):
            tag = i.extract()
            href = i.xpath('./@href').extract_first()
            text = i.xpath('./text()').extract_first()

            # 补全内部链接，忽略本页面的#定位
            if not href.startswith('http') and not href.startswith('#'):
                href_abs = urljoin(url, href)
                # print href, href_abs
                tag_new = tag.replace(href, href_abs)
            else:
                href_abs = href
                tag_new = tag

            # 图标链接，如果text为None，replace表现异常
            if text and not href.startswith('#'):
                text_new = u'{} ({})'.format(text, href_abs)
                # print text.encode('gbk','replace'), text_new.encode('gbk','replace')
                tag_new = tag_new.replace(text, text_new)

                # 保证整体替换
            content = content.replace(tag, tag_new)

        return content


if __name__ == '__main__':
    # url = 'https://doc.scrapy.org/en/latest/index.html'
    # obj = HTMLtoPDF(url, proxy=True)

    # url = 'http://python3-cookbook.readthedocs.io/zh_CN/latest/index.html'
    # obj = HTMLtoPDF(url, font_size=20, css_links='div[class="toctree-wrapper compound"] a::attr(href)')

    # url = 'http://www.seleniumhq.org/docs/'
    # obj = HTMLtoPDF(url, proxy=True, css_links='div#selenium-documentation a::attr(href)', css_content='div#mainContent')

    # pip install beautifulsoup4; from bs4 import BeautifulSoup
    # url = 'https://www.crummy.com/software/BeautifulSoup/bs4/doc/'
    # obj = HTMLtoPDF(url, pdf='BeautifulSoup', css_links='div.sphinxsidebarwrapper a::attr(href)', css_content='div.body')

    # url = 'https://www.liaoxuefeng.com/wiki/001374738125095c955c1e6d8bb493182103fac9270762a000'
    # obj = HTMLtoPDF(url, proxy=True, pdf='python2', css_links='ul#x-wiki-index a::attr(href)', css_content='div.x-content', threads_count=10)

    # url = 'https://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000'
    # url = 'https://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000'
    # obj = HTMLtoPDF(url, proxy=True, pdf='python3', css_links='ul#x-wiki-index a::attr(href)', css_content='div.x-content', threads_count=10)

    # url = 'https://docs.python.org/2/howto/index.html'
    # obj = HTMLtoPDF(url, pdf='python2howto', css_links='div[class="toctree-wrapper compound"] a::attr(href)', css_content='div.body')

    # url = 'http://lxml.de/'
    # obj = HTMLtoPDF(url, pdf='lxml', css_links='div.menu a::attr(href)', css_content='div.document')

    # url = 'http://docs.python-requests.org/zh_CN/latest/'
    # obj = HTMLtoPDF(url, pdf='requests', css_links='div[class="toctree-wrapper compound"] a::attr(href)', css_content='div.body')

    # url = 'http://twistedmatrix.com/documents/current/core/howto/index.html'
    # obj = HTMLtoPDF(url, pdf='twisted_core_guide', css_links='div[class="body"] a::attr(href)', css_content='div.body')

    # url = 'http://linux.vbird.org/linux_basic/'
    # obj = HTMLtoPDF(url, pdf='linux_basic', css_links='div[class="mainarea"] a::attr(href)', css_content='div.mainarea')

    # url = 'http://linux.vbird.org/linux_server/'
    # obj = HTMLtoPDF(url, pdf='linux_server', css_links='td[width="718"] a::attr(href)', css_content='td[width="718"]')

    # url = 'http://linux.vbird.org/linux_desktop/'
    # obj = HTMLtoPDF(url, pdf='linux_desktop', css_links='td[width="718"] a::attr(href)', css_content='td[width="718"]')

    # url = 'http://www.cnblogs.com/my8100/default.html?page=1'
    # obj = HTMLtoPDF(url, page=7, pdf='my8100', css_links='div#mainContent div.postTitle a::attr(href)', css_content='div.post')

    # url = 'https://webpack.docschina.org/concepts/'
    # obj = HTMLtoPDF(url, pdf='webpack_概念', css_links='div.sidebar-item a::attr(href)', xpath_content="//section[@class='page__content']/node()[position()<4]")
    # obj.run()

    # url = 'https://webpack.docschina.org/configuration/'
    # obj = HTMLtoPDF(url, pdf='webpack_配置', css_links='div.sidebar-item a::attr(href)', xpath_content="//section[@class='page__content']/node()[position()<4]")
    # obj.run()

    # url = 'https://webpack.docschina.org/api/'
    # obj = HTMLtoPDF(url, pdf='webpack_API', css_links='div.sidebar-item a::attr(href)', xpath_content="//section[@class='page__content']/node()[position()<4]")
    # obj.run()

    # url = 'https://webpack.docschina.org/guides/'
    # obj = HTMLtoPDF(url, pdf='webpack_指南', css_links='div.sidebar-item a::attr(href)', xpath_content="//section[@class='page__content']/node()[position()<4]")
    # obj.run()

    # url = 'https://webpack.docschina.org/loaders/'
    # obj = HTMLtoPDF(url, pdf='webpack_LOADERS', css_links='div.sidebar-item a::attr(href)', xpath_content="//section[@class='page__content']/node()[position()<4]")
    # obj.run()

    url = 'https://webpack.docschina.org/plugins/'
    # obj = HTMLtoPDF(url, pdf='webpack_插件', css_links='div.sidebar-item a::attr(href)', xpath_content="//section[@class='page__content']/node()[position()<4]")
    obj = HTMLtoPDF(url, pdf='webpack_插件', css_links='div.sidebar-item a::attr(href)', xpath_content="//section[@class='page__content']/h1[1],//section[@class='page__content']/div[2]")

    obj.run()