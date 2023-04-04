# %% set working directory if needed
import os
os.getcwd()
os.chdir('/Users/MargheritaP/Documents/GitHub/bike-stations')  
#os.getcwd()

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

# %% load trips data as potential commuter data
anaheim_trips = "Data/anaheim_trips.tntp"

with open(anaheim_trips, 'r') as f:
    data = f.readlines()

table = []
for line in data:
    if 'Origin' in line:
        origin = line.strip().split()[1]
        # Add missing destination for first origin
        #table.append([origin, '1', '0'])
    else:
        for destination in line.strip().split(';')[:-1]:
            destination_number, weight = destination.split(':')
            table.append([origin, destination_number.strip(), weight.strip()])
    # Add missing destination for last origin
    #table.append([origin, '37', '0'])

#print(table)
trips = pd.DataFrame(table, columns=['Origin', 'Destination', 'Weight'])
print(trips.shape)
print(trips.head())


# %% read ANAHEIM road data as dataframes

# Zones: 38 __ Nodes: 416 __ Links: 914 __ Trips: 104,694.40
# Time: minutes __ Distance: feet __ Speed: feet per minute 

anaheim = "Data/anaheim.tntp"
anaheim = pd.read_csv(anaheim, skiprows=8, sep='\t').drop(["~",";"], axis=1)


#flow data
flow = "Data/anaheim_flow.tntp"
flow = pd.read_csv(flow, sep='\t|\s', engine='python')
anaheim = anaheim.merge(flow[["Volume"]], left_index=True, right_index=True)

print(anaheim.head())

# %% read SIOUX FALLS road data as dataframes

siouxfalls = "Data/SiouxFalls_net.tntp"
siouxfalls = pd.read_csv(siouxfalls, skiprows=8, sep='\t').drop(["~",";"], axis=1)

#flow data
flow = "Data/SiouxFalls_flow.tntp"
flow = pd.read_csv(flow, sep='\t|\s', engine='python')
siouxfalls = siouxfalls.merge(flow[["Volume"]], left_index=True, right_index=True)

print(siouxfalls.head())

# %% convert the ANAHEIM dataframe data to a graph.
g = ig.Graph.TupleList(anaheim.itertuples(index=False), directed=True, weights=False, edge_attrs=["capacity","length","free_flow_time","b","power","speed","toll","link_type", "Volume"])

# add colour as edge attribute - on the basis of volume
g.es['color'] = continuous_to_rgb(np.log(anaheim.Volume +1)).tolist()

# give zone-nodes a different colour and shape to make them visible

zone_indices = list(range(1,39))

colors = ["red" if i in zone_indices else "grey" for i in range(g.vcount())]
shapes = ["square" if i in zone_indices else "circle" for i in range(g.vcount())]
g.vs["color"] = colors
g.vs["shape"] = shapes

# add degree as vertex attribute
degree = g.degree()
g.vs["degree"] = degree

# calculate vertex sizes based on degree

sizes = [d * 1.4 for d in degree]

#adjust layout -  for full list of options: https://igraph.org/python/tutorial/0.9.6/visualisation.html#graph-layouts
layout = g.layout("kamada_kawai") # most suitable: kamada_kawai __ DrL __fruchterman_reingold __ davidson_harel

# get graph information and plot
g.summary() # 416 vertices and 914 edges
ig.plot(g, vertex_size = sizes, layout=layout, edge_arrow_size = 0.3, vertex_frame_width=0.5)

# %% convert the SIOUX FALLS dataframe data to a graph.
g = ig.Graph.TupleList(siouxfalls.itertuples(index=False), directed=True, weights=False, edge_attrs=["capacity","length","free_flow_time","b","power","speed","toll","link_type", "Volume"])

# add colour as edge attribute - on the basis of volume
g.es['color'] = continuous_to_rgb(np.log(anaheim.Volume +1)).tolist()

# give zone-nodes a different colour and shape to make them visible

zone_indices = list(range(1,1)) #not applicable for sioux falls

colors = ["red" if i in zone_indices else "grey" for i in range(g.vcount())]
shapes = ["square" if i in zone_indices else "circle" for i in range(g.vcount())]
g.vs["color"] = colors
g.vs["shape"] = shapes

# add degree as vertex attribute
degree = g.degree()
g.vs["degree"] = degree

# calculate vertex sizes based on degree

sizes = [d *2 for d in degree]

#adjust layout -  for full list of options: https://igraph.org/python/tutorial/0.9.6/visualisation.html#graph-layouts
layout = g.layout("kamada_kawai") # most suitable: kamada_kawai __ DrL __fruchterman_reingold __ davidson_harel

# get graph information and plot
g.summary() # 416 vertices and 914 edges
ig.plot(g, vertex_size = sizes, layout=layout, edge_arrow_size = 0.3, vertex_frame_width=0.5)


# %%

# find all shortest paths between vertices in the subset
shortest_paths = []
for source in zone_indices:
    for target in zone_indices:
        if source != target:
            paths = g.get_all_shortest_paths(source, to=target, weights='free_flow_time')
            shortest_paths.extend(paths)

#print(shortest_paths) # list of lists
trip_paths = pd.DataFrame({
    'path': shortest_paths,
    'Origin': [lst[0] for lst in shortest_paths],
    'Destination': [lst[-1] for lst in shortest_paths],
    'path_length': [len(lst) for lst in shortest_paths]
})
    
contains_zone = [any(1 <= node <= 38 for node in path[1:-1]) for path in trip_paths['path']]

trip_paths['contains_zone'] = contains_zone


print(trip_paths[0:10])
print(trip_paths.shape)

#count the number of duplicates
num_duplicates = trip_paths.duplicated(subset=['Origin', 'Destination']).sum()
print(f"There are {num_duplicates} duplicates in the DataFrame, as multiple candidates for the shortest path exist between many nodes.")

grouped = trip_paths.groupby(['Origin', 'Destination']).size().reset_index(name='count')
grouped_filtered = grouped[grouped['count'] > 1]

print(grouped_filtered)

## for simplicity, I now simply randomly select one potential shortest path betwen each zone-node
## we could later try to attach likelihoods of any of them being used based on the volume along each of the paths

trip_paths_simple = trip_paths.groupby(['Origin', 'Destination']).apply(pd.DataFrame.sample, n=1).reset_index(drop=True)
print(trip_paths_simple.head())
print(trip_paths_simple.shape) # as expected, we are back to 1406 rows (38*37)

# check that there are no more duplicate
#num_duplicates = trip_paths_simple.duplicated(subset=['Origin', 'Destination']).sum()
#num_duplicates

# %% Generate fake station data (as below, but now for the whole graph) - I wasn't able to run this as it takes too long:
bike_stations = random.sample(g.vs.indices,2)
station_paths = g.get_all_simple_paths(bike_stations[0], bike_stations[1])
station_paths.append(g.get_all_simple_paths(bike_stations[1], bike_stations[0]))

is_bike_edge = paths_to_edges(station_paths, anaheim)

# visualize and plot
g.es['color'] = ['grey' if edge else 'pink' for edge in is_bike_edge]
ig.plot(g, vertex_size = sizes, layout=layout, edge_arrow_size = 0.3, vertex_frame_width=0.5)

# %% optional: generate a subgraph to work with fewer nodes
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

print(riders.shape)
print(riders.head())

# %% alternative: instead of fake commuter data: real commuter data
real_riders = pd.read_csv("real commutes.csv")

real_riders_merged = pd.merge(real_riders, trip_paths_simple, on=['Origin', 'Destination'])
# g_df = g.get_edge_dataframe()

real_riders_merged["travel_time"]= real_riders_merged['path'].apply(calculate_travel_time, args=(sg_df,))
# because we are using the subgraph, there will be travel times == 0 (not in the subplot)
# we filter them out. when using the whole graph, the data is fully computed
riders = real_riders_merged[real_riders_merged["travel_time"]!=0]


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
        travel_time_bike.append(riders.iloc[i]['travel_time'])
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
            travel_time_bike.append(riders.iloc[i]['travel_time'])
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

# paths = []
# time = []
# volume = []

# # %%
# riders
# # %%
# def has_nan(lst):
#     return np.isnan(lst).any()
# for v in sg.vs.indices:
#     d_paths=dict()
#     possible_paths=sg.get_all_shortest_paths(v)
#     #figure out which paths are the shortest between two pairs of nodes
#     for i,path in enumerate(possible_paths):
#         d_paths[i]=round(get_total_volume(path, sg_df),2)

#     d_paths={k:v/sum(list(d_paths.values())) for k,v in d_paths.items()}
#     if has_nan(list(d_paths.values())) ==False:
#         sampled_indices = np.random.choice(list(d_paths.keys()), size=3, p=list(d_paths.values()))
#         sampled_paths=[possible_paths[i] for i in sampled_indices]
#     # break
#         paths.extend(sampled_paths)
# # %%

# riders = pd.DataFrame({"path":paths, "travel_time":time, "volume": volume})
# # %%
