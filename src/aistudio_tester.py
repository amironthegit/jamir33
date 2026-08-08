import urllib.request
import ssl
import concurrent.futures
import threading

# دامنه واقعی که AI Studio برای اجرای مدل به آن متصل می‌شود
TEST_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT = 8  # حداکثر زمان انتظار برای هر سرور (ثانیه)
MAX_WORKERS = 20  # تعداد تست‌های همزمان
TARGET_COUNT = 10  # 🎯 به محض پیدا کردن ۱۰ کانفیگ سالم، متوقف شو

def test_single_config(proxy_url):
    """
    یک کانفیگ را تست می‌کند.
    اگر به API گوگل وصل شد (هر کدی غیر از Timeout یا Proxy Error)، True برمی‌گرداند.
    """
    try:
        # تنظیمات پروکسی
        proxy_handler = urllib.request.ProxyHandler({
            'http': proxy_url,
            'https': proxy_url
        })
        
        # نادیده گرفتن خطاهای SSL (چون برخی سرورها سرتیفیکیت خودامضا دارند)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))
        
        req = urllib.request.Request(TEST_URL, headers={
            'User-Agent': 'Mozilla/5.0'
        })
        
        # ارسال درخواست
        with opener.open(req, timeout=TIMEOUT) as resp:
            return True
            
    except urllib.error.HTTPError as e:
        # کدهای 400, 401, 403 یعنی به سرور گوگل رسیدیم ولی کلید API نداریم -> یعنی پروکسی سالم است!
        if e.code in (400, 401, 403, 404):
            return True
        return False
    except Exception:
        # Timeout, Connection Refused, Proxy Error -> پروکسی خراب است
        return False

def filter_working_configs(configs):
    """
    لیست کانفیگ‌ها را می‌گیرد و فقط آنهایی که به AI Studio وصل می‌شوند را برمی‌گرداند.
    🛑 به محض رسیدن به TARGET_COUNT متوقف می‌شود.
    """
    print(f"🧪 Testing configs against Google AI Studio API (Target: {TARGET_COUNT})...")
    working_configs = []
    lock = threading.Lock()
    stop_event = threading.Event()
    
    def worker(cfg):
        if stop_event.is_set():
            return None
            
        result = test_single_config(cfg)
        
        if result:
            with lock:
                if len(working_configs) < TARGET_COUNT:
                    working_configs.append(cfg)
                    print(f"✅ PASS ({len(working_configs)}/{TARGET_COUNT}): {cfg[:50]}...")
                    
                    # 🛑 اگر به هدف رسیدیم، پرچم توقف را بالا ببر
                    if len(working_configs) >= TARGET_COUNT:
                        print(f"🎯 Target reached! Stopping further tests.")
                        stop_event.set()
                        return cfg
        return None

    # اجرای موازی
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(worker, cfg): cfg for cfg in configs}
        
        # منتظر می‌مانیم تا یا همه تمام شوند یا stop_event فعال شود
        for future in concurrent.futures.as_completed(futures):
            if stop_event.is_set():
                # بقیه تسک‌های در حال اجرا را لغو کن (اگر هنوز شروع نشده باشند)
                for f in futures:
                    f.cancel()
                break
                
    print(f"✨ Result: Found {len(working_configs)} working configs for AI Studio.")
    return working_configs
