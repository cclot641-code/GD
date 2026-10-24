import os
from playwright.sync_api import sync_playwright
import requests

PRODUCT_CODE = "4570118196217"
URL = f"https://gashapon.jp/shop/gplus_list.php?product_code={PRODUCT_CODE}"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def check_stock():
    with sync_playwright() as p:
        # 啟動無頭瀏覽器 (Headless Browser)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # 前往目標網頁
            page.goto(URL, timeout=30000)
            
            # 等待頁面上的店鋪區塊載入（根據該網頁結構，等待包含店名的元素出現）
            # 這裡我們等待頁面加載完成並抓取所有店舖名稱
            page.wait_for_selector("body", timeout=10000)
            
            # 額外等待 3 秒讓 AJAX 動態請求完全渲染
            page.wait_for_timeout(3000)
            
            # 透過 JavaScript 抓取所有店名與地址的文字
            # 根據該網站的排版，店名通常會在標題或特定的區塊中
            shops = page.evaluate("""() => {
                const results = [];
                // 尋找所有可能的店鋪名稱元素（包含官方商店名稱等）
                // 依據該網站，店名常出現在帶有特定字樣的標題或區塊
                const elements = document.querySelectorAll('h3, .shop_name, div');
                elements.forEach(el => {
                    const text = el.innerText.trim();
                    // 過濾出包含分店或店舖特徵的文字
                    if ((text.includes('店') || text.includes('ショップ')) && text.length < 50 && !results.includes(text)) {
                        results.push(text);
                    }
                });
                return results;
            }""")

            browser.close()

            # 整理並過濾掉重複或無關的字串
            valid_shops = [s for s in shops if "店" in s or "ショップ" in s]
            
            if valid_shops:
                message = f"🚨 **【扭蛋庫存即時更新】** 🚨\n找到以下有貨的店舖：\n" + "\n".join([f"• {shop}" for shop in valid_shops[:10]])
                message += f"\n\n🔗 點此查看完整清單：\n{URL}"
            else:
                # 如果沒抓到具體店名，至少提供網址
                message = f"🔍 扭蛋頁面已更新，請直接點擊查看有貨店舖：\n{URL}"

            send_to_discord(message)

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
