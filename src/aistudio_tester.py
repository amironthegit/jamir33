import urllib.request
import ssl
import concurrent.futures

# دامنه واقعی که AI Studio برای اجرای مدل به آن متصل می‌شود
TEST_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT = 8  # حداکثر زمان انتظار برای هر سرور (ثانیه)
MAX_WORKERS = 20  # تعداد تست‌های همزمان

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
            # اگر هر پاسخی بگیریم (حتی 403 یا 401)، یعنی شبکه وصل است و بلاک نیست
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
    """
    print(f"🧪 Testing {len(configs)} configs against Google AI Studio API...")
    working_configs = []
    
    # اجرای موازی برای سرعت بالا
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # نگاشت کانفیگ به نتیجه تست
        future_to_config = {executor.submit(test_single_config, cfg): cfg for cfg in configs}
        
        for future in concurrent.futures.as_completed(future_to_config):
            cfg = future_to_config[future]
            try:
                if future.result():
                    working_configs.append(cfg)
                    print(f"✅ PASS: {cfg[:50]}...")
                else:
                    print(f"❌ FAIL: {cfg[:50]}...")
            except Exception:
                pass
                
    print(f"✨ Result: {len(working_configs)} out of {len(configs)} configs can access AI Studio.")
    return working_configs
