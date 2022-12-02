from datasette import hookimpl, Forbidden, Response, NotFound
from urllib.parse import quote_plus, unquote_plus

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
def permission_allowed(datasette, action, actor, resource):
    async def inner():
        # Root actor can always edit public status
        if actor and actor.get("id") == "root" and action == "public-tables":
            return True
        if action == "execute-sql" and not actor:
            return await datasette.permission_allowed(
                actor, "view-database", resource=resource
            )
        if action != "view-table":
            return None
        # Say 'yes' if this table is public
        database_name, table_name = resource
        db = db_from_config(datasette)
        if await table_is_public(db, table_name):
            return True

    return inner


async def table_is_public(db, table_name):
    # TODO: include database_name in check
    rows = await db.execute(
        "select 1 from _public_tables where table_name = ?", [table_name]
    )
    if len(rows):
        return True


@hookimpl
def table_actions(datasette, actor, database, table):
    async def inner():
        if not await datasette.permission_allowed(
            actor, "public-tables", resource=database, default=False
        ):
            return []
        if database != "_internal":
            noun = "table"
            if table in await datasette.get_database(database).view_names():
                noun = "view"
            is_private = not await table_is_public(db_from_config(datasette), table)
            return [
                {
                    "href": datasette.urls.path(
                        "/-/public-table/{}/{}".format(database, quote_plus(table))
                    ),
                    "label": "Make {} {}".format(
                        noun, "public" if is_private else "private"
                    ),
                }
            ]

    return inner


async def check_permissions(datasette, request, database):
    if database == "_internal" or not await datasette.permission_allowed(
        request.actor, "public-tables", resource=database, default=False
    ):
        raise Forbidden("Permission denied for changing table privacy")


async def change_table_privacy(request, datasette):
    table = unquote_plus(request.url_vars["table"])
    database_name = request.url_vars["database"]
    await check_permissions(datasette, request, database_name)
    this_db = datasette.get_database(database_name)
    is_view = table in await this_db.view_names()
    noun = "View" if is_view else "Table"
    if (
        not await this_db.table_exists(table)
        # This can use db.view_exists() after that goes out in a stable release
        and table not in await this_db.view_names()
    ):
        raise NotFound("{} not found".format(noun))

    permission_db = db_from_config(datasette)

    if request.method == "POST":
        form_data = await request.post_vars()
        action = form_data.get("action")
        if action == "make-public":
            msg = "public"
            await permission_db.execute_write(
                "insert or ignore into _public_tables (table_name) values (?)", [table]
            )
        elif action == "make-private":
            msg = "private"
            await permission_db.execute_write(
                "delete from _public_tables where table_name = ?", [table]
            )
        datasette.add_message(request, "{} '{}' is now {}".format(noun, table, msg))
        return Response.redirect(datasette.urls.table(database_name, table))

    is_private = not await table_is_public(permission_db, table)

    return Response.html(
        await datasette.render_template(
            "public_table_change_privacy.html",
            {
                "database": database_name,
                "table": table,
                "is_private": is_private,
                "noun": noun.lower(),
            },
            request=request,
        )
    )


@hookimpl
def register_routes():
    return [
        (
            r"^/-/public-table/(?P<database>[^/]+)/(?P<table>[^/]+)$",
            change_table_privacy,
        ),
    ]


def db_from_config(datasette):
    config = datasette.plugin_config("datasette-public") or {}
    db_name = config.get("database") or None
    return datasette.get_database(db_name)
