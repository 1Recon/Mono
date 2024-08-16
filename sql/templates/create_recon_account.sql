create table "recon-{ account_id }"(
    JournalNumber integer foreign key references Journals(JournalNumber),
    JournalLineID text primary key,
    Mapping text
) without rowid;
