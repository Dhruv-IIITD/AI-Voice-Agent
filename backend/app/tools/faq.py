from __future__ import annotations

FAQ_ENTRIES = {
    "pricing": "The demo product offers a free trial, a team tier, and an enterprise plan with custom pricing.",
    "integrations": "The product integrates with Slack, Salesforce, HubSpot, and a public REST API.",
    "security": "The platform supports SSO, role-based access, audit logs, and data encryption at rest and in transit.",
}


async def lookup_faq(arguments: dict[str, str]) -> str:
    question = (arguments.get("question") or "").lower()
    for keyword, answer in FAQ_ENTRIES.items():
        if keyword in question:
            return answer
    return (
        "I could not find an exact FAQ match. Available topics are pricing, integrations, and security."
    )

