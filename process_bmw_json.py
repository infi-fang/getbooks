import json
from pathlib import Path

base = Path(__file__).resolve().parent
source_path = base / 'bmw_source_data.json'
cleaned_path = base / 'bmw_cleaned_data.json'

with source_path.open('r', encoding='utf-8') as f:
    data = json.load(f)

items = data.get('list', data if isinstance(data, list) else [])
cleaned = []

for item in items:
    cleaned.append({
        'productId': item.get('productId'),
        'productName': item.get('productName'),
        'albumPics': item.get('albumPics'),
        'settlementPrice': item.get('settlementPrice'),
        'title': item.get('title'),
        'cashType': item.get('cashType'),
        'unionName': item.get('unionName'),
        'publishStatus': item.get('publishStatus'),
        'virtualType': item.get('virtualType'),
    })

with cleaned_path.open('w', encoding='utf-8') as f:
    json.dump(cleaned, f, ensure_ascii=False, indent=2)

print(f'Processed {len(cleaned)} items and wrote {cleaned_path}')
