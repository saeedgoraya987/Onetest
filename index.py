import requests
from random_username.generate import generate_username
import random
import time
import string
from datetime import datetime
import os
import traceback
import telebot
from telebot import types
from io import BytesIO
import threading

BOT_TOKEN = "8474094509:AAGqWT_fyBOQpY2gwIQ5O3GShT5-wdKeVbI"
ADMIN_IDS = [6109365101, 5090817443]  # Replace with actual admin Telegram IDs

bot = telebot.TeleBot(BOT_TOKEN)

INSTAGRAM_BASE = "https://www.instagram.com/"
CREATE_ENDPOINT = "https://www.instagram.com/accounts/web_create_ajax/attempt/"
SMS_ENDPOINT = "https://i.instagram.com/api/v1/accounts/send_signup_sms_code/"

PROXY_LIST = [
    "http://user_1764739960_aa5c-zone-abc-region-NG:qzJcOGeQ@as.a455dd28c5cb69e2.abcproxy.vip:4950",
]

RATE_LIMIT_DELAY = 180
USE_PROXY_AFTER_RATE_LIMIT = True
MAX_IP_FLAGS_BEFORE_STOP = 5
BATCH_SIZE = 10
BATCH_DELAY = random.randint(120, 180)

processing_lock = threading.Lock()
active_processes = {}
proxy_index = 0

def get_next_proxy():
    global proxy_index
    if not PROXY_LIST:
        return None
    
    proxy = PROXY_LIST[proxy_index % len(PROXY_LIST)]
    proxy_index += 1
    return {"http": proxy, "https": proxy}

def gen_password():
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(12)) + str(random.randint(1000, 9999))

def is_admin(uid):
    return uid in ADMIN_IDS

def check_ip_status():
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        r = session.get(INSTAGRAM_BASE, timeout=10)
        
        if r.status_code == 403:
            return "blocked", "IP blocked (403 Forbidden)"
        elif r.status_code == 429:
            return "rate_limited", "Too many requests (429)"
        elif r.status_code != 200:
            return "error", f"Unexpected status: {r.status_code}"
        
        csrf = session.cookies.get("csrftoken")
        mid = session.cookies.get("mid")
        
        if not csrf or not mid:
            return "flagged", "No cookies received - IP likely flagged"
        
        return "ok", "IP working normally"
    except Exception as e:
        return "error", f"Check failed: {str(e)}"

def send_sms(phone, username=None, firstname=None, password=None, force_proxy=False):
    ts = int(datetime.now().timestamp())
    phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    if not password:
        password = gen_password()
    if not username:
        username = generate_username(1)[0] + str(random.randint(1, 1000))
    if not firstname:
        firstname = generate_username(1)[0]
    
    retry = 0
    max_retry = 3
    
    while retry < max_retry:
        try:
            session = requests.Session()
            
            if force_proxy and PROXY_LIST:
                proxy = get_next_proxy()
                if proxy:
                    session.proxies.update(proxy)
                    proxy_str = list(proxy.values())[0].split('@')[1] if '@' in list(proxy.values())[0] else list(proxy.values())[0]
                else:
                    proxy_str = "Direct"
            else:
                proxy_str = "Direct"
            
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.instagram.com/",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://www.instagram.com",
            })
            
            r = session.get(INSTAGRAM_BASE, timeout=10)
            
            if r.status_code == 403:
                return {
                    "ok": False,
                    "err": "IP blocked (403)",
                    "user": username,
                    "pass": password,
                    "name": firstname,
                    "limited": False,
                    "ip_flagged": True,
                }
            
            if r.status_code == 429:
                return {
                    "ok": False,
                    "err": "Rate limit (429)",
                    "user": username,
                    "pass": password,
                    "name": firstname,
                    "limited": True,
                    "ip_flagged": False,
                }
            
            if r.status_code != 200:
                retry += 1
                time.sleep(3)
                continue
            
            csrf = session.cookies.get("csrftoken")
            mid = session.cookies.get("mid")
            
            if not csrf or not mid:
                return {
                    "ok": False,
                    "err": "Cookie fetch failed",
                    "user": username,
                    "pass": password,
                    "name": firstname,
                    "limited": False,
                    "ip_flagged": True,
                }
            
            post_headers = {
                "x-csrftoken": csrf,
                "referer": "https://www.instagram.com/accounts/emailsignup/",
                "x-instagram-ajax": "1",
                "x-ig-app-id": "936619743392459",
                "x-requested-with": "XMLHttpRequest",
            }
            
            data = {
                "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:{ts}:{password}",
                "phone_number": phone,
                "username": username,
                "first_name": firstname,
                "opt_into_one_tap": "false",
                "client_id": mid,
                "seamless_login_enabled": "1",
            }
            
            r1 = session.post(CREATE_ENDPOINT, data=data, headers=post_headers)
            
            if r1.status_code == 429:
                return {
                    "ok": False,
                    "err": "Rate limit (429)",
                    "user": username,
                    "pass": password,
                    "name": firstname,
                    "limited": True,
                    "ip_flagged": False,
                }
            
            if r1.status_code == 403:
                return {
                    "ok": False,
                    "err": "Blocked (403)",
                    "user": username,
                    "pass": password,
                    "name": firstname,
                    "limited": False,
                    "ip_flagged": True,
                }
            
            try:
                j1 = r1.json()
                if j1.get("status") == "fail":
                    msg = j1.get("message", "Creation failed")
                    if "spam" in str(j1) or "feedback_required" in msg:
                        return {
                            "ok": False,
                            "err": f"Blocked: {msg}",
                            "user": username,
                            "pass": password,
                            "name": firstname,
                            "limited": True,
                            "ip_flagged": True,
                        }
            except:
                pass
            
            sms_data = {
                "device_id": mid,
                "phone_number": phone,
            }
            
            r2 = session.post(SMS_ENDPOINT, data=sms_data, headers=post_headers)
            
            if r2.status_code == 429:
                return {
                    "ok": False,
                    "err": "SMS rate limit (429)",
                    "user": username,
                    "pass": password,
                    "name": firstname,
                    "limited": True,
                    "ip_flagged": False,
                }
            
            if r2.status_code == 403:
                return {
                    "ok": False,
                    "err": "SMS blocked (403)",
                    "user": username,
                    "pass": password,
                    "name": firstname,
                    "limited": False,
                    "ip_flagged": True,
                }
            
            try:
                j2 = r2.json()
                if j2.get("status") == "ok":
                    return {
                        "ok": True,
                        "user": username,
                        "pass": password,
                        "name": firstname,
                        "phone": phone,
                        "proxy": proxy_str,
                        "limited": False,
                        "ip_flagged": False,
                    }
                else:
                    return {
                        "ok": False,
                        "err": j2.get("message", "SMS failed"),
                        "user": username,
                        "pass": password,
                        "name": firstname,
                        "limited": False,
                        "ip_flagged": False,
                    }
            except Exception as e:
                return {
                    "ok": False,
                    "err": f"Parse error: {str(e)}",
                    "user": username,
                    "pass": password,
                    "name": firstname,
                    "limited": False,
                    "ip_flagged": False,
                }
                
        except Exception as e:
            retry += 1
            if retry >= max_retry:
                return {
                    "ok": False,
                    "err": f"Network error: {str(e)}",
                    "user": username,
                    "pass": password,
                    "name": firstname,
                    "limited": False,
                    "ip_flagged": False,
                }
            time.sleep(2)
    
    return {
        "ok": False,
        "err": "Max retries",
        "user": username,
        "pass": password,
        "name": firstname,
        "limited": False,
        "ip_flagged": False,
    }

@bot.message_handler(commands=['start'])
def start_handler(msg):
    uid = msg.from_user.id
    
    txt = "🤖 Instagram SMS Bot\n\n"
    txt += "Commands:\n"
    txt += "/start - Start\n"
    txt += "/send - Send SMS\n"
    txt += "/status - Status\n"
    txt += "/checkip - Check IP status\n"
    txt += "/help - Help\n\n"
    
    if is_admin(uid):
        txt += f"✅ Authorized (ID: {uid})"
    else:
        txt += f"❌ Unauthorized (ID: {uid})"
    
    bot.reply_to(msg, txt)

@bot.message_handler(commands=['help'])
def help_handler(msg):
    txt = "📖 Instructions\n\n"
    txt += "Send .txt file with phone numbers:\n"
    txt += "+911234567890\n"
    txt += "+919876543210\n\n"
    txt += "Features:\n"
    txt += "- Smart proxy rotation (1 per number)\n"
    txt += "- Auto 2-3 min delay per 10 numbers\n"
    txt += "- Auto rate limit handling\n"
    txt += "- Detailed logs\n"
    txt += "- Real-time updates"
    
    bot.reply_to(msg, txt)

@bot.message_handler(commands=['checkip'])
def checkip_handler(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Admin only")
        return
    
    bot.reply_to(msg, "🔍 Checking IP status...")
    
    status, message = check_ip_status()
    
    if status == "ok":
        txt = "✅ IP Status: GOOD\n\n"
        txt += f"✓ {message}\n"
        txt += "You can send SMS without proxy"
    elif status == "flagged":
        txt = "⚠️ IP Status: FLAGGED\n\n"
        txt += f"⚠ {message}\n"
        txt += "Recommendation: Use proxy"
    elif status == "blocked":
        txt = "❌ IP Status: BLOCKED\n\n"
        txt += f"✗ {message}\n"
        txt += "Action required: Use proxy or change IP"
    elif status == "rate_limited":
        txt = "🚫 IP Status: RATE LIMITED\n\n"
        txt += f"⏱ {message}\n"
        txt += f"Wait {RATE_LIMIT_DELAY}s or use proxy"
    else:
        txt = "⚠️ IP Status: ERROR\n\n"
        txt += f"Error: {message}"
    
    bot.reply_to(msg, txt)

@bot.message_handler(commands=['status'])
def status_handler(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Admin only")
        return
    
    txt = "📊 Status\n\n"
    txt += f"✅ Bot running\n"
    txt += f"🔐 Admins: {len(ADMIN_IDS)}\n"
    txt += f"🌐 Proxies: {len(PROXY_LIST)}\n"
    txt += f"📦 Batch size: {BATCH_SIZE} numbers\n"
    txt += f"⏱ Batch delay: {BATCH_DELAY}s\n"
    txt += f"🔄 Proxy rotation: Sequential\n"
    txt += f"⚙️ Active tasks: {len(active_processes)}\n\n"
    txt += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    bot.reply_to(msg, txt)

@bot.message_handler(commands=['send'])
def send_handler(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Unauthorized")
        return
    
    bot.reply_to(msg, "📤 Send .txt file with phone numbers")

@bot.message_handler(content_types=['document'])
def doc_handler(msg):
    uid = msg.from_user.id
    
    if not is_admin(uid):
        bot.reply_to(msg, "❌ Unauthorized")
        return
    
    doc = msg.document
    
    if not doc.file_name.endswith('.txt'):
        bot.reply_to(msg, "❌ Send .txt file only")
        return
    
    with processing_lock:
        if uid in active_processes:
            bot.reply_to(msg, "⚠️ Already processing. Wait.")
            return
        active_processes[uid] = True
    
    try:
        bot.reply_to(msg, "📥 Downloading...")
        
        file_info = bot.get_file(doc.file_id)
        file_data = bot.download_file(file_info.file_path)
        
        phones = []
        for line in file_data.decode('utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                phones.append(line)
        
        if not phones:
            bot.reply_to(msg, "❌ No numbers found")
            with processing_lock:
                active_processes.pop(uid, None)
            return
        
        # INITIAL LIVE MESSAGE
        progress_msg = bot.send_message(msg.chat.id, "⏳ Preparing...")
        
        results = []
        use_proxy = True
        rate_hits = 0
        ip_flags = 0
        success = 0
        failed = 0
        
        total = len(phones)
        
        for i, phone in enumerate(phones, 1):
            
            # RUN YOUR EXISTING SMS FUNCTION
            res = send_sms(phone, force_proxy=use_proxy)
            res["phone"] = phone
            res["idx"] = i
            results.append(res)

            # UPDATE STATS
            if res.get("ok"):
                success += 1
            else:
                failed += 1

            if res.get("limited"):
                rate_hits += 1

            if res.get("ip_flagged"):
                ip_flags += 1
                if ip_flags >= MAX_IP_FLAGS_BEFORE_STOP:
                    bot.send_message(msg.chat.id, f"❌ Stopped after {ip_flags} IP flags!")
                    break

            # PROGRESS BAR
            percent = int((i / total) * 100)
            bar = make_progress_bar(percent)

            progress_text = (
                f"{bar}\n"
                f"🔄 Processing: {percent}% ({i}/{total})\n\n"
                f"📊 **Stats**\n"
                f"✅ Success: {success}\n"
                f"❌ Failed: {failed}\n"
                f"⚠️ Rate Limits: {rate_hits}\n"
                f"🚫 IP Flags: {ip_flags}\n\n"
                f"📱 Last processed: {phone}"
            )

            # UPDATE LIVE MESSAGE
            try:
                bot.edit_message_text(
                    chat_id=msg.chat.id,
                    message_id=progress_msg.message_id,
                    text=progress_text,
                    parse_mode="Markdown"
                )
            except:
                pass

            # RATE LIMIT COOL DOWN
            if res.get("limited"):
                time.sleep(RATE_LIMIT_DELAY)

            # BATCH COOLDOWN
            if i % BATCH_SIZE == 0 and i < total:
                delay = random.randint(120, 180)
                time.sleep(delay)
            else:
                if i < total:
                    time.sleep(random.randint(3, 7))
        
        # BUILD LOG FILE
        log = "=" * 60 + "\n"
        log += "PROCESS LOG\n"
        log += f"Date: {datetime.now()}\n"
        log += "=" * 60 + "\n\n"

        ok_count = 0
        fail_count = 0
        
        for r in results:
            log += "-" * 40 + "\n"
            log += f"Phone: {r['phone']}\n"
            log += f"Status: {'SUCCESS' if r['ok'] else 'FAILED'}\n"
            if r['ok']:
                ok_count += 1
                log += f"Username: {r['user']}\n"
                log += f"Password: {r['pass']}\n"
                log += f"Name: {r['name']}\n"
                log += f"Proxy: {r.get('proxy', 'N/A')}\n"
            else:
                fail_count += 1
                log += f"Error: {r.get('err', 'Unknown')}\n"
                if r.get('ip_flagged'):
                    log += "IP_FLAGGED: YES\n"
            log += "-" * 40 + "\n\n"

        summary = (
            f"📊 **Summary**\n\n"
            f"Total: {len(phones)}\n"
            f"✅ Success: {ok_count}\n"
            f"❌ Failed: {fail_count}\n"
            f"⚠️ Rate limits: {rate_hits}\n"
            f"🚫 IP flags: {ip_flags}\n\n"
            f"📄 Log file below"
        )
        
        bot.send_message(msg.chat.id, summary)
        
        log_file = BytesIO(log.encode("utf-8"))
        log_file.name = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        bot.send_document(msg.chat.id, log_file, caption="📋 Complete log")
        
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ Error:\n{str(e)}")
        
    finally:
        with processing_lock:
            active_processes.pop(uid, None)

if __name__ == "__main__":
    print("="*50)
    print("🤖 Instagram SMS Bot Starting...")
    print("="*50)
    print(f"👤 Admins: {ADMIN_IDS}")
    print(f"🌐 Proxies loaded: {len(PROXY_LIST)}")
    print(f"📦 Batch size: {BATCH_SIZE} numbers")
    print(f"⏱  Batch delay: 2-3 minutes")
    print(f"🔄 Proxy: Sequential rotation")
    print(f"🚫 Max IP flags: {MAX_IP_FLAGS_BEFORE_STOP}")
    print("="*50)
    print("✅ Bot ready! Send /start in Telegram")
    print("="*50)
    
    bot.infinity_polling()
