def process_order(order_id: str) -> bool:
    return True


class OrderService:
    def __init__(self) -> None:
        self.orders: list[str] = []

    def add(self, order_id: str) -> None:
        self.orders.append(order_id)
