#!/usr/bin/env python3
# booking.py - يفتح الرابط الذي أرسله المستخدم

import json
import os
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

print(f"🚀 بدء التشغيل - {datetime.now()}")

# الرابط من التطبيق (من secrets.BOOKING_URL)
BOOKING_URL = os.environ.get("BOOKING_URL", "")

if not BOOKING_URL:
    print("❌ لا يوجد رابط! لم يرسل التطبيق أي رابط")
    exit(1)

print(f"🔗 الرابط المستلم: {BOOKING_URL}")

def book_appointment(url):
    """يفتح الرابط ويضغط على زر 'قم بالحجز الأن'"""
    
    result = {
        "success": False,
        "queue_number": None,
        "doctor_name": None,
        "clinic_name": None,
        "booking_time": datetime.now().isoformat(),
        "status": "لم يتم التنفيذ"
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # 1. فتح الرابط الذي أرسله المستخدم
            print(f"🌐 فتح الرابط: {url}")
            page.goto(url, wait_until='domcontentloaded')
            page.wait_for_timeout(3000)
            print("✅ تم تحميل الصفحة")
            
            # 2. الضغط على زر "قم بالحجز الأن"
            print("🔍 البحث عن زر الحجز...")
            
            # البحث عن الزر
            btn = page.locator("a:has-text('قم بالحجز الأن')")
            if btn.count() == 0:
                btn = page.locator("a:has-text('احجز الآن')")
            if btn.count() == 0:
                btn = page.locator("a[href*='Booking']")
            
            if btn.count() == 0:
                raise Exception("❌ لم أجد زر 'قم بالحجز الأن'")
            
            btn.click()
            print("✅ تم الضغط على زر الحجز")
            page.wait_for_timeout(5000)
            
            # 3. استخراج رقم الدور
            page_content = page.content()
            number_match = re.search(r'<h1[^>]*>(\d+)</h1>', page_content)
            if number_match:
                result["queue_number"] = number_match.group(1)
                print(f"📋 رقم الدور: {result['queue_number']}")
            else:
                # محاولة بديلة
                number_match = re.search(r'رقمك[^\d]*(\d+)', page_content)
                if number_match:
                    result["queue_number"] = number_match.group(1)
                    print(f"📋 رقم الدور: {result['queue_number']}")
            
            # استخراج اسم الدكتور
            doctor_match = re.search(r'<h5[^>]*>(د/[^<]+)</h5>', page_content)
            if doctor_match:
                result["doctor_name"] = doctor_match.group(1).strip()
                print(f"👨‍⚕️ الطبيب: {result['doctor_name']}")
            
            # استخراج اسم العيادة
            clinic_match = re.search(r'<h6[^>]*>([^<]+)</h6>', page_content)
            if clinic_match:
                result["clinic_name"] = clinic_match.group(1).strip()
                print(f"🏥 العيادة: {result['clinic_name']}")
            
            if result["queue_number"]:
                result["success"] = True
                result["status"] = "✅ تم الحجز!"
            else:
                result["status"] = "❌ لم أجد رقم الدور"
                
        except Exception as e:
            print(f"❌ خطأ: {e}")
            result["status"] = f"❌ خطأ: {str(e)[:80]}"
            
        finally:
            browser.close()
    
    return result

def main():
    result = book_appointment(BOOKING_URL)
    
    # حفظ النتيجة
    with open("booking_result.json", "w", encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("\n📊 النتيجة النهائية:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
