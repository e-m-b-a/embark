# System test - Sprint 11

The test was performed on commit c281678. The dev server was used, a fresh database, fresh generated migrations, fresh workers (on Ubuntu 24.04).

Below "**BAD**" implies that an improvement can be done, "**BUG**" implies that there is an actual bug.

## Test 1:

New configuration, 2 workers (first worker: user `root`, second worker: `demo_user1`). 3 firmware analysis, queued a priori

### Findings:

- **BAD**: Configuration scan: Status is very long in "Scanning" (e.g. 240 sec on my machine), even for small IP ranges (e.g. 192.168.56.120/28)
- **BUG**: Configuration scan: Workers are added, even if user/password is wrong. Results in failing update_sytem_info, installation, .... Similar problem if user exists, but has no sudo permissions
- **BUG**: workers.tasks.update_worker_info: "An error occurred while updating worker %s: %s", but the second placeholder is empty
- **BAD**: Error "Worker: %s could not be removed from orchestrator" is logged, even if it is expected (e.g. create workers using config scan, but don't install, just initiate a config deletion)
- **BUG**: If a configuration is deleted, a worker is not deleted if not added to the orchestrator a priori (Wrong exception handling). Even worse: As the worker has no remaining configuration, it is not visible in the UI, but still in the DB
- **BAD**: Necessary page reload if orchestrator/workers are enabled. Why not auto-reload the page?
- **BAD**: Celery logger has a level too low. Logs irrelevant info such as "Authenticated (password) successful", "Connected (version 2.0, client OpenSSH_9.6p1)",...
- **BAD** (?): Worker installation can be started even if config is not yet fully scanned

## Test 2:

New configuration, 2 workers (Either `root` user for both workers, or `demo_user1` for both workers). 3 firmware analysis, queued a priori

### Findings:

- **BAD** (?): Analysis ID column is just empty if no analysis is assigned
- **BAD**: Soft- / Hard Reset without confirmation popup. I could accidentally reset (a config of) workers
- **BAD** (Probably not AMOS related): In "Progress" -> "Follow Logs" has twice the button "Raw EMBA log file", but they do different things
- **BUG**: Firmware analysis stay in the "Progress" view, even if they are finished. Probably the scan is not marked as finished correctly.
- **BUG**: In "Reports", the Report download stays in status "Results are on their way". Probably the scan is not marked as finished correctly.

## Test 3:

New configuration, 1 worker (user `demo_user1`), 2 firmware analysis, Soft Reset the worker during the first analysis, Hard Reset during the second

### Findings:

- **BUG**: Hard Reset triggers Soft-/Hard Reset Task, however the order is random. Commands might fail if the Hard Reset is the first. Fix: Execute Soft Reset at the beginning of the Hard Reset, but not async
- **BUG**: hard reset does not remove worker from orchestrator, however, EMBA and all dependencies are removed
- **BUG**: hard reset does not set the worker status to `UNCONFIGURED`, while EMBA and dependencies are uninstalled
- **BUG** (?): If a worker is soft resetted while an analysis is running, the analysis is dropped (and not restarted)
- **BAD**: `init_sudoers_file` / `undo_sudoers_file` is executed if root user is used (only for other users needed)

