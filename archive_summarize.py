# -*- coding: utf-8 -*-
"""情报站归档浓缩(方案B阶段2):读索引→抓正文→主题聚类→DeepSeek浓缩→写知识库
输出:Documents/爱格迈知识库/06-行业知识/行业手册 07 · 三年新闻浓缩.md
"""
import re, os, sys, json, time, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_summary  # 复用 fetch_full / llm_chat / get_api_key

BASE = os.path.dirname(os.path.abspath(__file__))
IDX = os.path.join(BASE, 'archive_index.json')
OUT = r'C:\Users\24788\Documents\爱格迈知识库\06-行业知识\行业手册 07 · 三年新闻浓缩.md'
SYSTEM = (
    '你是农机行业分析专家。用户提供若干条近三年农机行业新闻(标题+正文),'
    '请浓缩成有行业深度的知识条目。规则:\n'
    '1. 按主题归纳(政策/市场/技术/主机厂动态/行业事件),提炼关键事实与数据\n'
    '2. 每条要点注明涉及的企业/机构与年份\n'
    '3. 指出对"本土核心部件供应商(混动动力系统)"的启示(如有)\n'
    '4. 不得编造新闻中没有的内容;不确定的标注[待核实]\n'
    '5. 输出纯 JSON:{"topics":[{"name":"政策","points":["..."]}]}'
)

def load_index():
    d = json.load(open(IDX, encoding='utf-8'))
    return d['items']

def grab_body(it):
    body = gen_summary.fetch_full(it['url'], max_chars=800)
    return body

def batch(items, n=20):
    for i in range(0, len(items), n):
        yield items[i:i + n]

def main():
    items = load_index()
    print(f'索引 {len(items)} 条,开始抓正文+浓缩...')
    all_topics = {}
    for bi, batch_items in enumerate(batch(items)):
        lines = []
        for it in batch_items:
            body = grab_body(it)
            if body:
                lines.append(f"[{it['date']}][{it['source']}] {it['title']}\n正文: {body}")
            else:
                lines.append(f"[{it['date']}][{it['source']}] {it['title']}(正文获取失败)")
            time.sleep(0.15)
        prompt = f'以下是近三年农机行业新闻(第{bi+1}批,共{len(batch_items)}条):\n\n' + '\n\n'.join(lines)
        ok = False
        for attempt in range(3):
            try:
                resp = gen_summary.llm_chat(SYSTEM, prompt, max_tokens=6000, timeout=600)
                d = json.loads(resp)
                for t in d.get('topics', []):
                    name = t.get('name', '其他')
                    all_topics.setdefault(name, []).extend(t.get('points', []))
                print(f'  批{bi+1}: {len(batch_items)}条 → {len(d.get("topics",[]))} 主题(第{attempt+1}次)')
                ok = True
                break
            except Exception as e:
                print(f'  批{bi+1}: 第{attempt+1}次失败 {str(e)[:60]}')
                time.sleep(3)
        if not ok:
            # 兜底:仅标题浓缩(不加正文,减负)
            try:
                t_lines = [f"[{it['date']}][{it['source']}] {it['title']}" for it in batch_items]
                resp = gen_summary.llm_chat(SYSTEM, '以下是新闻标题列表:\n' + '\n'.join(t_lines),
                                            max_tokens=6000, timeout=600)
                d = json.loads(resp)
                for t in d.get('topics', []):
                    all_topics.setdefault(t.get('name', '其他'), []).extend(t.get('points', []))
                print(f'  批{bi+1}: 兜底(仅标题)成功')
            except Exception as e:
                print(f'  批{bi+1}: 兜底也失败 {str(e)[:60]}')
        time.sleep(1)

    # 写知识库
    lines = ['# 行业手册 07 · 三年新闻浓缩(2023-2026)', '']
    lines.append('> 来源:情报站归档抓取(中联/久保田/CAAMM/雷沃/农机通/CAMDA 等源,一拖/农机化司/农机360 受反爬限制未含)。')
    lines.append(f'> 生成:{datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}。数据以原文为准,引用前核实时效。')
    lines.append('')
    for name, points in all_topics.items():
        lines.append(f'## {name}')
        for p in points:
            lines.append(f'- {p}')
        lines.append('')
    lines.append('## 相关')
    lines.append('- [[农机行业手册 01 · 市场全景]] · [[农机行业手册 04 · 技术路线]] · [[农机行业手册 02 · 主机厂图谱]]')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'\n完成: {OUT}')

if __name__ == '__main__':
    main()
