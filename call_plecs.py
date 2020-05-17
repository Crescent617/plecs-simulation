import sys
import time
import xmlrpc.client
from pathlib import Path
from collections import abc

_, MODEL_FILE = sys.argv


class PlecsProxy:

    def __init__(self, port=1080):
        self._options = {
            'ModelVars': {},
            'SolverOpts': {},
            'AnalysisOpts': {}
        }
        mdl_path = Path(MODEL_FILE)
        assert mdl_path.exists()

        # return the absolute model path
        mdl_abs_path = str(Path(mdl_path).resolve())

        # configure the XML-RPC port -> needs to coincide with the PLECS configuration
        # start PLECS
        self._proxy = xmlrpc.client.Server(f'http://localhost:{port}/RPC2')
        self._handler = self._proxy.plecs

        # define model name and other element paths
        self._model = mdl_path.stem

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

    def hold_trace(self, trace_name='', max_name_len=30):
        """
        Hold trace for the scopes.
        if not specify, set trace name by model vars.
        """
        if not trace_name:
            trace_name = ', '.join(
                f'{k} = {v}' for k, v in self._options['ModelVars'].items())

        for scp in self._scopes:
            self._handler.scope(scp, 'HoldTrace', trace_name[:max_name_len])

    def save_trace(self, trace_name, filename):
        ...

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


# init
plecs = PlecsProxy()
plecs.add_scope('Scope')
plecs.clear()

# modify the parameters for simulation
model_vars = {
    'c_sw': 6e-9,
}
for k, v in model_vars.items():
    plecs.set_model_var(k, v)

solver_opts = {
    'StartTime': 0.0,
    'StopTime': 0.1,
    'MaxStep': 1e-6
}
for k, v in solver_opts.items():
    plecs.set_solver_opt(k, v)


# define values for parameter sweep
sweep_paras = {
    'load': [25, 50, 100, 200, 400, 800]
}

# loop for all values
for k, vals in sweep_paras.items():
    for v in vals:
        # set value
        plecs.set_model_var(k, v)
        # start simulation, using opts struct
        plecs.simulate()
        # add trace to the scope
        plecs.hold_trace()
        print(get_time(), f"{k} = {v} has been done.")
