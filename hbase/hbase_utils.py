import happybase
import time



def get_connection():

    connection = happybase.Connection(host="master", port=9090, timeout=10000)

    connection.open()

    return connection






def performance_count(f):

    def wrapper(*args, **kwargs):

        start = time.perf_counter()

        result = f(*args, **kwargs)

        latency = (time.perf_counter() - start) * 1000

        return result, latency

    return wrapper





def get_regions(table_name):
    connection = get_connection()
    regions = connection.table(table_name).regions()
    connection.close()

    result = []
    for region in regions:
        start_key = region["start_key"].decode("utf-8")
        end_key = region["end_key"].decode("utf-8")
        server = region["server_name"].decode("utf-8")
        result.append((start_key, end_key, server))
    return result






def get_region_details(table_name):
    """
        we added another function containing region name just to do not break previous code 
    """
    connection = get_connection()

    regions = connection.table(table_name).regions()

    connection.close()

    result = []

    for region in regions:

        result.append({
            "region_name": region["name"].decode("utf-8"),
            "start_key": region["start_key"].decode("utf-8"),
            "end_key": region["end_key"].decode("utf-8"),
            "server": region["server_name"].decode("utf-8").split(",")[0],
            "server_name": region["server_name"].decode("utf-8")
        })

    return result







def find_region(group, regions):

    for region in regions:
        start_key = region["start_key"]
        end_key = region["end_key"]

        if ((not start_key or group.key_start >= start_key) and (not end_key or group.key_end < end_key)):
            return region

    return None