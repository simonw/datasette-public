from datasette.app import Datasette
import pytest
import sqlite3


@pytest.mark.asyncio
@pytest.mark.parametrize("db_name", (None, "data2"))
async def test_plugin_creates_table(tmpdir, db_name):
    db_path = str(tmpdir / "data.db")
    db_path2 = str(tmpdir / "data2.db")
    for path in (db_path, db_path2):
        sqlite3.connect(path).execute("vacuum")
    metadata = {}
    if db_name:
        metadata["plugins"] = {"datasette-public": {"database": db_name}}
    ds = Datasette([db_path, db_path2], metadata=metadata)
    await ds.invoke_startup()
    # The database in the config should have the table now
    if db_name:
        assert _get_tables(db_path) == []
        assert _get_tables(db_path2) == ["_public_tables"]
    else:
        assert _get_tables(db_path) == ["_public_tables"]
        assert _get_tables(db_path2) == []


@pytest.mark.asyncio
async def test_error_if_database_is_immutable(tmpdir):
    db_path = str(tmpdir / "data.db")
    sqlite3.connect(db_path).execute("vacuum")
    ds = Datasette(immutables=[db_path])
    with pytest.raises(AssertionError):
        await ds.invoke_startup()


def _get_tables(path):
    return [
        r[0]
        for r in sqlite3.connect(path)
        .execute("select name from sqlite_master where type = 'table'")
        .fetchall()
    ]
