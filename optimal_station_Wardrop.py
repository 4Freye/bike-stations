# In this python file we compute the cost for a network under a Wardrop Equilibrium.
# If you don't know what that is, two good places to start:
    # Pau's slides on this, slide 9 ish https://classroom.google.com/c/NDkyMDU5MTg0Mjg1/m/NTk4MTEzNTU4NzM3/details
    # check out the methodology section of the Networks II paper here:
    # https://classroom.google.com/c/NDkyMDU5MTg0Mjg1/p/NTQzNjcyNDMwMTkx?pli=1

# This python file requires installing this github repository:
# https://github.com/yingqiuz/netflows#wardrop-equilibrium-flow
# you can do this by running the following, according to the readme for the respository:
# git clone https://github.com/yingqiuz/netflows.git
# cd netflows
# python setup.py install
# I'd recommend not nesting the repositories (installing it inside of the bike-stations repository).
# Just a gut feeling.

# %% import packages
import numpy as np
from itertools import combinations
import pandas as pd
import igraph as ig
import random
from bike_functions import *

# %% load trips data as potential commuter data
anaheim_trips = "anaheim_trips.tntp"

with open('anaheim_trips.tntp', 'r') as f:
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
#print(trips.shape)
#print(trips.head())


# %% read road data as dataframes

# Zones: 38 __ Nodes: 416 __ Links: 914 __ Trips: 104,694.40
# Time: minutes __ Distance: feet __ Speed: feet per minute 

anaheim = "anaheim.tntp"
anaheim = pd.read_csv(anaheim, skiprows=8, sep='\t').drop(["~",";"], axis=1)
print(anaheim.head())

#flow data
flow = "anaheim_flow.tntp"
flow = pd.read_csv(flow, sep='\t|\s', engine='python')
anaheim = anaheim.merge(flow[["Volume"]], left_index=True, right_index=True)

# %% convert the dataframe data to a graph.
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

# %%
from netflows import CreateGraph

distance_matrix = create_weighted_adjacency_matrix(anaheim.init_node, anaheim.term_node, anaheim.free_flow_time)
weight_matrix = create_weighted_adjacency_matrix(anaheim.init_node, anaheim.term_node, anaheim.capacity)


# create the Graph object
graph = CreateGraph(adj=g.get_adjacency().data, dist=distance_matrix, weights=weight_matrix)


 # %%
from netflows import wardrop_equilibrium_bpr_solve

wardrop_equilibrium_bpr_solve(
        graph, 1, 2, tol=1e-8, maximum_iter=10000, cutoff=None, a=None, u=None
)

