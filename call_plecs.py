import sys
import time
import xmlrpc.client
from pathlib import Path

def get_time():
    return time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime())
    

_, mdl_filename = sys.argv

mdl_path = Path(mdl_filename)
assert mdl_path.exists()

# return the absolute model path
mdl_abs_path = str(Path(mdl_path).resolve())

# configure the XML-RPC port -> needs to coincide with the PLECS configuration
port = '1080'
# start PLECS
proxy = xmlrpc.client.Server('http://localhost:' + port + '/RPC2')
plecs = proxy.plecs

# define model name and other element paths
model = mdl_path.stem
scope = model + '/Scope'

# open the model using the XMLRPC server, needs absolute path
plecs.load(mdl_abs_path)
# clear existing traces in the scope
# plecs.scope(scope, 'ClearTraces')

# modify the parameters for simulation
options: dict = {
    'ModelVars': {
        'c_s': 0,
        'l_s': 0,
    },
    'SolverOpts': {
        'StartTime': 0,
        'StopTime': 0.1,
    },
    'AnalysisOpts': {}
}

# define values for parameter sweep
sweep_paras = {
    'c_s': [0, 1e-7, 1e-8, 1e-9, 1e-10],
    'l_s': [1e-6, 1e-5, 1e-4]
}

# loop for all values
for k, vals in sweep_paras.items():
    for v in vals:
        # set value
        options['ModelVars'][k] = v
        # start simulation, using opts struct
        plecs.simulate(model, options)
        # add trace to the scope
        k = k.capitalize()
        plecs.scope(scope, 'HoldTrace', f'{k} = {v}')
        print(get_time(), f"'{k} = {v}' has been done.")
