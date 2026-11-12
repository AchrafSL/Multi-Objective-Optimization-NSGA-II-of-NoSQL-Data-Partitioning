# Multi-Objective Optimization (NSGA-II) for NoSQL Data Partitioning in Apache HBase

> 📄 **Academic Report:** [Rapport_techno_de_stockage_finale.docx](./Rapport_techno_de_stockage_finale.docx)

[![Academic Project](https://img.shields.io/badge/Project-Master%20Big%20Data-blue.svg)](https://uit.ac.ma)
[![Database](https://img.shields.io/badge/NoSQL-Apache%20HBase%20%7C%20Hadoop-orange.svg)](https://hbase.apache.org/)
[![Optimization](https://img.shields.io/badge/Algorithm-NSGA--II%20%7C%20Pareto-green.svg)](https://en.wikipedia.org/wiki/Non-dominated_sorting_in_genetic_algorithms)
[![Python](https://img.shields.io/badge/Python-3.x-yellow.svg)](https://www.python.org/)

---

## 📌 Project Overview

This repository contains the full implementation and experimental evaluation of an **adaptive, workload-driven, multi-objective data partitioning framework** for distributed NoSQL databases (**Apache HBase** on **Hadoop/HDFS**). 

In modern distributed storage systems, data is divided into partitions (e.g., HBase Regions) spread across cluster nodes (RegionServers). Traditional partitioning and auto-balancing mechanisms typically distribute partitions uniformly or reactively based on coarse storage metrics. However, **a uniform partition count does not imply a balanced workload**. Dynamic access patterns, hot-spots, and non-uniform query frequencies create severe load imbalances where certain nodes process up to 60% of all queries while others remain idle, despite each hosting an identical number of regions.

To address this challenge, this project integrates:
1. **Fine-grained Workload Profiling**: Tracking query request frequencies, temporal sliding-window hotness, and real HBase read latencies.
2. **Heuristic Seed Strategies**: Three baseline strategies (*Cost-Efficient*, *Balanced*, *Performance*) designed to explore specific operational priorities.
3. **Multi-Objective Evolutionary Optimization (NSGA-II)**: Searching the non-dominated Pareto frontier to find optimal trade-offs between **Migration Cost** (minimizing network and I/O transfer) and **Workload Imbalance** (minimizing server load variation).
4. **Physical HBase Execution & Verification**: A complete physical orchestration engine that materializes logical data groups into concrete HBase Regions and executes non-disruptive region moves directly on a live HBase cluster.

---

## 🎓 Academic Context

- **Institution**: Université Ibn Tofaïl (Kenitra, Morocco)
- **Faculty**: Faculté des Sciences de Kénitra
- **Master Program**: Master Big Data, Intelligence Artificielle et Applications Avancées (BD&IA)
- **Academic Year**: 2025 / 2026
- **Authors**:
  - **Achraf SALIMI**
  - **Hamza EL KABRAOUI**
- **Supervisor**: **Pr. Ayoub SGHIR**

---

## 🏛️ System Architecture & Workflow

The end-to-end framework bridges high-level genetic optimization with low-level distributed storage execution:

```
+-----------------------------------------------------------------------------------+
|                              1. Data Ingestion & Storage                         |
|  Transactional E-Commerce Dataset (customer, product, transactions, click_stream) |
|           Ingested into Apache HBase via HappyBase / Thrift Batch Inserter        |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                              2. DataGroup Modeling                                |
|    90 Logical DataGroups created across 4 tables with deterministic key boundaries|
|    Mapped 1-to-1 to 90 Physical HBase Application Regions across 3 RegionServers  |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                        3. Workload Generation & Profiling                         |
|   1,000,000 requests evaluated over 1,000 temporal sliding windows (Normal & Skewed) |
|   Real GET query latencies and hotness metrics measured on live HBase cluster     |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                      4. Heuristic Seed Strategies Generation                       |
|   • Cost-Efficient: Minimizes data migration size for overloaded servers          |
|   • Balanced: Iteratively reduces server load variance                            |
|   • Performance: Prioritizes groups with high hotness & high query latency        |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                      5. Multi-Objective Optimization (NSGA-II)                    |
|   • Minimizes Migration Cost (bytes moved) & Workload Imbalance (StdDev / Mean)   |
|   • Non-dominated Sorting, Crowding Distance, Crossover, and Target Server Mutation|
|   • Pareto Front generation & Multi-Criteria Decision Making (MCDM Normalization)  |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                       6. Physical Cluster Migration & Validation                  |
|   • Disables internal HBase automatic load balancer                               |
|   • Discovers physical Region IDs and live RegionServer ServerNames               |
|   • Dispatches physical 'move' commands via HBase Shell                           |
|   • Polls and verifies real Region placement and cluster post-migration state     |
+-----------------------------------------------------------------------------------+
```

---

## 📊 Dataset & Ingestion

The experiments are conducted on the **[Transactional E-Commerce Dataset (Kaggle)](https://www.kaggle.com/datasets/bytadit/transactional-ecommerce)**, consisting of four core tables:

| Table | Logical Rows Loaded | RowKey | Key Range Subdivision | Column Family |
| :--- | :--- | :--- | :--- | :--- |
| **`customer`** | 100,000 | `customer_id` | 10 DataGroups (`customer_G1` .. `G10`) | `info` |
| **`product`** | 44,446 | `id` | 10 DataGroups (`product_G1` .. `G10`) | `info` |
| **`transactions`** | 852,584 | `booking_id` | 30 DataGroups (`transactions_G1` .. `G30`) | `info` |
| **`click_stream`** | 3,966,210 | `event_id` | 40 DataGroups (`click_stream_G1` .. `G40`) | `info` |
| **Total** | **4,963,240** | — | **90 DataGroups / 90 Regions** | — |

### 📥 Dataset Download & Setup
1. Download the raw CSV dataset from Kaggle:  
   👉 **[bytadit/transactional-ecommerce on Kaggle](https://www.kaggle.com/datasets/bytadit/transactional-ecommerce)**
2. Unpack the files and place the four CSV files into the `dataset/` folder:
   ```plaintext
   dataset/
   ├── click_stream.csv
   ├── customer.csv
   ├── product.csv
   └── transactions.csv
   ```
> [!NOTE]  
> The `dataset/*.csv` files total ~2 GB and are excluded from Git via `.gitignore`. You must download them from Kaggle before running data loading scripts.

- **Storage Footprint**: The raw CSV files represent ~1.86 GB. When loaded into HBase, logical data occupies ~2.6 GB. With an HDFS replication factor of 3 ($3\times$), the physical cluster storage occupied is **~7.7 GB**.
- **Batch Ingestion Benchmark**: An initial test using Hadoop MapReduce `ImportTsv` required **1 hour 22 minutes** to load only the 44k product records due to task timeouts. The custom Python + HappyBase batch ingester (`batch_size=1000`) executed via the HBase Thrift Gateway proved dramatically faster, reliable, and resource-efficient.

---

## ⚙️ Mathematical Modeling & Formulation

### 1. DataGroup Hotness
For each DataGroup $g$ over $N = 1000$ temporal sliding windows:
$$\text{Hotness}(g) = \frac{1}{N} \sum_{i=1}^{N} \text{Frequency}_i(g)$$
where $\text{Frequency}_i(g)$ denotes the proportion of queries received by group $g$ in window $i$.

### 2. Performance Heuristic Score
For active groups whose hotness and average latency exceed the 75th percentile:
$$\text{Score}(g) = 0.5 \times \frac{\text{Latency}(g)}{\text{Latency}_{\max}} + 0.5 \times \frac{\text{Hotness}(g)}{\text{Hotness}_{\max}}$$

### 3. Multi-Objective Formulation (NSGA-II)
Each individual (chromosome) encodes a set of migrations $C = \{(g, S_{\text{target}})\}$. Two conflicting objective functions are minimized:

1. **Objective 1 — Migration Cost ($f_1$)**:
   The total data volume transferred across the network:
   $$f_1(C) = \sum_{(g, S_{\text{target}}) \in C, \, S_{\text{target}} \neq S_{\text{current}}} \text{Size}(g)$$

2. **Objective 2 — Workload Imbalance ($f_2$)**:
   The Coefficient of Variation ($CV$) of the request workloads across RegionServers:
   $$f_2(C) = \frac{\sigma(L)}{\mu(L)} = \frac{\sqrt{\frac{1}{M}\sum_{j=1}^{M}(L_j - \bar{L})^2}}{\bar{L}}$$
   where $M = 3$ (slave1, slave2, slave3) and $L_j$ is the total query requests served by server $j$ after applying migration plan $C$.

### 4. Multi-Criteria Decision Making (MCDM)
To select the best trade-off from the non-dominated Pareto front, Min-Max normalization is applied with balanced 50/50 weighting:
$$\text{Score}(sol) = 0.5 \times \frac{f_1 - \min(f_1)}{\max(f_1) - \min(f_1)} + 0.5 \times \frac{f_2 - \min(f_2)}{\max(f_2) - \min(f_2)}$$
The Pareto solution with the minimum composite score is designated as the target migration plan.

---

## 🧪 Experimental Infrastructure

The testbed consists of a fully distributed Hadoop/HBase cluster deployed across virtualized Linux nodes:
- **`master`**: Hadoop NameNode, YARN ResourceManager, Apache ZooKeeper, HBase HMaster.
- **`slave1`**: HDFS DataNode, YARN NodeManager, HBase RegionServer.
- **`slave2`**: HDFS DataNode, YARN NodeManager, HBase RegionServer.
- **`slave3`**: HDFS DataNode, YARN NodeManager, HBase RegionServer.
- **Storage**: ~30 GB allocated per virtual machine; HDFS replication = 3.
- **Coordination**: ZooKeeper on `master` coordinating HBase cluster quorum.
- **Thrift Gateway**: HBase Thrift Server on `master:9090` bridging Python and HBase.

---

## 📈 Experimental Results & Discussion

### 1. Initial State: The Illusion of Equal Partitioning
Initially, the 90 application regions are distributed strictly equally (30 regions per node). Despite this numerical balance, request distribution is heavily skewed:

```
Initial Region Count:   slave1: 30 (33.3%) | slave2: 30 (33.3%) | slave3: 30 (33.3%)
Normal Workload Load:   slave1:  9.97%     | slave2: 30.01%     | slave3: 60.02%  (Hotspot!)
Skewed Workload Load:   slave1: 10.01%     | slave2: 30.01%     | slave3: 59.98%  (Hotspot!)
```

`slave3` received **60% of all queries**, demonstrating that conventional partition-count balancing fails to prevent severe cluster degradation.

### 2. Optimization Summary

NSGA-II was executed with a population size of 10 over 10 generations ($p_m = 0.1$):

| Workload Type | Migrations Selected | Estimated Cost (bytes) | Workload Imbalance ($CV$) | Physical Execution Time |
| :--- | :---: | :---: | :---: | :---: |
| **Normal Workload** | **6** | **56,410,176** (~56.4 MB) | **0.1284** | 568.6 seconds |
| **Skewed Workload** | **6** | **66,598,404** (~66.6 MB) | **0.0851** | ~600 seconds |

### 3. Detailed Before vs. After Comparison

#### A. Normal Workload
- **Migrated Regions (6)**: `transactions_G6`, `customer_G7`, `transactions_G7`, `transactions_G9`, `transactions_G8`, `customer_G10` (all from `slave3` $\to$ `slave1`).
- **Cumulative Physical Region Size**: ~212 MB.

| RegionServer | Regions Before | Regions After | Requests Before | Requests After | Workload Change (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`slave1`** | 30 | 36 | 99,719 | 306,132 | **+207.0%** |
| **`slave2`** | 30 | 30 | 300,121 | 300,121 | **0.0%** (unchanged) |
| **`slave3`** | 30 | 24 | 600,160 | 393,747 | **-34.4%** (alleviated) |
| **Total** | **90** | **90** | **1,000,000** | **1,000,000** | **Conservation verified** |

#### B. Skewed Workload
- **Migrated Regions (6)**: `transactions_G2`, `transactions_G3`, `transactions_G4`, `transactions_G7`, `transactions_G8`, `customer_G2` (all from `slave3` $\to$ `slave1`).

| RegionServer | Regions Before | Regions After | Requests Before | Requests After | Workload Change (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`slave1`** | 30 | 36 | 100,096 | 330,531 | **+230.2%** |
| **`slave2`** | 30 | 30 | 300,090 | 300,090 | **0.0%** (unchanged) |
| **`slave3`** | 30 | 24 | 599,814 | 369,379 | **-38.4%** (alleviated) |
| **Total** | **90** | **90** | **1,000,000** | **1,000,000** | **Conservation verified** |

### 4. Key Takeaways
- **Hotspot Alleviation**: Overloaded server `slave3` experienced a **34.4% to 38.4% reduction** in query pressure.
- **Preservation of Stable Nodes**: Server `slave2` was already operating near the ideal mean load ($\approx 333,333$ requests); the algorithm intelligently left its regions untouched, avoiding unnecessary churn.
- **Physical Feasibility**: All 6 moves in each workload were physically executed on live RegionServers without data loss or cluster downtime.

---

## 🔬 Comparison with Related Work

| Project / Research Work | Year | NoSQL / HBase | NSGA-II / Multi-Obj | Migration Cost Model | Live Move Decision | Adaptive Workload |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **This Project (NSGA-II NoSQL Partitioning)** | **2026** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |
| *MigCast in Monte Carlo* | 2021 | Yes | No | Yes | No | Yes |
| *To Migrate or not to Migrate* | 2022 | No | No | Yes | Yes | Yes |
| *Multi-objective Graph Partitioning (NSGA-II)* | 2024 | No | Yes | No | No | No |
| *Survey of Data Partitioning (AQWA, Cumulus, ML SWORD)* | 2024 | Yes | No | Yes | No | Yes |

---

## 📂 Repository Structure

```plaintext
.
├── dataset/                                # Raw E-Commerce CSV dataset
│   ├── click_stream.csv                    # User event activity logs
│   ├── customer.csv                        # Customer demographics & metadata
│   ├── product.csv                         # Product catalogue & categories
│   └── transactions.csv                    # Payment & booking transactions
│
├── hbase/                                  # HBase client & ingestion utilities
│   ├── hbase_utils.py                      # Connection helpers & region metadata extractors
│   ├── load_hbase.py                       # HappyBase batch loader (1000 records/batch)
│   └── reader.py                           # High-performance Thrift reader with persistent socket
│
├── model/                                  # DataGroup logical modeling
│   ├── create_groups.py                    # Splits tables into DataGroup boundaries
│   ├── groups_util.py                      # DataGroup dataclass & helper routines
│   └── groups/                             # Saved group boundary definitions (.txt)
│       ├── click_stream_groups.txt         # 40 groups (click_stream_G1 .. G40)
│       ├── customer_groups.txt             # 10 groups (customer_G1 .. G10)
│       ├── product_groups.txt              # 10 groups (product_G1 .. G10)
│       └── transactions_groups.txt         # 30 groups (transactions_G1 .. G30)
│
├── workload/                               # Workload generation, execution & profiling
│   ├── generate_workload.py                # Generates synthetic 1M query requests
│   ├── executor.py                         # Dispatches live GET queries to HBase & records latency
│   ├── workload_profiler.py                # Computes temporal window request distributions
│   ├── hotness.py                          # Identifies moving hotspots per time window
│   ├── workload_utils.py                   # Probabilistic distributions & statistical helpers
│   └── workloadOutput/                     # Workload files, traces, and execution logs
│       ├── moving_normalDist.csv           # 1M queries (Normal distribution)
│       ├── moving_skewedDist.csv           # 1M queries (Skewed dynamic hotspot)
│       ├── normal_execution.csv            # Real measured HBase execution latencies (Normal)
│       ├── skewed_execution.csv            # Real measured HBase execution latencies (Skewed)
│       ├── normal_profiling_results.txt    # Window-by-window request frequency
│       ├── skewed_profiling_results.txt    # Window-by-window request frequency
│       ├── normal_hotspots.txt             # Hotspot identification trace
│       └── skewed_hotspots.txt             # Hotspot identification trace
│
├── strategies/                             # Heuristic seed strategies
│   ├── cost_efficient.py                   # Low migration cost heuristic
│   ├── balanced.py                         # Load balancing heuristic
│   ├── performance.py                      # Hotness & latency-driven heuristic
│   └── strategy_utils.py                   # Percentile calculations & group stat updaters
│
├── nsga2/                                  # Evolutionary Multi-Objective Optimization
│   ├── representation.py                   # Chromosome encoding & decoding (group_id -> target)
│   ├── population.py                       # Initial population generator seeded by strategies
│   ├── evaluation.py                       # Objective functions (Migration Cost & Imbalance)
│   ├── genetic.py                          # Crossover & server reassignment mutation operators
│   ├── nsga.py                             # Non-dominated sorting & Crowding Distance
│   ├── nsga2.py                            # Main NSGA-II generational execution loop
│   └── decision.py                         # MCDM Min-Max normalization & 50/50 compromise selector
│
├── migration/                              # Physical HBase migration orchestrator
│   ├── final_migrator.py                   # Automated physical region mover & verifier
│   ├── physical_migration_spliter.py       # Materializes DataGroup boundaries into HBase Regions
│   ├── fix_initial_distribution.py         # Restores initial 30/30/30 physical balance
│   ├── reset_experiments.py                # Experiment reset utility
│   ├── save_plan.py                        # Exports selected plans to JSON
│   └── plans/                              # Generated migration plans
│       ├── normal_migration_plan.json      # Final plan for Normal workload
│       └── skewed_migration_plan.json      # Final plan for Skewed workload
│
├── main.py                                 # Main optimization entry point
└── README.md                               # Project documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python**: 3.8+
- **Apache Hadoop & HDFS**: Distributed cluster running with HDFS replication factor $\ge 1$.
- **Apache HBase & ZooKeeper**: HBase cluster active with Thrift Server running on `master:9090`.
- **Python Dependencies**:
  ```bash
  pip install happybase numpy
  ```

### 2. Download Dataset
Download the [Transactional E-Commerce Dataset from Kaggle](https://www.kaggle.com/datasets/bytadit/transactional-ecommerce) and place the four CSV files into the `dataset/` directory:
- `dataset/customer.csv`
- `dataset/product.csv`
- `dataset/transactions.csv`
- `dataset/click_stream.csv`

### 3. Data Ingestion into HBase
Ensure the HBase Thrift daemon is running on the master node:
```bash
hbase thrift start -p 9090
```
Then load each table into HBase using the batch loader:
```bash
python -m hbase.load_hbase dataset/customer.csv customer customer_id
python -m hbase.load_hbase dataset/product.csv product id
python -m hbase.load_hbase dataset/transactions.csv transactions booking_id
python -m hbase.load_hbase dataset/click_stream.csv click_stream event_id
```

### 4. Generate & Profile Workloads
Generate synthetic workload traces with normal and skewed hotspot shifts:
```bash
python -m workload.generate_workload
```
Execute workloads against HBase to record latencies:
```bash
python -m workload.executor
```
Profile request distributions and detect temporal hotspots:
```bash
python -m workload.workload_profiler
python -m workload.hotness
```

### 5. Run Multi-Objective Optimization (NSGA-II)
Run the full optimization pipeline across both Normal and Skewed execution profiles:
```bash
python main.py
```
This will:
1. Load execution logs and update DataGroup request/latency statistics.
2. Generate heuristic plans (*Cost-Efficient*, *Balanced*, *Performance*).
3. Evolve the population using NSGA-II to find the Pareto frontier.
4. Select the optimal trade-off plan via MCDM.
5. Export `normal_migration_plan.json` and `skewed_migration_plan.json`.

### 6. Execute Physical HBase Migration
Apply the generated migration plan directly on the live HBase cluster:
```bash
python -m migration.final_migrator migration/plans/normal_migration_plan.json
# Or for skewed workload:
python -m migration.final_migrator migration/plans/skewed_migration_plan.json
```
The script will disable the HBase balancer, look up region encoded IDs, move each region to its target RegionServer, and poll HBase until the relocation is physically verified.

### 7. Reset Cluster for New Runs
To reset the cluster back to the initial 30/30/30 physical region distribution:
```bash
python -m migration.reset_experiments
```

---


## 📚 References

1. **MigCast in Monte Carlo**: *« MigCast in Monte Carlo: The Impact of Data Model Evolution in NoSQL Databases »*, arXiv:2104.11787, 2021.
2. **Operator Migration**: *« To Migrate or not to Migrate: An Analysis of Operator Migration in Distributed Stream Processing »*, arXiv:2203.03501, 2022.
3. **Graph Partitioning with NSGA-II**: *« A multi-objective partitioning algorithm for large-scale graph based on NSGA-II »*, Expert Systems with Applications, DOI: 10.1016/j.eswa.2024.125756, 2024.
4. **Data Partitioning Survey**: *« A Survey of Data Partitioning Techniques »*, Journal of Computer Science and Technology (JCST), 2024.
5. **Apache HBase Reference Guide**: RegionServer Load Balancer & Architecture documentation, [hbase.apache.org](https://hbase.apache.org/book.html).
6. **Bigtable**: F. Chang et al., *« Bigtable: A Distributed Storage System for Structured Data »*, USENIX OSDI, 2006.
7. **HDFS**: K. Shvachko et al., *« The Hadoop Distributed File System »*, IEEE MSST, 2010.
8. **ZooKeeper**: P. Hunt et al., *« ZooKeeper: Wait-free Coordination for Internet-scale Systems »*, USENIX ATC, 2010.
9. **NSGA-II**: K. Deb, A. Pratap, S. Agarwal, T. Meyarivan, *« A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II »*, IEEE Transactions on Evolutionary Computation, vol. 6, no. 2, pp. 182–197, 2002.
10. **Workload-Driven Partitioning**: C. Curino et al., *« Schism: A Workload-Driven Approach to Database Replication and Partitioning »*, PVLDB, 2010.
