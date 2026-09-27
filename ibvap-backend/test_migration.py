import asyncio
from alembic.config import Config
from alembic import command
from app.db.database import engine, Base
from sqlalchemy import inspect

async def test_migration():
    # Create a fresh DB
    import os
    import uuid
    from pathlib import Path
    
    db_dir = Path('tests/test_dbs')
    db_dir.mkdir(exist_ok=True)
    db_file = db_dir / f'migration_test_{uuid.uuid4().hex}.db'
    db_url = f'sqlite+aiosqlite:///{db_file.as_posix()}'
    
    # Run alembic upgrade
    alembic_cfg = Config('alembic.ini')
    alembic_cfg.set_main_option('sqlalchemy.url', db_url)
    
    # This will create the tables
    command.upgrade(alembic_cfg, 'head')
    print('Migration upgrade successful')
    
    # Verify schema
    from sqlalchemy.ext.asyncio import create_async_engine
    test_engine = create_async_engine(db_url)
    async with test_engine.begin() as conn:
        def get_tables(conn):
            insp = inspect(conn)
            return insp.get_table_names()
        tables = await conn.run_sync(get_tables)
        print('Tables after migration:', tables)
        
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
                    print(f'  {c["name"]}: {c["type"]} nullable={c["nullable"]}')
                print('Indexes:')
                for i in idxs:
                    print(f'  {i["name"]}: {i["column_names"]} unique={i.get("unique", False)}')
                print('Foreign Keys:')
                for f in fks:
                    print(f'  {f["name"]}: {f["constrained_columns"]} -> {f["referred_table"]}.{f["referred_columns"]}')
    
    await test_engine.dispose()
    try:
        db_file.unlink()
    except:
        pass

asyncio.run(test_migration())