import csv
import os
from hbase.reader import get_row, close_connection

"""
    En execute ce code sur linux
"""

def execute_workload(workload_file, output_file):

    with open(workload_file, "r", encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(input_file)

        with open(output_file, "w", encoding="utf-8", newline="") as output_file:
            writer = csv.writer(output_file)

            writer.writerow(["request_id", "window_number", "table", "group_id", "key", "latency_ms"])

            for row in reader:

                result, latency = get_row(row["table"], row["key"])

                writer.writerow([
                    row["request_id"],
                    row["window_number"],
                    row["table"],
                    row["group_id"],
                    row["key"],
                    round(latency, 3)
                ])



if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    INPUT_DIR = os.path.join(BASE_DIR, "input")
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")

    execute_workload(os.path.join(INPUT_DIR, "moving_normalDist.csv"), os.path.join(OUTPUT_DIR, "normal_execution.csv"))
    execute_workload(os.path.join(INPUT_DIR, "moving_skewedDist.csv"), os.path.join(OUTPUT_DIR, "skewed_execution.csv"))

    close_connection()