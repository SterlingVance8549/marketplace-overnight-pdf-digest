from marketplace_digest import MarketplaceRecord, handoff_state, record_prompt


def test_missing_owner_makes_handoff_visible_to_the_digest() -> None:
    record = MarketplaceRecord.model_validate(
        {
            "order_id": "ord-1042",
            "seller": "Northstar Ceramics",
            "assets": [{"name": "packing photos", "status": "approved"}],
            "buyer_updates": [{"buyer": "Mina", "note": "delivery window confirmed"}],
            "handoff": {"owner": None, "next_step": "book courier"},
        }
    )

    assert handoff_state(record) == "HANDOFF NEEDED"
    prompt = record_prompt(record)
    assert "Order ID: ord-1042" in prompt
    assert "Handoff owner: unassigned" in prompt
    assert "Handoff state: HANDOFF NEEDED" in prompt
