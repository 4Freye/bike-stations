import matplotlib.cm as cm
import matplotlib.colors
import matplotlib.pyplot as plt
from functools import reduce
import numpy as np
import pandas as pd
#from pytrans.UrbanNetworkAnalysis import TransportationNetworks as tn
import scipy.integrate as integrate 
import networkx as nx
from scipy.optimize import minimize_scalar

def combine_series(series_list):
    return reduce(lambda s1, s2: s1 | s2, series_list).astype(bool)

def paths_to_edges(list_of_paths, edges_df):
    bike_edges = []
    for path in list_of_paths:
        bike_edges.append(edges_df['source'].isin(path[:-1]) & edges_df['target'].isin(path[1:]))
    return combine_series(bike_edges)


def continuous_to_rgb(numbers, cmap_name='viridis', reverse_cmap=False):
    cmap = cm.get_cmap(cmap_name)
    if reverse_cmap:
        cmap = cmap.reversed()
    norm = matplotlib.colors.Normalize(vmin=min(numbers),vmax=max(numbers))
    cmap = getattr(plt.cm, cmap_name)
    colors = cmap(norm(numbers))
    return colors[:, :3]

def get_total_volume(nodes, edges):
    # Filter the edges dataframe to only include edges between nodes in the list
    filtered_edges = edges[(edges['source'].isin(nodes[:-1])) & (edges['target'].isin(nodes[1:]))]
    
    # Calculate the sum of the volume column for the filtered edges
    total_volume = filtered_edges['Volume'].sum()
    
    return total_volume

def is_subpath(path, longer_path):
    # Check if path is a subpath of longer_path
    if len(path) > len(longer_path):
        return False
    for i in range(len(longer_path) - len(path) + 1):
        if longer_path[i:i+len(path)] == path:
            return True
    return False

def filter_subpaths(paths):
    # Initialize a set to store subpaths
    subpaths = set()
    # Sort the paths by length, descending
    sorted_paths = sorted(paths, key=len, reverse=True)
    # Loop through each path
    for path in sorted_paths:
        # If the path is already marked as a subpath, skip it
        if tuple(path) in subpaths:
            continue
        # Check if the path is a subpath of any longer paths
        for longer_path in sorted_paths:
            if path == longer_path:
                continue
            if is_subpath(path, longer_path):
                subpaths.add(tuple(path))
                break
    # Return only the paths that are not subpaths
    return [list(path) for path in sorted_paths if tuple(path) not in subpaths]

def any_subpath(short_paths, long_path):
    for path in short_paths:
        if not path:
            continue
        if all(node in long_path for node in path):
            idx = long_path.index(path[0])
            if long_path[idx:idx+len(path)] == path:
                return True
    return False

def calculate_travel_time(path, edges_df):

    if 'init_node' in edges_df.columns:
        source= 'init_node'
        target= 'term_node'
    else:
        source = 'source'
        target = 'target'
    # Select the edges that correspond to the given path
    edges = edges_df.loc[edges_df[source].isin(path[:-1]) & edges_df[target].isin(path[1:])]

    # Calculate the total travel time for the path
    travel_time = (edges['length'] / edges['speed']).sum()

    return travel_time

def calculate_travel_time_ff(path, edges_df):

    if 'init_node' in edges_df.columns:
        source= 'init_node'
        target= 'term_node'
    else:
        source = 'source'
        target = 'target'
    # Select the edges that correspond to the given path
    edges = edges_df.loc[edges_df[source].isin(path[:-1]) & edges_df[target].isin(path[1:])]

    # Calculate the total travel time for the path
    travel_time = edges['free_flow_time'].sum()

    return travel_time


def calculate_travel_time_bike(path, edges_df, is_bike_edge):
    # Select the edges that correspond to the given path
    edges = edges_df.loc[edges_df['source'].isin(path[:-1]) & edges_df['target'].isin(path[1:])].copy()

    # Select the edges that correspond to the given path
    edges['bike'] = is_bike_edge

    # Calculate the total travel time for the path. For bike edge, make it 2x as fast
    travel_time = (edges[edges.bike]['length'] / (edges[edges.bike]['speed']*2)).sum()
    travel_time += (edges[~edges.bike]['length'] / edges[~edges.bike]['speed']).sum()
    
    return travel_time

def calculate_travel_time_bike_ff(path, edges_df, is_bike_edge):
    edges = edges_df.loc[edges_df['source'].isin(path[:-1]) & edges_df['target'].isin(path[1:])].copy()

    edges['bike'] = is_bike_edge

    travel_time = (edges[edges.bike]['free_flow_time']).sum()/2
    travel_time += (edges[~edges.bike]['free_flow_time']).sum()
    
    return travel_time


def filter_stations(station_list):
    filtered_tuple = []
    for tuple in station_list:
        if tuple[0] < tuple[1]:
            filtered_tuple.append(tuple)
    return filtered_tuple

def calculate_path_free_flow_time(path, graph):
    free_flow_time_sum = 0
    for i in range(len(path) - 1):
        source = path[i]
        target = path[i + 1]
        free_flow_time_sum += graph[source][target]['time']
    return free_flow_time_sum

def calculate_path_length(path, graph):
    path_length = 0
    for i in range(len(path) - 1):
        source = path[i]
        target = path[i + 1]
        path_length += graph[source][target]['object'].length
    return path_length

def calculate_path_capacity(path, graph, path_length):
    capacity = 0
    for i in range(len(path) - 1):
        source = path[i]
        target = path[i + 1]
        capacity += graph[source][target]['object'].capacity * graph[source][target]['object'].length/path_length
    return capacity

def add_or_modify_undirected_edge(graph, node1, node2, time, length, capacity):
    if graph.has_edge(node1, node2):
        # If a directed edge exists, convert it to an undirected edge
        graph.remove_edge(node1, node2)
        graph.add_edge(node1, node2, directed=False)
    else:
        # If no edge exists, add an undirected edge
        graph.add_edge(node1, node2)
        graph.add_edge(node2, node1)
    
    # update Link object for new station
    new_link = tn.Link(from_node = node1, to_node = node2, alpha=.15, beta=4, free_speed = time, SO = False, capacity = capacity, flow=0, length = length)
    graph.edges[(node1, node2)]['object'] = new_link
    new_link = tn.Link(from_node = node2, to_node = node1, alpha=.15, beta=4, free_speed = time, SO = False, capacity = capacity, flow=0, length = length)
    graph.edges[(node2, node1)]['object'] = new_link

    # update time for new station
    graph.edges[(node1, node2)]['time'] = time
    graph.edges[(node2, node1)]['time'] = time

    return graph

# Method for calculating link travel time based on BPR function.
def BPR(t0, xa, ca, alpha, beta):
    ta = t0*(1+alpha*(xa/ca)**beta)
    return ta

# Method for calculating objective function value. 
def calculateZ(theta, network, SO):
    z = 0
    for linkKey, linkVal in network.items():
        t0 = linkVal['t0']
        ca = linkVal['capa']
        beta = linkVal['beta']
        alpha = linkVal['alpha']
        aux = linkVal['auxiliary'][-1]
        flow = linkVal['flow'][-1]
        
        if SO == False:
            z += integrate.quad(lambda x: BPR(t0, x, ca, alpha, beta), 0, flow+theta*(aux-flow))[0]
        elif SO == True:
            z += list(map(lambda x : x * BPR(t0, x, ca, alpha, beta), [flow+theta*(aux-flow)]))[0]
    return z

# Finds theta, the optimal solution of the line search that minimizing the objective function along the line between current flow and auxiliary flow.
def lineSearch(network, SO):
    theta = minimize_scalar(lambda x: calculateZ(x, network, SO), bounds = (0,1), method = 'Bounded')
    return theta.x

def compute_eq_cost(station, siouxFalls):
    siouxFalls2 = siouxFalls
    siouxFalls2.graph = siouxFalls.graph.copy()

    # get the shortest path between two nodes
    shortest_path = nx.shortest_path(siouxFalls2.graph, station[0],station[1], weight='time')

    # Calculate time, length and capacity
    bike_edge_time = calculate_path_free_flow_time(shortest_path, siouxFalls2.graph) * 1/2
    path_length = calculate_path_length(shortest_path, siouxFalls2.graph)
    capacity = calculate_path_capacity(shortest_path, siouxFalls2.graph, path_length)

    # If not an edge yet then add one:    
    siouxFalls2.graph = add_or_modify_undirected_edge(siouxFalls2.graph, station[0], station[1], bike_edge_time, path_length, capacity)

    # initialization

    # define output variables, network and fwResult
    network = {(u,v): {'t0':d['object'].t0, 'alpha':d['object'].alpha, \
            'beta':d['object'].beta, 'capa':d['object'].capacity, 'flow':[], \
            'auxiliary':[], 'cost':[]} for (u, v, d) in siouxFalls2.graph.edges(data=True)}

    fwResult = {'theta':[], 'z':[]}

    # initial all-or-nothing assignment and update link travel time(cost)
    siouxFalls2.all_or_nothing_assignment()
    siouxFalls2.update_linkcost()

    for linkKey, linkVal in network.items():
        linkVal['cost'].append(siouxFalls2.graph[linkKey[0]][linkKey[1]]['weight'])
        linkVal['auxiliary'].append(siouxFalls2.graph[linkKey[0]][linkKey[1]]['object'].vol)
        linkVal['flow'].append(siouxFalls2.graph[linkKey[0]][linkKey[1]]['object'].vol)

    ## iterations
    iterNum = 0
    iteration = True
    while iteration:
        iterNum += 1
        siouxFalls2.all_or_nothing_assignment()
        siouxFalls2.update_linkcost()
        
        # set auxiliary flow using updated link flow
        for linkKey, linkVal in network.items():
            linkVal['auxiliary'].append(siouxFalls2.graph[linkKey[0]][linkKey[1]]['object'].vol)
            
        # getting optimal move size (theta)
        theta = lineSearch(network, False)
        fwResult['theta'].append(theta)
        
        # set link flow (move) based on the theta, auxiliary flow, and link flow of previous iteration
        for linkKey, linkVal in network.items():
            aux = linkVal['auxiliary'][-1]
            flow = linkVal['flow'][-1]
            linkVal['flow'].append(flow + theta*(aux-flow))
            
            siouxFalls2.graph[linkKey[0]][linkKey[1]]['object'].vol =  flow + theta * (aux - flow)
            siouxFalls2.graph[linkKey[0]][linkKey[1]]['object'].flow = flow + theta * (aux - flow)
            
        # update link travel time
        siouxFalls2.update_linkcost()
        
        # calculate objective function value
        z=0
        for linkKey, linkVal in network.items():
            linkVal['cost'].append(siouxFalls2.graph[linkKey[0]][linkKey[1]]['weight'])
            totalcost = siouxFalls2.graph[linkKey[0]][linkKey[1]]['object'].get_objective_function()
            z += totalcost
            
        fwResult['z'].append(z)        
            
        # convergence test
        if iterNum == 1:
            iteration = True
        else:
            if abs(fwResult['z'][-2] - fwResult['z'][-1]) <= 0.001 or iterNum==3000:
                iteration = False
    print('station {} eq cost computed. Cost: {}'.format(station,fwResult['z'][-1]) )
    return fwResult['z'][-1]
