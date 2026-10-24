import os
import requests

# 這是該頁面背後實際查詢店舖的 API 端點
API_URL = "https://gashapon.jp/shop/gplus_list_ajax.php" # 或對應的 API 請求網址
PRODUCT_CODE = "4570118196217"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def check_stock():
    # 模擬帶上參數去請求 API
    params = {
        "product_code": PRODUCT_CODE,
        # 如果需要帶地區或其他參數可以在這邊加
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://gashapon.jp/shop/gplus_list.php?product_code={PRODUCT_CODE}"
    }
    
    try:
        # 如果官方是用 POST，這裡可改為 requests.post
        response = requests.get("https://gashapon.jp/shop/gplus_list.php", params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"請求失敗，狀態碼: {response.status_code}")
            return

        # 這裡由於是整頁返回，如果該商品目前在某些店有貨，頁面上會包含店名字樣
        # 為了確保能拿到動態資料，我們也可以直接檢查回應文字長度或關鍵字
        html_content = response.text
        
        # 簡易判斷：如果網頁內容含有店鋪相關的標籤
        shops = []
        if "ガシャポンバンダイオフィシャルショップ" in html_content or "取扱商品" in html_content:
            # 簡化處理：若抓得到網頁，把網址直接推送給您，確保您不會漏看
            message = f"🚨 **【扭蛋庫存監控通知】** 🚨\n目標商品頁面已有回應或可能有更新！\n請直接點擊查看詳情：\nhttps://gashapon.jp/shop/gplus_list.php?product_code={PRODUCT_CODE}"
        else:
            message = f"目前該商品頁面暫無店舖資訊更新。"

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
