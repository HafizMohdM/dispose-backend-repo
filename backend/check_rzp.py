import sys, os
sys.path.append(os.getcwd())
try:
    import razorpay
    from app.core.config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    
    order_id = 'order_SL6YWWvmWAf4vc'
    order = client.order.fetch(order_id)
    print(f'Order ID: {order_id}')
    print(f'Status: {order.get("status")}')
    print(f'Amount Paid: {order.get("amount_paid")}')
    
    payments = client.order.payments(order_id)
    print('\nPayments for this order:')
    for p in payments.get('items', []):
        print(f'- Payment ID: {p.get("id")}, Status: {p.get("status")}, Method: {p.get("method")}, Error: {p.get("error_description")}')

except Exception as e:
    import traceback
    traceback.print_exc()
