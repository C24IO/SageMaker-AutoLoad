#
# run command: locust --host=localhost:8000
#

import os
import json
import time
import boto3
import gevent
import inspect
import numpy as np
from locust import HttpUser, task
from locust.env import Environment
from botocore.config import Config
from locust.log import setup_logging
from locust import User, TaskSet, task, events
from locust.contrib.fasthttp import FastHttpUser
from locust.stats import stats_printer, stats_history
from locust import HttpUser, task, events, between, constant, constant_pacing
from locust.runners import STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP, WorkerRunner, STATE_RUNNING

run_logs_dir = 'run-logs/'

def stopwatch(func):
    def wrapper(*args, **kwargs):
        # get task's function name
        previous_frame = inspect.currentframe().f_back
        _, _, task_name, task_func_name, _ = inspect.getframeinfo(previous_frame)
        #print(task_func_name[0].split('.')[-1].split('(')[0])
        #print(inspect.getframeinfo(previous_frame))
        task_func_name = task_func_name[0].split('.')[-1].split('(')[0]

        self_here = args[0]

        start = time.time()
        result = None

        try:

            result = func(*args, **kwargs)
            total = int((time.time() - start) * 1000)

        except Exception as e:
            events.request_failure.fire(request_type=task_name,
                                        name=task_func_name,
                                        response_time=total,
                                        response_length=len(result),
                                        exception=e)
        else:
            #total = int((time.time() - start) * 1000)
            _ = result
            events.request_success.fire(request_type=task_name,
                                        name=task_func_name,
                                        response_time=total,
                                        response_length=len(result))
        return result
    return wrapper

class ProtocolClient:
    def __init__(self, host):

        self.endpoint_name = host.split('/')[-1]
        self.region = 'us-east-1'
        self.content_type = 'text/csv'
        self.payload = '5.0,3.5,1.3,0.3\n'
        
        print(self.endpoint_name)
 
        boto3config = Config(
            retries={
                'max_attempts': 100,
                'mode': 'standard'
            }
        )
        #boto3.set_stream_logger('botocore') #Creates hugehuge logfiles
        self.sagemaker_client = boto3.client('sagemaker-runtime',
                                             config=boto3config,
                                             region_name=self.region)

    @stopwatch
    # this is the method we want to measure
    def sagemaker_client_invoke_endpoint(self):

        #print(dir(self._locust_environment.stats))
        #print(dir(self._locust_environment.runner))
        #print(self._locust_environment.runner.state)
        #print(self._locust_environment.runner.stats.total.current_rps)
        #print(self._locust_environment.runner.stats.total.total_rps)
        #print(self._locust_environment.runner.stats.total.num_reqs_per_sec)
        #print(self._locust_environment.runner.stats.total.use_response_times_cache)
        #print(self._locust_environment.runner.state)
        """
        if self._locust_environment.runner.state in [STATE_RUNNING]:
            print('~~~')
            print(self._locust_environment.runner.stats.total.total_rps)
            #self._locust_environment.runner.stats.total.use_response_times_cache = True
            #print((self._locust_environment.runner.stats.total.get_current_response_time_percentile(0.95)))
            print(self._locust_environment.runner.stats.total.num_reqs_per_sec)
            print((self._locust_environment.runner.stats.total.get_response_time_percentile(0.95)))
            print((self._locust_environment.runner.stats.total.get_response_time_percentile(1)))
            print((self._locust_environment.runner.stats.total.fail_ratio))
            #self._locust_environment.runner.stats.total.use_response_times_cache = False
            print('~~~')
        #print(dir(self._locust_environment.runner.client))
        #print(dir(self._locust_environment.runner.stats))
        #print(dir(self._locust_environment.runner.stats.total))
        """
        response = self.sagemaker_client.invoke_endpoint(
            EndpointName=self.endpoint_name,
            Body=self.payload,
            ContentType=self.content_type
        )
        response_body = response["Body"].read()
        return response_body

class ProtocolLocust(FastHttpUser):
    abstract = True
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = ProtocolClient(self.host)
        self.client._locust_environment = self.environment

class ProtocolTasks(TaskSet):
    @task
    def custom_protocol_boto3(self):
        self.client.sagemaker_client_invoke_endpoint()

class ProtocolUser(ProtocolLocust):
    wait_time = constant(0)
    tasks = [ProtocolTasks]
