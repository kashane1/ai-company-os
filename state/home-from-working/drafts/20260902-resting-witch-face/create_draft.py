"""Create one unpublished witch shirt from the existing Gildan template."""
import base64
import hashlib
import json
import os
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHOP_ID = 28779955
TEMPLATE_ID = '6a988f0a00aa8684080e906c'
ART = Path('/Users/kashane/Downloads/resting-witch-face1.png')
TITLE = 'Resting Witch Face Shirt, Funny Halloween Witch Graphic Tee, Spooky Season Gift'
api = runpy.run_path('state/home-from-working/pricing/20260902T223452Z-minus-8/update_prices.py')
request = api['request']


def save(name, value):
    path = ROOT / name
    path.write_text(json.dumps(value, indent=2))
    os.chmod(path, 0o600)


def main():
    listing = request('GET', f'shops/{SHOP_ID}/products.json?limit=50')
    assert not listing.get('next_page_url'), 'Review full pagination before creating'
    matches = [p for p in listing['data'] if p['title'] == TITLE]
    if matches:
        assert len(matches) == 1
        save('created-product.json', matches[0])
        print(json.dumps({'existing_draft_id': matches[0]['id'], 'visible': matches[0]['visible']}))
        return
    assert not (ROOT / 'create-attempted.json').exists(), 'Reconcile prior attempt before another POST'
    template = request('GET', f'shops/{SHOP_ID}/products/{TEMPLATE_ID}.json')
    assert template['blueprint_id'] == 6 and template['print_provider_id'] == 99
    assert min(v['price'] for v in template['variants'] if v['is_enabled']) == 1799
    save('template.json', template)
    content = ART.read_bytes()
    assert len(content) < 5 * 1024 * 1024
    save('artwork.json', {'path': str(ART), 'sha256': hashlib.sha256(content).hexdigest(), 'width_px': 1024, 'height_px': 1536, 'placement_inches': [8, 12], 'dpi': 128})
    if (ROOT / 'upload.json').exists():
        upload = json.loads((ROOT / 'upload.json').read_text())
    else:
        upload = request('POST', 'uploads/images.json', {'file_name': ART.name, 'contents': base64.b64encode(content).decode()})
        save('upload.json', upload)
    assert upload['width'] == 1024 and upload['height'] == 1536
    description = (
        'Resting witch face.\n\n'
        'A stern witch, a crooked green hat, and bold gold lettering give this shirt its dry Halloween humor. '
        'The detailed, vintage-inspired illustration is made for spooky-season outfits, casual Halloween gatherings, '
        'and anyone whose expression does the talking.\n\n'
        'Printed on a Gildan 5000 Heavy Cotton T-shirt, this tee has a comfortable classic fit and durable midweight feel.\n\n'
        'PRODUCT FEATURES' + template['description'].split('PRODUCT FEATURES', 1)[1]
    )
    tags = ['resting witch face', 'witch face shirt', 'funny witch shirt', 'halloween shirt', 'witch graphic tee', 'spooky season shirt', 'witchy gift', 'halloween humor', 'sarcastic shirt', 'vintage witch art', 'fall graphic tee', 'gothic witch shirt', 'halloween gift']
    assert len(tags) == 13 and len(set(tags)) == 13 and all(len(t) <= 20 for t in tags)
    variants = [{k:v[k] for k in ('id','price','is_enabled','is_default')} for v in template['variants']]
    payload = {
        'title': TITLE,
        'description': description,
        'safety_information': template['safety_information'],
        'tags': tags,
        'blueprint_id': 6,
        'print_provider_id': 99,
        'variants': variants,
        'print_areas': [{
            'variant_ids': [v['id'] for v in variants],
            'placeholders': [{
                'position': 'front',
                'images': [{'id': upload['id'], 'x': 0.5, 'y': 0.05 + 1800/4919, 'scale': 2400/3951, 'angle': 0}],
            }],
        }],
        'external': {'shipping_template_id': template['external']['shipping_template_id']},
        'sales_channel_properties': {'free_shipping': False},
        'is_printify_express_enabled': False,
    }
    save('create-request.json', payload)
    save('create-attempted.json', {'title': TITLE, 'shop_id': SHOP_ID, 'operation': 'create_unpublished_product_only'})
    product = request('POST', f'shops/{SHOP_ID}/products.json', payload)
    save('created-product.json', product)
    print(json.dumps({'id': product['id'], 'title': product['title'], 'visible': product['visible'], 'external': product.get('external'), 'mockup_count': len(product['images']), 'enabled_variants': sum(v['is_enabled'] for v in product['variants'])}), flush=True)

if __name__ == '__main__':
    main()
