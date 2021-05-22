from celery import Celery
import time

app = Celery('tasks', broker='redis://redis:6379')

# タスク実行後の結果をredisに格納する
app.conf.result_backend = 'redis://redis:6379/0'

@app.task
def add(x, y):
    return x + y

@app.task
def show(text):
    # time.sleep(5)
    print('{}'.format(text))
    return '{}'.format(text)
