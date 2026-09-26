import asyncio
import asyncpg

async def verify():
    conn = await asyncpg.connect("postgresql://sih_user:sih_password@127.0.0.1:5433/sih_monitor")
    rev = await conn.fetchval("SELECT version_num FROM alembic_version")
    print(f"Current Alembic revision in DB: {rev}")
    
    cols = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'projects' ORDER BY ordinal_position"
    )
    print("\nProjects table columns:")
    for c in cols:
        print(f"  - {c['column_name']}: {c['data_type']}")
        
    tables = await conn.fetch(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
    )
    print("\nPublic tables:")
    for t in tables:
        print(f"  - {t['table_name']}")
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(verify())
