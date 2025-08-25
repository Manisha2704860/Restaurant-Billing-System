def calculate_subtotal(order, menu):
    return sum(menu.get(item, 0) * qty for item, qty in order.items())

def calculate_gst_and_total(subtotal, gst_percent=5, discount=0):
    gst_amount = subtotal * gst_percent / 100
    total = subtotal + gst_amount - discount
    return gst_amount, total
