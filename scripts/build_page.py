#!/usr/bin/env python3
import re
import sys
from datetime import datetime, timezone, timedelta

import yaml
from jinja2 import Template

JST = timezone(timedelta(hours=9))
WEEKDAYS_JA = ['月', '火', '水', '木', '金', '土', '日']

# webchangesのジョブ判定(verb)を画面表示用のラベルに変換
STATUS_LABELS = {
    'NEW': '新規検知',
    'CHANGED': '更新あり',
    'ERROR': '取得エラー',
    'UNCHANGED': '変更なし',
    'UNCHANGED,ERROR_ENDED': 'エラー復旧',
}

# raw_output.txt冒頭のサマリー部の行 (例: "01. CHANGED: ジョブ名" / "CHANGED: ジョブ名")
SUMMARY_LINE_RE = re.compile(r'^(?:\d+\.\s+)?([A-Z][A-Z, _]*)\s*:\s*(.+)$')


def parse_jobs_yaml(filepath):
    jobs = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for doc in yaml.safe_load_all(f):
            if doc and isinstance(doc, dict) and 'url' in doc:
                jobs.append({
                    'name': doc.get('name', doc['url']),
                    'url': doc['url'],
                })
    return jobs


def parse_webchanges_summary(raw_output_file):
    """webchangesの標準出力(raw_output.txt)先頭のサマリー部から、ジョブ名 -> 判定結果を取り出す。

    サマリー部は '='*N の区切り線2本の間にあり、変更が全く無い実行では出力自体が空になる。
    """
    statuses = {}
    try:
        with open(raw_output_file, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        return statuses

    separators = [i for i, line in enumerate(lines) if line and set(line) == {'='}]
    if len(separators) < 2:
        return statuses

    for line in lines[separators[0] + 1:separators[1]]:
        m = SUMMARY_LINE_RE.match(line.strip())
        if m:
            verb, name = m.groups()
            # 'CHANGED,REPEATED' や 'ERROR,REPEATED' 等は先頭の判定に丸める
            statuses[name] = verb.split(',')[0]
    return statuses


def format_jst_datetime(dt):
    weekday = WEEKDAYS_JA[dt.weekday()]
    return f"{dt.year}年{dt.month:02d}月{dt.day:02d}日（{weekday}）、{dt.hour:02d}時{dt.minute:02d}分{dt.second:02d}秒（日本時間）"


def main():
    jobs_file = sys.argv[1] if len(sys.argv) > 1 else 'jobs.yaml'
    raw_output_file = sys.argv[2] if len(sys.argv) > 2 else 'raw_output.txt'
    template_file = sys.argv[3] if len(sys.argv) > 3 else 'templates/index.html.j2'
    output_file = sys.argv[4] if len(sys.argv) > 4 else 'index.html'

    jobs = parse_jobs_yaml(jobs_file)
    statuses = parse_webchanges_summary(raw_output_file)

    sites = []
    for job in jobs:
        verb = statuses.get(job['name'], 'UNCHANGED')
        sites.append({
            'name': job['name'],
            'url': job['url'],
            'status': STATUS_LABELS.get(verb, verb),
            'changed': verb in ('NEW', 'CHANGED'),
            'error': verb == 'ERROR',
        })

    recent_updates = [site for site in sites if site['changed']]
    error_sites = [site for site in sites if site['error']]

    with open(template_file, 'r', encoding='utf-8') as f:
        template = Template(f.read())

    now_jst_formatted = format_jst_datetime(datetime.now(JST))

    rendered_html = template.render(
        generated_at=now_jst_formatted,
        recent_updates=recent_updates,
        error_sites=error_sites,
        sites=sites,
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(rendered_html)

    print(f"Successfully generated {output_file}")


if __name__ == '__main__':
    main()
