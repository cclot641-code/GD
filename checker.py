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

    # 2. 設定運作時間範圍：07:00 至 24:00
    start_limit = 7 * 60      # 07:00
    end_limit = 24 * 60       # 24:00

    if not (start_limit <= current_total_minutes < end_limit):
        print(f"目前時間 ({now_jst.strftime('%H:%M')}) 不在營運時間內 (07:00 - 24:00)，跳過執行。")
        return

    print(f"目前時間 ({now_jst.strftime('%H:%M')}) 在營運時間內，開始即時執行爬蟲...")

    # 3. 執行 Playwright 爬蟲
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
            
            # 全新反向邏輯：先找地址，再往回找店名
            shops_data = page.evaluate("""() => {
                const results = [];
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                
                for (let i = 0; i < lines.length; i++) {
                    let line = lines[i];
                    
                    // 判斷這一行是否為日本地址（必須包含「市」或「区」，且包含都道府縣其中一個字，排除垃圾提示句）
                    const isAddress = (line.includes('市') || line.includes('区')) && 
                                      (line.includes('都') || line.includes('道') || line.includes('府') || line.includes('県')) && 
                                      !line.includes('都道府県') && 
                                      !line.includes('お店をさがす') &&
                                      line.length < 100;
                    
                    if (isAddress) {
                        let address = line;
                        let shopName = "";
                        
                        // 往回找 1 到 2 行作為店名
                        for (let j = 1; j <= 2; j++) {
                            if (i - j >= 0) {
                                let prevLine = lines[i - j];
                                // 只要上一行不是網頁介面雜訊，就認定它是店名
                                if (prevLine.length < 80 && 
                                    !prevLine.includes('検索') && 
                                    !prevLine.includes('公式アカウント') && 
                                    !prevLine.includes('どこ？') && 
                                    !prevLine.includes('取扱商品') &&
                                    !prevLine.includes('km') &&
                                    !prevLine.includes('©')) {
                                    shopName = prevLine;
                                    break;
                                }
                            }
                        }
                        
                        if (shopName && address) {
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
                    # 萃取「市」級（如 東京都八王子市、静岡県静岡市葵区 等）
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
