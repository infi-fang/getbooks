"""把抓取下来的 pin_old.json 清洗成与 pin_source_data.json 一致的结构。

来源文件 pin_old.json 是多次接口响应片段被直接拼接产生的脏数据：
顶层没有闭合的大括号、中间重复出现 `"list": [`、末尾缺少收尾，
标准 json.load 会报 `Extra data`，所以需要容错扫描。
"""

import json
from pathlib import Path

base = Path(__file__).resolve().parent
source_path = base / 'pin_old.json'
schema_path = base / 'pin_source_data.json'
cleaned_path = base / 'pin_real_sorce_data.json'

# 与 pin_source_data.json 保持完全一致的字段顺序
CANONICAL_ORDER = [
    'id', 'uid', 'opAt', 'createAt', 'valid', 'delTag',
    'companyId', 'festivalId', 'festivalCategoryId',
    'name', 'itemSpuInfo', 'itemSkuBanned', 'itemSkuEnabled',
    'imageUrl', 'description',
    'standardPrice', 'marketPrice', 'itemPriceTotal', 'itemPriceLimit',
    'costPrice', 'priceDiscount', 'priceDiscountType',
    'sort', 'deliveryAddress', 'reviewStatus', 'tag',
    'autoRefreshPrice', 'pinucId', 'festivalPackageCode', 'costPriceError',
    'sourceFestivalPackageUid', 'needSyncItemInfo',
    'stockOutDesc', 'stockOutDescEn', 'diverted',
    'lastEditTime', 'excelCreate', 'packageCount',
    'stockOut', 'alreadyBought', 'offSale',
    'tagIds', 'itemSkuBanneds', 'itemSkuEnableds', 'template',
]


def parse_items(text):
    """容错扫描：捞出所有包含商品特征的 JSON 对象。"""
    decoder = json.JSONDecoder()
    items = []
    i, n = 0, len(text)
    while i < n:
        if text[i] == '{':
            try:
                obj, end = decoder.raw_decode(text, i)
            except ValueError:
                i += 1
                continue
            if isinstance(obj, dict) and 'itemSpuInfo' in obj and 'id' in obj:
                items.append(obj)
                i = end
                continue
        i += 1
    return items


def reorder(item):
    """按目标 schema 顺序输出字段，schema 之外的字段追加在末尾。"""
    ordered = {}
    for key in CANONICAL_ORDER:
        if key in item:
            ordered[key] = item[key]
    for key in item:
        if key not in ordered:
            ordered[key] = item[key]
    return ordered


def main():
    raw_items = parse_items(source_path.read_text(encoding='utf-8'))

    # 按 id 去重，保留首次出现
    seen = set()
    items = []
    for item in raw_items:
        if item['id'] in seen:
            continue
        seen.add(item['id'])
        items.append(item)

    # 淘汰无效 / 已删除数据
    items = [i for i in items if i.get('valid') is True and i.get('delTag') is not True]

    # 与源文件一致：按 sort 降序
    items.sort(key=lambda x: (-x.get('sort', 0), -x['id']))

    result = {'list': [reorder(i) for i in items]}

    with cleaned_path.open('w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f'Raw parsed: {len(raw_items)}, after dedup/filter: {len(items)}')
    print(f'Written to {cleaned_path}')


if __name__ == '__main__':
    main()
