import sys
import os
import shutil
import argparse
import subprocess

PG_BIN = "/usr/lib/postgresql/9.1/bin/"
PG_CONF = '/etc/postgresql/9.1/main/postgresql.conf'

def pg_ctl( database_path, mod = 'start' ):
    """
        Start/Stop PostgreSQL with variable data_directory.
        mod = [start, end, restart, reload]
    """
    new_data_directory = "'%s'" % database_path
    cmd = 'sed -i "s|data_directory = .*|data_directory = %s|g" %s' % (new_data_directory, PG_CONF)
    subprocess.call(cmd, shell=True)
    subprocess.call('service postgresql %s' % (mod), shell=True)


def set_pg_permission( database_path ):
    """
        Set the correct permissions for a newly created PostgreSQL data_directory.
    """
    subprocess.call('chown -R postgres:postgres %s' % database_path, shell=True)
    subprocess.call('chmod -R 0700 %s' % database_path, shell=True)


def create_pg_db(user, password, database, database_path, schema):
    """
        Initialize PostgreSQL Database, add database user und create the pubmed Database.
    """
    os.makedirs( database_path )
    set_pg_permission( database_path )
    # initialize a new postgres database
    subprocess.call("su - postgres -c '%s --auth=trust --pgdata=%s'" % (os.path.join(PG_BIN, 'initdb'), database_path), shell=True)

    shutil.copy('/etc/ssl/certs/ssl-cert-snakeoil.pem', os.path.join(database_path, 'server.crt'))
    shutil.copy('/etc/ssl/private/ssl-cert-snakeoil.key', os.path.join(database_path, 'server.key'))
    set_pg_permission( os.path.join(database_path, 'server.crt') )
    set_pg_permission( os.path.join(database_path, 'server.key') )

    # change data_directory in postgresql.conf and start the service with the new location
    pg_ctl( database_path, 'start' )

    subprocess.call( """su - postgres -c "psql --command \\"CREATE USER parser WITH SUPERUSER PASSWORD 'parser'\\";"
                    """, shell=True )

    subprocess.call("su - postgres -c 'createdb -O %s %s'" % (user, database), shell=True)
    subprocess.call( """su - postgres -c "psql --dbname %s --command \\"CREATE SCHEMA %s AUTHORIZATION %s\\";"
                    """  % (database, schema, user), shell=True )

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Initializing a complete PubMed2Go database.')

    parser.add_argument("--dbuser", required=True,
                    help="Username of the pubmed2go Database Administrator. That name will be specified in the universe_wsgi.xml file.")

    parser.add_argument("--dbpassword", required=True,
                    help="Password of the pubmed2go Database Administrator. That name will be specified in the universe_wsgi.xml file.")

    parser.add_argument("--db-name", dest='db_name', required=True,
                    help="Pubmed2go Database name. That name will be specified in the universe_wsgi.xml file.")

    parser.add_argument("--db-schema", dest='db_schema', required=True,
                    help="Pubmed2go schema name. That name will be specified in the universe_wsgi.xml file.")

    parser.add_argument("--dbpath",
                    help="Pubmed2go Database path.")

    options = parser.parse_args()

    """
        Initialize the Pubmed2go Database + adding an Admin user.
        This database is the default one, created by the Dockerfile. 
        The user can set a volume (-v /path/:/export/) to get a persistent database.
    """
    create_pg_db(options.dbuser, options.dbpassword, options.db_name, options.dbpath, options.db_schema)


