#!/usr/bin/env python3
# booking.py - حجز تلقائي في مستشفى إيليت

import json
import os
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

print(f"🚀 بدء تشغيل حجز مستشفى إيليت - {datetime.now()}")

# قراءة الرابط من متغيرات البيئة
BOOKING_URL = os.environ.get("BOOKING_URL", "https://www.elitehospital.org/Booking/Find?culture=ar")
DEVICE_TOKEN = os.environ.get("DEVICE_TOKEN", "")

# محاولة قراءة من ملف config.json
if os.path.exists("config.json"):
    try:
        with open("config.json", "r", encoding='utf-8') as f:
            config = json.load(f)
            BOOKING_URL = config.get("booking_url", BOOKING_URL)
            DEVICE_TOKEN = config.get("device_token", DEVICE_TOKEN)
            print("✅ تم تحميل الإعدادات من config.json")
    except Exception as e:
        print(f"⚠️ فشل تحميل config.json: {e}")

print(f"🔗 BOOKING_URL: {BOOKING_URL}")
print(f"📱 DEVICE_TOKEN: {'✅' if DEVICE_TOKEN else '❌'}")

def setup_browser(playwright):
    """إعداد متصفح Playwright"""
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--window-size=1920,1080'
        ]
    )
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
    )
    page = context.new_page()
    page.set_default_timeout(30000)
    return browser, page

def book_appointment(booking_url):
    """تنفيذ عملية الحجز"""
    with sync_playwright() as playwright:
        browser = None
        result = {
            "success": False,
            "queue_number": None,
            "doctor_name": None,
            "clinic_name": None,
            "booking_time": None,
            "status": "لم يتم التنفيذ",
            "error": None
        }
        
        try:
            browser, page = setup_browser(playwright)
            print(f"🌐 فتح الرابط: {booking_url}")
            
            page.goto(booking_url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(3000)
            print("✅ تم تحميل الصفحة")
            
            # البحث عن زر "قم بالحجز الأن"
            print("🔍 البحث عن زر الحجز...")
            booking_btn = None
            selectors = [
                "a:has-text('قم بالحجز الأن')",
                "a:has-text('احجز الآن')",
                "a[href*='Booking']",
                "a.cta",
                "button:has-text('حجز')"
            ]
            
            for selector in selectors:
                try:
                    btn = page.locator(selector)
                    if btn.count() > 0 and btn.is_visible():
                        booking_btn = btn
                        print(f"✅ تم العثور على زر الحجز")
                        break
                except:
                    continue
            
            if booking_btn is None:
                # محاولة البحث عن أي رابط يحتوي على كلمة حجز
                all_links = page.locator('a')
                for i in range(all_links.count()):
                    text = all_links.nth(i).inner_text()
                    if 'حجز' in text or 'Booking' in text:
                        booking_btn = all_links.nth(i)
                        print(f"✅ تم العثور على زر من النص: {text}")
                        break
            
            if booking_btn is None:
                raise Exception("لم يتم العثور على زر 'قم بالحجز الأن'")
            
            booking_btn.click()
            print("✅ تم الضغط على زر الحجز")
            page.wait_for_timeout(5000)
            
            # استخراج رقم الدور
            print("🔍 استخراج رقم الدور...")
            page_content = page.content()
            queue_number = None
            
            patterns = [
                r'<h1[^>]*>(\d+)</h1>',
                r'<h2[^>]*>(\d+)</h2>',
                r'رقمك[^\d]*(\d+)',
                r'رقم الدور[^\d]*(\d+)',
                r'Your number[^\d]*(\d+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_content, re.IGNORECASE)
                if match:
                    queue_number = match.group(1)
                    break
            
            if queue_number is None:
                # البحث في العناصر
                elements = page.locator('h1, h2, h3, span.number')
                for i in range(elements.count()):
                    text = elements.nth(i).inner_text().strip()
                    if text.isdigit() and len(text) <= 4:
                        queue_number = text
                        break
            
            if queue_number is None:
                raise Exception("لم يتم العثور على رقم الدور")
            
            print(f"📋 رقم الدور: {queue_number}")
            result["queue_number"] = queue_number
            
            # استخراج اسم الطبيب
            doctor_match = re.search(r'<h5[^>]*>(د/[^<]+)</h5>', page_content)
            if doctor_match:
                result["doctor_name"] = doctor_match.group(1).strip()
                print(f"👨‍⚕️ الطبيب: {result['doctor_name']}")
            
            # استخراج اسم العيادة
            clinic_match = re.search(r'<h6[^>]*>([^<]+)</h6>', page_content)
            if clinic_match:
                result["clinic_name"] = clinic_match.group(1).strip()
                print(f"🏥 العيادة: {result['clinic_name']}")
            
            result["success"] = True
            result["booking_time"] = datetime.now().isoformat()
            result["status"] = "✅ تم الحجز بنجاح!"
            
        except PlaywrightTimeout as e:
            print(f"❌ انتهاء المهلة: {e}")
            result["status"] = "❌ انتهاء المهلة"
            result["error"] = str(e)
            
        except Exception as e:
            print(f"❌ خطأ: {e}")
            result["status"] = f"❌ خطأ: {str(e)[:50]}"
            result["error"] = str(e)
            
        finally:
            if browser:
                browser.close()
                
        return result

def save_result(result):
    """حفظ النتيجة في ملف JSON"""
    try:
        with open("booking_result.json", "w", encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("✅ تم حفظ النتيجة في booking_result.json")
        return True
    except Exception as e:
        print(f"❌ فشل حفظ الملف: {e}")
        return False

def main():
    print("=" * 60)
    print("🏥 حجز مستشفى إيليت التلقائي")
    print("=" * 60)
    
    start_time = time.time()
    result = book_appointment(BOOKING_URL)
    
    print(f"\n⏱️ وقت التنفيذ: {time.time() - start_time:.2f} ثانية")
    save_result(result)
    
    print("\n📊 النتيجة:")
    print(f"📋 الحالة: {result['status']}")
    if result['success']:
        print(f"📋 رقم الدور: {result['queue_number']}")
        if result.get('doctor_name'):
            print(f"👨‍⚕️ الطبيب: {result['doctor_name']}")
        if result.get('clinic_name'):
            print(f"🏥 العيادة: {result['clinic_name']}")

if __name__ == "__main__":
    main()
