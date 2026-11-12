#!/usr/bin/env python3

"""
    This was used to transfer our data to Hbase
    This is the code executed on linux not here.
"""

import csv
import sys
import time
import happybase

BATCH_SIZE = 1000


def load_data(csv_file, table_name, row_key):

    connection = happybase.Connection(host="master",port=9090)

    connection.open()

    table = connection.table(table_name)

    start = time.time()
    count = 0

    with open(csv_file,"r", encoding="utf-8", newline="") as file:

        reader = csv.DictReader(file)

        with table.batch(batch_size=BATCH_SIZE) as batch:

            for row in reader:

                key = str(row[row_key]).strip().encode("utf-8")

                data = {}

                for column, value in row.items():

                    if column != row_key and value:

                        hbase_column = f"info:{column}".encode("utf-8")
                        hbase_value = str(value).strip().encode("utf-8", errors="replace")

                        data[hbase_column] = hbase_value

                batch.put(key, data)

                count += 1

                if count % 5000 == 0:
                    print(f"{count} rows loaded")

    elapsed = time.time() - start

    print()
    print("Loading finished.")
    print(f"Rows loaded: {count}")
    print(f"Time: {elapsed:.2f} seconds")

    if elapsed > 0:
        print(f"Rate: {count / elapsed:.0f} rows/sec")

    connection.close()





if len(sys.argv) != 4:

    print("Usage: python3 load_hbase.py <csv_file> <table> <row_key>")

    sys.exit(1)


load_data(sys.argv[1], sys.argv[2],sys.argv[3])
