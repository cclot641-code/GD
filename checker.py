from collections import Counter
import os
import re
import urllib.parse
from playwright.sync_api import sync_playwright
import requests

PRODUCT_CODE = "4570118196217"
URL = f"https://gashapon.jp/shop/gplus_list.php?product_code={PRODUCT_CODE}"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def send_to_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print("錯誤：未設定 DISCORD_WEBHOOK_URL 密鑰！")
        return
    
    data = {"content": message}
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    print(f"Discord 回應狀態碼: {response.status_code}")

def check_stock():
    print(f"開始爬取網址: {URL}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        
        try:
            page.goto(URL, timeout=30000)
            page.wait_for_selector("body", timeout=10000)
            page.wait_for_timeout(5000) # 多給一點時間讓 JS 渲染
            
            # 抓取頁面所有文字
            shop_data = page.evaluate("""() => {
                const bodyText = document.body.innerText;
                return bodyText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            }""")

            browser.close()
            print(f"成功抓取到的文字總行數: {len(shop_data)}")

            # 如果抓到的文字太少，代表可能被擋或尚未載入
            if len(shop_data) < 10:
                send_to_discord(f"⚠️ **【監控警報】** 抓到的網頁內容過少（可能被 Cloudflare 阻擋），請手動確認：\n{URL}")
                return

            shops_list = []
            i = 0
            while i < len(shop_data):
                line = shop_data[i]
                
                footer_keywords = [
                    "スケジュール", "キャラクター", "ブランド", "ショップ", "ログイン", "さがす", 
                    "閉じる", "ホーム>", "ご利用規約", "プライバシーポリシー", "よくあるご質問", 
                    "お問合せ", "アンケート", "ウェブアクセシビリティ", "Do Not Sell", "BANDAI", 
                    "NAMCO", "無断転用", "登録商標", "コピーライト", "©", "All Rights Reserved"
                ]
                
                if any(fk in line for fk in footer_keywords) and not ("店" in line or "デパート" in line):
                    i += 1
                    continue
                
                if ("ガシャポン" in line or "デパート" in line or "店" in line) and len(line) < 80:
                    shop_name = line
                    address = ""
                    
                    for j in range(1, 4):
                        if i + j < len(shop_data):
                            next_line = shop_data[i + j]
                            if any(p in next_line for p in ["都", "道", "府", "県", "市", "区", "町", "村"]) and not any(fk in next_line for fk in footer_keywords):
                                address = next_link = next_line
                                break
                    
                    if address:
                        match = re.search(r'(^.*?[都道府県].+?[市])', address)
                        city = match.group(1) if match else "其他地區"
                    else:
                        city = "未知地區"
                        address = "未抓取到詳細地址"

                    map_query = urllib.parse.quote(f"{shop_name} {address}")
                    map_url = f"https://www.google.com/maps/search/?api=1&query={map_query}"
                    
                    shops_list.append({
                        "name": shop_name,
                        "address": address,
                        "city": city,
                        "url": map_url
                    })
                i += 1

            if shops_list:
                city_counts = Counter([s['city'] for s in shops_list])
                summary_str = "/".join([f"{city}({count})" for city, count in city_counts.items()])
                
                content = f"🚨 **【扭蛋庫存即時更新】** 🚨\n{summary_str}\n\n------------------\n"
                entries = []
                for s in shops_list:
                    entry = f"📍 **{s['name']}**\n🏠 地址：{s['address']}\n🔗 [Google地圖導航]({s['url']})"
                    entries.append(entry)
                
                content += "\n\n".join(entries)
                content += f"\n\n🔗 官方查詢頁面：\n{URL}"
            else:
                content = f"🔍 腳本正常運行，但未在頁面中解析到符合條件的店舖名稱。\n官方查詢頁面：\n{URL}"

            send_to_discord(content)

        except Exception as e:
            browser.close()
            error_msg = f"❌ **【監控錯誤】** 執行發生例外錯誤：\n`{str(e)}`"
            print(error_msg)
            send_to_discord(error_msg)

if __name__ == "__main__":
    check_stock()
