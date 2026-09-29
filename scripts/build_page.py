#!/usr/bin/env python3
import sys
import yaml
import requests
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from jinja2 import Template

JST = timezone(timedelta(hours=9))
WEEKDAYS_JA = ['月', '火', '水', '木', '金', '土', '日']

def parse_urls_yaml(filepath):
    sites = []
    with open(filepath, 'r', encoding='utf-8') as f:
        docs = yaml.safe_load_all(f)
        for doc in docs:
            if doc and isinstance(doc, dict) and 'url' in doc:
                sites.append({
                    'name': doc.get('name', doc['url']),
                    'url': doc['url'],
                    'last_modified': '不明',
                    'last_modified_dt': None,
                    'etag': '-'
                })
    return sites

def format_jst_datetime(dt):
    if not dt:
        return '不明'
    dt_jst = dt.astimezone(JST)
    weekday = WEEKDAYS_JA[dt_jst.weekday()]
    return f"{dt_jst.year}年{dt_jst.month:02d}月{dt_jst.day:02d}日（{weekday}）、{dt_jst.hour:02d}時{dt_jst.minute:02d}分{dt_jst.second:02d}秒（日本時間）"

def fetch_headers(sites):
    headers_info = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    for site in sites:
        url = site['url']
        last_modified_str = '不明'
        last_modified_dt = None
        etag = '-'
        try:
            res = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            if res.status_code >= 400:
                res = requests.get(url, headers=headers, timeout=10, stream=True)
            
            lm = res.headers.get('Last-Modified')
            if lm:
                try:
                    dt = parsedate_to_datetime(lm)
                    last_modified_dt = dt
                    last_modified_str = format_jst_datetime(dt)
                except Exception:
                    last_modified_str = lm
            
            et = res.headers.get('ETag')
            if et:
                etag = et.strip('"')
        except Exception as e:
            last_modified_str = f"取得失敗 ({type(e).__name__})"

        headers_info.append({
            'name': site['name'],
            'url': url,
            'last_modified': last_modified_str,
            'last_modified_dt': last_modified_dt,
            'etag': etag
        })
    return headers_info

def parse_recent_updates(sites_metadata):
    # Last-Modified日時が存在するサイトを新しい順（降順）にソート
    valid_sites = [s for s in sites_metadata if s['last_modified_dt'] is not None]
    sorted_sites = sorted(valid_sites, key=lambda s: s['last_modified_dt'], reverse=True)
    return sorted_sites

def main():
    urls_file = sys.argv[1] if len(sys.argv) > 1 else 'jobs.yaml'
    raw_output_file = sys.argv[2] if len(sys.argv) > 2 else 'raw_output.txt'
    template_file = sys.argv[3] if len(sys.argv) > 3 else 'templates/index.html.j2'
    output_file = sys.argv[4] if len(sys.argv) > 4 else 'index.html'

    # URL定義読み込み
    sites = parse_urls_yaml(urls_file)
    
    # 各URLのレスポンスヘッダー取得
    sites_metadata = fetch_headers(sites)

    # 最近更新された順にソートしたリスト
    recent_updates = parse_recent_updates(sites_metadata)

    # テンプレート読み込み
    with open(template_file, 'r', encoding='utf-8') as f:
        template = Template(f.read())

    # 現在日時 (JST)
    now_dt = datetime.now(JST)
    now_jst_formatted = format_jst_datetime(now_dt)

    # HTMLレンダリング
    rendered_html = template.render(
        generated_at=now_jst_formatted,
        recent_updates=recent_updates,
        sites=sites_metadata
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(rendered_html)
    
    print(f"Successfully generated {output_file}")

if __name__ == '__main__':
    main()
