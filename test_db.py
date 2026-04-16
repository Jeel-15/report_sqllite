import os
from mongoengine import connect
from dotenv import load_dotenv
from models.user import User

load_dotenv()
sqlite_path = os.getenv("SQLITE_PATH", os.path.join(os.path.dirname(__file__), "data", "app.db"))
connect(path=sqlite_path)

print(f"Connected to SQLite: {sqlite_path}")
user_count = User.objects.count()
print(f"Total Users in DB: {user_count}")
