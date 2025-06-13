#!/usr/bin/env python3

import argparse
from Bio import SeqIO

def filter_fasta_by_length(input_file, output_file, min_length=0, max_length=None):
    """
    Filter sequences in a FASTA file based on length criteria.
    
    Parameters:
    - input_file: Path to input FASTA file
    - output_file: Path to output FASTA file
    - min_length: Minimum sequence length (inclusive)
    - max_length: Maximum sequence length (inclusive), if None, no upper limit
    
    Returns:
    - count_total: Total number of sequences in input file
    - count_kept: Number of sequences that passed the filter
    """
    count_total = 0
    count_kept = 0
    
    # Open output file for writing
    with open(output_file, 'w') as out_handle:
        # Parse input FASTA file using BioPython
        for record in SeqIO.parse(input_file, "fasta"):
            count_total += 1
            seq_length = len(record.seq)
            
            # Check if sequence meets length criteria
            if max_length is None:
                # Only apply minimum length filter
                if seq_length >= min_length:
                    SeqIO.write(record, out_handle, "fasta")
                    count_kept += 1
            else:
                # Apply both min and max filters
                if min_length <= seq_length <= max_length:
                    SeqIO.write(record, out_handle, "fasta")
                    count_kept += 1
                
    return count_total, count_kept

def main():
    parser = argparse.ArgumentParser(description='Filter FASTA sequences by length')
    parser.add_argument('-i', '--input', required=True, help='Input FASTA file')
    parser.add_argument('-o', '--output', required=True, help='Output FASTA file')
    parser.add_argument('-min', '--min_length', type=int, default=0, help='Minimum sequence length (default: 0)')
    parser.add_argument('-max', '--max_length', type=int, default=None, help='Maximum sequence length (default: no limit)')
    
    args = parser.parse_args()
    
    total, kept = filter_fasta_by_length(
        args.input, 
        args.output, 
        args.min_length, 
        args.max_length
    )
    
    print(f"Total sequences: {total}")
    print(f"Sequences kept: {kept} ({kept/total*100:.2f}% of total)")
    print(f"Sequences filtered out: {total - kept} ({(total-kept)/total*100:.2f}% of total)")

if __name__ == "__main__":
    main()
