import json
import time
import os

def calculate_verified():
    spots_file = 'spots.json'
    verified_file = 'verified.json'

    if not os.path.exists(spots_file):
        print(f"Файл {spots_file} не найден. Сохраняем пустой список в {verified_file}.")
        with open(verified_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        return

    try:
        with open(spots_file, 'r', encoding='utf-8') as f:
            spots = json.load(f)
    except Exception as e:
        print(f"Ошибка при чтении {spots_file}: {e}")
        with open(verified_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        return

    cutoff_time = time.time() - 7 * 86400
    recent_spots = [spot for spot in spots if spot.get('timestamp', 0) > cutoff_time]

    print(f"Всего точек в базе: {len(spots)}")
    print(f"Точек за последние 7 дней: {len(recent_spots)}")

    if not recent_spots:
        print("За последние 7 дней точек не найдено. Сохраняем пустой список.")
        top3 = []
    else:
        # Сортировка по количеству лайков по убыванию
        recent_spots.sort(key=lambda x: x.get('likes', 0), reverse=True)
        top3 = recent_spots[:3]

        print(f"\nТоп-{len(top3)} проверенных точек (по лайкам):")
        for i, spot in enumerate(top3, 1):
            print(f"{i}. [{spot.get('waterbody')}] {spot.get('coordinates')} | Лайков: {spot.get('likes', 0)}, Просмотров: {spot.get('views', 0)} (ID: {spot.get('id')})")

    with open(verified_file, 'w', encoding='utf-8') as f:
        json.dump(top3, f, ensure_ascii=False, indent=4)

    print(f"\nФайл {verified_file} успешно обновлен (сохранено {len(top3)} точек).")

if __name__ == '__main__':
    calculate_verified()
