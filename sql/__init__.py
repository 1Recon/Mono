from jinja2 import Environment, PackageLoader, select_autoescape
import sqlite3
import os

env = Environment(loader=PackageLoader(__name__), autoescape=select_autoescape())
db_dir = os.path.dirname(__file__)

def get_tenant_db(tenant_id: str) -> sqlite3.Connection:
    return sqlite3.connect(f"{db_dir}/tenants/{tenant_id}.db")

def get_user_db() -> sqlite3.Connection:
    return sqlite3.connect(f"{db_dir}/users.db", isolation_level="EXCLUSIVE")

def base():
    return env.get_template("base.sql").render()


