
# %%
import os
import sys
import numpy as np
import pandas as pd
#import openmatrix as omx
import igraph as ig
import random
import matplotlib.cm as cm
import matplotlib.colors
import matplotlib.pyplot as plt
from functools import reduce

os.chdir("/Users/ericfrey/Documents/networks/ps4")
# %%
#read road data
anaheim = "anaheim.tntp"
anaheim = pd.read_csv(anaheim, skiprows=8, sep='\t').drop(["~",";"], axis=1)

#flow data
flow = "anaheim_flow.tntp"
flow = pd.read_csv(flow, sep='\t|\s', engine='python')
anaheim = anaheim.merge(flow[["Volume"]], left_index=True, right_index=True)
# %%
# get graph
g = ig.Graph.TupleList(anaheim.itertuples(index=False), directed=True, weights=False, edge_attrs=["capacity","length","free_flow_time","b","power","speed","toll","link_type", "Volume"])

g.es['color'] = continuous_to_rgb(np.log(anaheim.Volume +1)).tolist()

sg = g.subgraph(g.neighborhood(1, order= 7))
sg_df = sg.get_edge_dataframe()

ig.plot(sg)

# %% generate fake rider data:
paths = []
time = []
volume = []
for v in sg.vs.indices:
    
    path = random.sample(filter_subpaths(sg.get_all_shortest_paths(v)), 1)[0]
    if len(path) >1:
        paths.append(path)
        time.append(calculate_travel_time(path, sg_df))
        volume.append(get_total_volume(path, sg_df))

riders = pd.DataFrame({"path":paths, "travel_time":time, "volume": volume})

# %% Generate fake station data:
bike_stations = random.sample(sg.vs.indices,2)
station_paths = sg.get_all_simple_paths(bike_stations[0], bike_stations[1])
station_paths.append(sg.get_all_simple_paths(bike_stations[1], bike_stations[0]))

is_bike_edge = paths_to_edges(station_paths, sg_df)

# visualize and plot
sg.es['color'] = ['red' if edge else 'black' for edge in is_bike_edge]
ig.plot(sg)

# %% calculate new travel time based on this

travel_time_bike = []
for i, path in enumerate(riders.path):
    if any_subpath(station_paths, path):
        travel_time_bike.append(calculate_travel_time_bike(path, sg_df, is_bike_edge))
    else:
        travel_time_bike.append(riders.loc[i]['travel_time'])
riders['travel_time_bike'] = pd.Series(travel_time_bike)

# %%
print(riders.travel_time.sum())
print(riders.travel_time_bike.sum())
# %%
