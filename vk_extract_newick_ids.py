#!/usr/bin/env python3

import argparse
import sys
import re

def extract_ids_from_newick(newick_file, output_file=None):
    """
    Extract all IDs (leaf names) from a Newick format tree file.
    
    Args:
        newick_file (str): Path to the input Newick tree file
        output_file (str): Path to the output file (None for stdout)
    
    Returns:
        list: List of extracted IDs
    """
    try:
        # Read the Newick tree string
        with open(newick_file, 'r') as f:
            newick_str = f.read().strip()
        
        # Remove any newlines or extra whitespace
        newick_str = re.sub(r'\s+', '', newick_str)
        
        # Extract all labels from the Newick string
        # This regex matches:
        # 1. Labels that are not followed by : (no branch length)
        # 2. Labels that are followed by : and a number (with branch length)
        # But excludes capturing internal node labels if they exist
        ids = []
        
        # Basic pattern: find words that are followed by a colon and number, or words/numbers before commas and parentheses
        pattern = r'([^,():;\[\]]+)(?:\:[\d.eE+-]+)?(?=[,);])'
        
        # Find all matches
        for match in re.finditer(pattern, newick_str):
            label = match.group(1)
            # Skip bootstrap values (usually just numbers)
            if not label.replace('.', '').isdigit():  # Allow for decimal points in numbers
                ids.append(label)
        
        # Write IDs to output
        output = sys.stdout if output_file is None else open(output_file, 'w')
        try:
            for id in ids:
                print(id, file=output)
        finally:
            if output is not sys.stdout:
                output.close()
        
        return ids
    
    except FileNotFoundError:
        print(f"Error: Newick file not found: {newick_file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing Newick file: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Extract all IDs (leaf names) from a Newick format tree file')
    parser.add_argument('-i', '--input', required=True, help='Input Newick tree file')
    parser.add_argument('-o', '--output', help='Output file with extracted IDs (default: stdout)')
    
    args = parser.parse_args()
    
    ids = extract_ids_from_newick(args.input, args.output)
    
    print(f"Extracted {len(ids)} IDs from the Newick file", file=sys.stderr)
    if args.output:
        print(f"IDs saved to {args.output}", file=sys.stderr)

if __name__ == "__main__":
    main()
