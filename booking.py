#!/usr/bin/env python3
# booking.py - حجز تلقائي في مستشفى إيليت باستخدام Playwright

import json
import os
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

print(f"🚀 بدء تشغيل حجز مستشفى إيليت - {datetime.now()}")

# قراءة الرابط من متغيرات البيئة
BOOKING_URL = os.environ.get("BOOKING_URL", "https://www.elitehospital.org/Booking/Find?culture=ar")
print(f"🔗 BOOKING_URL: {BOOKING_URL}")

def book_appointment(booking_url):
    """تنفيذ عملية الحجز باستخدام Playwright"""
    
    result = {
        "success": False,
        "queue_number": None,
        "doctor_name": None,
        "clinic_name": None,
        "booking_time": datetime.now().isoformat(),
        "status": "لم يتم التنفيذ",
        "error": None
    }
    
    with sync_playwright() as playwright:
        # تشغيل المتصفح بدون واجهة (أسرع)
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
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        page.set_default_timeout(30000)
        
        try:
            print(f"🌐 فتح الرابط: {booking_url}")
            page.goto(booking_url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(2000)  # انتظار قصير
            print("✅ تم تحميل الصفحة")
            
            # ========== البحث عن زر "قم بالحجز الأن" ==========
            print("🔍 البحث عن زر الحجز...")
            
            # محاولة العثور على الزر بطرق متعددة (أسرع)
            booking_btn = None
            selectors = [
                "a:has-text('قم بالحجز الأن')",
                "a:has-text('احجز الآن')",
                "a[href*='Booking']",
                "a.cta"
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
                raise Exception("لم يتم العثور على زر 'قم بالحجز الأن'")
            
            # الضغط على الزر
            booking_btn.click()
            print("✅ تم الضغط على زر الحجز")
            page.wait_for_timeout(3000)
            
            # ========== استخراج رقم الدور ==========
            print("🔍 استخراج رقم الدور...")
            page_content = page.content()
            queue_number = None
            
            # أنماط البحث عن الرقم
            patterns = [
                r'<h1[^>]*>(\d+)</h1>',
                r'<h2[^>]*>(\d+)</h2>',
                r'رقمك[^\d]*(\d+)',
                r'رقم الدور[^\d]*(\d+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_content, re.IGNORECASE)
                if match:
                    queue_number = match.group(1)
                    break
            
            if queue_number is None:
                # البحث في العناصر الظاهرة
                elements = page.locator('h1, h2, h3, .number')
                for i in range(elements.count()):
                    text = elements.nth(i).inner_text().strip()
                    if text.isdigit() and len(text) <= 4:
                        queue_number = text
                        break
            
            if queue_number is None:
                raise Exception("لم يتم العثور على رقم الدور")
            
            print(f"📋 رقم الدور: {queue_number}")
            result["queue_number"] = queue_number
            
            # ========== استخراج اسم الطبيب ==========
            doctor_match = re.search(r'<h5[^>]*>(د/[^<]+)</h5>', page_content)
            if doctor_match:
                result["doctor_name"] = doctor_match.group(1).strip()
                print(f"👨‍⚕️ الطبيب: {result['doctor_name']}")
            
            # ========== استخراج اسم العيادة ==========
            clinic_match = re.search(r'<h6[^>]*>([^<]+)</h6>', page_content)
            if clinic_match:
                result["clinic_name"] = clinic_match.group(1).strip()
                print(f"🏥 العيادة: {result['clinic_name']}")
            
            result["success"] = True
            result["status"] = "✅ تم الحجز بنجاح!"
            
        except PlaywrightTimeout as e:
            print(f"❌ انتهاء المهلة: {e}")
            result["status"] = "❌ انتهاء المهلة"
            result["error"] = str(e)
            
        except Exception as e:
            print(f"❌ خطأ: {e}")
            result["status"] = f"❌ خطأ: {str(e)[:80]}"
            result["error"] = str(e)
            
        finally:
            browser.close()
    
    return result

def save_result(result):
    """حفظ النتيجة في ملف JSON (مثل grades.json)"""
    # حفظ في الموقع الرئيسي
    with open("booking_result.json", "w", encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # حفظ في مجلد docs/api لـ GitHub Pages
    os.makedirs("docs/api", exist_ok=True)
    with open("docs/api/status.json", "w", encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("✅ تم حفظ النتيجة في booking_result.json")
    return True

def main():
    print("=" * 60)
    print("🏥 حجز مستشفى إيليت التلقائي (Playwright)")
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
    else:
        print(f"❌ الخطأ: {result.get('error', 'خطأ غير معروف')}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
