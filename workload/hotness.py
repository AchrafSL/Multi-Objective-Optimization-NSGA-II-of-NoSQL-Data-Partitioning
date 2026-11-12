"""
    finds the hotest group in each time window
"""

import os

from workload.workload_profiler import profile_workload
from workload.workload_utils import save_hotspots


def detect_hotspots(profile_results):

    hotspots = {}

    for window in profile_results:

        groups = profile_results[window]

        hottest_group = None
        highest_requests = 0

        for group_id in groups:

            request_count = groups[group_id]

            if request_count > highest_requests:
                highest_requests = request_count
                hottest_group = group_id

        hotspots[window] = {"group_id": hottest_group, "request_count": highest_requests}

    return hotspots








if __name__ == "__main__":

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    WorkloadOutput_DIR = os.path.join(BASE_DIR, "workload", "workloadOutput")

    # Dist Input files
    normal_workload_file = os.path.join(WorkloadOutput_DIR, "moving_normalDist.csv")
    skewed_workload_file = os.path.join(WorkloadOutput_DIR, "moving_skewedDist.csv")


    # HotSpot Output files
    normal_hotspots_file = os.path.join(WorkloadOutput_DIR, "normal_hotspots.txt")
    skewed_hotspots_file = os.path.join(WorkloadOutput_DIR, "skewed_hotspots.txt")


    # profiling again and not loading the results because it's faster this way
    normal_results = profile_workload(normal_workload_file)
    skewed_results = profile_workload(skewed_workload_file)


    # Detect the hotsplot in each group
    normal_hotspots = detect_hotspots(normal_results)
    skewed_hotspots = detect_hotspots(skewed_results)

    # Export the results
    save_hotspots(normal_hotspots, normal_hotspots_file)
    save_hotspots(skewed_hotspots, skewed_hotspots_file)