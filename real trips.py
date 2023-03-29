# %% import packages
import numpy as np
from itertools import combinations
import pandas as pd
import igraph as ig

from queue import PriorityQueue

#from igraph.drawing.colors import GradientPalette#ColorScale, ColorBrewer
#import ColorBrewer

import random
from bike_functions import *

#%% import trips 
with open('trips.txt') as f:
    data = f.readlines()


#%% restructure trips dataset 
df = pd.DataFrame(columns=['Origin', 'Destination', 'Volume'])
for line in data:
    if 'Origin' in line:
        origin = int(line.split()[1])
    else:
        destinations = line.strip().split(';')
        for dest in destinations:
            if dest:
                dest, volume = dest.split(':')
                df = df.append({'Origin': origin, 'Destination': int(dest), 'Volume': float(volume)}, ignore_index=True)

#%% check
df.head()
#%% save
df.to_csv("real commutes.csv", index=False)

