if shops_data:
                regions = []
                entries = []
                
                for item in shops_data:
                    addr = item['address']
                    # 萃取「市」級（如 東京都八王子市、宮城県仙台市、大阪府岸和田市）
                    match = re.search(r'^(.*?([都道府縣県].*?市|.*?市|.*?区))', addr)
                    if match:
                        region = match.group(1).strip()
                        region = re.sub(r'\s+', '', region)
                        if region not in regions:
                            regions.append(region)
                    
                    entries.append(f"{item['name']}\n地址：{addr}")
                
                # 按照您要求的格式：最上方是總結，接著空兩行，然後是店鋪清單（移除了標題與底部連結）
                summary_line = ",".join(regions)
                content = f"{summary_line}\n\n" + "\n\n".join(entries)
            else:
                content = f"🔍 目前頁面未偵測到有貨店舖，請點擊連結確認：\n{URL}"
