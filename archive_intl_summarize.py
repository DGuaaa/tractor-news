# -*- coding: utf-8 -*-
"""国际新闻浓缩:英文原文→中文浓缩 → 知识库《行业手册 08 · 国际动态浓缩》"""
import re, os, sys, json, time, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_summary

BASE = os.path.dirname(os.path.abspath(__file__))
IDX = os.path.join(BASE, 'archive_intl_index.json')
OUT = r'C:\Users\24788\Documents\爱格迈知识库\06-行业知识\行业手册 08 · 国际动态浓缩.md'
SYSTEM = (
    '你是农机行业国际分析师,精通英语与中文。用户提供若干条国外农机行业新闻(英文标题+正文),'
    '请浓缩成中文知识条目。规则:\n'
    '1. 按主题归纳(国际技术/国际市场/国际主机厂动态/对中国农机启示),提炼关键事实与数据\n'
    '2. 每条要点注明涉及的企业/国家与时间\n'
    '3. 特别关注:混动/电动/无人驾驶技术进展、约翰迪尔/CNH/爱科/芬特/采埃孚/博世动态\n'
    '4. 指出对"中国本土核心部件供应商(混动动力系统)"的启示(如有)\n'
    '5. 不得编造新闻中没有的内容;不确定的标注[待核实]\n'
    '6. 输出纯 JSON:{"topics":[{"name":"国际技术","points":["..."]}]}'
)

def main():
    items = json.load(open(IDX, encoding='utf-8'))['items']
    print(f'国际索引 {len(items)} 条,开始抓正文+浓缩...')
    all_topics = {}
    # 小批 10 条,重试 3 次
    for bi in range(0, len(items), 10):
        chunk = items[bi:bi + 10]
        lines = []
        for it in chunk:
            body = gen_summary.fetch_full(it['url'], max_chars=900)
            if body:
                lines.append(f"[{it['date']}][{it['source']}] {it['title']}\n正文: {body}")
            else:
                lines.append(f"[{it['date']}][{it['source']}] {it['title']}(正文获取失败)")
            time.sleep(0.2)
        prompt = f'以下是国外农机行业新闻(小批{bi//10+1},共{len(chunk)}条):\n\n' + '\n\n'.join(lines)
        ok = False
        for attempt in range(3):
            try:
                resp = gen_summary.llm_chat(SYSTEM, prompt, max_tokens=6000, timeout=600)
                d = json.loads(resp)
                for t in d.get('topics', []):
                    all_topics.setdefault(t.get('name', '其他'), []).extend(t.get('points', []))
                print(f'  小批{bi//10+1}: 成功(第{attempt+1}次)')
                ok = True
                break
            except Exception as e:
                print(f'  小批{bi//10+1}: 第{attempt+1}次失败 {str(e)[:50]}')
                time.sleep(3)
        if not ok:
            print(f'  小批{bi//10+1}: 放弃')
        time.sleep(1)
    if not all_topics:
        print('无结果'); return
    lines = ['# 行业手册 08 · 国际动态浓缩(2026)']
    lines.append('')
    lines.append('> 来源:FutureFarming / AgriBusinessGlobal / FarmEquipment(近期新闻,国外源历史受反爬限制)。')
    lines.append(f'> 生成:{datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}。英文原文由AI翻译浓缩,引用前核实。')
    lines.append('')
    for name, points in all_topics.items():
        lines.append(f'## {name}')
        for p in points:
            lines.append(f'- {p}')
        lines.append('')
    lines.append('## 相关')
    lines.append('- [[行业手册 07 · 三年新闻浓缩]] · [[农机行业手册 04 · 技术路线]]')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
    print(f'\n完成: {OUT}')

if __name__ == '__main__':
    main()
