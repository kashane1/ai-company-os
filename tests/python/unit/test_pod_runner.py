from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from PIL import Image

from packages.pod.runner import PrintifyClient, apply_run, prepare_run
from packages.policies.approvals import PolicyViolation
from packages.policies.pod import require_draft_approval
from packages.schemas.approval import ApprovalRecord, ApprovalStatus


SHOP = 28779955
SOURCE = 'a' * 24
DRAFT = 'b' * 24


def product(identifier, linked=False):
    return {
        'id': identifier, 'shop_id': SHOP, 'blueprint_id': 6, 'print_provider_id': 99,
        'is_locked': False, 'is_deleted': False, 'visible': True,
        'external': {'id': '123' if linked else '', 'handle': '', 'shipping_template_id': 'ship'},
        'title': 'Template', 'description': 'Old intro\n\nPRODUCT FEATURES\nCotton', 'tags': ['old'],
        'variants': [{'id': 12100, 'sku': identifier, 'price': 1799, 'cost': 740,
                      'is_enabled': True, 'is_default': True, 'is_available': True}],
        'safety_information': 'Care instructions', 'sales_channel_properties': {'free_shipping': False},
        'is_printify_express_enabled': False, 'is_economy_shipping_enabled': False,
        'print_areas': [{'variant_ids': [12100], 'placeholders': [{'position': 'front',
            'images': [{'id': 'old-art', 'x': .5, 'y': .42, 'scale': .6, 'angle': 0}]}]}],
        'images': [{'src': f'https://images.printify.com/mockup/{identifier}/12100/92570/test.jpg?camera_label=front',
                    'mockup_id': f'{identifier}_12100_92570_front', 'variant_ids': [12100],
                    'position': 'front', 'is_default': True, 'is_selected_for_publishing': True, 'order': None}],
    }


@pytest.fixture
def prepared(tmp_path):
    image = tmp_path / 'art.png'
    Image.new('RGBA', (100, 150), (0, 0, 0, 255)).save(image)
    client = Mock()
    client.get_product.side_effect = [product(SOURCE, True), product(DRAFT)]
    directory = tmp_path / 'run'
    review = prepare_run(client, SOURCE, DRAFT, image,
                         {'title': 'New shirt', 'intro': 'A new design.', 'tags': ['new shirt']}, directory)
    return client, directory, review, image


def approved(review):
    return ApprovalRecord(id='approval-1', status=ApprovalStatus.APPROVED,
                          summary='Owner requested this exact draft', created_at='2026-09-02T00:00:00Z',
                          approval_type='pod_draft_update', subject_type='pod_manifest',
                          subject_id=review['revision'], action='update_printify_draft')


def test_prepare_never_uploads_or_updates(prepared):
    client, directory, review, _ = prepared
    client.upload.assert_not_called()
    client.update_draft.assert_not_called()
    assert review['payload']['description'] == 'A new design.\n\nPRODUCT FEATURES\nCotton'
    assert (directory / 'review.json').exists()


def test_approval_is_bound_to_exact_revision(prepared):
    client, directory, review, _ = prepared
    with pytest.raises(PolicyViolation):
        apply_run(client, directory, replace(approved(review), subject_id='wrong'))
    client.upload.assert_not_called()
    client.update_draft.assert_not_called()


def test_pending_or_wrong_action_is_rejected(prepared):
    _, _, review, _ = prepared
    for record in [replace(approved(review), status=ApprovalStatus.PENDING),
                   replace(approved(review), action='publish'),
                   replace(approved(review), approval_type='something_else')]:
        with pytest.raises(PolicyViolation):
            require_draft_approval(record, review['revision'])


def test_changed_artwork_cannot_use_old_approval(prepared):
    client, directory, review, image = prepared
    image.write_bytes(b'changed')
    with pytest.raises(ValueError, match='[Aa]rtwork'):
        apply_run(client, directory, approved(review))
    client.upload.assert_not_called()


def test_apply_and_retry_update_same_draft_once(prepared):
    from copy import deepcopy
    client, directory, review, _ = prepared
    before = product(DRAFT)
    upload = {'id': 'new-art', 'width': 100, 'height': 150, 'mime_type': 'image/png'}
    after = deepcopy(before)
    after.update(deepcopy(review['payload']))
    after['print_areas'][0]['placeholders'][0]['images'][0]['id'] = 'new-art'
    client.get_product.side_effect = [before, after, after]
    client.upload.return_value = upload
    first = apply_run(client, directory, approved(review))
    second = apply_run(client, directory, approved(review))
    assert first['product_id'] == second['product_id'] == DRAFT
    assert second['status'] == 'already_verified'
    assert client.upload.call_count == client.update_draft.call_count == 1


def test_ambiguous_upload_is_not_blindly_repeated(prepared):
    client, directory, review, _ = prepared
    client.get_product.side_effect = None
    client.get_product.return_value = product(DRAFT)
    client.upload.side_effect = ValueError('timeout')
    with pytest.raises(ValueError, match='timeout'):
        apply_run(client, directory, approved(review))
    client.upload.side_effect = None
    with pytest.raises(ValueError, match='[Rr]econcile'):
        apply_run(client, directory, approved(review))
    assert client.upload.call_count == 1


def test_client_refuses_live_target_before_put():
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=product(DRAFT, True))
    client = PrintifyClient('fake-token', transport=httpx.MockTransport(respond))
    with pytest.raises(ValueError, match='[Pp]ublished|[Ll]inked|[Ll]ive'):
        client.update_draft(DRAFT, {'title': 'New'})
    assert [r.method for r in requests] == ['GET']


def test_client_disallows_variant_or_publish_payload():
    client = PrintifyClient('fake-token', transport=httpx.MockTransport(lambda r: pytest.fail('network')))
    with pytest.raises(ValueError):
        client.update_draft(DRAFT, {'variants': []})
    with pytest.raises(ValueError):
        client.get_product('../publish')


@pytest.mark.parametrize('field,value', [('is_locked', None), ('is_deleted', None),
                                        ('external', 'malformed')])
def test_client_refuses_unknown_target_state(field, value):
    target = product(DRAFT)
    target[field] = value
    requests = []

    def respond(request):
        requests.append(request.method)
        return httpx.Response(200, json=target)

    client = PrintifyClient('fake-token', transport=httpx.MockTransport(respond))
    with pytest.raises(ValueError):
        client.update_draft(DRAFT, {'title': 'New'})
    assert requests == ['GET']


def test_prepare_rejects_invisible_art_before_api_access(tmp_path):
    image = tmp_path / 'blank.png'
    Image.new('RGBA', (100, 150), (0, 0, 0, 0)).save(image)
    client = Mock()
    with pytest.raises(ValueError, match='transparent'):
        prepare_run(client, SOURCE, DRAFT, image,
                    {'title': 'New shirt', 'intro': 'A design.', 'tags': ['shirt']},
                    tmp_path / 'run')
    client.get_product.assert_not_called()


def test_successful_but_uncertain_update_is_reconciled_without_repeating(prepared):
    from copy import deepcopy

    client, directory, review, _ = prepared
    before = product(DRAFT)
    after = deepcopy(before)
    after.update(deepcopy(review['payload']))
    after['print_areas'][0]['placeholders'][0]['images'][0]['id'] = 'new-art'
    client.get_product.side_effect = [before, after]
    client.upload.return_value = {
        'id': 'new-art', 'width': 100, 'height': 150, 'mime_type': 'image/png',
    }
    client.update_draft.side_effect = ValueError('timeout after server saved')
    with pytest.raises(ValueError, match='timeout'):
        apply_run(client, directory, approved(review))
    receipt = apply_run(client, directory, approved(review))
    assert receipt['status'] == 'already_verified'
    assert client.upload.call_count == client.update_draft.call_count == 1


def test_large_placement_survives_upload_and_retry(tmp_path):
    from copy import deepcopy

    image = tmp_path / 'large.png'
    Image.new('RGBA', (1024, 1536), (0, 0, 0, 255)).save(image)
    client = Mock()
    client.get_product.side_effect = [product(SOURCE, True), product(DRAFT)]
    directory = tmp_path / 'run'
    review = prepare_run(client, SOURCE, DRAFT, image,
                         {'title': 'Large shirt', 'intro': 'Large design.', 'tags': ['shirt']},
                         directory, scale_percent=305)
    assert review['placement']['requested_scale_percent'] == 305
    assert review['artwork']['dpi'] == 98.4
    before = product(DRAFT)
    after = deepcopy(before)
    after.update(deepcopy(review['payload']))
    expected = after['print_areas'][0]['placeholders'][0]['images'][0]
    expected['id'] = 'large-art'
    client.get_product.side_effect = [before, after, after]
    client.upload.return_value = {'id': 'large-art', 'width': 1024, 'height': 1536, 'mime_type': 'image/png'}
    apply_run(client, directory, approved(review))
    retry = apply_run(client, directory, approved(review))
    sent = client.update_draft.call_args.args[1]['print_areas'][0]['placeholders'][0]['images'][0]
    assert sent == expected
    assert sent['y'] == .5 and sent['scale'] == pytest.approx(1024 * 3.05 / 3951)
    assert retry['status'] == 'already_verified'
    assert client.upload.call_count == client.update_draft.call_count == 1


def test_cli_requires_shared_store_decision_even_with_local_approval_file(tmp_path, monkeypatch):
    import json
    import runpy
    import sys

    (tmp_path / 'approval-request.json').write_text(json.dumps({'id': 'fake', 'status': 'approved'}))
    main = runpy.run_path(str(Path(__file__).resolve().parents[3] / 'scripts/pod_draft.py'))['main']
    store = Mock()
    store.load.side_effect = FileNotFoundError('No shared approval')
    execute = Mock()
    monkeypatch.setitem(main.__globals__, 'ApprovalStore', lambda: store)
    monkeypatch.setitem(main.__globals__, 'require_secret', lambda *args, **kwargs: 'fake-token')
    monkeypatch.setitem(main.__globals__, 'PrintifyClient', Mock())
    monkeypatch.setitem(main.__globals__, 'apply_run', execute)
    monkeypatch.setattr(sys, 'argv', ['pod_draft.py', 'apply', '--run-dir', str(tmp_path),
                                     '--approval-id', 'fake'])
    assert main() == 1
    store.load.assert_called_once_with('fake')
    execute.assert_not_called()
