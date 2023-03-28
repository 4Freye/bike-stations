#%%
import igraph as ig
gr=ig.Graph.Read_GraphML('../../bike-stations/manhatten.graphml')
# %%
gr.vs.attributes()
# %%
gr.vs[9].attributes()
# %%
gr.ecount()
# %%
# ig.plot(gr)
# %%
sg = gr.subgraph(gr.neighborhood(1, order= 3))
sg_df = sg.get_edge_dataframe()
# %%
# ig.plot(sg)
# %%
sg_df.geometry[0]

# %%
