from datasette import hookimpl

CREATE_TABLE_SQL = """
create table _public_tables (table_tame text primary key)
""".strip()


@hookimpl
def startup(datasette):
    config = datasette.plugin_config("datasette-public") or {}
    db_name = config.get("database") or None

    async def inner():
        db = datasette.get_database(db_name)
        assert db.is_mutable, "Database is immutable"
        if "_public_tables" not in await db.table_names():
            await db.execute_write(CREATE_TABLE_SQL)

    return inner
