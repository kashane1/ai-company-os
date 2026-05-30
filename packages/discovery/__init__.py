"""Discovery layer — the front of the loop.

Turns raw signals from sources into scored, evidenced ``OpportunityRecord``s,
then hands the survivors to the validate gate. Tool-agnostic: every source sits
behind the ``Connector`` contract; compliance (robots.txt + rate limits) is
enforced in one place, not reinvented per connector.

See ``docs/founder/discovery-guide.md`` for how to use it and
``docs/founder/opportunity-scorecard.md`` for the scoring spec.
"""
