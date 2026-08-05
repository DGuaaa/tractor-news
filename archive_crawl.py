# -*- coding: utf-8 -*-
"""情报站归档抓取(方案B阶段1):9源近3年新闻索引
策略:一拖按月目录、CAMDA按年目录、农机化司频道列表、其余源当前列表+分页尽力
输出:archive_index.json(标题/日期/URL/源)
"""
import sys, os, re, json, time, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crawl

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'archive_index.json')
INDEX = []

def add(src, title, url, date=''):
    if not title or len(title) < 8:
        return
    title = title.strip()
    for it in INDEX:
        if it['title'][:25] == title[:25] and it['source'] == src:
            return
    INDEX.append({'source': src, 'title': title, 'url': url, 'date': date})

def fetch_slow(url, timeout=15, retries=2):
    for i in range(retries + 1):
        try:
            h = crawl.fetch(url, timeout=timeout)
            if h:
                return h
        except Exception:
            pass
        time.sleep(2)
    return ''

def grab_links(h):
    return re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{8,70})</a>', h)

# ===== 1. 一拖:按月目录(202308..202608) =====
def collect_yto():
    n = 0
    for ym in ['202308','202309','202310','202311','202312','202401','202402','202403','202404',
               '202405','202406','202407','202408','202409','202410','202411','202412','202501',
               '202502','202503','202504','202505','202506','202507','202508','202509','202510',
               '202511','202512','202601','202602','202603','202604','202605','202606','202607','202608']:
        h = fetch_slow(f'http://www.ytogroup.cn/xwdt_5457/gsxw/{ym}/')
        if not h:
            continue
        for u, t in grab_links(h):
            if re.search(r'/t\d{8}_', u):
                m = re.search(r't(\d{4})(\d{2})(\d{2})_', u)
                date = f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else ym[:4] + '-' + ym[4:]
                url = u if u.startswith('http') else f'http://www.ytogroup.cn/xwdt_5457/gsxw/{ym}/' + u.lstrip('./')
                add('一拖东方红', t, url, date)
                n += 1
        time.sleep(1.2)
    print(f'一拖: {n} 条(去重后 {sum(1 for i in INDEX if i["source"]=="一拖东方红")})')

# ===== 2. CAMDA:首页全量(含历史链接) =====
def collect_camda():
    n = 0
    for url in ['https://www.camda.cn/', 'https://www.camda.cn/analyze/']:
        h = fetch_slow(url)
        if not h:
            continue
        for u, t in grab_links(h):
            m = re.search(r'/(\d{4})/\d+\.html', u)
            if m:
                url = u if u.startswith('http') else 'https://www.camda.cn' + u
                add('农机流通协会', t, url, m.group(1) + '-01-01')
                n += 1
        time.sleep(1.5)
    print(f'CAMDA: {n} 条')

# ===== 3. 农机化司:频道列表 =====
def collect_njhs():
    n = 0
    for path in ['gzdt/', 'gdxw/', 'nyhsd/', 't2024', '']:
        pass
    for path in ['gzdt/', 'gdxw/']:
        h = fetch_slow(f'http://www.njhs.moa.gov.cn/{path}')
        if not h:
            continue
        for u, t in grab_links(h):
            m = re.search(r't(\d{4})(\d{2})(\d{2})_', u)
            if m:
                date = f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
                url = u if u.startswith('http') else 'http://www.njhs.moa.gov.cn' + u.lstrip('.')
                add('农机化司', t, url, date)
                n += 1
        time.sleep(1.2)
    print(f'农机化司: {n} 条')

# ===== 4. 其余源:当前列表 =====
def collect_others():
    srcs = [
        ('农机360要闻', 'https://news.nongji360.com/list/23.html', r'\.html'),
        ('农机通', 'https://www.nongjitong.com/news/', r'20\d{2}/\d+\.html'),
        ('CAAMM', 'http://www.caamm.org.cn/zxzx/index.htm', r'/\d+\.htm'),
        ('雷沃', 'https://www.lovol.com.cn/news/lovol-news.jsp', r'medianews-detail-\d+\.htm'),
        ('中联', 'https://www.zoomlion.com/news/trends.html', r'details\d+_\d+\.html'),
        ('久保田', 'http://www.kubota.com.cn/', r'newsone\.do'),
    ]
    for name, url, pat in srcs:
        h = fetch_slow(url)
        if not h:
            print(f'{name}: 抓取失败')
            continue
        n = 0
        for u, t in grab_links(h):
            if re.search(pat, u):
                full = u if u.startswith('http') else ('http://www.caamm.org.cn' + u if name == 'CAAMM' else url.split('/')[0] + '//' + url.split('/')[2] + u)
                add(name, t, full)
                n += 1
        time.sleep(1.2)
        print(f'{name}: {n} 条')

def main():
    collect_yto()
    collect_camda()
    collect_njhs()
    collect_others()
    INDEX.sort(key=lambda x: x['date'], reverse=True)
    json.dump({'updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'items': INDEX},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n总计: {len(INDEX)} 条 -> {OUT}')

if __name__ == '__main__':
    main()
