from sqlalchemy import inspect
from app.db.database import Base, engine
import asyncio

async def check_schema():
    async with engine.begin() as conn:
        # Get actual table info
        def get_tables(conn):
            insp = inspect(conn)
            return insp.get_table_names()
        tables = await conn.run_sync(get_tables)
        print('Tables:', tables)
        
        for t in tables:
            if 'track' in t.lower():
                def get_cols(conn, table_name):
                    insp = inspect(conn)
                    cols = insp.get_columns(table_name)
                    idxs = insp.get_indexes(table_name)
                    fks = insp.get_foreign_keys(table_name)
                    return cols, idxs, fks
                cols, idxs, fks = await conn.run_sync(get_cols, t)
                print(f'\n=== {t} ===')
                print('Columns:')
                for c in cols:
                    print(f'  {c["name"]}: {c["type"]} nullable={c["nullable"]} default={c.get("default")}')
                print('Indexes:')
                for i in idxs:
                    print(f'  {i["name"]}: {i["column_names"]} unique={i.get("unique", False)}')
                print('Foreign Keys:')
                for f in fks:
                    print(f'  {f["name"]}: {f["constrained_columns"]} -> {f["referred_table"]}.{f["referred_columns"]}')

asyncio.run(check_schema())