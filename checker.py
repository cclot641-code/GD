import os
import re
from playwright.sync_api import sync_playwright
import requests

PRODUCT_CODE = "4570118196217"
URL = f"https://gashapon.jp/shop/gplus_list.php?product_code={PRODUCT_CODE}"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# 日本行政區劃開頭，用來比對與精準抓取地址
PREFECTURES = r"(東京都|北海道|(京都|大阪)府|青森|岩手|宮城|秋田|山形|福島|茨城|栃木|群馬|埼玉|千葉|神奈川|新潟|富山|石川|福井|山梨|長野|岐阜|靜岡|愛知|三重|滋賀|兵庫|奈良|和歌山|鳥取|島根|岡山|廣島|山口|德島|香川|愛媛|高知|福岡|佐賀|長崎|熊本|大分|宮崎|鹿兒島|沖繩)"

def check_stock():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 設定視窗大小並帶上常見的 User-Agent
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        
        try:
            page.goto(URL, timeout=30000)
            page.wait_for_selector("body", timeout=10000)
            # 等待動態載入的店舖資料渲染完成
            page.wait_for_timeout(4000)
            
            # 使用 JavaScript 精確萃取店家名稱與地址
            shop_data = page.evaluate("""() => {
                const results = [];
                // 尋找包含店鋪資訊的區塊（通常是列表項或特有卡片）
                // 先嘗試定位每一個店舖卡片容器，若無則遍歷包含店名與地址的文字區塊
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                
                return lines;
            }""")

            browser.close()

            # 解析與過濾提取出的文字
            cleaned_shops = []
            i = 0
            while i < len(shop_data):
                line = shop_data[i]
                
                # 排除選單關鍵字
                ignored_keywords = ["スケジュール", "キャラクター", "ブランド", "ショップ", "ログイン", "さがす", "閉じる", "ホーム>", "ご利用規約"]
                if any(kw in line for kw in ignored_keywords):
                    i += 1
                    continue
                
                # 判斷是否為店名 (通常含有 ガシャポン、デパート、オフィシャルショップ 等)
                if ("ガシャポン" in line or "ショップ" in line or "デパート" in line) and len(line) < 60:
                    shop_name = line
                    address = ""
                    
                    # 往下檢查下一行或隔一行是否為日本地址（包含縣市名或郵遞區號）
                    for j in range(1, 4):
                        if i + j < len(shop_data):
                            next_line = shop_data[i + j]
                            # 判斷是否包含都道府縣字樣或地址特徵
                            if any(pref in next_line for pref in ["都", "道", "府", "県"]) and any(c.isdigit() for c in next_line):
                                address = next_line
                                break
                            elif "市" in next_line or "區" in next_line or "区" in next_line:
                                address = next_line
                                break
                    
                    entry = f"📍 **{shop_name}**"
                    if address:
                        entry += f"\n🏠 地址：{address}"
                    
                    if entry not in cleaned_shops:
                        cleaned_shops.append(entry)
                
                i += 1

            # 發送至 Discord
            if cleaned_shops:
                content = f"🚨 **【扭蛋庫存即時更新】** 🚨\n找到以下有貨的店舖與地址：\n\n" + "\n\n".join(cleaned_shops[:10])
                content += f"\n\n🔗 點此查看官方清單：\n{URL}"
            else:
                content = f"🔍 目前頁面更新，請點擊連結查看詳細店舖：\n{URL}"

            send_to_discord(content)

        except Exception as e:
            browser.close()
            print(f"爬取發生錯誤: {e}")

def send_to_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print("未設定 Discord Webhook")
        return
    
    data = {"content": message}
    requests.post(DISCORD_WEBHOOK_URL, json=data)

if __name__ == "__main__":
    check_stock()
