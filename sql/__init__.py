from jinja2 import Environment, PackageLoader, select_autoescape
import sqlite3
import os

env = Environment(loader=PackageLoader(__name__), autoescape=select_autoescape())
db_dir = os.path.dirname(__file__)

def get_tenant_db(tenant_id: str) -> sqlite3.Connection:
    return sqlite3.connect(f"{db_dir}/xero_tenants/{tenant_id}.db")

def get_user_db() -> sqlite3.Connection:
    return sqlite3.connect(f"{db_dir}/users.db")

def get_xero_tokens_db() -> sqlite3.Connection:
    return sqlite3.connect(f"{db_dir}/xero_tokens.db", isolation_level="EXCLUSIVE")

def xero_base(tenant_id: str):
    stmt = env.get_template("base.sql").render()
    con = get_tenant_db(tenant_id)
    try:
        with con:
            con.executescript(stmt)
    finally:
        con.close()

def create_recon_account(account_id: str, tenant_id: str):
    stmt = env.get_template("create_recon_account.sql").render(account_id=account_id)
    con = get_tenant_db(tenant_id)
    try:
        with con:
            con.executescript(stmt)
    finally:
        con.close()
