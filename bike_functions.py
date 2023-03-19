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
    # Select the edges that correspond to the given path
    edges = edges_df.loc[edges_df['source'].isin(path[:-1]) & edges_df['target'].isin(path[1:])]

    # Calculate the total travel time for the path
    travel_time = (edges['length'] / edges['speed']).sum()
    
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