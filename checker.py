import os
import re
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright
import requests

PRODUCT_CODE = "4570118196217"
URL = f"https://gashapon.jp/shop/gplus_list.php?product_code={PRODUCT_CODE}"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def check_stock():
    # 1. 取得當前日本時間 (JST, UTC+9)
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    current_hour = now_jst.hour
    current_minute = now_jst.minute
    current_total_minutes = current_hour * 60 + current_minute

    # 2. 設定運作時間範圍：07:00 至 24:00 (即 420 分鐘到 1440 分鐘)
    start_limit = 7 * 60      # 07:00
    end_limit = 24 * 60       # 24:00

    if not (start_limit <= current_total_minutes < end_limit):
        print(f"目前時間 ({now_jst.strftime('%H:%M')}) 不在營運時間內 (07:00 - 24:00)，跳過執行。")
        return

    print(f"目前時間 ({now_jst.strftime('%H:%M')}) 在營運時間內，開始即時執行爬蟲...")

    # 3. 立即執行爬蟲
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
            
            shops_data = page.evaluate("""() => {
                const results = [];
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                
                for (let i = 0; i < lines.length; i++) {
                    let line = lines[i];
                    
                    // 放寬條件：只要結尾是「店」或者包含特定關鍵字，且小於 80 字元，即視為店名
                    if ((line.endsWith('店') || line.includes('ガシャポン') || line.includes('デパート') || line.includes('ショップ')) && 
                        line.length < 80 && 
                        !line.includes('検索') && 
                        !line.includes('公式アカウント') && 
                        !line.includes('どこ？')) {
                        
                        let shopName = line;
                        let address = "";
                        
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

            if shops_data:
                regions = []
                entries = []
                
                for item in shops_data:
                    addr = item['address']
                    match = re.search(r'^(.*?([都道府縣県].*?市|.*?市|.*?区))', addr)
                    if match:
                        region = match.group(1).strip()
                        region = re.sub(r'\s+', '', region)
                        if region not in regions:
                            regions.append(region)
                    
                    entries.append(f"{item['name']}\n地址：{addr}")
                
                summary_line = ",".join(regions)
                content = f"{summary_line}\n\n" + "\n\n".join(entries)
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
