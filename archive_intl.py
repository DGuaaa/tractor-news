# -*- coding: utf-8 -*-
"""国外农机新闻抓取:RSS+首页 → archive_intl_index.json
源:FutureFarming(RSS+news首页)、AgriBusinessGlobal(RSS)、FarmEquipment(首页)
"""
import sys, os, re, json, time, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crawl

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'archive_intl_index.json')
INDEX = []

def add(src, title, url, date=''):
    if not title or len(title) < 8:
        return
    title = title.strip()
    for it in INDEX:
        if it['title'][:40] == title[:40] and it['source'] == src:
            return
    INDEX.append({'source': src, 'title': title, 'url': url, 'date': date})

def parse_rss(h):
    items = []
    for it in re.findall(r'<item>(.*?)</item>', h, re.S):
        t = re.search(r'<title>(.*?)</title>', it, re.S)
        d = re.search(r'<pubDate>(.*?)</pubDate>', it, re.S)
        l = re.search(r'<link>(.*?)</link>', it, re.S)
        if t and l:
            items.append((t.group(1).strip(), l.group(1).strip(),
                          d.group(1).strip()[:16] if d else ''))
    return items

def main():
    # 1. FutureFarming RSS
    try:
        h = crawl.fetch('https://www.futurefarming.com/feed/', timeout=20)
        for t, u, d in parse_rss(h):
            add('FutureFarming', t, u, d)
        print(f'FutureFarming RSS: {len(parse_rss(h))} 条')
    except Exception as e:
        print('FutureFarming RSS FAIL:', str(e)[:50])
    time.sleep(1.5)

    # 2. AgriBusinessGlobal RSS
    try:
        h = crawl.fetch('https://www.agribusinessglobal.com/feed/', timeout=20)
        for t, u, d in parse_rss(h):
            add('AgriBusinessGlobal', t, u, d)
        print(f'AgriBusinessGlobal RSS: {len(parse_rss(h))} 条')
    except Exception as e:
        print('AgriBusinessGlobal RSS FAIL:', str(e)[:50])
    time.sleep(1.5)

    # 3. FutureFarming news 首页
    try:
        h = crawl.fetch('https://www.futurefarming.com/news/', timeout=20)
        for u, t in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{10,70})</a>', h):
            if '/news/' in u or '/tech-in-focus/' in u or '/smart-farming/' in u:
                add('FutureFarming', t.strip(), u)
        print('FutureFarming news首页: 已并入')
    except Exception as e:
        print('FutureFarming news FAIL:', str(e)[:50])
    time.sleep(1.5)

    # 4. FarmEquipment 首页
    try:
        h = crawl.fetch('https://www.farm-equipment.com/', timeout=20)
        for u, t in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{12,80})</a>', h):
            if re.search(r'/\d{4}/', u) or '/news' in u:
                full = u if u.startswith('http') else 'https://www.farm-equipment.com' + u
                add('FarmEquipment', t.strip(), full)
        print('FarmEquipment 首页: 已并入')
    except Exception as e:
        print('FarmEquipment FAIL:', str(e)[:50])

    INDEX.sort(key=lambda x: x['date'], reverse=True)
    json.dump({'updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'items': INDEX},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n国际索引总计: {len(INDEX)} 条 -> {OUT}')

if __name__ == '__main__':
    main()
