import sys, os
sys.path.append(os.getcwd())
from app.core.database import SessionLocal
from app.models.subscription import Subscription
from app.models.invoice import Invoice

def check_db():
    db = SessionLocal()
    print('--- SUBSCRIPTIONS ---')
    subs = db.query(Subscription).all()
    if not subs:
        print("No subscriptions found.")
    for s in subs:
        status_val = s.status.value if hasattr(s.status, 'value') else str(s.status)
        print(f'Sub ID: {s.id} | Org: {s.organization_id} | Status: {status_val}')

    print('\n--- INVOICES ---')
    invoices = db.query(Invoice).all()
    if not invoices:
        print("No invoices found.")
    for i in invoices:
        status_val = i.status.value if hasattr(i.status, 'value') else str(i.status)
        print(f'Inv ID: {i.id} | Sub ID: {i.subscription_id} | Org: {i.organization_id} | Status: {status_val}')

if __name__ == "__main__":
    check_db()
