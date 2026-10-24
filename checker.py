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
            
            # 直接在瀏覽器內部用 JavaScript 抓取所有店舖名稱與緊隨其後的地址
            shops_data = page.evaluate("""() => {
                const results = [];
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                
                // 尋找包含店名特徵的行
                for (let i = 0; i < lines.length; i++) {
                    let line = lines[i];
                    // 判斷是否為店名
                    if ((line.includes('ガシャポン') || line.includes('デパート') || line.includes('ショップ')) && 
                        line.length < 80 && 
                        !line.includes('検索') && 
                        !line.includes('公式アカウント') && 
                        !line.includes('どこ？')) {
                        
                        let shopName = line;
                        let address = "";
                        
                        // 往後尋找地址（通常包含都道府縣或市區町村）
                        for (let j = 1; j <= 3; j++) {
                            if (i + j < lines.length) {
                                let nextLine = lines[i + j];
                                if ((nextLine.includes('都') || nextLine.includes('道') || nextLine.includes('府') || nextLine.includes('県') || nextLine.includes('市')) &&
                                    !nextLine.includes('都道府県') && !nextLine.includes('お店をさがす')) {
                                    address = nextLine;
                                    break;
                                }
                            }
                        }
                        
                        if (address) {
                            results.push({ name: shopName, address: address });
                        }
                    }
                }
                return results;
            }""")

            browser.close()

            # 組合成乾淨的訊息格式
            if shops_data:
                entries = []
                for item in shops_data:
                    entries.append(f"{item['name']}\n地址：{item['address']}")
                
                content = "🚨 **【扭蛋庫存即時更新】** 🚨\n\n" + "\n\n".join(entries)
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
