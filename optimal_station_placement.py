
# %% import packages
import numpy as np
from itertools import combinations
import pandas as pd
import igraph as ig
import random
from bike_functions import *

# %% read road data as dataframes
anaheim = "anaheim.tntp"
anaheim = pd.read_csv(anaheim, skiprows=8, sep='\t').drop(["~",";"], axis=1)

#flow data
flow = "anaheim_flow.tntp"
flow = pd.read_csv(flow, sep='\t|\s', engine='python')
anaheim = anaheim.merge(flow[["Volume"]], left_index=True, right_index=True)
# %% convert the dataframe data to a graph.
g = ig.Graph.TupleList(anaheim.itertuples(index=False), directed=True, weights=False, edge_attrs=["capacity","length","free_flow_time","b","power","speed","toll","link_type", "Volume"])

g.es['color'] = continuous_to_rgb(np.log(anaheim.Volume +1)).tolist()

sg = g.subgraph(g.neighborhood(1, order= 7))
sg_df = sg.get_edge_dataframe()

# here's what the subgraph looks like. The edges are colored by volume of traffic.
ig.plot(sg)

# %% generate some fake commuter data:
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


print('travel time without stations: ', riders.travel_time.sum())
print('travel time with two randomly placed stations: ', riders.travel_time_bike.sum())
# %% Ok, we did a small scale, now let's see the time reduction when we iterate over all possible stations
stations = filter_stations(list(combinations(sg.vs.indices,2)))

station_time = []
for station in stations:
    station_paths = sg.get_all_simple_paths(station[0], station[1])
    station_paths.append(sg.get_all_simple_paths(station[1], station[0]))

    is_bike_edge = paths_to_edges(station_paths, sg_df)

    travel_time_bike = []
    for i, path in enumerate(riders.path):
        if any_subpath(station_paths, path):
            travel_time_bike.append(calculate_travel_time_bike(path, sg_df, is_bike_edge))
        else:
            travel_time_bike.append(riders.loc[i]['travel_time'])
    riders['travel_time_bike'] = pd.Series(travel_time_bike)
    station_time.append(riders.travel_time_bike.sum())

# report of stations and their times:
station_df = pd.DataFrame({"station":stations, "station_time":station_time})
# this is a visualization of travel time iterating over all possible stations.
# we see most bike station placements result in little time reduction, while there are a few outliers
# that reduce time a lot
station_df.station_time.hist()

# top 10 station placements and their times
station_df.sort_values('station_time').head(10)
# %% visualization of best station
station = station_df.sort_values('station_time').head(1).station.values[0]
station_paths = sg.get_all_simple_paths(station[0], station[1])
station_paths.append(sg.get_all_simple_paths(station[1], station[0]))

is_bike_edge = paths_to_edges(station_paths, sg_df)

# visualize and plot
sg.es['color'] = ['red' if edge else 'black' for edge in is_bike_edge]
sg.vs['color'] = ['red' if node in station else 'black' for node in sg.vs.indices]
print('best bike station placement:')
ig.plot(sg)
# %%

############################################
# Generating rider data that reflects the volume of each edge

paths = []
time = []
volume = []

# %%
riders
# %%
def has_nan(lst):
    return np.isnan(lst).any()
for v in sg.vs.indices:
    d_paths=dict()
    possible_paths=sg.get_all_shortest_paths(v)
    #figure out which paths are the shortest between two pairs of nodes
    for i,path in enumerate(possible_paths):
        d_paths[i]=round(get_total_volume(path, sg_df),2)

    d_paths={k:v/sum(list(d_paths.values())) for k,v in d_paths.items()}
    if has_nan(list(d_paths.values())) ==False:
        sampled_indices = np.random.choice(list(d_paths.keys()), size=3, p=list(d_paths.values()))
        sampled_paths=[possible_paths[i] for i in sampled_indices]
    # break
        paths.extend(sampled_paths)
# %%

riders = pd.DataFrame({"path":paths, "travel_time":time, "volume": volume})
# %%
