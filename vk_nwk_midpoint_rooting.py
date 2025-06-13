#!/usr/bin/env python3
"""
Midpoint Rooting for Phylogenetic Trees

This script reads a Newick-formatted phylogenetic tree and roots it at the midpoint
of the longest path between any two leaves.
"""

import sys
import argparse
from Bio import Phylo
import copy
import networkx as nx

def tree_to_graph(tree):
    """Convert a Bio.Phylo tree to a NetworkX graph with branch lengths as edge weights."""
    G = nx.Graph()
    
    # Add all nodes and edges with their branch lengths
    for clade in tree.find_clades():
        # Add node
        G.add_node(clade.name if clade.name else id(clade))
        
        # Connect to its parent if it has one
        if clade.branch_length is not None and hasattr(clade, 'parent') and clade.parent:
            parent_id = clade.parent.name if clade.parent.name else id(clade.parent)
            node_id = clade.name if clade.name else id(clade)
            G.add_edge(parent_id, node_id, weight=clade.branch_length)
    
    return G

def find_longest_path_networkx(tree):
    """Find the longest path between any two leaf nodes using NetworkX."""
    # Convert tree to NetworkX graph
    G = nx.Graph()
    
    # Add all clades as nodes
    for clade in tree.find_clades():
        clade_id = id(clade)
        G.add_node(clade_id, clade=clade)
        if clade.branch_length is not None and hasattr(clade, 'parent') and clade.parent:
            parent_id = id(clade.parent)
            G.add_edge(parent_id, clade_id, weight=clade.branch_length)
    
    # Get leaf node IDs
    leaf_ids = [id(leaf) for leaf in tree.get_terminals()]
    
    # Find the longest path
    max_distance = 0
    furthest_pair = None
    
    for i in range(len(leaf_ids)):
        for j in range(i + 1, len(leaf_ids)):
            try:
                # Calculate shortest path distance
                path = nx.shortest_path(G, source=leaf_ids[i], target=leaf_ids[j], weight='weight')
                
                # Calculate total distance of path
                distance = 0
                for k in range(len(path) - 1):
                    distance += G[path[k]][path[k+1]]['weight']
                
                if distance > max_distance:
                    max_distance = distance
                    # Get the actual clades
                    node1 = G.nodes[leaf_ids[i]]['clade']
                    node2 = G.nodes[leaf_ids[j]]['clade']
                    furthest_pair = (node1, node2, path)
            except nx.NetworkXNoPath:
                continue
    
    if not furthest_pair:
        raise ValueError("Could not find a valid path between any leaf nodes")
    
    return max_distance, furthest_pair

def get_safe_midpoint(tree, node1, node2, path_ids):
    """Find the midpoint on the path between node1 and node2 using NetworkX path."""
    # Create a graph of the tree
    G = nx.Graph()
    
    # Add all clades as nodes with mapping to their objects
    id_to_clade = {}
    for clade in tree.find_clades():
        clade_id = id(clade)
        G.add_node(clade_id)
        id_to_clade[clade_id] = clade
        if clade.branch_length is not None and hasattr(clade, 'parent') and clade.parent:
            parent_id = id(clade.parent)
            G.add_edge(parent_id, clade_id, weight=clade.branch_length)
    
    # Calculate the total distance and find the midpoint
    total_distance = 0
    distances = [0]  # Starting with 0 for the first node
    
    for i in range(len(path_ids) - 1):
        edge_weight = G[path_ids[i]][path_ids[i+1]]['weight']
        total_distance += edge_weight
        distances.append(total_distance)
    
    # Find the midpoint (half of total distance)
    midpoint_distance = total_distance / 2
    
    # Find which edge contains the midpoint
    for i in range(len(distances) - 1):
        if distances[i] <= midpoint_distance < distances[i+1]:
            edge_start = path_ids[i]
            edge_end = path_ids[i+1]
            edge_length = distances[i+1] - distances[i]
            fraction = (midpoint_distance - distances[i]) / edge_length
            
            return id_to_clade[edge_start], id_to_clade[edge_end], fraction
    
    # Fallback
    middle_idx = len(path_ids) // 2
    return id_to_clade[path_ids[middle_idx-1]], id_to_clade[path_ids[middle_idx]], 0.5

def custom_midpoint_root(tree):
    """Root the tree at the midpoint of the longest path using a custom approach."""
    try:
        # Try built-in method first
        rooted_tree = copy.deepcopy(tree)
        rooted_tree.root_at_midpoint()
        return rooted_tree
    except Exception as e:
        # If built-in method fails, use our custom approach
        print(f"Built-in midpoint rooting failed ({str(e)}), using custom method.")
        
        # Find the longest path
        max_distance, furthest_data = find_longest_path_networkx(tree)
        node1, node2, path_ids = furthest_data
        
        # Find the midpoint
        clade1, clade2, fraction = get_safe_midpoint(tree, node1, node2, path_ids)
        
        # Make a new copy of the tree for rooting
        rooted_tree = copy.deepcopy(tree)
        
        # Root between the nodes that contain the midpoint
        if fraction < 0.1:
            # If midpoint is very close to clade1, root with clade1 as outgroup
            rooted_tree.root_with_outgroup(clade1)
        elif fraction > 0.9:
            # If midpoint is very close to clade2, root with clade2 as outgroup
            rooted_tree.root_with_outgroup(clade2)
        else:
            # Root on the branch between clade1 and clade2
            # First, find their most recent common ancestor
            mrca = rooted_tree.common_ancestor([c.name for c in [clade1, clade2] if c.name])
            
            if mrca:
                # Root with the MRCA as outgroup, which effectively puts the root on one of the branches
                rooted_tree.root_with_outgroup(mrca)
            else:
                # Fallback - just root with one of the clades
                rooted_tree.root_with_outgroup(clade1)
        
        return rooted_tree

def main():
    parser = argparse.ArgumentParser(description='Root a phylogenetic tree at the midpoint of the longest path between any two leaves.')
    parser.add_argument('input_file', help='Input Newick tree file')
    parser.add_argument('output_file', help='Output Newick tree file')
    parser.add_argument('--format', default='newick', choices=['newick', 'nexus', 'phyloxml', 'nexml'],
                        help='Format of the input/output files (default: newick)')
    parser.add_argument('--force-custom', action='store_true',
                        help='Force using custom midpoint rooting method instead of BioPython\'s')
    
    args = parser.parse_args()
    
    try:
        # Read the tree
        tree = Phylo.read(args.input_file, args.format)
        
        # Root the tree at the midpoint
        if args.force_custom:
            rooted_tree = custom_midpoint_root(tree)
        else:
            try:
                # Try BioPython's built-in method first
                rooted_tree = copy.deepcopy(tree)
                rooted_tree.root_at_midpoint()
            except Exception as e:
                print(f"Built-in midpoint rooting failed ({str(e)}), falling back to custom method.")
                rooted_tree = custom_midpoint_root(tree)
        
        # Write the rooted tree
        Phylo.write(rooted_tree, args.output_file, args.format)
        print(f"Midpoint rooted tree written to {args.output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
