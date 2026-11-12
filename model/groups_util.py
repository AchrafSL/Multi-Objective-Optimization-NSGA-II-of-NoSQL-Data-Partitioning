import os
import csv

class DataGroup:
    def __init__(
        self,
        group_id,
        table,
        key_start=None,
        key_end=None,
        size=0,
        request_count=0,
        access_frequency=0.0,
        hotness=0.0,
        current_server=None
    ):
        self.group_id = group_id
        self.table = table
        self.key_start = key_start
        self.key_end = key_end
        self.size = size
        self.request_count = request_count
        self.access_frequency = access_frequency
        self.hotness = hotness
        self.current_server = current_server

    def __repr__(self):
        return (
            f"DataGroup("
            f"id={self.group_id}, "
            f"table={self.table}, "
            f"key_start={self.key_start}, "
            f"key_end={self.key_end}, "
            f"size={self.size}, "
            f"requests={self.request_count}, "
            f"access_frequency={self.access_frequency}, "
            f"hotness={self.hotness}, "
            f"server={self.current_server})"
        )










def get_dataset_features(file_path, row_key):
    row_count = 0

    with open(file_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row_count += 1

    return {
        "rows": row_count,
        "size_bytes": os.path.getsize(file_path)
    }








def save_groups(groups, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        for group in groups:
            f.write(f"{group}\n")









def get_region_keys(file_path, row_key, regions):
    """
        - given all region keys -> maps region to it's keys.
        - load the dataset keys only when it's needed to avoid that memory problem we faced.
    """
    result = []

    for region_start, region_end, server in regions:
        region_keys = []

        with open(file_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                key = row[row_key].strip()

                if (not region_start or key >= region_start) and (not region_end or key < region_end):
                    region_keys.append(key)


        if region_keys:
            region_keys.sort()
            result.append((region_keys, server))

    return result