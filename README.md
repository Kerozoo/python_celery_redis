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

docker-compose logs app
app_1    | [2021-05-24 23:37:56,388: WARNING/ForkPoolWorker-8] x=1, 
y=2
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

# chain task

- exec tasks

```
>>> from task.tasks import add
>>> from celery import chain
>>>
>>> chain_task = chain(add.si(1,2), add.si(2,3), add.si(3,4))
>>> # 直列タスクの確認
>>> chain_task
task.tasks.add(1, 2) | add(2, 3) | add(3, 4)
>>> type(chain_task)
<class 'celery.canvas._chain'>
>>>
>>> # 直列タスクを実行、結果をtasksに格納
>>> tasks = chain_task.delay()
>>> 
>>> # tasksの結果をそれぞれ取得
>>> ## tasksには最後に実行したadd(3, 4)の結果が格納されているので、
>>> ## parentで親タスク結果を逆順で取得していく
>>> 
>>> ## 3番目に実行したタスク
>>> type(tasks)
<class 'celery.result.AsyncResult'>
>>> tasks.task_id
'cdeb09db-aeb6-49c1-aa98-bbcab61e40c8'
>>> tasks.result
7
>>> ## 2番目に実行したタスク
>>> type(tasks.parent)
<class 'celery.result.AsyncResult'>
>>> tasks.parent.task_id
'6b60b2d0-1663-46d2-be55-12815ec72a52'
>>> tasks.parent.result
5
>>> ## 1番目に実行したタスク
>>> type(tasks.parent.parent)
<class 'celery.result.AsyncResult'>
>>> tasks.parent.parent.task_id
'5e60984f-74ec-4287-8cc1-4c8fefaf5df2'
>>> tasks.parent.parent.result
3
```

- logs

```
docker-compose logs app

# 長くなるので、必要な箇所のみ抜粋
## 1番目に実行したタスク
[2021-05-25 23:34:13] x=1, y=2
[2021-05-25 23:34:13] [5e60984f-74ec-4287-8cc1-4c8fefaf5df2] succeeded in 3s: 3
## 2番目に実行したタスク(1番終了後に実行)
[2021-05-25 23:34:16] x=2, y=3
[2021-05-25 23:34:16] [6b60b2d0-1663-46d2-be55-12815ec72a52] succeeded in 3s: 5
## 3番目に実行したタスク(2番終了後に実行)
[2021-05-25 23:34:19] x=3, y=4
[2021-05-25 23:34:19] [cdeb09db-aeb6-49c1-aa98-bbcab61e40c8] succeeded in 3s: 7
```

# group task

- exec tasks

```
>>> from task.tasks import add
>>> from celery import chain
>>>
>>> group_task = group(add.si(1,2), add.si(2,3), add.si(3,4))
>>> # 並列タスクの確認
>>> group_task
group((task.tasks.add(1, 2), add(2, 3), add(3, 4)))
>>> type(group_task)
<class 'celery.canvas.group'>
>>> # 並列タスクを実行、結果をtasksに格納
>>> tasks = group_task.delay()
>>> 
>>> # tasksの結果をそれぞれ取得
>>> ## tasksにはAsyncResultを複数もつGroupResultが格納される
>>> 
>>> ## GroupResult
>>> type(tasks)
<class 'celery.result.GroupResult'>
>>> tasks
<GroupResult: 449b1269-3907-44bf-8eb6-9ef013775e0f
    [ce8e5c87-4fad-4dd7-83ff-1c881daab013,
     6339f8a0-15c9-408a-bc02-75a504d14c05,
     0d99f7b2-88a5-44e4-a44a-f02583c3cf73]>
>>> tasks.children
[<AsyncResult: ce8e5c87-4fad-4dd7-83ff-1c881daab013>,
 <AsyncResult: 6339f8a0-15c9-408a-bc02-75a504d14c05>,
 <AsyncResult: 0d99f7b2-88a5-44e4-a44a-f02583c3cf73>]
>>>
>>> ## [0]に格納されているAsyncResult
>>> type(tasks[0])
<class 'celery.result.AsyncResult'>
>>> tasks[0].task_id
'ce8e5c87-4fad-4dd7-83ff-1c881daab013'
>>> tasks[0].result
3
>>> ## [1]に格納されているAsyncResult
>>> type(tasks[1])
<class 'celery.result.AsyncResult'>
>>> tasks[1].task_id
'6339f8a0-15c9-408a-bc02-75a504d14c05'
>>> tasks[1].result
5
>>> ## [2]に格納されているAsyncResult
>>> type(tasks[2])
<class 'celery.result.AsyncResult'>
>>> tasks[2].task_id
'0d99f7b2-88a5-44e4-a44a-f02583c3cf73'
>>> tasks[2].result
7
```

- logs

```
docker-compose logs app

# 長くなるので、必要な箇所のみ抜粋
## 全て同時刻に並列で処理されていることを確認
[2021-05-27 00:29:20] x=2, y=3
[2021-05-27 00:29:20] x=1, y=2
[2021-05-27 00:29:20] x=3, y=4
[2021-05-27 00:29:20] [6339f8a0-15c9-408a-bc02-75a504d14c05] succeeded in 3s: 5
[2021-05-27 00:29:20] [ce8e5c87-4fad-4dd7-83ff-1c881daab013] succeeded in 3s: 3
[2021-05-27 00:29:20] [0d99f7b2-88a5-44e4-a44a-f02583c3cf73] succeeded in 3s: 7
```