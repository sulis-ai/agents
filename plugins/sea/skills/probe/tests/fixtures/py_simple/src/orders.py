class Order:
    def __init__(self, id, total):
        self.id = id
        self.total = total

def place_order(order):
    if order.total <= 0:
        raise ValueError("invalid total")
    return f"Order {order.id} placed"
