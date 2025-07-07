# Changelog

## UNRELEASED

### FIXED

- Missing WorkerDependencyVersion deletion on config delete

### ADDED

- Worker health check and fetch analysis logs ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=112364687&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C46))
- Trigger orchestrator at critical moments ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=114047181&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C59)) 
- Use celery for IP range scanning and update config UI ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=118038092&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C91))
- `process_update_queue` call once the analysis is finished ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=114650622&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C70))
- Add wiki entries for API ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=114744149&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C71))

## [sprint-11](https://github.com/amosproj/amos2025ss01-embark/releases/tag/sprint-11-release) - 2025-07-02

### FIXED

- Missing sudo at worker soft reset ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=112364355&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C43))
- User permission checks for different resources ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=118050504&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C93))

### ADDED

- Safe and prioritized worker update management ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=114650622&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C70))
- Distributed lock to orchestrator to ensure synchronization across multiple instances ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=116668070&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C89))
- Show workers app only when enabled ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=113440769&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C52))
- Download specific worker nodes dependency version ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=116857375&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C90))

## [sprint-10](https://github.com/amosproj/amos2025ss01-embark/releases/tag/sprint-10-release) - 2025-06-25

### FIXED

- Fix a bug related to incorrect start of celery ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=115359765&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C79))
- Fix a bug related to collecting worker dependency information
- Fix a bug related to collecting worker external repo and emba version information
- Fix a bug related to updating APT dependencies ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=114467717&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C61))

### ADDED

- Collect dependency version info for workers ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=114773112&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C73))
- Settings App to EMBArk ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=114643627&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C66))
- Settings helper `workers_enabled` check
- Available Update check ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=114467717&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C61))
- Celery for reset ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=115510818&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C81))
- Add configuration user to sudoers file ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=115519308&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C82))

### CHANGED

- Use settings worker path variables

## [sprint-09](https://github.com/amosproj/amos2025ss01-embark/releases/tag/sprint-09-release) - 2025-06-18

### ADDED

- Add configured workers to orchestrator ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=114649534&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C69))
- Firmware analysis start on worker node ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=113296109&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C51))
- Celery task for worker update ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=114647889&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C68))

### FIXED

- Various workflow errors ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=115336615&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C75))

## [sprint-08](https://github.com/amosproj/amos2025ss01-embark/releases/tag/sprint-08-release) - 2025-06-11

### ADDED

- Update/Reset buttons for configurations ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=112359403&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C42))
- Additional worker information query ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=111222216&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C40))
- Worker soft reset functionality ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=112364355&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C43))
- Worker update functionality ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=112364538&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C45))
- Celery setup ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=113497561&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C55))
- Periodic worker information updates ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=112364821&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C47))
- Worker hard reset functionality ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=112364415&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C44))

### FIXED

- workflow caching (docker reference not found) ([Issue](https://github.com/orgs/amosproj/projects/79?pane=issue&itemId=110335090&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C33))

## [sprint-07](https://github.com/amosproj/amos2025ss01-embark/releases/tag/sprint-07-release) - 2025-06-04

### ADDED

- Github workflow caching ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=110335090&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C33))
- Update/Reset buttons for workers ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=112359403&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C42))
- FIFO scheduling for orchestrator ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=111220090&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C37))
- Worker pool information functions ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=111221169&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C38))
- Job id to worker nodes table ([Issue](https://github.com/orgs/amosproj/projects/79/views/2?pane=issue&itemId=111221228&issue=amosproj%7Camos2025ss01-embark-orchestration-framework%7C39))

---
Older sprints have not been tracked.
