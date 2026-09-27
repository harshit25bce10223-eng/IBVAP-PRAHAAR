import asyncio
from alembic.config import Config
from alembic import command
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

async def test_migration():
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
    
    # Verify schema using sync engine
    from sqlalchemy import create_engine
    sync_engine = create_engine(db_url.replace('sqlite+aiosqlite', 'sqlite'))
    insp = inspect(sync_engine)
    tables = insp.get_table_names()
    print('Tables after migration:', tables)
    
    for t in tables:
        if 'track' in t.lower():
            cols = insp.get_columns(t)
            idxs = insp.get_indexes(t)
            fks = insp.get_foreign_keys(t)
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
    
    try:
        db_file.unlink()
    except:
        pass

asyncio.run(test_migration())