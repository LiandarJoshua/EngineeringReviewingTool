from fastapi import APIRouter
import sqlite3

router = APIRouter()

@router.get("/orders")
def list_orders():
    # Intentional: no pagination
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders")
    return cursor.fetchall()

@router.get("/orders/{order_id}")
def get_order(order_id: str):
    # Intentional: IDOR — no ownership check
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM orders WHERE id = {order_id}")
    return cursor.fetchone()
