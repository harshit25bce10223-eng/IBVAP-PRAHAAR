from sqlalchemy import inspect, create_engine
engine = create_engine('sqlite:///ibvap.db')
insp = inspect(engine)
tables = insp.get_table_names()
print('Tables:', tables)
for t in tables:
    if 'anpr' in t.lower() or 'vehicle' in t.lower() or 'plate' in t.lower():
        cols = insp.get_columns(t)
        print(f'  {t}: {[c["name"] for c in cols]}')