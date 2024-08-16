import re
import json
from datetime import datetime, timezone
import pandas as pd

def convert_date(s):
    pat = re.compile('[0-9]+')
    ticks = int(pat.findall(s)[0])
    return datetime.fromtimestamp(ticks / 1000, timezone.utc)


class JournalsParser():
    cols_journal = set(
        [
            "JournalNumber",
            "JournalID",
            "JournalDate",
            "CreatedDateUTC",
            "Reference",
            "SourceID",
            "SourceType",
        ]
    )
    cols_journal_line = set(
        [
            "JournalLineID",
            "JournalNumber",
            "AccountID",
            "AccountCode",
            "AccountType",
            "AccountName",
            "NetAmount",
            "GrossAmount",
            "TaxAmount",
            "TaxType",
            "TaxName",
            "Description",
            "TrackingCategories",
        ]
    )

    def __init__(self, journals: list[dict], offset=0):
        journal_entries = []
        self.journal_lines = []
        self.journal_lines_tracking = []
        for journal in journals:
            journal_entry = {}
            journal_id = journal["JournalID"]
            if journal['JournalNumber'] <= offset:
                continue
            for col in self.cols_journal:
                val = journal.get(col)
                if isinstance(val, str) and val.find('/Date') == 0:
                    val = convert_date(val)
                journal_entry[col] = val
            if 'JournalLines' in journal:
                self.insert_journal_lines(journal['JournalLines'], journal_id)
            journal_entries.append(journal_entry)
        self.df_journals = pd.DataFrame.from_dict(journal_entries) # type: ignore
        self.df_journal_lines = pd.DataFrame.from_dict(self.journal_lines) # type: ignore
        self.df_journal_lines_tracking = pd.DataFrame.from_dict(self.journal_lines_tracking) # type: ignore
        del self.journal_lines
        del self.journal_lines_tracking

    def insert_journal_lines(self, journal_lines: list[dict], journal_id):
        for journal_line in journal_lines:
            journal_line_entry = {}
            for col in self.cols_journal_line:
                val = journal_line.get(col)
                if isinstance(val, str) and val.find('/Date') == 0:
                    val = convert_date(val)
                elif isinstance(val, dict):
                    val = json.dumps(val)
                journal_line_entry[col] = val
            journal_line_entry['JournalID'] = journal_id
            self.journal_lines.append(journal_line_entry)


class AccountsParser():
    cols_account = set(
        [
            "AccountID",
            "Code",
            "Name",
            "Type",
            "BankAccountNumber",
            "Status",
            "Description",
            "BankAccountType",
            "CurrencyCode",
            "TaxType",
            "EnablePaymentsToAccount",
            "ShowInExpenseClaims",
            "Class",
            "SystemAccount",
            "ReportingCode",
            "ReportingCodeName",
            "HasAttachments",
            "UpdatedDateUTC",
            "AddToWatchlist",
        ]
    )

    def __init__(self, accounts: list[dict]) -> None:
        account_entries = []
        for account in accounts:
            account_entry = {}
            for key, val in account.items():
                if key in self.cols_account:
                    if isinstance(val, str) and val.find('/Date') == 0:
                        account_entry[key] = convert_date(val)
                    else:
                        account_entry[key] = val
            account_entries.append(account_entry)
        self.df_accounts = pd.DataFrame.from_dict(account_entries) #type: ignore


class OrganisationParser():
    cols_organisation = set(
        [
            "TenantID",
            "Name",
            "LegalName",
            "PaysTax",
            "Version",
            "OrganisationType",
            "BaseCurrency",
            "CountryCode",
            "IsDemoCompany",
            "OrganisationStatus",
            "RegistrationNumber",
            "EmployerIdentificationNumber",
            "TaxNumber",
            "FinancialYearEndDay",
            "FinancialYearEndMonth",
            "SalesTaxBasis",
            "SalesTaxPeriod",
            "DefaultSalesTax",
            "DefaultPurchasesTax",
            "PeriodLockDate",
            "EndOfYearLockDate",
            "CreatedDateUTC",
            "Timezone",
            "OrganisationEntityType",
            "ShortCode",
            "OrganisationID",
            "Edition",
            "Class",
            "LineOfBusiness",
        ]
    )

    def __init__(self, organisations: list[dict], tenant_id) -> None:
        organisation_entry = {}
        for key, val in organisations[0].items():
            if key in self.cols_organisation:
                if isinstance(val, str) and val.find('/Date') == 0:
                    organisation_entry[key] = convert_date(val)
                else:
                    organisation_entry[key] = val
        organisation_entry['TenantID'] = tenant_id
        self.df_organisations = pd.DataFrame.from_dict([organisation_entry]) #type: ignore


class UsersParser():
    cols_users = set(
        [
            "UserID",
            "EmailAddress",
            "FirstName",
            "LastName",
            "UpdatedDateUTC",
            "IsSubscriber",
            "OrganisationRole",
        ]
    )

    def __init__(self, users: list[dict]) -> None:
        user_entries = []
        for user in users:
            user_entry = {c: user.get(c) for c in self.cols_users}
            user_entries.append(user_entry)
        self.df_users = pd.DataFrame.from_dict(user_entries)
