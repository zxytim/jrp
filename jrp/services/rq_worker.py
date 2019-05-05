import argparse
from jrp import config
from redis import StrictRedis
from multiprocessing import Process
from setproctitle import setproctitle

import time

import rq
from rq.queue import FailedQueue


def start_worker(worker):
    setproctitle('rq-worker:{}'.format(worker.name))
    worker.work()


class Task:
    def init_parser(self, parser):
        pass

    def run(self, args):
        pass



def parse_queue_config(config):
    """
    :param config: a list of string of format "<name>:<quantity>"
    """
    rst = []
    for conf in config:
        name, count = conf.split(':')
        count = int(count)
        rst.append((name, count))
    return rst


class RQWorker(Task):
    def init_parser(self, parser):
        parser.add_argument(
            'config', nargs='+', help='name:quantity')

    def run(self, args):
        redis = StrictRedis(config.REDIS_HOST, config.REDIS_PORT)
        workers = []

        queue_config = parse_queue_config(args.config)
        with rq.Connection(redis):
            for name, count in queue_config:
                queue = rq.Queue(name)

                for i in range(count):
                    w = rq.Worker([queue], name='{}:{}'.format(name, i))
                    workers.append(w)

        procs = [
            Process(target=start_worker, args=(w, )) for w in workers
        ]
        for p in procs:
            p.start()

        for p in procs:
            p.join()


class RQFailureRecover(Task):
    def init_parser(self, parser):
        parser.add_argument(
            'queue_names', nargs='+', help='one name at a time')
        parser.add_argument(
            '--interval', default=60, type=float)

    def run(self, args):
        redis = StrictRedis(config.REDIS_HOST, config.REDIS_PORT)

        names = args.queue_names
        fq = FailedQueue(connection=redis)

        def check_fjob(fjob):
            if fjob.origin not in names:
                return None

            # XXX: Damn... Should change to another database soon
            if isinstance(fjob.exc_info, str):
                temporary_errors = [
                    'sqlite3.OperationalError: database is locked',
                    'rq.timeouts.JobTimeoutException: Task exceeded maximum timeout value',
                    'elasticsearch.exceptions.ConnectionTimeout: ConnectionTimeout caused by',
                    'elasticsearch.exceptions.ConnectionError: ConnectionError',
                    'elasticsearch.exceptions.TransportError: TransportError',
                    'requests.exceptions.ConnectionError: HTTPSConnectionPool',
                    'pdftotext',
                    'not pdf, but `text/xml`',
                    'OperationalError: database is locked',
                    """oss2.exceptions.RequestError: {'status': -2, 'x-oss-request-id': '', 'details': "RequestError: ('Connection aborted.', timeout('timed out'))"}""",
                    "requests.exceptions.ConnectionError: ('Connection aborted.', timeout('timed out'))",
                    """"RequestError: ('Connection aborted.', BrokenPipeError(32, 'Broken pipe'))"}""",
                    """oss2.exceptions.RequestError: {'status': -2, 'x-oss-request-id': '', 'details': "RequestError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))"}""",
                    'port=80): Read timed out. (read timeout=60)"}',
                ]
                for s in temporary_errors:
                    if s in fjob.exc_info:
                        return 'requeue'

                permitted_errors = [
                    'sqlite3.IntegrityError: UNIQUE constraint failed: progress.key'
                ]
                for s in permitted_errors:
                    if s in fjob.exc_info:
                        return 'delete'

            return None

        while True:
            count_requeue = 0
            count_delete = 0

            fjobs = fq.get_jobs()
            for fjob in fjobs:
                t = check_fjob(fjob)
                if t == 'requeue':
                    fq.requeue(fjob.id)
                    count_requeue += 1
                elif t == 'delete':
                    fjob.delete()
                    count_delete += 1

            num_remain = len(fjobs) - count_requeue - count_delete
            print('{} failed jobs: {} requeued, {} deleteed, {} remains'.format(
                len(fjobs), count_requeue, count_delete, num_remain)
            )
            time.sleep(args.interval)


def main():
    parser = argparse.ArgumentParser()

    tasks = [
        ('rq-worker', RQWorker()),
        ('rq-failure-recover', RQFailureRecover()),
    ]

    subparsers = parser.add_subparsers(
        dest='task', required=True)

    for name, task in tasks:
        subp = subparsers.add_parser(name)
        task.init_parser(subp)
        subp.set_defaults(func=task.run)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
