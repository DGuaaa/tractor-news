# -*- coding: utf-8 -*-
"""拖拉机市场情报站 - AI 总结生成脚本
读取 news.json → 调 DeepSeek 生成两份去敏文案(每日总结+宏观概览) → 输出 summary.js
"""
import re, json, os, sys, ssl, urllib.request, datetime, time

BASE = r'C:\Users\24788\Desktop\tractor_market_site'
ENV_PATH = r'C:\Users\24788\AppData\Local\hermes\.env'
MODEL = 'deepseek-v4-flash'
API = 'https://api.deepseek.com/chat/completions'

def get_api_key():
    # 优先环境变量,其次读 hermes .env
    key = os.environ.get('DEEPSEEK_API_KEY', '')
    if key:
        return key
    try:
        for line in open(ENV_PATH, encoding='utf-8'):
            if line.strip().startswith('DEEPSEEK_API_KEY='):
                return line.strip().split('=', 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ''

def fetch(url, timeout=20):
    """抓取网页(农机360等源需降低SSL安全级别)"""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    try:
        ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
    except Exception:
        pass
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception:
        return ''

def llm_chat(system, user, max_tokens=5000, timeout=600):
    key = get_api_key()
    if not key:
        raise RuntimeError('DEEPSEEK_API_KEY 未找到')
    payload = {
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
        'temperature': 0.6,
        'max_tokens': max_tokens,
        'response_format': {'type': 'json_object'},  # DeepSeek JSON 模式,保证合法输出
    }
    req = urllib.request.Request(API, data=json.dumps(payload).encode('utf-8'),
                                 headers={'Content-Type': 'application/json',
                                          'Authorization': f'Bearer {key}'})
    d = json.load(urllib.request.urlopen(req, timeout=timeout))
    return d['choices'][0]['message']['content']

SYSTEM_PROMPT = (
    '你是一名资深农机产业分析师,服务对象是拖拉机行业的高级技术专家与高管。'
    '输出必须专业、有行业深度,用中文,不写废话。'
    '【重要脱敏要求】:绝不提及任何具体产品型号(如E-CVT3004类编号)、'
    '任何具体公司的内部信息、内部项目名称、内部人员。'
    '涉及机会分析时使用"本土核心部件供应商"等泛化表述。'
    '所有结论必须基于用户提供的新闻内容,不得编造。'
    '【引用要求】:每条要点必须标注其依据的新闻编号(如 [3] 表示第3条新闻),'
    '编号只能来自新闻列表,不得编造;sources 数组由新闻列表自动生成,你只需在 refs 中引用编号。'
)

KB_DIR = r'C:\Users\24788\Documents\爱格迈知识库\06-行业知识'

def load_kb_context(max_chars=4500):
    """读取知识库行业手册,提取行业背景知识(供专家判断参考)"""
    parts = []
    try:
        if not os.path.isdir(KB_DIR):
            return ''
        for f in sorted(os.listdir(KB_DIR)):
            if not f.endswith('.md') or '手册' not in f:
                continue
            try:
                txt = open(os.path.join(KB_DIR, f), encoding='utf-8').read()
            except Exception:
                continue
            # 只提取要点行(- 开头)和标题
            lines = []
            for line in txt.split('\n'):
                line = line.strip()
                if line.startswith('- ') and not line.startswith('- [['):
                    lines.append(line[2:])
                elif line.startswith('# ') and not lines:
                    lines.append(line[2:])
                elif line.startswith('## '):
                    lines.append('【' + line[3:] + '】')
            # 07/08 大文件只取前 12 条(含启示章节优先)
            limit = 12 if ('07' in f or '08' in f) else 8
            body = '\n'.join(lines[:limit])
            if body:
                parts.append(f'[{f.replace(".md","")}]\n{body}')
    except Exception:
        pass
    ctx = '\n\n'.join(parts)
    return ctx[:max_chars]

def fetch_full(url, max_chars=1200):
    """抓取新闻正文全文:优先<p>段落拼接,失败回退全文;截断防上下文超限"""
    try:
        html = fetch(url, timeout=15)
        html = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', html, flags=re.S)
        paras = re.findall(r'<p[^>]*>(.*?)</p>', html, re.S)
        text = ' '.join(re.sub(r'<[^>]+>', ' ', p) for p in paras)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) < 100:  # 无 p 标签,退回全文去标签
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_chars]
    except Exception:
        return ''

def build_prompt(news):
    lines = []
    total = 0
    for i, it in enumerate(news, 1):
        body = fetch_full(it['url'])
        total += len(body)
        if body:
            lines.append(f"{i}. [{it['date']}][{it['source']}] {it['title']}\n   正文: {body}")
        else:
            lines.append(f"{i}. [{it['date']}][{it['source']}] {it['title']}\n   (正文获取失败,仅有标题)")
        time.sleep(0.1)  # 对源网站友好
    kb = load_kb_context()
    kb_part = f'\n\n【行业背景知识库(供判断参考,非今日新闻)】\n{kb}\n' if kb else ''
    return (
        f'以下是今日抓取的农机行业新闻({len(news)}条,含正文全文,每条有编号):\n\n'
        + '\n\n'.join(lines) + kb_part + '\n\n'
        + '请基于以上新闻生成两份文案,严格按以下 JSON 结构输出(不要输出任何其他文字):\n'
        + '{\n'
        + '  "daily": {\n'
        + '    "title": "农机产业观察 · 日期",\n'
        + '    "judgment": "核心判断一句话",\n'
        + '    "points": [{"text": "要点1(专业表述,含关键数据)", "refs": [3]}, {"text": "要点2", "refs": [1,5]}, ...共6条左右],\n'
        + '    "insights": [{"text": "产业视角1(供本土核心部件供应商参考)", "refs": [2]}, {"text": "产业视角2", "refs": []}, {"text": "产业视角3", "refs": [4]}]\n'
        + '  },\n'
        + '  "overview": {\n'
        + '    "title": "拖拉机产业季度观察",\n'
        + '    "sections": [{"name": "政策面", "body": "分析段落"}, {"name": "市场面", "body": "..."}, {"name": "产业面", "body": "..."}],\n'
        + '    "opportunities": ["结构性机会1", "机会2", "机会3", "机会4"]\n'
        + '  }\n'
        + '}\n'
        + '要求:'
        + '1. daily 的要点要有数据支撑和产业解读,可结合【行业背景知识库】做专家级判断(引用背景知识时 refs 留空即可);'
        + '2. refs 只能引用新闻编号(1~' + str(len(news)) + '),且必须真实存在;'
        + '3. overview 的分析要有产业链视角,体现专家级深度。'
    )

def parse_json_content(content):
    """宽容解析模型输出:代码块 → 直接解析 → 常见修复"""
    if not content:
        return None
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m = re.search(r'\{.*\}', content, re.S)
    if not m:
        return None
    s = m.group(0)
    for attempt in (s,
                    re.sub(r',\s*([}\]])', r'\1', s),           # 去尾逗号
                    re.sub(r'[\u201c\u201d]', '"', s),           # 中文引号
                    re.sub(r"'(?=([^']*'))", '"', s.replace('\"', "''"))):  # 单引号
        try:
            return json.loads(attempt)
        except Exception:
            continue
    return None

def main():
    news = json.load(open(os.path.join(BASE, 'news.json'), encoding='utf-8'))['items']
    if not news:
        print('no news'); return 1
    data = None
    for attempt in range(2):  # 最多重试1次
        content = llm_chat(SYSTEM_PROMPT, build_prompt(news))
        data = parse_json_content(content)
        if data:
            break
        print(f'summary attempt {attempt+1} JSON parse fail')
    if not data:
        print('summary FAIL: 无法解析模型输出')
        return 1
    # 附加 sources 映射:编号→新闻(编号由程序保证与 refs 对应,URL 不可能编造)
    data['sources'] = [
        {'id': i, 'title': it['title'], 'url': it['url'],
         'source': it['source'], 'date': it.get('date', '')}
        for i, it in enumerate(news, 1)
    ]
    data['date'] = datetime.date.today().isoformat()
    # 标题日期强制为今天(即使新闻源当天未更新,总结也标注最新日期)
    if 'daily' in data and data['daily'].get('title'):
        today_cn = datetime.date.today().strftime('%Y年%m月%d日')
        data['daily']['title'] = re.sub(r'20\d{2}年\d{2}月\d{2}日', today_cn, data['daily']['title'])
    with open(os.path.join(BASE, 'summary.js'), 'w', encoding='utf-8') as f:
        f.write('window.SUMMARY_DATA = ' + json.dumps(data, ensure_ascii=False) + ';\n')
    print('summary.js generated:', data['daily']['title'])
    return 0

if __name__ == '__main__':
    sys.exit(main())
