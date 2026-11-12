"""
    Le but des simple calculer combient des requette GET chanque groupe recoit pour chaque time window
"""

import csv
import os

from workload.workload_utils import save_profile_results

def profile_workload(workload_file):

    window_groups = {}

    with open(workload_file, "r", encoding="utf-8", newline="") as f:

        reader = csv.DictReader(f)

        for row in reader:

            window = int(row["window_number"])
            group_id = row["group_id"]

            if window not in window_groups:
                window_groups[window] = {}

            if group_id not in window_groups[window]:
                window_groups[window][group_id] = 0

            window_groups[window][group_id] += 1

    return window_groups






if __name__ == "__main__":

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    WorkloadOutput_DIR = os.path.join(BASE_DIR, "workload","workloadOutput")
    workload_normal_file = os.path.join(WorkloadOutput_DIR, "moving_normalDist.csv")
    workload_skewed_file = os.path.join(WorkloadOutput_DIR, "moving_skewedDist.csv")



    normal_results_file = os.path.join(WorkloadOutput_DIR,"normal_profiling_results.txt")
    skewed_results_file = os.path.join(WorkloadOutput_DIR,"skewed_profiling_results.txt")


    normal_results = profile_workload(workload_normal_file)
    skewed_results = profile_workload(workload_skewed_file)


    save_profile_results(normal_results, normal_results_file)
    save_profile_results(skewed_results, skewed_results_file)