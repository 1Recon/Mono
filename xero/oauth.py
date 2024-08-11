from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
from cryptography.fernet import Fernet
from sql import get_user_db, get_tenant_db
import jwt
import json

scope = ("offline_access openid profile email accounting.transactions.read "
    "accounting.reports.read accounting.journals.read accounting.settings.read "
    "accounting.contacts.read accounting.attachments.read accounting.budgets.read")


def set_tenant_user(tenant_id: str, tenant_name: str, user: str):
    con = get_tenant_db(tenant_id)
    with con:
        con.execute(f"")
    pass

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
        for tenant_id, tenant_name in tenant_ids.items():
            set_tenant_user(tenant_id, tenant_name, self.user)

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
            self.client_secret = xero_client_info[str(self.oauth.client_id)]
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
            store_xero_oauth2_token(self.token, self.client_id, self.user)


