from fastapi import APIRouter
import sqlite3

router = APIRouter()

@router.get("/users/{user_id}")
def get_user(user_id: str):
    # Intentional vulnerability: SQL injection
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
    return cursor.fetchone()

@router.get("/users/search")
def search_users(name: str):
    # Intentional vulnerability: SQL injection via search
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE name LIKE '%" + name + "%'"
    cursor.execute(query)
    return cursor.fetchall()

@router.get("/users")
def list_users():
    # Intentional vulnerability: no pagination
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()
