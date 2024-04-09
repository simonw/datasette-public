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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "public_instance,public_table,should_allow",
    (
        (True, False, True),
        (False, False, False),
        (False, True, True),
        (True, True, True),
    ),
)
@pytest.mark.parametrize("is_view", (True, False))
async def test_public_table(
    tmpdir, public_instance, public_table, should_allow, is_view
):
    db_path = str(tmpdir / "data.db")
    conn = sqlite3.connect(db_path)
    if is_view:
        conn.execute("create view t1 as select 1")
    else:
        conn.execute("create table t1 (id int)")
    if public_table:
        with conn:
            conn.execute("create table _public_tables (table_name text primary key)")
            conn.execute("insert into _public_tables (table_name) values (?)", ["t1"])
    metadata = {}
    if not public_instance:
        metadata["allow"] = False
    ds = Datasette([db_path], metadata=metadata)
    await ds.invoke_startup()
    response = await ds.client.get("/data/t1")
    if should_allow:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_where_is_denied(tmpdir):
    db_path = str(tmpdir / "data.db")
    conn = sqlite3.connect(db_path)
    conn.execute("create table t1 (id int)")
    with conn:
        conn.execute("create table _public_tables (table_name text primary key)")
        conn.execute("insert into _public_tables (table_name) values (?)", ["t1"])
    ds = Datasette([db_path], metadata={"allow": False})
    await ds.invoke_startup()
    # This should be allowed
    assert (await ds.client.get("/data/t1")).status_code == 200
    # This should not
    assert (await ds.client.get("/data")).status_code == 403
    # Neither should this
    response = await ds.client.get("/data/t1?_where=1==1")
    assert ">1 extra where clause<" not in response.text
    # BUT they should be allowed to use it IF they have database permission
    ds._metadata_local["databases"] = {"data": {"allow": True}}
    response2 = await ds.client.get("/data/t1?_where=1==1")
    assert ">1 extra where clause<" in response2.text


@pytest.mark.asyncio
@pytest.mark.parametrize("user_is_root", (True, False))
@pytest.mark.parametrize("is_view", (True, False))
async def test_ui_for_editing_table_privacy(tmpdir, user_is_root, is_view):
    db_path = str(tmpdir / "data.db")
    conn = sqlite3.connect(db_path)
    noun = "table"
    if is_view:
        noun = "view"
        conn.execute("create view t1 as select 1")
    else:
        conn.execute("create table t1 (id int)")
    ds = Datasette([db_path], metadata={"allow": {"id": "*"}})
    await ds.invoke_startup()
    # Regular user can see table but not edit privacy
    cookies = {
        "ds_actor": ds.sign({"a": {"id": "root" if user_is_root else "user"}}, "actor")
    }
    menu_fragment = '<li><a href="/-/public-table/data/t1">Make {} public</a>'.format(
        noun
    )
    response = await ds.client.get("/data/t1", cookies=cookies)
    if user_is_root:
        assert menu_fragment in response.text
    else:
        assert menu_fragment not in response.text

    # Check permissions on /-/public-table/data/t1 page
    response2 = await ds.client.get("/-/public-table/data/t1", cookies=cookies)
    if user_is_root:
        assert response2.status_code == 200
    else:
        assert response2.status_code == 403
    # non-root user test ends here
    if not user_is_root:
        return
    # Test root user can toggle table privacy
    html = response2.text
    assert "{} is currently <strong>private</strong>".format(noun.title()) in html
    assert '<input type="hidden" name="action" value="make-public">' in html
    assert '<input type="submit" value="Make public">' in html
    assert _get_public_tables(db_path) == []
    csrftoken = response2.cookies["ds_csrftoken"]
    cookies["ds_csrftoken"] = csrftoken
    response3 = await ds.client.post(
        "/-/public-table/data/t1",
        cookies=cookies,
        data={"action": "make-public", "csrftoken": csrftoken},
    )
    assert response3.status_code == 302
    assert response3.headers["location"] == "/data/t1"
    assert _get_public_tables(db_path) == ["t1"]
    # And toggle it private again
    response4 = await ds.client.get("/-/public-table/data/t1", cookies=cookies)
    html2 = response4.text
    assert "{} is currently <strong>public</strong>".format(noun.title()) in html2
    assert '<input type="hidden" name="action" value="make-private">' in html2
    assert '<input type="submit" value="Make private">' in html2
    response5 = await ds.client.post(
        "/-/public-table/data/t1",
        cookies=cookies,
        data={"action": "make-private", "csrftoken": csrftoken},
    )
    assert response5.status_code == 302
    assert response5.headers["location"] == "/data/t1"
    assert _get_public_tables(db_path) == []


def _get_public_tables(db_path):
    conn = sqlite3.connect(db_path)
    return [row[0] for row in conn.execute("select table_name from _public_tables")]


def _get_tables(path):
    return [
        r[0]
        for r in sqlite3.connect(path)
        .execute("select name from sqlite_master where type = 'table'")
        .fetchall()
    ]
