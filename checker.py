import os
from playwright.sync_api import sync_playwright
import requests

PRODUCT_CODE = "4570118196217"
URL = f"https://gashapon.jp/shop/gplus_list.php?product_code={PRODUCT_CODE}"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def check_stock():
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
            page.wait_for_timeout(4000)
            
            # 抓取頁面所有文字行
            shop_data = page.evaluate("""() => {
                const bodyText = document.body.innerText;
                return bodyText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            }""")

            browser.close()

            cleaned_shops = []
            i = 0
            while i < len(shop_data):
                line = shop_data[i]
                
                # 嚴格過濾導覽列、選單與頁尾版權文字
                footer_keywords = [
                    "スケジュール", "キャラクター", "ブランド", "ショップ", "ログイン", "さがす", 
                    "閉じる", "ホーム>", "ご利用規約", "プライバシーポリシー", "よくあるご質問", 
                    "お問合せ", "アンケート", "ウェブアクセシビリティ", "Do Not Sell", "BANDAI", 
                    "NAMCO", "無断転用", "登録商標", "コピーライト", "©", "All Rights Reserved"
                ]
                
                # 如果這行是純選單或版權宣告，直接跳過
                if any(fk in line for fk in footer_keywords) and not ("店" in line or "デパート" in line):
                    i += 1
                    continue
                
                # 識別店名（包含「店」或「デパート」的行）
                if ("ガシャポン" in line or "デパート" in line or "店" in line) and len(line) < 80:
                    shop_name = line
                    address = ""
                    
                    # 向下檢查接下來的 3 行內是否有地址
                    for j in range(1, 4):
                        if i + j < len(shop_data):
                            next_line = shop_data[i + j]
                            # 含有地址常見的行政區劃或字眼，且不是版權/選單文字
                            if any(p in next_line for p in ["都", "道", "府", "県", "市", "区", "町", "村", "丁目", "番"]) and not any(fk in next_line for fk in footer_keywords):
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
                content = f"🚨 **【扭蛋庫存即時更新】** 🚨\n找到以下有貨的店舖與地址：\n\n" + "\n\n".join(cleaned_shops)
                content += f"\n\n🔗 點此查看官方清單：\n{URL}"
            else:
                content = f"🔍 目前頁面未偵測到有貨店舖，請點擊連結確認：\n{URL}"

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
