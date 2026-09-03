"""Authorized one-time +$2 update, fixed to the saved current-price baseline."""
import json
import os
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = json.loads((ROOT / 'before.json').read_text())
SHOP_ID = BASELINE['shop_id']
previous = runpy.run_path(str(ROOT.parent / '20260902T223452Z-minus-8/update_prices.py'))
request = previous['request']
variant_payload = previous['variant_payload']
unchanged = previous['unchanged_product_fields']


def save(name, value):
    path = ROOT / name
    path.write_text(json.dumps(value, indent=2))
    os.chmod(path, 0o600)


def main():
    products = BASELINE['products']
    assert len(products) == 5 and SHOP_ID == 28779955
    for original in products:
        assert original['blueprint_id'] == 6 and original['print_provider_id'] == 99
        assert original['visible'] and original['external']['id']
        identifier = original['id']
        path = f'shops/{SHOP_ID}/products/{identifier}.json'
        current = request('GET', path)
        target = variant_payload(original)
        for variant in target:
            if variant['is_enabled']:
                variant['price'] += 200
        if variant_payload(current) != target:
            assert not current['is_locked']
            assert variant_payload(current) == variant_payload(original), 'Concurrent price changes'
            assert not unchanged(original, current), 'Concurrent product changes'
            save(identifier + '-request.json', {'variants': target})
            request('PUT', path, {'variants': target})
        after = request('GET', path)
        save(identifier + '-after.json', after)
        assert variant_payload(after) == target
        assert not unchanged(original, after), 'Unexpected non-price changes'
        result = {'id': identifier, 'verified': True, 'enabled_variants': sum(v['is_enabled'] for v in after['variants']), 'prices': {v['title']: v['price'] for v in after['variants'] if v['is_enabled']}, 'non_price_fields_unchanged': True}
        save(identifier + '-verification.json', result)
        print(json.dumps(result), flush=True)
    for original in products:
        identifier = original['id']
        receipt_path = ROOT / (identifier + '-etsy-sync-receipt.json')
        if receipt_path.exists():
            continue
        payload = {'title': False, 'description': False, 'images': False, 'variants': True, 'tags': False, 'keyFeatures': False, 'shipping_template': False}
        save(identifier + '-etsy-sync-request.json', payload)
        result = request('POST', f'shops/{SHOP_ID}/products/{identifier}/publish.json', payload)
        save(receipt_path.name, result)
        print(json.dumps({'id': identifier, 'etsy_sync': result}), flush=True)

if __name__ == '__main__':
    main()
