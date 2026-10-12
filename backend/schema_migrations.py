"""Small idempotent schema upgrades; preserve existing wallet links and evidence."""
from sqlalchemy import inspect, text


def migrate_wallet_bindings(engine):
    # One binding per Veris user; a wallet may independently sign for multiple users.
    # Document ownership remains keyed by user_id, never just by wallet address.
    with engine.begin() as connection:
        dialect = connection.dialect.name
        if dialect == 'postgresql':
            connection.execute(text("SET LOCAL lock_timeout = '10s'"))
            connection.execute(text('SELECT pg_advisory_xact_lock(763921104)'))
        elif dialect == 'sqlite':
            connection.exec_driver_sql('BEGIN IMMEDIATE')
        inspector = inspect(connection)
        table = 'veris_wallet_bindings'
        if not inspector.has_table(table):
            return
        constraints = [c for c in inspector.get_unique_constraints(table)
                       if c['column_names'] == ['address']]
        indexes = [i for i in inspector.get_indexes(table)
                   if i.get('unique') and i['column_names'] == ['address']
                   and not i.get('duplicates_constraint')]
        sqlite_unique_address = False
        if dialect == 'sqlite':
            # SQLite reflection can omit inline UNIQUE clauses in legacy DDL.
            quote = connection.dialect.identifier_preparer.quote
            for index in connection.exec_driver_sql('PRAGMA index_list(veris_wallet_bindings)').mappings():
                if index['unique']:
                    columns = [row['name'] for row in connection.exec_driver_sql(
                        'PRAGMA index_info(' + quote(index['name']) + ')').mappings()]
                    sqlite_unique_address |= columns == ['address']
        if not constraints and not indexes and not sqlite_unique_address:
            return
        if dialect == 'sqlite':
            connection.exec_driver_sql('CREATE TABLE veris_wallet_bindings_v2 '
                                       '(user_id VARCHAR(36) NOT NULL PRIMARY KEY, '
                                       'address VARCHAR(42) NOT NULL, connected_at VARCHAR(40) NOT NULL)')
            connection.exec_driver_sql('INSERT INTO veris_wallet_bindings_v2 '
                                       '(user_id,address,connected_at) SELECT user_id,address,connected_at '
                                       'FROM veris_wallet_bindings')
            connection.exec_driver_sql('DROP TABLE veris_wallet_bindings')
            connection.exec_driver_sql('ALTER TABLE veris_wallet_bindings_v2 RENAME TO veris_wallet_bindings')
        elif dialect == 'postgresql':
            quote = connection.dialect.identifier_preparer.quote
            for constraint in constraints:
                connection.exec_driver_sql('ALTER TABLE veris_wallet_bindings DROP CONSTRAINT '
                                           + quote(constraint['name']))
            for index in indexes:
                connection.exec_driver_sql('DROP INDEX ' + quote(index['name']))
        else:
            raise RuntimeError('Wallet binding migration requires PostgreSQL or SQLite.')
