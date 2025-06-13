#!/usr/bin/env python3

import argparse
import sys

def convert_multiline_to_singleline(input_file, output_file=None):
    """
    Convert a multiline FASTA file to single-line FASTA format.
    
    Args:
        input_file (str): Path to the input multiline FASTA file
        output_file (str): Path to the output single-line FASTA file (None for stdout)
    """
    output = sys.stdout if output_file is None else open(output_file, 'w')
    
    try:
        current_header = None
        current_sequence = []
        
        with open(input_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('>'):
                    # Output the previous sequence if there was one
                    if current_header:
                        print(current_header, file=output)
                        print(''.join(current_sequence), file=output)
                    
                    # Start a new sequence
                    current_header = line
                    current_sequence = []
                else:
                    # Add line to the current sequence
                    current_sequence.append(line)
            
            # Output the last sequence
            if current_header:
                print(current_header, file=output)
                print(''.join(current_sequence), file=output)
    
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)
    finally:
        if output is not sys.stdout:
            output.close()

def main():
    parser = argparse.ArgumentParser(description='Convert multiline FASTA to single-line FASTA format')
    parser.add_argument('-i', '--input', required=True, help='Input multiline FASTA file')
    parser.add_argument('-o', '--output', help='Output single-line FASTA file (default: stdout)')
    
    args = parser.parse_args()
    
    convert_multiline_to_singleline(args.input, args.output)
    
    if args.output:
        print(f"Converted FASTA saved to {args.output}", file=sys.stderr)

if __name__ == "__main__":
    main()
