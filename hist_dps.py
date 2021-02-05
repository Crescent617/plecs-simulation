import matplotlib.pyplot as plt
import pandas as pd


df = pd.read_csv('./dps_sps.csv', skiprows=lambda x: x % 1000 != 0)
df['Time']
df[df['Time'] < 1]
df = df[df['Time'] < 1]
split = 0

for i in range(1, len(df)):
    if df['Time'].iloc[i] < df['Time'].iloc[i - 1]:
        split = i
        break


df1 = df.iloc[:split]
df2 = df.iloc[split:]
plt.style.use('seaborn-white')

plt.plot(df1['Time'], df1['V_D:Measured voltage'])
plt.plot(df2['Time'], df2['V_D:Measured voltage'])
plt.grid(True)

plt.tight_layout()
plt.show()
