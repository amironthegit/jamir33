import re, os, json, base64, sys
import html as html_lib
import urllib.request, urllib.error
from datetime import datetime, timezone

CHANNEL = "v2ray1_ng"
TELEGRAM_WEB_URL = f"https://t.me/s/{CHANNEL}"
META_PATH = "output/meta.json"
OUTPUT_DIR = "output"

# ✅ Regex اصلاح‌شده: کل لینک تا رسیدن به فاصله یا تگ HTML
CONFIG_REGEX = re.compile(
    r'(?:vmess|vless|trojan|ss|ssr|hysteria2?|tuic)://[^\s<>"\']+',
    re.IGNORECASE
)

def fetch_channel_html():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    }
    req = urllib.request.Request(TELEGRAM_WEB_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode('utf-8', errors='ignore')
            print(f"Fetched {len(data)} bytes")
            return data
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"Network Error: {e}")
        sys.exit(1)

def load_last_processed_post():
    try:
        with open(META_PATH) as f:
            return json.load(f).get("last_post_id")
    except Exception:
        return None

def split_posts(html):
    # ✅ روش جدید و مطمئن: تقسیم صفحه بر اساس data-post
    parts = re.split(r'data-post="([^"]+)"', html)
    posts = []
    i = 1
    while i + 1 < len(parts):
        posts.append((parts[i], parts[i + 1]))
        i += 2
    return posts

def clean_config(raw):
    cfg = html_lib.unescape(raw).strip()
    return cfg.rstrip('.,;\'"')

def extract_new_configs(html, last_post_id):
    posts = split_posts(html)
    print(f"Posts found in page: {len(posts)}")
    if not posts:
        return [], None
    new_configs, newest_id = [], None
    for post_id, chunk in reversed(posts):
        if last_post_id and post_id == last_post_id:
            print(f"Stop at last processed post: {post_id}")
            break
        cleaned, seen = [], set()
        for raw in CONFIG_REGEX.findall(chunk):
            cfg = clean_config(raw)
            if cfg not in seen and len(cfg) > 20:
                seen.add(cfg)
                cleaned.append(cfg)
        if cleaned:
            print(f"Post {post_id}: {len(cleaned)} configs")
            if newest_id is None:
                newest_id = post_id
            new_configs.extend(cleaned)
    return new_configs, newest_id

def encode_subscription(configs):
    return base64.b64encode('\n'.join(configs).encode('utf-8')).decode('ascii')

def main():
    print(f"Scraping {TELEGRAM_WEB_URL} ...")
    html = fetch_channel_html()
    last = load_last_processed_post()
    print(f"Last processed: {last or '(first run)'}")
    configs, newest = extract_new_configs(html, last)
    if not configs:
        print("No new configs found.")
        sys.exit(0)
    now = datetime.now(timezone.utc).isoformat()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, 'sub.txt'), 'w') as f:
        f.write(encode_subscription(configs))
    with open(os.path.join(OUTPUT_DIR, 'meta.json'), 'w') as f:
        json.dump({"count": len(configs), "updated_at": now,
                   "source": CHANNEL, "last_post_id": newest}, f, indent=2)
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w') as f:
        f.write(f'<h1>Active</h1><p>Configs: {len(configs)}</p><p>Updated: {now}</p>')
    print(f"Success! {len(configs)} configs saved. Newest post: {newest}")
    print(f"Sample: {configs[0][:80]}...")

if __name__ == "__main__":
    main()
