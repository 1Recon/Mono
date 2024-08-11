from .parser import JournalsParser
from .api import XeroApi
from sql import get_tenant_db
from sqlite3 import Connection
from pandas import DataFrame
import traceback
import sys

def write_df_to_sql(con:Connection, df: DataFrame, tablename: str, schema: str):
    df.to_sql(tablename, con=con, if_exists='append', index=False, schema=schema)


class JournalUpdater():

    def __init__(self, tenant_id, api_client: XeroApi):
        self.tenant_id = tenant_id
        self.api_client = api_client


    def get_last_jrnlno(self):
        jrnlno = 0
        stmt = f"SELECT TOP 1 JournalNumber from xero.Journals ORDER BY JournalNumber DESC;"
        con = get_tenant_db(self.tenant_id)
        result = con.execute(stmt)
        first = result.fetchone()
        if first:
            jrnlno = first[0]
        con.close()
        return jrnlno

    def update_sql(self):
        offset = self.get_last_jrnlno()
        try:
            parser = JournalsParser(self.api_client.get_journals(offset))
        except:
            print(traceback.format_exc() + f'\n tenant_id = {self.tenant_id}', file=sys.stderr)
            return {"error": True, "description": "Failed to get xero data"}
        if len(parser.df_journals) > 0:
            con = get_tenant_db(self.tenant_id)
            with con:
                try:
                    write_df_to_sql(con, parser.df_journals, 'Journals', 'xero')
                    write_df_to_sql(con, parser.df_journal_lines, 'JournallLines', 'xero')
                except Exception:
                    con.close()
                    return {
                        'error': True,
                        'description': 'Failed while writing to to db'
                    }
            con.close()
        entries = len(parser.df_journals)
        last_update = None
        if entries > 0:
            last_update = parser.df_journals['CreatedDateUTC'][entries - 1] # type: ignore
            last_entry = parser.df_journals['JournalNumber'][entries - 1] # type: ignore
        else:
            last_update = self.last_update()
            last_entry = offset + entries
        if entries >= 100:
            return {
                'error': False,
                'done': False,
                'description': f'Updated {entries} Journal entries\nLast Journal number: {last_entry}',
                'last_update': str(last_update)
            }
        return {
            'error': False,
            'done': True,
            'description': f'Updated {entries} Journal entries\nLast Journal number: {last_entry}',
            'last_update': str(self.last_update())
        }

    def full_update(self) -> dict:
        while True:
            offset = self.get_last_jrnlno()
            parser = JournalsParser(self.api_client.get_journals(offset))
            if parser is None:
                return {
                    'error': True,
                    'description': traceback.format_exc(),
                    'last_update': str(self.last_update())
                }
            elif len(parser.df_journals) > 0:
                con = get_tenant_db(self.tenant_id)
                with con:
                    try:
                        write_df_to_sql(con, parser.df_journals, 'Journals', 'xero')
                        write_df_to_sql(con, parser.df_journal_lines, 'JournalLines', 'xero')
                        write_df_to_sql(con, parser.df_journal_lines_tracking, 'JournalLineTracking', 'xero')
                    except Exception:
                        con.close()
                        return {
                            'error': True,
                            'description': 'Failed while writing to to db'
                        }
                con.close()
            entries = len(parser.df_journals)
            offset += entries
            if entries < 100:
                break
        return {
            'error': False,
            'description': f'Updated Journal entries\nLast Journal number: {offset}',
            'last_update': str(self.last_update())
        }

    def last_update(self):
        stmt = f"SELECT TOP 1 CreatedDateUTC FROM xero.Journals ORDER BY CreatedDateUTC DESC"
        con = get_tenant_db(self.tenant_id)
        result = con.execute(stmt)
        first = result.fetchone()
        if first:
            return first[0]
        con.close()
        return None
