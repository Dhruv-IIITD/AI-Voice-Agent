from __future__ import annotations

ORDER_STATUS = {
    "A100": "Order A100 is confirmed and scheduled to ship tomorrow morning.",
    "B205": "Order B205 is delayed pending address verification.",
    "C309": "Order C309 has been delivered and signed for.",
}


async def lookup_order_status(arguments: dict[str, str]) -> str:
    order_id = (arguments.get("order_id") or "").upper()
    if not order_id:
        return "No order ID was provided."
    return ORDER_STATUS.get(
        order_id,
        f"I could not find order {order_id}. Try one of the demo IDs: A100, B205, or C309.",
    )

