# Celery

We use celery to process asynchronous tasks. Once the webserver is started (either in `dev` or `deploy` environment), a celery worker is started. This worker waits for new tasks to process using Redis.

To create new tasks, once should create a `tasks.py` file in the desired module (e.g. `embark/workers/tasks.py`).

Example task:

```python
from celery import shared_task

@shared_task
def foo(bar):
   # Do some fancy operation
   return 0
```

The task can then by started by first importing the module and then starting the task:

```python
from .tasks import foo
# ...
foo.delay()
```
**Note**: You have to call `delay`, otherwise the function is not executed by the worker, but locally instead.

## Logs

The logs can be found in `./logs/celery.log`.

## Development with Celery

Celery workers have to be restarted to detect code changes (e.g. registration of new tasks). To ease development, one should use a naive python thread and change to a celery task afterwards:

```python
import threading
# ...
threading.Thread(target=foo, args=(bar,)).start()
```

If it is desired to restart a celery worker, see `./dev-tools/debug-server-start.sh` how to do this (search for `Celery`).

