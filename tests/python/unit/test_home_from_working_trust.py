from packages.home_from_working.trust import audit_listing_trust, derive_live_etsy_trust


def test_trust_audit_reports_unknown_instead_of_assuming_live_fields():
    result = audit_listing_trust({"key": "design/one", "etsy": {}})
    assert result["overall"] == "blocked_unknown"
    assert result["checks"]["production_partner"] == "unknown"
    assert result["checks"]["ai_disclosure"] == "unknown"
    assert result["checks"]["shipping_origin"] == "unknown"


def test_trust_audit_passes_complete_truthful_record():
    result = audit_listing_trust(
        {
            "key": "design/one",
            "etsy": {
                "production_partner_disclosed": True,
                "ai_disclosure_complete": True,
                "shipping_origin_verified": True,
                "processing_policy_complete": True,
                "returns_policy_complete": True,
                "size_information_complete": True,
            },
        }
    )
    assert result["overall"] == "pass"
    assert set(result["checks"].values()) == {"pass"}


def test_explicit_false_is_a_failure_not_unknown():
    result = audit_listing_trust(
        {"key": "design/one", "etsy": {"production_partner_disclosed": False}}
    )
    assert result["overall"] == "fail"
    assert result["checks"]["production_partner"] == "fail"


def test_live_etsy_evidence_derives_trust_fields_without_title_matching():
    listing = {
        "listing_id": 42,
        "description": (
            "FIT AND SIZING\nCompare the size chart.\n"
            "AI-assisted tools were used during illustration."
        ),
        "shipping_profile_id": 7,
        "return_policy_id": 8,
        "production_partner_ids": [4],
        "inventory": [
            {
                "property_values": [
                    {"property_name": "Size", "values": ["S", "M"]}
                ]
            }
        ],
    }
    fields = derive_live_etsy_trust(
        listing,
        shipping_profiles=[
            {
                "shipping_profile_id": 7,
                "origin_country_iso": "US",
                "processing_min": 2,
                "processing_max": 5,
            }
        ],
        production_partners=[
            {"production_partner_id": 4, "is_active": True, "is_deleted": False}
        ],
    )

    assert fields == {
        "production_partner_disclosed": True,
        "ai_disclosure_complete": True,
        "shipping_origin_verified": True,
        "processing_policy_complete": True,
        "returns_policy_complete": True,
        "size_information_complete": True,
    }


def test_live_etsy_evidence_flags_missing_required_disclosures():
    fields = derive_live_etsy_trust(
        {
            "listing_id": 42,
            "description": "A shirt without sizing or AI disclosure.",
            "production_partner_ids": [],
            "inventory": [],
        },
        shipping_profiles=[],
        production_partners=[],
    )

    assert fields == {
        "production_partner_disclosed": False,
        "ai_disclosure_complete": False,
        "shipping_origin_verified": False,
        "processing_policy_complete": None,
        "returns_policy_complete": False,
        "size_information_complete": False,
    }


def test_live_etsy_evidence_marks_absent_partner_and_processing_status_unknown():
    fields = derive_live_etsy_trust(
        {
            "listing_id": 42,
            "production_partner_ids": [4],
        },
        shipping_profiles=[],
        production_partners=[{"production_partner_id": 4}],
    )

    assert fields["production_partner_disclosed"] is None
    assert fields["processing_policy_complete"] is None


def test_live_etsy_evidence_recognizes_clothing_sizes_property_513():
    fields = derive_live_etsy_trust(
        {
            "listing_id": 42,
            "description": "FIT AND SIZING. Use the size chart.",
            "inventory": [
                {
                    "property_values": [
                        {"property_id": 513, "property_name": "Clothing sizes"}
                    ]
                }
            ],
        },
        shipping_profiles=[],
        production_partners=[],
    )

    assert fields["size_information_complete"] is True


def test_live_etsy_evidence_keeps_missing_ai_disclosure_as_a_failure():
    fields = derive_live_etsy_trust(
        {
            "listing_id": 42,
            "description": "FIT AND SIZING. Use the size chart.",
            "inventory": [
                {
                    "property_values": [
                        {"property_id": 513, "property_name": "Clothing sizes"}
                    ]
                }
            ],
        },
        shipping_profiles=[],
        production_partners=[],
    )

    assert fields["ai_disclosure_complete"] is False


def test_live_etsy_evidence_recognizes_ai_image_generation_disclosure():
    fields = derive_live_etsy_trust(
        {
            "listing_id": 42,
            "description": (
                "Artwork for this design was created with the assistance of an "
                "AI image-generation tool and arranged into the finished shirt design."
            ),
        },
        shipping_profiles=[],
        production_partners=[],
    )

    assert fields["ai_disclosure_complete"] is True
