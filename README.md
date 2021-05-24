# How to run

- exec task

```
docker-compose up
docker-compose exec app bash

root@95ef66cd9bdf:/code# python
>>> from task.tasks import add
>>> task = add.si(1, 2)
>>> result = task.delay()
>>> result.result
3
>>> result
<AsyncResult: cf4cadbd-7ceb-4045-be10-ae67565b265b>565b265b>
```

- check result

```
docker-compose exec redis bash

root@fb3fcfaf3468:/data# redis-cli
127.0.0.1:6379> select 0
OK
127.0.0.1:6379> keys *
1) "celery-task-meta-cf4cadbd-7ceb-4045-be10-ae67565b265b"
2) "_kombu.binding.celeryev"
3) "_kombu.binding.celery.pidbox"
4) "_kombu.binding.celery"
127.0.0.1:6379> get celery-task-meta-cf4cadbd-7ceb-4045-be10-ae67565b265b
"{\"status\": \"SUCCESS\", \"result\": \"3\", \"traceback\": null, \"children\": [], \"date_done\": \"2021-05-22T04:07:53.321601\", \"task_id\": \"cf4cadbd-7ceb-4045-be10-ae67565b265b\"}"
```