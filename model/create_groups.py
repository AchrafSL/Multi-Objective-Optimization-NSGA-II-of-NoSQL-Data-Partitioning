from model.groups_util import DataGroup, get_dataset_features, get_region_keys, save_groups
from hbase.hbase_utils import get_regions

"""
    Runs on linux not windows
"""


def create_groups(file_path, table, row_key_name, number_of_groups=10):
    """
        create logical groups from the table in each region to simplify the process.
    """

    features = get_dataset_features(file_path, row_key_name) # contains: row_count, file_size.
    bytes_per_row = features["size_bytes"] / features["rows"]

    regions = get_regions(table)  # contains list of [ (start_key, end_key, server_name), ...]
    region_data = get_region_keys(file_path, row_key_name, regions)# contains (region_keys, server_name)


    groups = []
    group_id = 1


    for region_keys, server in region_data:

        # Divide the keys of this region into logical groups.
        group_size = len(region_keys) // number_of_groups
        group_size = group_size if group_size != 0 else 1

 
        for i in range(number_of_groups):
            start = i * group_size
            end = len(region_keys) if (i == number_of_groups - 1) else (i + 1) * group_size
            group_keys = region_keys[start:end]

            if not group_keys:
                break

            groups.append(DataGroup(
                group_id=f"{table}_G{group_id}",
                table=table,
                key_start=group_keys[0],
                key_end=group_keys[-1],
                size=int(len(group_keys) * bytes_per_row),
                current_server=server
            ))

            group_id += 1

    return groups











if __name__ == "__main__":
    import os

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATASET_DIR = os.path.join(BASE_DIR, "..", "dataset")
    GROUPS_DIR = os.path.join(BASE_DIR, "groups")

    os.makedirs(GROUPS_DIR, exist_ok=True)

    tables = [
        ("customer", "customer.csv", "customer_id"),
        ("product", "product.csv", "id"),
        ("transactions", "transactions.csv", "booking_id"),
        ("click_stream", "click_stream.csv", "event_id")
    ]

    for table, file_name, row_key in tables:
        groups = create_groups(os.path.join(DATASET_DIR, file_name), table, row_key)
        save_groups(groups, os.path.join(GROUPS_DIR, f"{table}_groups.txt"))
        print(f"{table}: {len(groups)} groups created")

    print("All groups created.")