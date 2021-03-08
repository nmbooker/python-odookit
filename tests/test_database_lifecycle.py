import os
import subprocess

import pytest


@pytest.fixture()
def postgres_container():
    create_process = subprocess.run(
        [
            'docker',
            'create',
            'postgres:13',
            '-e', 'POSTGRES_USER',
            '-e', 'POSTGRES_PASSWORD',
        ],
        env=merge_dicts(
            os.environ,
            {'POSTGRES_USER': 'odoo', 'POSTGRES_PASSWORD': 'odoodbpassword'},
        ),
        stdout=subprocess.PIPE,
        check=True,
    )
    postgres_container_name = create_process.stdout.splitlines()[0]
    try:
        subprocess.run(['docker', 'start', postgres_container_name], check=True)
        yield postgres_container_name
        subprocess.run(['docker', 'stop', postgres_container_name], check=True)
    finally:
        subprocess.run(['docker', 'rm', postgres_container_name], check=True)


# TODO wire up Odoo container to the Postgres container

@pytest.fixture()
def odoo_container(postgres_container):
    creation_process = subprocess.run(
        [
            'docker',
            'create',
            'odoo:8',
            '--expose', '8069',
            '-e', 'HOST',
            '-e', 'USER',
            '-e', 'PASSWORD',
        ],
        env=merge_dicts(
            os.environ,
            {'HOST': postgres_container, 'USER': 'odoo', 'PASSWORD': 'odoodbpassword'},
        ),
        stdout=subprocess.PIPE,
        check=True,
    )
    odoo_container_name = creation_process.stdout.splitlines()[0]
    try:
        subprocess.run(['docker', 'start', odoo_container_name], check=True)
        odoo_ip_address = the_only(
            subprocess.run(
                [
                    'docker', 'container', 'inspect',
                    '-f', '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
                    odoo_container_name,
                ],
                stdout=subprocess.PIPE,
                check=True,
            )
            .stdout
            .splitlines()
        )
        yield odoo_ip_address.decode('utf-8')
        subprocess.run(['docker', 'stop', odoo_container_name], check=True)
    finally:
        subprocess.run(['docker', 'rm', '-f', odoo_container_name], check=True)


def test_get_list_of_odoo_databases_exits_with_status_code_0(odoo_container):
    process = subprocess.run(
        ['odookit-databases'],
        env=merge_dicts(os.environ, {'ODOOKIT_URL': odoo_url(odoo_container)}),
    )
    assert process.returncode == 0


def odoo_url(odoo_container_name):
    return f"http://{odoo_container_name}:8069"


@pytest.mark.skip('while debugging')
def test_database_lifecycle(odoo_container):
    initial_databases = current_databases(url=odoo_url(odoo_container))
    subprocess.run(
        [
            'odookit-create-database',
            '-p', 'opensesame',
            'test1',
        ],
        env=merge_dicts(os.environ, {'ODOOKIT_URL': odoo_url(odoo_container)}),
        check=True,
    )
    assert (
        current_databases(url=odoo_url(odoo_container))
        == initial_databases | {'test1'}
    ), 'new database now in databases list'

    subprocess.run(
        ['odookit-drop-database', 'test1'],
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


def merge_dicts(*dicts):
    result = {}
    for dict_ in dicts:
        result.update(dict_)
    return result


def the_only(iterable):
    iterator = iter(iterable)
    try:
        first = next(iterator)
    except StopIteration:
        raise ValueError('iterable was empty')
    else:
        try:
            next(iterator)
        except StopIteration:
            return first
        else:
            raise ValueError('iterable yielded more than one value')
