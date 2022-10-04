from datasette import hookimpl

CREATE_TABLE_SQL = """
create table _public_tables (table_name text primary key)
""".strip()


@hookimpl
def startup(datasette):
    async def inner():
        db = db_from_config(datasette)
        assert db.is_mutable, "Database is immutable"
        if "_public_tables" not in await db.table_names():
            await db.execute_write(CREATE_TABLE_SQL)

    return inner


@hookimpl
def permission_allowed(datasette, action, resource):
    async def inner():
        if action != "view-table":
            return None
        # Say 'yes' if this table is public
        database_name, table_name = resource
        # TODO: include database_name in check
        db = db_from_config(datasette)
        rows = await db.execute(
            "select 1 from _public_tables where table_name = ?", [table_name]
        )
        if len(rows):
            return True

    return inner


def db_from_config(datasette):
    config = datasette.plugin_config("datasette-public") or {}
    db_name = config.get("database") or None
    return datasette.get_database(db_name)
