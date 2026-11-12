from hbase.hbase_utils import get_connection, performance_count
import happybase

"""
    make sure the server: hbase thrift start -p 9090 
    IS ON.

    to do not make a new connect each time we read we changed the method.
"""


connection = happybase.Connection(host="master", port=9090, timeout=10000)
connection.open()

@performance_count
def get_row(table_name, row_key):
    table = connection.table(table_name)
    return table.row(row_key.encode("utf-8"))


def close_connection():
    connection.close()