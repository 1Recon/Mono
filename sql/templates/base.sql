create table xero.Organisations(
    TenantID text primary key,
    Name text,
    LegalName text,
    PaysTax boolean,
    Version text,
    OrganisationType text,
    BaseCurrency text,
    CountryCode text,
    IsDemoCompany boolean,
    OrganisationStatus text,
    RegistrationNumber text,
    EmployerIdentificationNumber text,
    TaxNumber text,
    FinancialYearEndDay integer,
    FinancialYearEndMonth integer,
    SalesTaxBasis text,
    SalesTaxPeriod text,
    DefaultSalesTax text,
    DefaultPurchasesTax text,
    PeriodLockDate datetime,
    EndOfYearLockDate datetime,
    CreatedDateUTC datetime,
    Timezone text,
    OrganisationEntityType text,
    ShortCode text,
    OrganisationID text,
    Edition text,
    Class text,
    LineOfBusiness text
) without rowid;

create table xero.Accounts(
    AccountID text primary key,
    Code text,
    Name text,
    Type text,
    BankAccountNumber text,
    Status text,
    Description text,
    BankAccountType text,
    CurrencyCode text,
    TaxType text,
    EnablePaymentsToAccount boolean,
    ShowInExpenseClaims boolean,
    Class text,
    SystemAccount text,
    ReportingCode text,
    ReportingCodeName text,
    HasAttachments boolean,
    UpdatedDateUTC datetime,
    AddToWatchlist boolean
) without rowid;

create table xero.Journals(
    JournalNumber integer primary key,
    JournalID text not null,
    JournalDate date not null,
    CreatedDateUTC datetime not null,
    Reference text,
    SourceID text,
    SourceType text
) without rowid;

create table xero.JournalLines(
    JournalLineID text primary key,
    JournalNumber integer foreign key references Journals(JournalNumber),
    AccountID text not null,
    AccountCode text,
    AccountType text,
    AccountName text,
    NetAmount decimal(22,4),
    GrossAmount decimal(22,4),
    TaxAmount decimal(22,4),
    TaxType text,
    TaxName text,
    Description text,
    TrackingCategories text
) without rowid;
