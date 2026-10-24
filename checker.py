import os
import requests
from bs4 import BeautifulSoup

# 目標扭蛋網址
URL = "https://gashapon.jp/shop/gplus_list.php?product_code=4570118196217"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def check_stock():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"網頁請求失敗，狀態碼: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 抓取頁面上的店舖名稱與地址
        # 根據該網站結構，店舖名稱通常包含在特定的標題中
        shops = []
        # 尋找所有店舖名稱的標籤 (依據實際頁面結構調整)
        for shop in soup.select('.shop-item-class, h3, .shop_name'): # 可根據實際抓取情況微調
            text = shop.get_text().strip()
            if text and text not in shops:
                shops.append(text)

        # 組合訊息
        message = "🚨 **【扭蛋庫存監控通知】** 🚨\n發現頁面有內容更新或目前有庫存的店舖清單：\n"
        if shops:
            message += "\n".join(shops[:15]) # 避免訊息過長，取前15筆
        else:
            message += "目前頁面已可訪問，請點擊連結查看詳細店舖：\n" + URL

        # 發送到 Discord
        send_to_discord(message)

    except Exception as e:
        print(f"發生錯誤: {e}")

def send_to_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print("未設定 Discord Webhook")
        return
    
    data = {"content": message}
    requests.post(DISCORD_WEBHOOK_URL, json=data)

if __name__ == "__main__":
    check_stock()
