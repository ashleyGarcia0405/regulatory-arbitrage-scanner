"""Moat type taxonomy with falsification playbooks."""

MOAT_TAXONOMY: dict[str, dict] = {
    "data_network_effect": {
        "description": "Value increases as more users contribute data, creating a self-reinforcing advantage.",
        "core_assumption": "Proprietary data is scarce, hard to replicate, and meaningfully improves the product.",
        "search_templates": [
            "open datasets alternatives to {claim}",
            "synthetic data replace {claim} network effect",
            "foundation model trained on public data parity with {claim}",
        ],
        "threat_signals": [
            "government mandates open data sharing",
            "foundation models trained on public corpora match specialized accuracy",
            "synthetic data generation closes the gap",
        ],
        "max_depth": 3,
    },
    "switching_costs": {
        "description": "Customers are locked in by integration depth, workflow dependency, or data portability friction.",
        "core_assumption": "Migration cost stays high and no interoperability mandate forces portability.",
        "search_templates": [
            "migration tools {claim} switching costs lowered",
            "API parity open source alternative to {claim}",
            "interoperability mandate {claim} portability regulation",
        ],
        "threat_signals": [
            "competitor launches one-click migration tool",
            "regulator mandates data portability in this category",
            "open standard emerges that commoditizes the integration layer",
        ],
        "max_depth": 3,
    },
    "distribution": {
        "description": "Privileged access to channels, partnerships, or embedded workflows that competitors cannot easily replicate.",
        "core_assumption": "Distribution channels remain exclusive and incumbents don't replicate the partnership.",
        "search_templates": [
            "channel alternatives to {claim} distribution advantage",
            "incumbent partnership announcement competing with {claim}",
            "new entrant distribution channel {claim} market",
        ],
        "threat_signals": [
            "large incumbent signs exclusive deal with same channel partner",
            "new direct-to-customer channel emerges that bypasses the distribution moat",
            "regulatory change mandates open access to the channel",
        ],
        "max_depth": 2,
    },
    "regulatory": {
        "description": "A license, certification, or rule creates a legal barrier that competitors must clear.",
        "core_assumption": "The regulation persists in its current form and compliance barriers remain high.",
        "search_templates": [
            "pending legislation rollback {claim} regulatory moat",
            "lobbying filings against {claim} rule",
            "regulatory sandbox approval competing startup {claim}",
        ],
        "threat_signals": [
            "congressional bill to repeal or weaken the rule",
            "well-funded incumbent lobbying to change the compliance requirements",
            "sandbox program lets competitors operate without the full license",
        ],
        "max_depth": 2,
    },
    "tech_differentiation": {
        "description": "A proprietary algorithm, model, or infrastructure capability that delivers meaningfully better outcomes.",
        "core_assumption": "The technical advantage cannot be replicated by open-source efforts or cloud managed services.",
        "search_templates": [
            "open source alternative {claim} technical advantage",
            "cloud managed service competing with {claim}",
            "academic paper replicating {claim} method released",
        ],
        "threat_signals": [
            "major open-source release closes the capability gap",
            "AWS/Google/Azure launches a managed service in this space",
            "published research shows commodity approach reaching parity",
        ],
        "max_depth": 3,
    },
    "brand_community": {
        "description": "A loyal user community or brand identity that drives organic growth and retention.",
        "core_assumption": "Community loyalty holds and incumbents cannot acquire or replicate the community identity.",
        "search_templates": [
            "incumbent acquisition community platform competing with {claim}",
            "big tech community product launch {claim} market",
            "community fragmentation {claim} brand loyalty",
        ],
        "threat_signals": [
            "large incumbent acquires the community's preferred adjacent platform",
            "brand controversy or trust event fragments the community",
            "better-resourced competitor launches a community-first product",
        ],
        "max_depth": 2,
    },
}

VALID_MOAT_TYPES = set(MOAT_TAXONOMY.keys())