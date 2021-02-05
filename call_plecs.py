import os
import re
import shutil
import sys
import time
import xmlrpc.client
from collections import abc, defaultdict
from concurrent.futures import as_completed, wait
from concurrent.futures.thread import ThreadPoolExecutor as PoolExecutor
from itertools import chain
from pathlib import Path
from queue import Queue

# ===================== config ==========================

PORT = 1081
MAX_WORKER = 8
MODULE_NUM = 15

MODEL_VARS = {
    'load': 1500,
    'c_sw': 2.57e-9 * MODULE_NUM,
    'c_bus': 1e-3 * MODULE_NUM,
    'l_s': 20e-6 / MODULE_NUM,
}

SOLVER_OPTS = {'StartTime': 0.0, 'StopTime': 0.5, 'MaxStep': 1e-5}
SCOPES = ['Scope', 'Scope2']

# define values for parameter sweep
time_unit = 0.4e-6
SWEEP_PARAS = {
    # 'load': [25, 50, 75, 100, 150, 200, 400, 800],
    # 'dz': [i*time_unit for i in range(6)],
    # 'c_sw': [i*1e-9 for i in (1, 5, 25)],
    'c_iso': [1e-6 * i for i in (0, 1, 10, 100, 1000)],
    # 'c_bus': [200*1e-6*i for i in (1, 5, 25)],
    # 'f_sw': [10e3, 20e3, 40e3]
}

# ====================== code ===========================

TRACE_SUFFIX = '.trace'
TRACES = Queue()


class PlecsProxy:
    def __init__(self, model_path, port):
        self._options = {'ModelVars': {}, 'SolverOpts': {}, 'AnalysisOpts': {}}
        # assert model_path.exists()

        # return the absolute model path
        mdl_abs_path = str(model_path.resolve())

        # configure the XML-RPC port -> needs to coincide with the PLECS configuration
        # start PLECS
        self._proxy = xmlrpc.client.Server(f'http://localhost:{port}/RPC2')
        self._handler = self._proxy.plecs

        # define model name and other element paths
        self._model = model_path.stem

        # open the model using the XMLRPC server, needs absolute path
        self._handler.load(mdl_abs_path)

        self._scopes = []

    def set_model_var(self, key, val):
        self._options['ModelVars'][key] = val

    def set_solver_opt(self, key, val):
        self._options['SolverOpts'][key] = val

    def add_scope(self, scope_name):
        """
        Add scope for the mode.
        scope name is defined by its path and name.
        """
        scp = '{}/{}'.format(self._model, scope_name)
        self._scopes.append(scp)

    def simulate(self):
        """ start simulate """
        self._handler.simulate(self._model, self._options)

    def hold_trace(self, trace_name='', max_name_len=50):
        """
        Hold trace for the scopes.
        if not specify, set trace name by model vars.
        """
        if not trace_name:
            trace_name = ', '.join(
                f'{k} = {v}' for k, v in self._options['ModelVars'].items()
            )

        for scp in self._scopes:
            self._handler.scope(scp, 'HoldTrace', trace_name[:max_name_len])

    def save_traces(self):
        for scp in self._scopes:
            name = re.sub(r'[\/]', '_', scp)
            self._handler.scope(scp, 'SaveTraces', name + TRACE_SUFFIX)
            TRACES.put(name + TRACE_SUFFIX)

    def load_traces(self, filename, scope=None):
        if not scope:
            scope = self._scopes[0]
        self._handler.scope(scope, 'LoadTraces', filename)

    def clear(self, scopes=None):
        """ clear existing traces in the scope. if not specify, clear all """
        if scopes is None:
            scopes = self._scopes
        if isinstance(scopes, str):
            self._handler.scope(scopes, 'ClearTraces')
        else:
            for scp in scopes:
                self.clear(scp)


def get_time():
    return time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime())


def info(*args, **kwargs):
    print(get_time(), *args, **kwargs)


def bar(*args):
    temp = '=' * 20
    print('\n', temp, *args, temp)


class Worker:
    def __init__(self, name: str, tool: PlecsProxy, task: dict):
        # init
        for scp in SCOPES:
            tool.add_scope(scp)
            tool.clear()

        # init the parameters for simulation
        for k, v in MODEL_VARS.items():
            tool.set_model_var(k, v)
        for k, v in SOLVER_OPTS.items():
            tool.set_solver_opt(k, v)

        self.name = name
        self.tool = tool
        self.task = task

    def run(self):
        for k in self.task:
            for v in self.task[k]:
                name = f'{k} = {v}'
                info(f'>>> {name} start')
                self.tool.set_model_var(k, v)
                self.tool.simulate()
                self.tool.hold_trace(trace_name=name)
                info(f">>> {name} has been done.")

        if self.name.startswith('~'):
            self.tool.save_traces()
            self.tool.clear()
        return True

    def __str__(self):
        return re.search(r'({.*})', str(self.task)).group()


if __name__ == "__main__":

    _, model_file = sys.argv
    assert os.path.isfile(model_file)

    os.chdir(os.path.dirname(__file__))

    base_model = Path(Path(model_file).name)

    models = [base_model]

    real_worker_num = min(MAX_WORKER, max(len(v) for v in SWEEP_PARAS.values()))

    for i in range(1, real_worker_num):
        mdl = Path('~' * i + base_model.name)
        shutil.copy(base_model, mdl)
        models.append(mdl)

    workers = []
    for mdl in models:
        w = Worker(mdl.name, PlecsProxy(mdl, port=PORT), defaultdict(list))
        workers.append(w)

    # assign task for each worker
    for k, vals in SWEEP_PARAS.items():
        i = 0
        while vals:
            workers[i].task[k].append(vals.pop())
            i = (i + 1) % real_worker_num

    # print tasks
    bar('tasks assignment')
    info(*[f'worker {i}: {w}' for i, w in enumerate(workers)], sep='\n')

    # go go go!
    bar('start simulation')

    with PoolExecutor(max_workers=real_worker_num) as executor:
        futures = [executor.submit(w.run) for w in workers]
        wait(futures)
        # for future in as_completed(futures):

    # load traces
    base_worker = workers[0]

    while not TRACES.empty():
        tr = TRACES.get()
        print('trace:', tr)
        base_worker.tool.load_traces(tr)
        os.remove(tr)

    bar('simulation done')

    # rm temp file
    for p in models[1:]:
        assert p != base_model
        os.remove(p)
        info('removed:', p)

    bar('successful')
