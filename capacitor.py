# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
from itertools import cycle
from IPython import get_ipython

# %% [markdown]
# # DAB直流母线电压上升——波形分析

# %%
import numpy as np
import pandas as pd

# import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib import rc

# ## for Palatino and other serif fonts use:
plt.style.use('seaborn-white')
# plt.rcParams['font.sans-serif'] = 'Times New Roman'
# plt.rcParams['mathtext.fontset'] = 'custom'
# plt.rcParams['mathtext.it'] = 'Times New Roman'
# plt.rcParams['text.usetex'] = False


# %%
U_DC = 'V_D'


def cut_index(df):
    pre = 0
    ans = [0]
    for i, x in enumerate(df.index):
        if x < pre:
            ans.append(i)
        pre = x
    return ans + [len(df.index)]


def _my_plot(df):
    cut = cut_index(df)

    for i, (s, e, t) in enumerate(zip(cut, cut[1:], cycle(['-', '--', '-.', ':']))):
        plt.plot(df.iloc[s:e, :], t, label=f'line{i}')


def my_plot(df):
    plt.figure(dpi=300, figsize=(6, 3))

    _my_plot(df[U_DC].to_frame())

    plt.legend()
    # sns.despine()
    plt.ylabel(r'$u_{dc2}/V$')
    # plt.ylim(0, 900)
    plt.xlabel(r'$t / s$')
    plt.grid(True)
    plt.tight_layout()


# %%
# c_sw = pd.read_csv('./diff_c_sw.csv', index_col=0, skiprows=lambda x: x % 1000 != 0)
# c_bus = pd.read_csv('./diff_c_bus.csv', index_col=0, skiprows=lambda x: x % 1000 != 0)

# freq = pd.read_csv('./diff_freq.csv', index_col=0, skiprows=lambda x: x % 1000 != 0)

# my_plot(c_sw)
# my_plot(c_bus)
# my_plot(freq)

l_s = pd.read_csv('./diff_l_s.csv', index_col=0, skiprows=lambda x: x % 100 != 0)
l_s.columns = ['V_D', 'v_ac', 'power']
my_plot(l_s)



# %%
