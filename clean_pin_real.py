"""从 pin_real_sorce_data.json 提取精简字段，结构对齐 pin_cleaned_data.json。

目标结构为扁平数组，每条只保留商品展示与定价相关的 10 个字段。
"""

import json
from pathlib import Path

base = Path(__file__).resolve().parent
source_path = base / 'pin_real_sorce_data.json'
cleaned_path = base / 'pin_real_cleaned_data.json'

FIELDS = [
    'id', 'name', 'imageUrl',
    'standardPrice', 'marketPrice', 'itemPriceTotal', 'itemPriceLimit',
    'costPrice', 'priceDiscount', 'priceDiscountType',
]


def main():
    with source_path.open('r', encoding='utf-8') as f:
        data = json.load(f)

    items = data.get('list', data if isinstance(data, list) else [])
    cleaned = [{field: item.get(field) for field in FIELDS} for item in items]

    with cleaned_path.open('w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f'Processed {len(cleaned)} items and wrote {cleaned_path}')


if __name__ == '__main__':
    main()
