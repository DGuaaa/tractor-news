# -*- coding: utf-8 -*-
"""拖拉机市场情报站 - AI 总结生成脚本
读取 news.json → 调 DeepSeek 生成两份去敏文案(每日总结+宏观概览) → 输出 summary.js
"""
import re, json, os, sys, urllib.request, datetime, time

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

def llm_chat(system, user, max_tokens=5000, timeout=300):
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
)

def build_prompt(news):
    lines = []
    for i, it in enumerate(news, 1):
        lines.append(f"{i}. [{it['date']}][{it['source']}] {it['title']}")
    return (
        f'以下是今日抓取的农机行业新闻({len(news)}条):\n\n'
        + '\n'.join(lines) + '\n\n'
        + '请基于以上新闻生成两份文案,严格按以下 JSON 结构输出(不要输出任何其他文字):\n'
        + '{\n'
        + '  "daily": {\n'
        + '    "title": "农机产业观察 · 日期",\n'
        + '    "judgment": "核心判断一句话",\n'
        + '    "points": ["要点1(专业表述,含关键数据)", "要点2", ...共6条左右],\n'
        + '    "insights": ["产业视角1(供本土核心部件供应商参考)", "产业视角2", "产业视角3"]\n'
        + '  },\n'
        + '  "overview": {\n'
        + '    "title": "拖拉机产业季度观察",\n'
        + '    "sections": [{"name": "政策面", "body": "分析段落"}, {"name": "市场面", "body": "..."}, {"name": "产业面", "body": "..."}],\n'
        + '    "opportunities": ["结构性机会1", "机会2", "机会3", "机会4"]\n'
        + '  }\n'
        + '}\n'
        + '要求:daily 的要点要有数据支撑和产业解读;overview 的分析要有产业链视角,体现专家级深度。'
    )

def main():
    news = json.load(open(os.path.join(BASE, 'news.json'), encoding='utf-8'))['items']
    if not news:
        print('no news'); return 1
    content = llm_chat(SYSTEM_PROMPT, build_prompt(news))
    # 提取 JSON(模型可能输出代码块或多余文字)
    m = re.search(r'\{.*\}', content, re.S)
    if not m:
        print('JSON parse fail, content head:', (content or '')[:300])
        return 1
    data = json.loads(m.group(0))
    data['date'] = datetime.date.today().isoformat()
    with open(os.path.join(BASE, 'summary.js'), 'w', encoding='utf-8') as f:
        f.write('window.SUMMARY_DATA = ' + json.dumps(data, ensure_ascii=False) + ';\n')
    print('summary.js generated:', data['daily']['title'])
    return 0

if __name__ == '__main__':
    sys.exit(main())
