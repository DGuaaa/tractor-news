# -*- coding: utf-8 -*-
"""拖拉机市场情报站 - 新闻抓取脚本
抓取农机360 + 农机通首页新闻,分类后输出 news.json
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
    # 去重保序
    seen, out = set(), []
    for it in items:
        if it['title'] not in seen:
            seen.add(it['title']); out.append(it)
    return out[:20]

def parse_nongjitong():
    """农机通:首页新闻列表(注意:/news/ 频道页已改版为JS动态加载,必须抓首页)"""
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
    return out[:15]

def classify(title):
    t = title
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
    for fn in (parse_nongji360, parse_nongjitong):
        try:
            items = fn()
            for it in items:
                it['tag'] = classify(it['title'])
                it['tag_class'] = TAG_MAP[it['tag']]
                it['date'] = datetime.date.today().isoformat()
            news.extend(items)
        except Exception as e:
            print('source error:', e)
    # 全局去重
    seen, out = set(), []
    for it in news:
        k = it['title'][:25]
        if k not in seen:
            seen.add(k); out.append(it)
    # 平衡分类:政策类最多12条,其他类各保留,总计最多40条
    policy_count = 0
    balanced, others = [], []
    for it in out:
        if it['tag'] == '政策':
            if policy_count < 12:
                policy_count += 1
                balanced.append(it)
        else:
            others.append(it)
    out = balanced + others[:28]
    out.sort(key=lambda x: 0 if x['tag'] == '政策' else 1)
    data = {'updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'items': out[:40]}
    with open(os.path.join(BASE, 'news.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    # JS 版:本地 file:// 打开也能加载(script 标签不受 CORS 限制)
    with open(os.path.join(BASE, 'news.js'), 'w', encoding='utf-8') as f:
        f.write('window.NEWS_DATA = ' + json.dumps(data, ensure_ascii=False) + ';\n')
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
