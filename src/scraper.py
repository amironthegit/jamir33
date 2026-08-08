import re, os, json, base64, urllib.request
from datetime import datetime, timezone

CHANNEL = "v2ray1_ng"
TELEGRAM_WEB_URL = f"https://t.me/s/{CHANNEL}"
META_PATH = "output/meta.json"

CONFIG_REGEX = re.compile(
    r'(?:vmess|vless|trojan|ss|hysteria2?):\/\/[A-Za-z0-9+\/=]+(?:#[^\s<]*)?',
    re.IGNORECASE
)

MESSAGE_BLOCK_REGEX = re.compile(
    r'<div[^>]*class="tgme_widget_message_wrap"[^>]*>.*?'
    r'data-post="([^"]+)".*?'
    r'<div class="tgme_widget_message_text[^"]*">(.*?)</div>',
    re.DOTALL | re.IGNORECASE
)

def fetch_channel_html():
    req = urllib.request.Request(TELEGRAM_WEB_URL, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode('utf-8', errors='ignore')

def load_last_processed_post():
    try:
        with open(META_PATH) as f:
            return json.load(f).get("last_post_id")
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def extract_new_configs(html, last_post_id):
    blocks = MESSAGE_BLOCK_REGEX.findall(html)
    if not blocks:
        print("⚠️ No message blocks found"); return [], None
    new_configs, newest_id = [], None
    for post_id, text_block in reversed(blocks):
        if last_post_id and post_id == last_post_id:
            print(f"🛑 Reached last processed post: {post_id}"); break
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
    print(f"🔍 Scraping {TELEGRAM_WEB_URL} ...")
    last = load_last_processed_post()
    print(f"📌 Last processed: {last or '(first run)'}")
    html = fetch_channel_html()
    configs, newest = extract_new_configs(html, last)
    if not configs:
        print("⏭️ No new configs. Keeping sub.txt unchanged."); return
    print(f"✅ {len(configs)} new configs | Newest post: {newest}")
    os.makedirs("output", exist_ok=True)
    with open("output/sub.txt", "w") as f: f.write(encode_subscription(configs))
    with open("output/meta.json", "w") as f:
        json.dump({"count": len(configs), "updated_at": datetime.now(timezone.utc).isoformat(),
                   "source": CHANNEL, "last_post_id": newest}, f, indent=2)
    print("💾 Subscription updated")

if __name__ == "__main__":
    main()
