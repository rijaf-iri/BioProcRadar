import os
import psycopg2
import pandas as pd
from .misc import load_yaml_file

def bioDBRadar(bioradar_dir):
    auth_file = os.path.join(
        bioradar_dir,
        'BioConfigRadar',
        'auth', 'biodb'
    )
    auth = load_yaml_file(auth_file)
    conn = psycopg2.connect(**auth)
    conn.autocommit = True
    cursor = conn.cursor()
    return cursor, conn

def executeSQLCmd(
        cursor, sqlCmd, args=None
    ):
    if args is None:
        cursor.execute(sqlCmd)
    else:
        cursor.execute(sqlCmd, args)
    return 0

def queryDB_pd_df(
        cursor, conn,
        sqlQuery, args=None
    ):
    if args is None:
        df = pd.read_sql_query(sqlQuery, conn)
    else:
        df = pd.read_sql_query(
                sqlQuery, conn, params=args
            )
    return df

def queryDB_json(cursor, sqlQuery, args=None):
    if args is None:
        cursor.execute(sqlQuery)
    else:
        cursor.execute(sqlQuery, args)

    res = convert2json(cursor)
    return res

def convert2json(cursor):
    row_headers = [x[0] for x in cursor.description]
    result = cursor.fetchall()

    json_data = []
    for res in result:
        json_data.append(
            dict(zip(row_headers, res))
        )
    return json_data
