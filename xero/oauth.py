from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
from cryptography.fernet import Fernet
from sql import get_user_db, get_xero_tokens_db
from utils.redis import redis_con_bytes
from config import fernet_key, client_id, client_secret, sso_id, sso_secret
from time import time
import jwt
import json

refresh_url = 'https://identity.xero.com/connect/token'
scope = (
    "offline_access openid profile email accounting.transactions.read "
    "accounting.reports.read accounting.journals.read accounting.settings.read "
    "accounting.contacts.read accounting.attachments.read accounting.budgets.read"
)

def encrypt_token(token: dict) -> bytes:
    text = json.dumps(token)
    f = Fernet(fernet_key)
    return f.encrypt(text.encode('utf-8'))

def decrypt_token(encypted_token: bytes) -> dict:
    f = Fernet(fernet_key)
    return json.loads(f.decrypt(encypted_token).decode())

def set_tenant_user(tenant_id: str, user_email: str):
    con = get_user_db()
    with con:
        con.execute(
            "insert into token_users(email, tenant_id) values (?, ?)",
            (user_email, tenant_id),
        )

def store_xero_oauth2_token(token: dict, user: str):
    con = get_xero_tokens_db()
    with con:
        con.execute(
            "delete from tokens where user = ?;",
            (user,),
        )
        con.execute(
            "insert into tokens(email, token) values (?, ?)",
            (user, encrypt_token(token)),
        )

def get_refreshed_token(user: str) -> dict:
    if redis_con_bytes:
        resp: bytes|None = redis_con_bytes.get(f'xero-token:{user}') # type: ignore
        if resp:
            return decrypt_token(resp)
    con = get_xero_tokens_db()
    with con:
        cur = con.execute(
            "select token from tokens where email = ?",
            (user,),
        )
        token = decrypt_token(cur.fetchone()[0])
        if token['expires_at'] - time() < 60:
            token = refresh_token(token)
            et = encrypt_token(token)
            con.execute(
                "update tokens set token = ? where email = ?",
                (et, user),
            )
            if redis_con_bytes:
                redis_con_bytes.set(f'xero-token:{user}', et, ex=(token['expires_in']-60))
    return token

def refresh_token(token: dict):
        auth = HTTPBasicAuth(client_id, client_secret)
        session = OAuth2Session(client_id, token=token)
        return session.refresh_token(
            refresh_url,
            refresh_token=token['refresh_token'],
            auth=auth
        )

class XeroTokenManager():

    def __init__(self, client_id: str, redirect_uri: str, client_secret=None, id_type: bool=False, auth_resp=None, state=None, scope=None):
        self.client_id = client_id
        self.id_type = id_type
        self.redirect_uri = redirect_uri
        self.client_secret = client_secret
        self.auth_resp = auth_resp
        self.oauth_state = state
        self.scope = scope
        if id_type:
            self.scope = "openid email"
        if self.auth_resp and not self.id_type:
            self.store_token_sql()


    def set_tenants_client(self):
        resp = self.oauth.get("https://api.xero.com/connections")
        tenant_ids = {ten['tenantId']: ten['tenantName'] for ten in resp.json()}
        for tenant_id in tenant_ids:
            set_tenant_user(tenant_id, self.user)

    @property
    def oauth(self):
        if not hasattr(self, '_oauth'):
            self._get_xero_oauth_session()
        return self._oauth

    @property
    def authorization_url(self):
        if not hasattr(self, '_authorization_url'):
            self._get_xero_oauth_session()
        return self._authorization_url

    @property
    def token(self):
        if not hasattr(self, '_token'):
            if self.auth_resp:
                self.get_xero_token(self.auth_resp)
            else:
                raise Exception("OAuth response not defined")
        return self._token

    @property
    def user(self):
        if not hasattr(self, '_user'):
            return self.get_user()
        return self._user

    def _get_xero_oauth_session(self):
        if self.scope is None:
            raise Exception('scope is None')
        self._oauth = OAuth2Session(
            self.client_id,
            scope=self.scope,
            redirect_uri=self.redirect_uri,
            state=self.oauth_state
        )
        self._authorization_url, self.oauth_state = self._oauth.authorization_url("https://login.xero.com/identity/connect/authorize")

    def get_xero_token(self, auth_resp: str):
        if self.client_secret is None:
            self.client_secret = client_secret
        access_token_url = "https://identity.xero.com/connect/token"
        self._token = self.oauth.fetch_token(
            access_token_url,
            authorization_response=auth_resp,
            client_secret=self.client_secret
        )

    def get_user(self) -> str:
        discovery_url = "https://identity.xero.com/.well-known/openid-configuration/jwks"
        jwks_client = jwt.PyJWKClient(discovery_url)
        signing_key = jwks_client.get_signing_key_from_jwt(self.token['id_token'])
        info = jwt.decode(self.token['id_token'], signing_key.key, algorithms=["RS256"], audience=self.client_id)
        self._user = info['email']
        return self._user

    def store_token_sql(self):
        if self.token and self.user:
            store_xero_oauth2_token(self.token, self.user)
