import csv
import random
import os
from workload.workload_utils import get_group_keys, choose_group, create_clickStream_groups, create_customer_groups, create_product_groups, create_transactions_groups


def generate_workload(groups, datasets, output_file, distribution, total_requests=1000000, window_size=1000):
    group_keys = get_group_keys(groups, datasets)

    with open(output_file, "w", encoding="utf-8", newline="") as f:

        writer = csv.writer(f)

        writer.writerow(["request_id", "window_number", "table", "operation", "key", "group_id"])

        window_number = 1

        shift = random.randint(0, 9)

        for request_id in range(1, total_requests + 1):

            group = choose_group(groups, distribution, shift) # choose a random group with probabilities 
            # the group with highest proba is the hotspot


            key = random.choice(group_keys[group.group_id]) # chose a random key from the keys of that group  

            writer.writerow([
                request_id,
                window_number,
                group.table,
                "GET",
                key,
                group.group_id
            ])


            if request_id % window_size == 0:
                shift = (shift + random.choice([-1, 0, 1])) % 10
                window_number += 1











if __name__ == "__main__":

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    WORKLOAD_OUTPUT_DIR = os.path.join(BASE_DIR,"workload","workloadOutput")


  
    normalDist_workload_file = os.path.join(WORKLOAD_OUTPUT_DIR, "moving_normalDist.csv")
    skewedDist_workload_file = os.path.join(WORKLOAD_OUTPUT_DIR, "moving_skewedDist.csv")

    customer_file = os.path.join(BASE_DIR, "dataset", "customer.csv")
    product_file = os.path.join(BASE_DIR, "dataset", "product.csv")
    transactions_file = os.path.join(BASE_DIR, "dataset", "transactions.csv")
    click_stream_file = os.path.join(BASE_DIR, "dataset", "click_stream.csv")

    customer_groups = create_customer_groups()
    product_groups = create_product_groups()
    transactions_groups = create_transactions_groups()
    click_stream_groups = create_clickStream_groups()

    groups = customer_groups + product_groups + transactions_groups + click_stream_groups

    datasets = {
        "customer": {
            "file": customer_file,
            "row_key": "customer_id"
        },
        "product": {
            "file": product_file,
            "row_key": "id"
        },
        "transactions": {
            "file": transactions_file,
            "row_key": "booking_id"
        },
        "click_stream": {
            "file": click_stream_file,
            "row_key": "event_id"
        }
    }

    generate_workload(groups, datasets, normalDist_workload_file, "moving_normal")
    generate_workload(groups, datasets, skewedDist_workload_file, "moving_skewed")