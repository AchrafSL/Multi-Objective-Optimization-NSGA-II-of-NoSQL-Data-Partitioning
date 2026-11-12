import csv


def load_execution(file_path):
    requests = []

    with open(file_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            requests.append(row)

    return requests







def update_group_stats(groups, requests):
    """
        use the requests results to update groups statistics
    """

    stats = {}
    window_requests = {}

    # Scan all requests once and collect statistics
    for request in requests:

        group_id = request["group_id"]
        window = int(request["window_number"])
        latency = float(request["latency_ms"])

        # Create statistics for this group if it does not exist
        if group_id not in stats:
            stats[group_id] = {
                "request_count": 0,
                "total_latency": 0,
                "windows": {}
            }

        # Update total requests and latency for the group
        stats[group_id]["request_count"] += 1
        stats[group_id]["total_latency"] += latency

        # Count requests of this group in this window
        if window not in stats[group_id]["windows"]:
            stats[group_id]["windows"][window] = 0

        stats[group_id]["windows"][window] += 1

        # Count total requests in this window
        if window not in window_requests:
            window_requests[window] = 0

        window_requests[window] += 1

    total_requests = len(requests)
    number_of_windows = len(window_requests)
    window_weight = 1 / number_of_windows




    # Update every DataGroup with its statistics
    for group in groups:

        if group.group_id not in stats:
            group.request_count = 0
            group.access_frequency = 0
            group.hotness = 0
            group.average_latency = 0
            continue

        group_stats = stats[group.group_id]

        group.request_count = group_stats["request_count"]

        # Frequency over the complete workload
        group.access_frequency = (group.request_count / total_requests)

        # Average frequency across all windows
        group.hotness = 0

        for window in window_requests:

            group_requests = group_stats["windows"].get(window, 0)

            frequency = (group_requests / window_requests[window])

            group.hotness += frequency * window_weight

        # Average GET latency
        group.average_latency = (group_stats["total_latency"] / group.request_count)

    return groups









def calc_75_percentile(groups):
    request_counts = []

    for group in groups:
        request_counts.append(group.request_count)

    request_counts.sort()

    index = int(len(request_counts) * 0.75) - 1

    return request_counts[index]