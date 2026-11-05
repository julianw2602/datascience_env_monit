# Cluster hello

Bootstraps a synthetic GPP series and prints a 95% interval.

## Run
python3 scripts/cluster_hello.py 200


**Content of .out file**
(scp the outfile from the server to the laptop has not worked yet)

Host: uc3n069.localdomain
Job ID: 8264118
Resamples: 5000
Mean daily GPP: 4.01 (95% CI 3.84 to 4.17)

============================= JOB FEEDBACK =============================

NodeName=uc3n069
Job ID: 8264118
Cluster: uc3
User/Group: fr_jw647/fr_fr
State: COMPLETED (exit code 0)
Nodes: 1
Cores per node: 2
CPU Utilized: 00:00:00
CPU Efficiency: 0.00% of 00:00:34 core-walltime
Job Wall-clock time: 00:00:17
Memory Utilized: 34.83 MB
Memory Efficiency: 0.87% of 3.91 GB (1.95 GB/core)


**STORAGE.md content**

# Storage and backup

## Where things live
- Code: GitHub (julianw2602/datascience_env_monit),
  my laptop, cluster HOME
- Results: cluster workspace `dsm`, path: "/pfs/work9/workspace/scratch/fr_jw647-dsm"


## Expiry
- Workspace `dsm` expires on: 02.01.2027
- I extend it on: 20.12.2026. Calendar reminder set: yes

## Backup
- Code: GitHub is the second copy
- Results I must keep: copied to my laptop on (hasn't worked yet)
- Raw data: original download source + university storage (no raw data doenloaded yet)

## Files
scripts/  the analysis code
jobs/     Slurm job scripts
docs/     notes and templates

## add line
line added 

the third commit message is best as it describes the exact process instead of vaguely hinting at the meaning/ just mashing buttons
## Author
Julian Wesche 03.11.2026
