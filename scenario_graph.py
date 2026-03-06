import networkx as nx
import plotly.graph_objects as go
from typing import List, Dict, Any
from logger import get_logger

logger = get_logger("ScenarioGraph")

class ScenarioGraph:
    """
    Visualizes test workflows as directed graphs.
    """
    def __init__(self):
        pass

    def build_graph(self, test_cases: List[Dict[str, Any]]) -> go.Figure:
        """
        Builds a directed graph representing the flow of actions across test cases.
        Uses Plotly to render the NetworkX graph.
        """
        if not test_cases:
            logger.warning("No test cases provided to build graph.")
            return go.Figure()

        G = nx.DiGraph()
        
        # We'll use a simple heuristic to extract nodes and edges.
        # Ideally, this would parse NLP actions, but here we treat sequences of steps as chains.
        
        for tc in test_cases:
            tc_id = tc.get("id", "Unknown TC")
            steps = tc.get("steps", [])
            
            if not steps:
                continue
                
            # Create a subgraph sequence for this test case
            prev_node = "Start"
            G.add_node(prev_node, title="Start Node")
            
            for i, step in enumerate(steps):
                # Using a truncated step text as the node name to keep the graph readable
                node_name = str(step)[:40] + ("..." if len(str(step)) > 40 else "")
                G.add_node(node_name, title=f"{tc_id} - Step {i+1}")
                G.add_edge(prev_node, node_name, weight=1)
                prev_node = node_name
                
            G.add_node(tc_id, title="Test Case End")
            G.add_edge(prev_node, tc_id, weight=2)
            
        # Optional layout calculation
        # Use spring layout or hierarchical (kamada_kawai)
        try:
            pos = nx.kamada_kawai_layout(G)
        except Exception:
             pos = nx.spring_layout(G)
             
        # Create Plotly traces
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1, color='#888'),
            hoverinfo='none',
            mode='lines')

        node_x = []
        node_y = []
        node_text = []
        node_hover_text = []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)
            node_hover_text.append(G.nodes[node].get("title", ""))

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=[t if len(t) < 15 else t[:12]+"..." for t in node_text], # Short text on node
            textposition="top center",
            hovertext=node_hover_text, # Full text on hover
            marker=dict(
                showscale=True,
                colorscale='YlGnBu',
                reversescale=True,
                color=[],
                size=20,
                colorbar=dict(
                    thickness=15,
                    title='Node Connections',
                    xanchor='left',
                    titleside='right'
                ),
                line_width=2))

        # Color nodes by degree (number of connections)
        node_adjacencies = []
        for node, adjacencies in enumerate(G.adjacency()):
            node_adjacencies.append(len(adjacencies[1]))
        node_trace.marker.color = node_adjacencies

        # Create Figure
        fig = go.Figure(data=[edge_trace, node_trace],
                     layout=go.Layout(
                        title='<br>Test Scenario Execution Flow',
                        titlefont_size=16,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        annotations=[ dict(
                            text="Directed graph representing steps executed across generated tests.",
                            showarrow=False,
                            xref="paper", yref="paper",
                            x=0.005, y=-0.002 ) ],
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                        )
        return fig
