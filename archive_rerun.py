# -*- coding: utf-8 -*-
"""补跑:批3(索引41-60条)小批次浓缩并合并进手册07"""
import re, os, sys, json, time, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_summary

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

def main():
    items = json.load(open(IDX, encoding='utf-8'))['items']
    items.sort(key=lambda x: x['date'], reverse=True)
    batch3 = items[40:60]
    print(f'补跑 {len(batch3)} 条(索引41-60)')
    lines = []
    for it in batch3:
        body = gen_summary.fetch_full(it['url'], max_chars=800)
        if body:
            lines.append(f"[{it['date']}][{it['source']}] {it['title']}\n正文: {body}")
        else:
            lines.append(f"[{it['date']}][{it['source']}] {it['title']}(正文获取失败)")
        time.sleep(0.15)
    # 拆成 2 个 10 条小批,每批重试3次
    all_points = {}
    for bi in range(0, len(batch3), 10):
        chunk = lines[bi:bi + 10]
        prompt = f'以下是近三年农机行业新闻(小批{bi//10+1}):\n\n' + '\n\n'.join(chunk)
        ok = False
        for attempt in range(3):
            try:
                resp = gen_summary.llm_chat(SYSTEM, prompt, max_tokens=6000, timeout=600)
                d = json.loads(resp)
                for t in d.get('topics', []):
                    all_points.setdefault(t.get('name', '其他'), []).extend(t.get('points', []))
                print(f'  小批{bi//10+1}: 成功(第{attempt+1}次)')
                ok = True
                break
            except Exception as e:
                print(f'  小批{bi//10+1}: 第{attempt+1}次失败 {str(e)[:50]}')
                time.sleep(3)
        if not ok:
            print(f'  小批{bi//10+1}: 放弃(3次失败)')
        time.sleep(1)
    if not all_points:
        print('无结果,退出')
        return
    # 合并进手册(在"相关"前插入)
    txt = open(OUT, encoding='utf-8').read()
    insert = []
    for name, points in all_points.items():
        insert.append(f'## {name}(补跑)')
        for p in points:
            insert.append(f'- {p}')
        insert.append('')
    txt = txt.replace('## 相关', '\n'.join(insert) + '## 相关')
    open(OUT, 'w', encoding='utf-8').write(txt)
    print(f'已合并,总主题数: {len(all_points)}')

if __name__ == '__main__':
    main()
