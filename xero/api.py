import logging
from requests import Response
from oauthlib.oauth2 import TokenExpiredError
from time import sleep,  time
from datetime import datetime, date
from typing import Callable, Any
from requests_oauthlib import OAuth2Session

log = logging.getLogger(__name__)

def xero_date_fmt(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%S')

class MiscException(Exception):
    pass

class RateLimit(Exception):
    pass

class XeroTokenSession():
    client_id: str
    client_secret: str
    get_new_token: Callable[[], dict]
    token: dict

    def __init__(self, client_id: str, client_secret: str, token_getter: Callable[[], dict]) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.get_new_token = token_getter
        self.token = token_getter()
        self.session = OAuth2Session(self.client_id, token=self.token)

    def fetch_new_token(self) -> None:
        self.token = self.get_new_token()
        self.session.token = self.token
        
    def request(self, method: str, url: str, *args, **kwargs ) -> Response:
        if self.token['expires_at'] < time():
            self.fetch_new_token()
        try:
            log.debug(f'Xero {method.upper()} {args=}, {kwargs=}')
            resp = self.session.request(method, url, *args, **kwargs)
            log.debug(resp.status_code)
            log.debug(resp.text)
        except TokenExpiredError:
            self.fetch_new_token()
            resp = self.session.request(method, url, *args, **kwargs)
            log.debug(resp.status_code)
            log.debug(resp.text)
        if resp.status_code == 429:
            problem = resp.headers.get('X-Rate-Limit-Problem')
            if problem is None:
                raise MiscException(f'headers returned {resp.headers}')
            if problem == 'minute':
                retry_time = int(resp.headers['Retry-After'])
                sleep(retry_time)
            elif problem == 'concurrent':
                sleep(1)
            else:
                raise RateLimit(f'X-Rate-Limit-Problem: {problem}')
            return self.request(method, url, *args, **kwargs)
        return resp


class XeroApi():
    tenant_id: str | None
    ts: XeroTokenSession

    def __init__(self, token_session: XeroTokenSession, tenant_id: str|None=None) -> None:
        self.ts = token_session
        self.tenant_id = tenant_id
        return

    def request(self, method: str, url: str, *args, **kwargs ) -> Response:
        if self.tenant_id is None:
            raise Exception('tenant_id not set')
        if 'headers' in kwargs:
            kwargs['headers']['Xero-tenant-id'] = self.tenant_id
        else:
            kwargs['headers'] = {'Xero-tenant-id': self.tenant_id}
        kwargs['headers'].setdefault('Accept', 'application/json')
        return self.ts.request(method, url, *args, **kwargs)

    def get(self, url, *args, **kwargs) -> Response:
        kwargs.setdefault("allow_redirects", True)
        return self.request("GET", url, *args, **kwargs)

    def options(self, url, *args, **kwargs) -> Response:
        kwargs.setdefault("allow_redirects", True)
        return self.request("OPTIONS", url, *args, **kwargs)

    def head(self, url, *args, **kwargs) -> Response:
        kwargs.setdefault("allow_redirects", False)
        return self.request("HEAD", url, *args, **kwargs)

    def post(self, url, *args, **kwargs) -> Response:
        kwargs.setdefault("allow_redirects", True)
        return self.request("POST", url, *args, **kwargs)

    def put(self, url, *args, **kwargs) -> Response:
        return self.request("PUT", url, *args, **kwargs)

    def patch(self, url, *args, **kwargs) -> Response:
        return self.request("PATCH", url, *args, **kwargs)

    def delete(self, url, *args, **kwargs) -> Response:
        return self.request("DELETE", url, *args, **kwargs)

    def get_connections(self) -> list[dict]:
        '''https://developer.xero.com/documentation/guides/oauth2/auth-flow/#5-check-the-tenants-youre-authorized-to-access'''
        try:
            resp = self.ts.session.get('https://api.xero.com/connections')
        except TokenExpiredError:
            self.ts.fetch_new_token()
            resp = self.ts.session.get('https://api.xero.com/connections')
        return resp.json()

    def remove_tenant(self):
        '''https://developer.xero.com/documentation/guides/oauth2/auth-flow/#removing-connections'''
        try:
            resp = self.ts.session.get(f'https://api.xero.com/connections/{self.tenant_id}')
        except TokenExpiredError:
            self.ts.fetch_new_token()
            resp = self.ts.session.get(f'https://api.xero.com/connections/{self.tenant_id}')
        return resp.ok

    def get_journals(self, offset:int|None=None, modified_after: datetime|None=None, paymentsOnly=False) -> list[dict]:
        '''https://developer.xero.com/documentation/api/accounting/journals'''
        url = 'https://api.xero.com/api.xro/2.0/Journals'
        params = {}
        headers = {}
        if modified_after:
            headers['If-Modified-Since'] = modified_after.strftime('%Y-%m-%dT%H:%M:%S')
        if offset:
            params['offset'] = offset
        if paymentsOnly:
            params['paymentsOnly'] = True
        resp  = self.get(url, params=params, headers=headers)
        return resp.json()['Journals']

    def get_organisations(self) -> list[dict]:
        '''https://developer.xero.com/documentation/api/accounting/organisation'''
        url = 'https://api.xero.com/api.xro/2.0/Organisation'
        resp  = self.get(url)
        return resp.json()['Organisations']

    def get_invoices(self, modified_after: datetime|None=None, where: str|None=None, page:int|None=None,
         summaryOnly:bool=False, order: str|None=None) -> list[dict]:
        '''https://developer.xero.com/documentation/api/accounting/invoices'''
        url = 'https://api.xero.com/api.xro/2.0/Invoices'
        headers = {}
        params = {}
        if modified_after:
            headers['If-Modified-Since'] = xero_date_fmt(modified_after)
        if where:
            params['where'] = where
        if page:
            params['page'] = page
        if summaryOnly:
            params['summaryOnly'] = summaryOnly
        if order:
            params['order'] = order
        resp  = self.get(url, params=params, headers=headers)
        return resp.json()['Invoices']

    def get_invoice(self, invoice_id: str) -> list[dict]:
        '''https://developer.xero.com/documentation/api/accounting/invoices'''
        url = f'https://api.xero.com/api.xro/2.0/Invoices/{invoice_id}'
        resp  = self.get(url)
        return resp.json()['Invoices']

    def get_accounts(self, modified_after: datetime|None=None, where: str|None=None, order: str|None=None) -> list[dict]:
        '''https://developer.xero.com/documentation/api/accounting/accounts'''
        url = 'https://api.xero.com/api.xro/2.0/Accounts'
        headers = {}
        params = {}
        if modified_after: headers['If-Modified-Since'] = xero_date_fmt(modified_after)
        if where: params['where'] = where
        if order: params['order'] = order
        resp  = self.get(url, params=params, headers=headers)
        return resp.json()['Accounts']

    def get_tracking_categories(self, where: str|None=None, order: str|None=None, includeArchived: bool=False) -> list[dict]:
        '''https://developer.xero.com/documentation/api/accounting/trackingcategories'''
        url = 'https://api.xero.com/api.xro/2.0/TrackingCategories'
        params = {}
        if where: params['where'] = where
        if order: params['order'] = order
        if includeArchived: params['includeArchived'] = includeArchived
        resp  = self.get(url, params=params)
        return resp.json()['TrackingCategories']

    def get_trial_balance(self, at_date: date|str|None=None, paymentsOnly: bool=False) -> list[dict]:
        '''https://developer.xero.com/documentation/api/accounting/reports/#trial-balance'''
        url = 'https://api.xero.com/api.xro/2.0/Reports/TrialBalance'
        params = {}
        if type(at_date) is str:
            params['date'] = at_date
        elif type(at_date) is date:
            params['date'] = at_date.strftime('%Y-%m-%d')
        if paymentsOnly: params['paymentsOnly'] = paymentsOnly # type: ignore
        resp  = self.get(url, params=params)
        return resp.json()['Reports']

    def get_contacts(self, modified_after: datetime|None=None, where: str|None=None, order: str|None=None,
        includeArchived: bool=False, page:int|None=None) -> list[dict]:
        '''https://developer.xero.com/documentation/api/accounting/contacts/#get-contacts'''
        url = 'https://api.xero.com/api.xro/2.0/Contacts'
        headers = {}
        params = {}
        if modified_after: headers['If-Modified-Since'] = xero_date_fmt(modified_after)
        if where: params['where'] = where
        if order: params['order'] = order
        if includeArchived: params['includeArchived'] = includeArchived
        if page: params['page'] = page
        resp  = self.get(url, params=params, headers=headers)
        return resp.json()['Contacts']

    def get_bank_transactions(self, modified_after: datetime|None=None, where: str|None=None,
        order: str|None=None, page:int|None=None) -> list[dict]:
        '''https://developer.xero.com/documentation/api/accounting/banktransactions'''
        url = 'https://api.xero.com/api.xro/2.0/BankTransactions'
        headers = {}
        params = {}
        if modified_after: headers['If-Modified-Since'] = xero_date_fmt(modified_after)
        if where: params['where'] = where
        if order: params['order'] = order
        if page: params['page'] = page
        resp  = self.get(url, params=params, headers=headers)
        return resp.json()['BankTransactions']

    def get_assets(self, page: int, page_size: int=200, status: str|None=None, filter_by: str|None=None, order_by: str|None=None):
        '''https://developer.xero.com/documentation/api/assets/assets'''
        url = 'https://api.xero.com/assets.xro/1.0/Assets'
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if filter_by: params['filterBy'] = filter_by
        if order_by: params['orderBy'] = order_by
        if status: params['status'] = status
        resp  = self.get(url, params=params)
        return resp.json()['items']

    def get_manual_journals(self, modified_after: datetime|None=None, where: str|None=None,
        order: str|None=None, page:int|None=None):
        '''https://developer.xero.com/documentation/api/accounting/manualjournals/#overview'''
        url = 'https://api.xero.com/api.xro/2.0/ManualJournals'
        headers = {}
        params = {}
        if modified_after: headers['If-Modified-Since'] = xero_date_fmt(modified_after)
        if where: params['where'] = where
        if order: params['order'] = order
        if page: params['page'] = page
        resp =  self.get(url, params=params, headers=headers)
        return resp.json()['ManualJournals']

    def get_credit_notes(self, modified_after: datetime|None=None, where: str|None=None,
        order: str|None=None, page:int|None=None):
        '''https://developer.xero.com/documentation/api/accounting/creditnotes/#get-creditnotes'''
        url = 'https://api.xero.com/api.xro/2.0/CreditNotes'
        headers = {}
        params = {}
        if modified_after: headers['If-Modified-Since'] = xero_date_fmt(modified_after)
        if where: params['where'] = where
        if order: params['order'] = order
        if page: params['page'] = page
        resp =  self.get(url, params=params, headers=headers)
        return resp.json()['CreditNotes']

    def get_credit_note(self, credit_note_id: str):
        '''https://developer.xero.com/documentation/api/accounting/creditnotes/#get-creditnotes'''
        url = f'https://api.xero.com/api.xro/2.0/CreditNotes/{credit_note_id}'
        resp =  self.get(url)
        return resp.json()['CreditNotes']

    def update_manual_journal(self, manjournal_id: str, payload: dict):
        '''https://developer.xero.com/documentation/api/accounting/manualjournals/#overview'''
        url = f'https://api.xero.com/api.xro/2.0/ManualJournals/{manjournal_id}'
        return self.post(url, json=payload)
