import requests
import json
import re
import os
from datetime import datetime


VK_TOKEN = os.environ.get("VK_TOKEN") 

VK_GROUPS = [
    "rr4mestakleva", 
    "pp4farmtrof", 
    "rr4pepper", 
    "pp4wikipedia", 
    "rf4map"
]

def normalize_wb(name):
    n = name.lower()
    if "комарин" in n: return "оз. Комариное"
    if "лосин" in n: return "оз. Лосиное"
    if "вьюн" in n: return "р. Вьюнок"
    if "острог" in n: return "оз. Старый Острог"
    if "бела" in n: return "р. Белая"
    if "куори" in n: return "оз. Куори"
    if "медвеж" in n: return "оз. Медвежье"
    if "волхов" in n: return "р. Волхов"
    if "донец" in n: return "р. Северский Донец"
    if "сура" in n or "суру" in n: return "р. Сура"
    if "архипелаг" in n: return "Ладожский архипелаг"
    if "ладожск" in n or "ладога" in n: return "Ладожское оз."
    if "янтар" in n: return "оз. Янтарное"
    if "ахтуб" in n: return "р. Ахтуба"
    if "медное" in n: return "оз. Медное"
    if "тунгус" in n: return "р. Нижняя Тунгуска"
    if "яма" in n or "яму" in n: return "р. Яма"
    if "норвеж" in n or "море" in n: return "Норвежское море"
    return name.title()

def clean_text(text):
    groups_to_remove = ["@rr4mestakleva", "@pp4farmtrof", "@rr4pepper", "@pp4wikipedia", "@rf4map", "@fishzones"]
    for g in groups_to_remove:
        text = re.sub(rf'(?i){g}\s*', '', text)
    
    text = text.replace('Вся информация по РР4 на нашем сайте - https://rr4farmtrof.com/', '')
    text = text.replace('Вся информация по РР4 на нашем сайте - http://rr4farmtrof.com/', '')
    text = text.replace('Вся информация по РР4 на нашем сайте - rr4farmtrof.com/', '')
    text = text.replace('Вся информация по РР4 на нашем сайте - rr4farmtrof.com', '')
    text = text.replace('Правила публикации постов: vk.com/-pravila', '')
    text = text.replace('Правила публикации постов: vk.com/-pravila', '')
    text = text.replace('Добавить пост: https://vk.com/rf4map?w=wall-134739321_11470/', '')
    text = text.replace('Добавить пост: https://vk.com/rf4map?w=wall-134739321_11470', '')
    text = text.replace('Правила публикации постов: vk.com/-rules/', '')
    text = text.replace('Правила публикации постов: vk.com/-rules', '')
    
    
    text = re.sub(r'#\w+', '', text)
    
    stop_words = [
        "- Автор:", "Автор:", "ПРЕДЛОЖИТЬ ПОСТ", "ПОИСК ТОЧКИ", 
        "БОЛЬШЕ ТОЧЕК", "СПАСИБО", "Условия:", "ПРЕДЛОЖИТЬ", 
        "Понравился пост?", "БОТ для поиска точек", "Наш сайт", "Наш Discord", "Наш дискорд"
    ]
    for word in stop_words:
        if word in text:
            text = text.split(word)[0] 
            
    text = text.replace('|  |', '|').replace('| - |', '|').replace('-  -', '-').strip(' |-\n')
    text = re.sub(r'\s+', ' ', text)
    return text

def parse_vk():
    print("Подключаемся к VKontakte...")
    
    if not VK_TOKEN:
        print("Ошибка: Токен ВК не найден в переменных окружения!")
        return

    old_spots = {}
    if os.path.exists('spots.json'):
        try:
            with open('spots.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for spot in data:
                    old_spots[spot['id']] = spot
            print(f"Загружено из базы: {len(old_spots)} старых точек.")
        except Exception as e:
            print("Ошибка чтения старой базы, создаем новую.")

    url = "https://api.vk.com/method/wall.get"
    new_posts_found = 0

    for group in VK_GROUPS:
        print(f"\n--- Парсинг группы: {group} ---")
        
        for offset in [0, 100, 200]:
            try:
                params = {
                    "domain": group, 
                    "count": 100,
                    "offset": offset,
                    "access_token": VK_TOKEN,  
                    "v": "5.193"               
                }
                response = requests.get(url, params=params).json()

                if "error" in response:
                    print(f"[-] Ошибка ВК ({group}): {response['error']['error_msg']}")
                    break

                for post in response["response"]["items"]:
                    post_id = f"{group}_{post.get('id')}"
                    
                    if post_id in old_spots:
                        continue

                    raw_text = post.get("text", "")
                    if not raw_text: continue

                    clean_description = clean_text(raw_text)
                    lower_clean_text = clean_description.lower()

                    spam_words = ["розыгрыш", "призовое место", "магазина", "барахолка", "купить", "промокод", "скидка", "рублей", "купон"]
                    if any(word in lower_clean_text for word in spam_words):
                        continue

                    spot_tag = "Обычная"
                    if any(word in lower_clean_text for word in ["трофей", "троф", "трофе", "синяк", "синь", "голуб", "голубая","звезд", "звёзд","⭐"]):
                        spot_tag = "Трофей"
                    elif any(word in lower_clean_text for word in ["фарм", "фар"]):
                        spot_tag = "Фарм"
                    elif any(word in lower_clean_text for word in ["высед", "высе", "высиж"]):
                        spot_tag = "Высед"

                    coords_match = re.search(r'(\d{1,3}\s*:\s*\d{1,3})', raw_text)
                    square_match = re.search(r'Квадрат:\s*([A-ZА-Я0-9, ]+)', raw_text, re.IGNORECASE)
                    if coords_match:
                        coordinates = coords_match.group(1).replace(" ", "") 
                    elif square_match:
                        coordinates = square_match.group(1).strip()
                    else:
                        continue 

                    waterbody_name = "Не указан"
                    wb_match = re.search(r'Водоем:\s*([^|]+)', raw_text, re.IGNORECASE)
                    if wb_match:
                        wb_temp = wb_match.group(1).strip()
                        if wb_temp and wb_temp != "-" and len(wb_temp) > 1:
                            waterbody_name = wb_temp
                    
                    if waterbody_name == "Не указан":
                        tags = re.findall(r'#([a-zа-яё0-9_]+)', raw_text.lower())
                        ignore_tags = ['трофей', 'фарм', 'гайд', 'сборка', 'вопрос', 'местаклева', 'рр4', 'rr4', 'rf4map', 'pp4farmtrof', 'rr4pepper', 'pp4wikipedia']
                        for tag in tags:
                            tag = tag.replace('_rf4map', '').replace('rf4_', '').replace('pp4_', '') 
                            if tag not in ignore_tags:
                                waterbody_name = tag
                                break
                    
                    waterbody_name = normalize_wb(waterbody_name)

                    images_list = []
                    attachments = post.get("attachments", [])
                    for att in attachments:
                        if att["type"] == "photo":
                            sizes = att["photo"]["sizes"]
                            best_photo = max(sizes, key=lambda x: x["width"])
                            images_list.append(best_photo["url"])

                    timestamp = post.get("date", 0)
                    date_str = datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y')

                    spot = {
                        "id": post_id,
                        "timestamp": timestamp,
                        "date": date_str,
                        "waterbody": waterbody_name,
                        "tag": spot_tag,
                        "coordinates": coordinates,
                        "description": clean_description,
                        "images": images_list
                    }
                    
                    old_spots[post_id] = spot
                    new_posts_found += 1
                    
            except Exception as e:
                print(f"Ошибка парсинга VK ({group}): {e}")
                
    print(f"\nВсего добавлено новых точек: {new_posts_found}")

    all_spots = list(old_spots.values())
    all_spots.sort(key=lambda x: x['timestamp'], reverse=True)

    all_spots = all_spots[:10000]

    with open('spots.json', 'w', encoding='utf-8') as f:
        json.dump(all_spots, f, ensure_ascii=False, indent=4)
        
    print(f"Готово! В базе spots.json сейчас {len(all_spots)} точек.")

if __name__ == "__main__":
    parse_vk()
