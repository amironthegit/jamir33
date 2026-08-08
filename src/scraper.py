import re, os, json, base64, urllib.request, urllib.error, sys
from datetime import datetime, timezone

CHANNEL = "v2ray1_ng"
TELEGRAM_WEB_URL = f"https://t.me/s/{CHANNEL}"
META_PATH = "output/meta.json"
OUTPUT_DIR = "output"

CONFIG_REGEX = re.compile(r'(?:vmess|vless|trojan|ss|hysteria2?):\/\/[A-Za-z0-9+\/=]+(?:#[^\s<]*)?', re.IGNORECASE)
MESSAGE_BLOCK_REGEX = re.compile(r'<div[^>]*class="tgme_widget_message_wrap"[^>]*>.*?data-post="([^"]+)".*?<div class="tgme_widget_message_text[^"]*">(.*?)</div>', re.DOTALL | re.IGNORECASE)

def fetch_channel_html():
    # هدرهای شبیه‌ساز مرورگر واقعی برای دور زدن فیلترهای تلگرام
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
            return resp.read().decode('utf-8', errors='ignore')
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error: {e.code} {e.reason}")
        print("Telegram is likely blocking GitHub Actions IPs.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Network Error: {e}")
        sys.exit(1)

def load_last_processed_post():
    try:
        with open(META_PATH) as f: return json.load(f).get("last_post_id")
    except: return None

def extract_new_configs(html, last_post_id):
    blocks = MESSAGE_BLOCK_REGEX.findall(html)
    if not blocks: return [], None
    new_configs, newest_id = [], None
    for post_id, text_block in reversed(blocks):
        if last_post_id and post_id == last_post_id: break
        configs = CONFIG_REGEX.findall(text_block)
        cleaned, seen = [], set()
        for cfg in configs:
            cfg = cfg.strip().replace('&amp;', '&')
            cfg = re.sub(r'<[^>]*>', '', cfg)
            if cfg not in seen and len(cfg) > 15:
                seen.add(cfg); cleaned.append(cfg)
        if cleaned:
            if newest_id is None: newest_id = post_id
            new_configs.extend(cleaned)
    return new_configs, newest_id

def encode_subscription(configs):
    return base64.b64encode('\n'.join(configs).encode('utf-8')).decode('ascii')

def main():
    print(f"Scraping {TELEGRAM_WEB_URL} ...")
    html = fetch_channel_html()
    last = load_last_processed_post()
    configs, newest = extract_new_configs(html, last)
    if not configs:
        print("No new configs found.")
        # فایل خالی نمی‌سازیم تا دیپلوی قبلی دست‌نخورده بماند
        sys.exit(0) 
        
    now = datetime.now(timezone.utc).isoformat()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(os.path.join(OUTPUT_DIR, 'sub.txt'), 'w') as f: f.write(encode_subscription(configs))
    with open(os.path.join(OUTPUT_DIR, 'meta.json'), 'w') as f:
        json.dump({"count": len(configs), "updated_at": now, "source": CHANNEL, "last_post_id": newest}, f)
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w') as f:
        f.write(f'<h1>Active</h1><p>Configs: {len(configs)}</p><p>Updated: {now}</p>')
    print("✅ Success! Files generated.")

if __name__ == "__main__":
    main()
