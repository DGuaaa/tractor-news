# -*- coding: utf-8 -*-
"""拖拉机市场情报站 - 新闻抓取脚本 v3
数据源:农机360(首页+要闻频道)、农机通、农业农村部农机化司
每条新闻提取真实发布日期(详情页/URL),不再贴抓取日期
"""
import re, json, os, time, sys, urllib.request, urllib.error, datetime, ssl

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = r'C:\Users\24788\Desktop\tractor_market_site'  # 网站数据输出目录(固定)

# 农机360 服务器使用弱DH密钥,Python 3.14 默认拒绝 -> 降低安全级别
_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
try:
    _ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
except Exception:
    pass
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx) as r:
        return r.read().decode('utf-8', errors='ignore')

def normalize_url(u):
    """统一转 https,避免 https 页面跳 http 被手机浏览器拦截"""
    return u.replace('http://', 'https://', 1)

def extract_date(item):
    """提取新闻真实发布日期:优先详情页日期,失败回退URL推断"""
    # URL 推断(快路径)
    url = item['url']
    m = re.search(r'/html/(\d{4})/(\d{2})/', url)
    if m: item['date'] = f"{m.group(1)}-{m.group(2)}"
    m = re.search(r'/(?:analyze|news)/(\d{4})/', url)
    if m: item['date'] = m.group(1)
    m = re.search(r't(\d{4})(\d{2})(\d{2})_', url)
    if m: item['date'] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # 详情页精确提取
    try:
        d = fetch(url, timeout=12)
        m = re.search(r'发布日期[：:]\s*(\d{4})-(\d{2})-(\d{2})', d)
        if not m:
            m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', d)  # 中文日期(如雷沃)
        if not m:
            m = re.search(r'(\d{4})-(\d{2})-(\d{2})', d)  # 裸横线日期(如CAAMM)
        if m: item['date'] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    except Exception:
        pass
    return item

def parse_nongji360():
    """农机360:首页新闻列表"""
    html = fetch('https://www.nongji360.com')
    items = []
    for href, text in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{10,70})</a>', html):
        t = text.strip()
        if not t or len(t) < 10:
            continue
        if '/html/' in href or '/report/' in href:
            items.append({'title': t, 'url': normalize_url(href if href.startswith('http') else 'https://www.nongji360.com' + href), 'source': '农机360'})
    seen, out = set(), []
    for it in items:
        if it['title'] not in seen:
            seen.add(it['title']); out.append(it)
    return out[:15]

def parse_nongji360_channel():
    """农机360:农机要闻频道"""
    try:
        html = fetch('https://news.nongji360.com/list/23')
    except Exception:
        return []
    items = []
    for href, text in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{10,70})</a>', html):
        t = text.strip()
        if not t or len(t) < 10:
            continue
        if '/html/' in href:
            items.append({'title': t, 'url': normalize_url(href if href.startswith('http') else 'https://news.nongji360.com' + href), 'source': '农机360'})
    seen, out = set(), []
    for it in items:
        if it['title'] not in seen:
            seen.add(it['title']); out.append(it)
    return out[:10]

def parse_nongjitong():
    """农机通:首页新闻列表(/news/ 频道页已改版为JS加载,必须抓首页)"""
    try:
        html = fetch('https://www.nongjitong.com')
    except Exception:
        return []
    items = []
    for href, text in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{8,80})</a>', html):
        t = text.strip()
        if not t or len(t) < 10:
            continue
        if '/news/' not in href:
            continue
        items.append({'title': t, 'url': normalize_url(href if href.startswith('http') else 'https://www.nongjitong.com' + href), 'source': '农机通'})
    seen, out = set(), []
    for it in items:
        if it['title'] not in seen:
            seen.add(it['title']); out.append(it)
    return out[:12]

def parse_njhs():
    """农业农村部农机化管理司:首页新闻(URL自带日期 tYYYYMMDD)"""
    try:
        html = fetch('http://www.njhs.moa.gov.cn/')
    except Exception:
        return []
    items = []
    for href, text in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{10,70})</a>', html):
        t = text.strip()
        if not t or len(t) < 12:
            continue
        if '/gzdt/' in href or '/gdxw/' in href:
            if href.startswith('http') and 'njhs.moa.gov.cn' not in href:
                continue  # 排除外部链接
            url = href if href.startswith('http') else 'http://www.njhs.moa.gov.cn' + href.lstrip('.')
            items.append({'title': t, 'url': url, 'source': '农业农村部农机化司'})
    seen, out = set(), []
    for it in items:
        if it['title'] not in seen:
            seen.add(it['title']); out.append(it)
    return out[:8]

def parse_caamm():
    """中国农业机械工业协会(CAAMM):资讯中心"""
    try:
        html = fetch('http://www.caamm.org.cn/zxzx/index.htm')
    except Exception:
        return []
    items = []
    for href, text in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{10,70})</a>', html):
        t = text.strip()
        if not t or len(t) < 12:
            continue
        if href.endswith('.htm') and '/zfzc/' in href:
            url = href if href.startswith('http') else 'http://www.caamm.org.cn' + href
            items.append({'title': t, 'url': url, 'source': '农机工业协会'})
    seen, out = set(), []
    for it in items:
        if it['title'] not in seen:
            seen.add(it['title']); out.append(it)
    return out[:6]

def parse_camda():
    """中国农业机械流通协会(CAMDA):AMI农机市场景气指数"""
    try:
        html = fetch('https://www.camda.cn/')
    except Exception:
        return []
    items = []
    for href, text in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{10,70})</a>', html):
        t = text.strip()
        if not t or len(t) < 12:
            continue
        if '/analyze/' in href:
            items.append({'title': t, 'url': href if href.startswith('http') else 'https://www.camda.cn' + href, 'source': '农机流通协会'})
    seen, out = set(), []
    for it in items:
        if it['title'] not in seen:
            seen.add(it['title']); out.append(it)
    return out[:6]

def parse_lovol():
    """潍柴雷沃:媒体中心"""
    try:
        html = fetch('https://www.lovol.com.cn/news/lovol-news.jsp')
    except Exception:
        return []
    items = []
    for href, text in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{8,70})</a>', html):
        t = text.strip()
        if not t or len(t) < 10:
            continue
        if 'medianews-detail' in href:
            items.append({'title': t, 'url': 'https://www.lovol.com.cn' + href, 'source': '潍柴雷沃'})
    seen, out = set(), []
    for it in items:
        if it['title'] not in seen:
            seen.add(it['title']); out.append(it)
    return out[:5]

def parse_zoomlion():
    """中联重科:公司动态"""
    try:
        html = fetch('https://www.zoomlion.com/news/trends.html')
    except Exception:
        return []
    items = []
    for href, text in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{8,70})</a>', html):
        t = text.strip()
        if not t or len(t) < 10:
            continue
        if '/content/details' in href:
            items.append({'title': t, 'url': 'https://www.zoomlion.com' + href, 'source': '中联重科'})
    seen, out = set(), []
    for it in items:
        if it['title'] not in seen:
            seen.add(it['title']); out.append(it)
    return out[:5]

def parse_kubota():
    """久保田中国:官网新闻"""
    try:
        html = fetch('http://www.kubota.com.cn/')
    except Exception:
        return []
    items = []
    for href, text in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{8,70})</a>', html):
        t = text.strip()
        if not t or len(t) < 10:
            continue
        if '/kams/newsone.do' in href:
            items.append({'title': t, 'url': 'http://www.kubota.com.cn' + href, 'source': '久保田中国'})
    seen, out = set(), []
    for it in items:
        if it['title'] not in seen:
            seen.add(it['title']); out.append(it)
    return out[:5]

def parse_yto():
    """一拖(东方红):公司新闻(URL自带日期 tYYYYMMDD)"""
    try:
        html = fetch('http://www.ytogroup.cn/xwdt_5457/gsxw/')
    except Exception:
        return []
    items = []
    for href, text in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{8,70})</a>', html):
        t = text.strip()
        if not t or len(t) < 10:
            continue
        if re.search(r'/t\d{8}_', href):
            url = href if href.startswith('http') else 'http://www.ytogroup.cn/xwdt_5457/gsxw/' + href.lstrip('./')
            items.append({'title': t, 'url': url, 'source': '一拖东方红'})
    seen, out = set(), []
    for it in items:
        if it['title'] not in seen:
            seen.add(it['title']); out.append(it)
    return out[:5]

def parse_intl_rss(url, source, max_items=4):
    """通用 RSS 解析(国际源):返回 items"""
    try:
        h = fetch(url, timeout=20)
    except Exception:
        return []
    items = []
    for it in re.findall(r'<item>(.*?)</item>', h, re.S):
        t = re.search(r'<title>(.*?)</title>', it, re.S)
        l = re.search(r'<link>(.*?)</link>', it, re.S)
        d = re.search(r'<pubDate>(.*?)</pubDate>', it, re.S)
        if not (t and l):
            continue
        title = t.group(1).strip()
        if len(title) < 8:
            continue
        date = ''
        if d:
            m = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', d.group(1))
            if m:
                mon = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06',
                       'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}
                date = f"{m.group(3)}-{mon.get(m.group(2), '01')}-{int(m.group(1)):02d}"
        items.append({'title': title, 'url': l.group(1).strip(),
                      'source': source, 'date': date})
    return items[:max_items]

def parse_futurefarming():
    return parse_intl_rss('https://www.futurefarming.com/feed/', 'FutureFarming')

def parse_agribusiness():
    return parse_intl_rss('https://www.agribusinessglobal.com/feed/', 'AgriBusinessGlobal')

def parse_worldnyjx():
    """沃得官网新闻(首页 catid=126 栏目链接)"""
    items = []
    try:
        h = fetch('http://www.worldnyjx.com/', timeout=15)
        for u, t in re.findall(r'<a[^>]*href="([^"]*catid=126[^"]*)"[^>]*>([^<]{8,60})</a>', h):
            url = u if u.startswith('http') else 'http://www.worldnyjx.com' + u.lstrip('.')
            items.append({'title': t.strip(), 'url': url, 'source': '沃得', 'date': ''})
    except Exception:
        pass
    return items[:6]

def parse_google_news(query, source, max_items=5):
    """谷歌新闻搜索(公司名→报道聚合)"""
    import urllib.parse
    url = 'https://news.google.com/search?q=' + urllib.parse.quote(query) + '&hl=zh-CN&gl=CN&ceid=CN:zh-Hans'
    items = []
    try:
        h = fetch(url, timeout=15)
        # 标题+链接块
        blocks = re.findall(r'<a[^>]*href="(\./read/[^"]+)"[^>]*>([^<]{8,80})</a>', h)
        dates = re.findall(r'datetime="([^"]+)"', h)
        for i, (u, t) in enumerate(blocks):
            title = t.strip()
            if not title or title in ('Business', 'Technology', 'World', 'More'):
                continue
            url_full = 'https://news.google.com' + u[1:] if u.startswith('.') else u
            date = dates[i][:10] if i < len(dates) else ''
            items.append({'title': title, 'url': url_full, 'source': source, 'date': date})
            if len(items) >= max_items:
                break
    except Exception:
        pass
    return items

def parse_jd_news():
    return parse_google_news('约翰迪尔 农机', '约翰迪尔')

def parse_zf_news():
    return parse_google_news('采埃孚 农机', '采埃孚')

def classify(title):
    t = title
    tl = t.lower()
    # 英文关键词分类(国际源)
    if re.search(r'hybrid|electric|battery|electrification|powertrain|transmission|cvt|engine|autonomous|robot|precision|digital|sensor', tl):
        return '技术'
    if re.search(r'policy|subsidy|regulation|emission|compliance|standard', tl):
        return '政策'
    if re.search(r'market|sales|dealer|acquisition|merger|investment|export|price|revenue|farm', tl):
        return '市场'
    # 违规/通报优先归政策(避免被"智能"等技术词误分)
    if re.search(r'违规|通报|处罚|注销', t): return '政策'
    if re.search(r'电动|混动|新能源|无人|智能|北斗|自动驾驶|氢|电机|电池', t): return '技术'
    if re.search(r'销量|排行榜|价格|出口|市场|展会|博览会|农机展|展览|成交|补贴额', t): return '市场'
    if re.search(r'补贴|政策|鉴定|公示|通告|通知|惠农|推广|监管|投诉', t): return '政策'
    if re.search(r'大会|发布|亮相|合作|签约|投产|交付|中标|财报|收购', t): return '行业'
    if re.search(r'拖拉机|收割机|农机|企业|公司|集团|YTO|雷沃|沃得|中联|久保田|约翰迪尔|格兰', t): return '行业'
    return '行业'

TAG_MAP = {'政策': 'tag-policy', '市场': 'tag-data', '技术': 'tag-tech', '行业': 'tag-news'}

def main():
    news = []
    for fn in (parse_nongji360, parse_nongji360_channel, parse_nongjitong, parse_njhs,
               parse_caamm, parse_camda, parse_lovol, parse_zoomlion, parse_kubota, parse_yto,
               parse_futurefarming, parse_agribusiness, parse_worldnyjx, parse_jd_news, parse_zf_news):
        try:
            items = fn()
            for it in items:
                it['tag'] = classify(it['title'])
                it['tag_class'] = TAG_MAP[it['tag']]
                it['date'] = ''
            news.extend(items)
        except Exception as e:
            print('source error:', e)
    # 全局去重
    seen, out = set(), []
    for it in news:
        k = it['title'][:25]
        if k not in seen:
            seen.add(k); out.append(it)
    # 逐条提取真实发布日期
    for it in out:
        try:
            extract_date(it)
            time.sleep(0.15)  # 对源网站友好
        except Exception:
            pass
    # 平衡分类:政策类最多12条,主源非政策最多20条,官网源最多12条,总计最多44条
    policy_count = 0
    balanced, others, corp = [], [], []
    for it in out:
        if it['tag'] == '政策':
            if policy_count < 12:
                policy_count += 1
                balanced.append(it)
        elif it['source'] in ('潍柴雷沃', '中联重科', '久保田中国', '一拖东方红', '沃得', '约翰迪尔', '采埃孚'):
            corp.append(it)  # 官网新闻作为补充,排在后面
        else:
            others.append(it)
    # 国际源(英文)优先保留,总量扩到 56
    intl = [it for it in others if it['source'] in ('FutureFarming', 'AgriBusinessGlobal')]
    others = [it for it in others if it['source'] not in ('FutureFarming', 'AgriBusinessGlobal')]
    out = balanced + intl[:8] + others[:16] + corp[:20]
    out = out[:56]
    out.sort(key=lambda x: 0 if x['tag'] == '政策' else 1)
    data = {'updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'items': out[:56]}
    with open(os.path.join(BASE, 'news.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    # JS 版:本地 file:// 打开也能加载(script 标签不受 CORS 限制)
    with open(os.path.join(BASE, 'news.js'), 'w', encoding='utf-8') as f:
        f.write('window.NEWS_DATA = ' + json.dumps(data, ensure_ascii=False) + ';\n')
    # 生成 AI 总结(调 DeepSeek,输出 summary.js)
    try:
        import subprocess
        PY = r'C:\Users\24788\AppData\Local\Python\bin\python.exe'
        r = subprocess.run([PY, os.path.join(BASE, 'gen_summary.py')],
                           capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            print('SUMMARY FAIL:', (r.stdout + r.stderr)[-200:])
        else:
            print('summary:', r.stdout.strip()[-80:])
    except Exception as e:
        print('SUMMARY ERROR:', e)
    # 上传到 GitHub Pages:git push 自动触发部署(兼容本地与 GitHub Actions 环境)
    try:
        import subprocess
        git = ['git', '-C', BASE]
        # Actions 环境:GITHUB_TOKEN 注入凭据;本地环境用已配置的 remote
        if os.environ.get('GITHUB_TOKEN'):
            subprocess.run(git + ['remote', 'set-url', 'origin',
                                  f"https://x-access-token:{os.environ['GITHUB_TOKEN']}@github.com/DGuaaa/tractor-news.git"],
                           capture_output=True, text=True, timeout=60)
        subprocess.run(git + ['config', 'user.name', 'DGuaaa'], capture_output=True, text=True, timeout=60)
        subprocess.run(git + ['config', 'user.email', 'DGuaaa@users.noreply.github.com'], capture_output=True, text=True, timeout=60)
        subprocess.run(git + ['add', '-A'], capture_output=True, text=True, timeout=60)
        r = subprocess.run(git + ['commit', '-m', f'auto-update {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}'],
                           capture_output=True, text=True, timeout=60)
        if 'nothing to commit' in r.stdout or 'nothing to commit' in r.stderr:
            print(f"OK: {len(out[:40])} items (无变化,未推送)")
            return 0
        else:
            r2 = subprocess.run(git + ['push', '-q', 'origin', 'main'], capture_output=True, text=True, timeout=120)
            if r2.returncode != 0:
                print(f'PUSH FAIL: {r2.stderr[-300:]}')
                return 1
            else:
                print(f"OK: {len(out[:40])} items + pushed to GitHub Pages")
                return 0
    except Exception as e:
        print(f"PUSH ERROR: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
