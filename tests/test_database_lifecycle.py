import datetime
import os
import subprocess


# TODO consider managing lifecycle of Odoo containers in here, so we can
#     guarantee what databases are available (making tests of odookit-databases
#     more meaningful) and destroy the whole stack at the end of each test,
#     making these truly unit tests.

__TEST_NAME = datetime.datetime.now().isoformat()


def test_get_list_of_odoo_databases_exits_with_status_code_0():
    process = subprocess.run(
        ['odookit-databases'],
        env=merge_dicts(os.environ, {'ODOOKIT_URL': odoo_url()}),
    )
    assert process.returncode == 0


def test_database_lifecycle():
    initial_databases = current_databases(url=odoo_url())
    subprocess.run(
        [
            'odookit-create-database',
            '-p', 'opensesame',
            database_name(),
        ],
        env=merge_dicts(os.environ, {'ODOOKIT_URL': odoo_url()}),
        check=True,
    )
    assert (
        current_databases(url=odoo_url())
        == initial_databases | {database_name()}
    ), 'new database now in databases list'

    subprocess.run(
        ['odookit-drop-database', database_name()],
        env=merge_dicts(os.environ, {'ODOOKIT_URL': odoo_url()}),
        check=True,
    )
    assert current_databases(url=odoo_url()) == initial_databases, \
        'new database disappeared from database list again'


def current_databases(url) -> frozenset:
    list_databases_result = subprocess.run(
        ['odookit-databases'],
        env=merge_dicts(os.environ, {'ODOOKIT_URL': url}),
        stdout=subprocess.PIPE,
        check=True,
    )
    return frozenset(list_databases_result.stdout.splitlines())


def alnum_only(string):
    return ''.join(char for char in string if char.isalnum())


def name_of_test():
    return __TEST_NAME


def database_name():
    return f'test{alnum_only(name_of_test())}'


def odoo_url():
    # Don't accidentally point at a real one set up in user's main environment
    return os.environ['TEST_ODOOKIT_URL']

def merge_dicts(*dicts):
    result = {}
    for dict_ in dicts:
        result.update(dict_)
    return result
