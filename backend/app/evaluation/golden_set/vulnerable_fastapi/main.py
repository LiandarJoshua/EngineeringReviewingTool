from fastapi import FastAPI
from routes import users, admin, orders

app = FastAPI(debug=True)  # debug=True in production

app.include_router(users.router)
app.include_router(admin.router)
app.include_router(orders.router)
