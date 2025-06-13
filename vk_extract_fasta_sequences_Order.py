#!/usr/bin/env python3

import argparse
import sys
from collections import OrderedDict

def parse_id_file(id_file_path):
    """
    Parse file containing sequence IDs.
    Returns a list of IDs in the order they appear in the file.
    """
    ids = []
    try:
        with open(id_file_path, 'r') as id_file:
            for line in id_file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                # If the line has multiple columns (e.g., tab-delimited), use only the first column as ID
                seq_id = line.split()[0]
                ids.append(seq_id)
        
        return ids
    except FileNotFoundError:
        print(f"Error: ID file not found: {id_file_path}", file=sys.stderr)
        sys.exit(1)

def load_fasta_sequences(fasta_file_path):
    """
    Load all sequences from a FASTA file into a dictionary.
    Returns a dictionary mapping sequence IDs to sequences.
    """
    sequences = {}
    current_id = None
    current_seq = []
    
    try:
        with open(fasta_file_path, 'r') as fasta_file:
            for line in fasta_file:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('>'):
                    # Save the previous sequence if there was one
                    if current_id:
                        sequences[current_id] = ''.join(current_seq)
                    
                    # Start a new sequence
                    header = line[1:]  # Remove the '>' character
                    current_id = header.split()[0]  # Use the first word as ID
                    current_seq = []
                else:
                    # Append sequence line
                    current_seq.append(line)
            
            # Save the last sequence
            if current_id:
                sequences[current_id] = ''.join(current_seq)
                
        return sequences
    except FileNotFoundError:
        print(f"Error: FASTA file not found: {fasta_file_path}", file=sys.stderr)
        sys.exit(1)

def extract_sequences(sequences, ids, include_description=False, output_file_path=None, missing_action='warn'):
    """
    Extract sequences in the order specified by the IDs list.
    
    Args:
        sequences (dict): Dictionary mapping sequence IDs to sequences
        ids (list): List of sequence IDs in the desired order
        include_description (bool): Whether to include the full description in the header
        output_file_path (str): Path to the output file (None for stdout)
        missing_action (str): Action to take when ID is not found ('warn', 'error', or 'skip')
    """
    output = sys.stdout if output_file_path is None else open(output_file_path, 'w')
    missing_ids = []
    extracted_count = 0
    
    try:
        for seq_id in ids:
            if seq_id in sequences:
                # Find the full header if include_description is True
                full_header = None
                if include_description:
                    for header in sequences.keys():
                        if header.split()[0] == seq_id:
                            full_header = header
                            break
                
                # Write the sequence
                if include_description and full_header:
                    print(f">{full_header}", file=output)
                else:
                    print(f">{seq_id}", file=output)
                
                # Format sequence to have line breaks every 60 characters
                seq = sequences[seq_id]
                for i in range(0, len(seq), 60):
                    print(seq[i:i+60], file=output)
                
                extracted_count += 1
            else:
                missing_ids.append(seq_id)
                if missing_action == 'error':
                    print(f"Error: Sequence ID '{seq_id}' not found in FASTA file", file=sys.stderr)
                    sys.exit(1)
                elif missing_action == 'warn':
                    print(f"Warning: Sequence ID '{seq_id}' not found in FASTA file", file=sys.stderr)
    
    finally:
        if output is not sys.stdout:
            output.close()
    
    # Report statistics
    print(f"Total IDs in list: {len(ids)}", file=sys.stderr)
    print(f"Sequences extracted: {extracted_count}", file=sys.stderr)
    print(f"Missing sequences: {len(missing_ids)}", file=sys.stderr)
    
    if missing_ids and missing_action != 'skip':
        print("Missing IDs:", file=sys.stderr)
        for missing_id in missing_ids[:10]:  # Show only the first 10 missing IDs
            print(f"  {missing_id}", file=sys.stderr)
        if len(missing_ids) > 10:
            print(f"  ... and {len(missing_ids) - 10} more", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description='Extract FASTA sequences in the order specified by an ID file')
    parser.add_argument('-f', '--fasta', required=True, help='Input FASTA file')
    parser.add_argument('-i', '--ids', required=True, help='File containing sequence IDs (one per line)')
    parser.add_argument('-o', '--output', help='Output FASTA file (default: stdout)')
    parser.add_argument('-d', '--description', action='store_true', 
                        help='Include full description in headers (default: use only ID)')
    parser.add_argument('-m', '--missing', choices=['warn', 'error', 'skip'], default='warn',
                        help='Action when ID not found (default: warn)')
    
    args = parser.parse_args()
    
    # Parse the ID file
    ids = parse_id_file(args.ids)
    
    # Load sequences from FASTA file
    sequences = load_fasta_sequences(args.fasta)
    
    # Extract and write sequences in order
    extract_sequences(
        sequences, 
        ids, 
        include_description=args.description,
        output_file_path=args.output,
        missing_action=args.missing
    )
    
    if args.output:
        print(f"Extracted sequences saved to {args.output}", file=sys.stderr)

if __name__ == "__main__":
    main()
