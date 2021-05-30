# How to run

- Exec task

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
[2021-05-24 23:37:56] x=1, y=2
```

- Check result

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

# Chain task

## How to use

- Exec tasks

```
>>> from task.tasks import add
>>> from celery import chain
>>>
>>> # 直列タスクの登録(si -> sにすると、直前のタスク結果がxに引数として入るようにできる)
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

- Logs

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

## Revoke chain task

- Exec task

```
>>> from task.tasks import add
>>> from celery import chain
>>> from celery.result import AsyncResult
>>>
>>> # 直列で(1,2) -> (2,3) -> (3,4) の順番で実行される
>>> revoke_task = chain(add.si(1,2), add.si(2,3), add.si(3,4))
>>>
>>> ########### キュー取り消し ###########
>>> # タスクがキューに入れられ、tasksに(3,4)のAsyncResultが格納される
>>> tasks = revoke_task.delay()
>>>
>>> # tasksのtask_idを確認(.parentで直前のタスクのAsyncResult取得)
>>> tasks.id #(3,4)
'3f70b94e-e5af-4e89-a0ce-2f6e1354da14'
>>> tasks.parent.id #(2,3)
'5af91f4c-be8b-4e3e-9e36-d4260d422d4d'
>>> tasks.parent.id #(1,2)
'24d48dc9-f256-4f9d-bafe-3b05c1412a8d'
>>> 
>>> # (3,4)のキューを取り消し、実行中であれば何もしない
>>> AsyncResult(tasks.id).revoke()
>>> tasks.result
TaskRevokedError('revoked')
>>> tasks.status
'REVOKED'
>>> 
>>> ########### 強制停止 ###########
>>> # タスクがキューに入れられ、tasksに(3,4)のAsyncResultが格納される
>>> tasks = revoke_task.delay()
>>>
>>> # tasksのtask_idを確認(.parentで直前のタスクのAsyncResult取得)
>>> tasks.id #(3,4)
'a0db4db2-4045-43ae-9fb0-67403a899302'
>>> tasks.parent.id #(2,3)
'46f8f732-7632-4390-a780-623c1df70783'
>>> tasks.parent.id #(1,2)
'b94df9bd-3665-4a46-bd0c-91e8e39f4399'
>>>
>>> # (2,3)のキューを取り消し、実行中であれば強制停止
>>> AsyncResult(tasks.parent.id).revoke(terminate=True)
>>> tasks.parent.result
TaskRevokedError('terminated')
>>> tasks.parent.status
'REVOKED'
```

- Logs

```
docker-compose logs app

# 必要な箇所のみ抜粋
########### キュー取り消し ###########
[2021-05-30 04:51:10] Received task: [24d48dc9-f256-4f9d-bafe-3b05c1412a8d]
[2021-05-30 04:51:12] Tasks flagged as revoked: 3f70b94e-e5af-4e89-a0ce-2f6e1354da14
[2021-05-30 04:51:13] x=1, y=2
[2021-05-30 04:51:13] Task [24d48dc9-f256-4f9d-bafe-3b05c1412a8d] succeeded in 3s: 3  
[2021-05-30 04:51:13] Received task: [5af91f4c-be8b-4e3e-9e36-d4260d422d4d]
[2021-05-30 04:51:16] x=2, y=3      
[2021-05-30 04:51:16] Task [5af91f4c-be8b-4e3e-9e36-d4260d422d4d] succeeded in 3s: 5   
[2021-05-30 04:51:16] Received task: [3f70b94e-e5af-4e89-a0ce-2f6e1354da14]
[2021-05-30 04:51:16] Discarding revoked task: [3f70b94e-e5af-4e89-a0ce-2f6e1354da14]

########### 強制停止 ###########
[2021-05-30 04:46:57] Received task: [b94df9bd-3665-4a46-bd0c-91e8e39f4399]
[2021-05-30 04:47:00] x=1, y=2
[2021-05-30 04:47:00] Received task: [46f8f732-7632-4390-a780-623c1df70783]
[2021-05-30 04:47:00] Task [b94df9bd-3665-4a46-bd0c-91e8e39f4399] succeeded in 3s: 3   
[2021-05-30 04:47:01] Tasks flagged as revoked: a0db4db2-4045-43ae-9fb0-67403a899302
[2021-05-30 04:47:02] Terminating 46f8f732-7632-4390-a780-623c1df70783 (Signals.SIGTERM)
[2021-05-30 04:47:02] Task handler raised error: Terminated(15)
Traceback (most recent call last):
  File "/usr/local/lib/python3.9/site-packages/billiard/pool.py", line 1774, in _set_terminated
    raise Terminated(-(signum or 0))
billiard.exceptions.Terminated: 15
```

# Group task

## How to use

- Exec tasks

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

- Logs

```
docker-compose logs app

# 必要な箇所のみ抜粋
## 全て同時刻に並列で処理されていることを確認
[2021-05-27 00:29:20] x=2, y=3
[2021-05-27 00:29:20] x=1, y=2
[2021-05-27 00:29:20] x=3, y=4
[2021-05-27 00:29:20] [6339f8a0-15c9-408a-bc02-75a504d14c05] succeeded in 3s: 5
[2021-05-27 00:29:20] [ce8e5c87-4fad-4dd7-83ff-1c881daab013] succeeded in 3s: 3
[2021-05-27 00:29:20] [0d99f7b2-88a5-44e4-a44a-f02583c3cf73] succeeded in 3s: 7
```

## Revoke group task

- Exec task

```
>>> from task.tasks import add
>>> from celery import chain, group
>>> from celery.result import AsyncResult, GroupResult
>>>
>>> # group((1,2), (2,3)) -> group((3,4), (4,5)) の順番で実行される
>>> revoke_task = chain(
...     group(add.si(1,2), add.si(2,3)),
...     group(add.si(3,4), add.si(4,5)))  
>>>
>>>
>>> ########### キュー取り消し ###########
>>> # タスクがキューに入れられ、tasksにgroup((3,4), (4,5))のGroupResultが格納 
される
>>> tasks = revoke_task.delay()
>>>
>>> # tasksのtask_idを確認(.parentで直前のタスクのGroupResult取得)
>>> tasks.id #group((3,4), (4,5))
'c4423b7a-75fd-4255-babe-6c00e8ae5063'
>>> tasks.children #(3,4), (4,5)のタスクID
[<AsyncResult: 9308f99d-4a08-476d-a378-6ff8209fbb9d>,
 <AsyncResult: 51ca5d8e-3690-4724-8276-862848e86d2a>]
>>> tasks.parent.id #group((1,2), (2,3))
'2e8a804a-890a-4c65-89ed-9657a82adc14'
>>> tasks.parent.children #(1,2), (2,3)のタスクID
[<AsyncResult: de643078-711b-49b6-8cf1-fb4d1d005279>,
 <AsyncResult: 9e77f6cb-344f-4ebf-bf45-1ed33b68ee43>]
>>>
>>> # group((3,4), (4,5))のキューを取り消し、実行中であれば何もしない
>>> GroupResult(tasks.id, tasks.children).revoke()
>>> tasks.results
[<AsyncResult: 9308f99d-4a08-476d-a378-6ff8209fbb9d>,
 <AsyncResult: 51ca5d8e-3690-4724-8276-862848e86d2a>]
>>> tasks.children[0].result
TaskRevokedError('revoked')
>>> tasks.children[0].status
'REVOKED'
>>> tasks.children[1].result
TaskRevokedError('revoked')
>>> tasks.children[1].status
'REVOKED'
>>> 
>>> 
########### 強制停止 ###########
# タスクがキューに入れられ、tasksにgroup((3,4), (4,5))のGroupResultが格納される
>>> tasks = revoke_task.delay()
arentで直前のタスクのGroupResult取得)
tasks.id #group((3,4),>>>
>>> # tasksのtask_idを確認(.parentで直前のタスクのGroupResult取得)
>>> tasks.id #group((3,4), (4,5))
'3201c780-26c0-4ea9-afea-d7226b88eb4f'
>>> tasks.children #(3,4), (4,5)のタスクID
[<AsyncResult: 49db9d88-1cad-4385-b4bc-c07653246c22>,
 <AsyncResult: c8c91047-10e4-4a1c-a242-c274593dc84d>]
>>> tasks.parent.id #group((1,2), (2,3))
'a8aa3fea-e67e-423b-81fa-dca9680f85eb'
>>> tasks.parent.children #(1,2), (2,3)のタスクID
[<AsyncResult: 0f04712b-9095-4aea-b768-e4e1e51827b3>,
 <AsyncResult: 370d3245-b9c2-482f-9b22-d5f4cd3c9ee9>]
>>>
>>> # group((3,4), (4,5))のキューを取り消し、実行中であれば強制停止
>>> GroupResult(tasks.id, tasks.children).revoke(terminate=True)
>>> tasks.results
[<AsyncResult: 49db9d88-1cad-4385-b4bc-c07653246c22>,
 <AsyncResult: c8c91047-10e4-4a1c-a242-c274593dc84d>]
>>> tasks.children[0].result
TaskRevokedError('terminated')
>>> tasks.children[0].status
'REVOKED'
>>> tasks.children[1].result
TaskRevokedError('terminated')
>>> tasks.children[1].status
'REVOKED'
```

- Logs

```
docker-compose logs app

# 必要な箇所のみ抜粋
########### キュー取り消し ###########
[2021-05-30 05:52:18] Received task: [de643078-711b-49b6-8cf1-fb4d1d005279]
[2021-05-30 05:52:18] Received task: [9e77f6cb-344f-4ebf-bf45-1ed33b68ee43]
[2021-05-30 05:52:20] Tasks flagged as revoked: 9308f99d-4a08-476d-a378-6ff8209fbb9d, 51ca5d8e-3690-4724-8276-862848e86d2a 
[2021-05-30 05:52:21] x=1, y=2       
[2021-05-30 05:52:21] x=2, y=3       
[2021-05-30 05:52:21] Task [de643078-711b-49b6-8cf1-fb4d1d005279] succeeded in 3s: 3   
[2021-05-30 05:52:21] Received task: [9308f99d-4a08-476d-a378-6ff8209fbb9d]
[2021-05-30 05:52:21] Discarding revoked task: [9308f99d-4a08-476d-a378-6ff8209fbb9d]
[2021-05-30 05:52:21] Task [9e77f6cb-344f-4ebf-bf45-1ed33b68ee43] succeeded in 3s: 5   
[2021-05-30 05:52:21] Received task: [51ca5d8e-3690-4724-8276-862848e86d2a]
[2021-05-30 05:52:21] Discarding revoked task: [51ca5d8e-3690-4724-8276-862848e86d2a]

########### 強制停止 ###########
[2021-05-30 05:56:28] Received task: [0f04712b-9095-4aea-b768-e4e1e51827b3]
[2021-05-30 05:56:28] Received task: [370d3245-b9c2-482f-9b22-d5f4cd3c9ee9]
[2021-05-30 05:56:31] x=1, y=2       
[2021-05-30 05:56:31] x=2, y=3       
[2021-05-30 05:56:31] Task [0f04712b-9095-4aea-b768-e4e1e51827b3] succeeded in 3s: 3   
[2021-05-30 05:56:31] Received task: [49db9d88-1cad-4385-b4bc-c07653246c22]
[2021-05-30 05:56:31] Task [370d3245-b9c2-482f-9b22-d5f4cd3c9ee9] succeeded in 3s: 5    
[2021-05-30 05:56:31] Received task: [c8c91047-10e4-4a1c-a242-c274593dc84d]
[2021-05-30 05:56:31] Terminating 49db9d88-1cad-4385-b4bc-c07653246c22 (Signals.SIGTERM)
[2021-05-30 05:56:31] Terminating c8c91047-10e4-4a1c-a242-c274593dc84d (Signals.SIGTERM)
[2021-05-30 05:56:31] Task handler raised error: Terminated(15)
Traceback (most recent call last):
  File "/usr/local/lib/python3.9/site-packages/billiard/pool.py", line 1774, in _set_terminated
    raise Terminated(-(signum or 0))
billiard.exceptions.Terminated: 15
[2021-05-30 05:56:31] Task handler raised error: Terminated(15)
Traceback (most recent call last):
  File "/usr/local/lib/python3.9/site-packages/billiard/pool.py", line 1774, in _set_terminated
    raise Terminated(-(signum or 0))
billiard.exceptions.Terminated: 15
```