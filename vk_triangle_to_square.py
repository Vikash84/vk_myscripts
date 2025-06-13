#!/usr/bin/env python3

import argparse
import sys
import pandas as pd
import numpy as np

def read_triangle_matrix(file_path, sep='\t', header=True, index_col=0):
    """
    Read a triangular matrix from a file.
    
    Args:
        file_path (str): Path to the input file
        sep (str): Column separator in the file
        header (bool): Whether the file has a header row
        index_col (int): Index of the column to use as row labels
    
    Returns:
        pandas.DataFrame: The loaded triangular matrix
    """
    try:
        # Set header parameter for pd.read_csv
        header_param = 0 if header else None
        
        # Read the matrix
        df = pd.read_csv(file_path, sep=sep, header=header_param, index_col=index_col)
        
        return df
        
    except FileNotFoundError:
        print(f"Error: Input file not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

def is_lower_triangle(df):
    """
    Determine if the matrix is lower triangular.
    
    Args:
        df (pandas.DataFrame): Input triangular matrix
    
    Returns:
        bool: True if lower triangular, False if upper triangular
    """
    # First, check if we can convert to numeric
    numeric_df = df.apply(pd.to_numeric, errors='coerce')
    
    # Count empty/NA values in lower and upper triangles
    # We treat empty strings, '0', and NaN all as potentially missing values
    lower_missing = 0
    upper_missing = 0
    
    n = len(df)
    for i in range(n):
        for j in range(n):
            val = df.iloc[i, j]
            is_empty = pd.isna(val) or val == '' or val == '0'
            
            if i > j:  # Lower triangle
                if is_empty:
                    lower_missing += 1
            elif i < j:  # Upper triangle
                if is_empty:
                    upper_missing += 1
    
    # If more missing values in upper triangle, it's likely a lower triangular matrix
    if upper_missing > lower_missing:
        return True
    else:
        return False

def triangle_to_square(df, lower=None, diagonal=None):
    """
    Convert a triangular matrix to a square matrix.
    
    Args:
        df (pandas.DataFrame): Input triangular matrix
        lower (bool): If True, assume input is lower triangular; if False, assume upper triangular; 
                     if None, auto-detect
        diagonal (float or None): Value to use for diagonal if missing
    
    Returns:
        pandas.DataFrame: Complete square matrix
    """
    # Create a copy to avoid modifying the original
    matrix = df.copy()
    
    # Ensure row and column labels match
    if not all(matrix.index == matrix.columns):
        # Use union of row and column labels
        all_labels = sorted(set(matrix.index) | set(matrix.columns))
        
        # Reindex to include all labels
        matrix = matrix.reindex(index=all_labels, columns=all_labels)
    
    # Auto-detect if it's a lower or upper triangular matrix
    if lower is None:
        lower = is_lower_triangle(matrix)
        print(f"Auto-detected matrix type: {'Lower' if lower else 'Upper'} triangular", file=sys.stderr)
    
    # Fill in the missing triangle
    square_matrix = matrix.copy()
    n = len(square_matrix)
    
    for i in range(n):
        for j in range(n):
            if i != j:  # Skip diagonal
                if lower and i < j:  # Upper triangle needs to be filled from lower
                    square_matrix.iloc[i, j] = matrix.iloc[j, i]
                elif not lower and i > j:  # Lower triangle needs to be filled from upper
                    square_matrix.iloc[i, j] = matrix.iloc[j, i]
    
    # Fill diagonal if specified
    if diagonal is not None:
        for i in range(n):
            square_matrix.iloc[i, i] = diagonal
    
    return square_matrix

def main():
    parser = argparse.ArgumentParser(description='Convert a triangular matrix to a square matrix')
    parser.add_argument('-i', '--input', required=True, help='Input file containing triangular matrix')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    parser.add_argument('-s', '--separator', default='\t', help='Column separator in files (default: tab)')
    parser.add_argument('--no-header', action='store_false', dest='header',
                      help='Specify if input file has no header row')
    parser.add_argument('--lower', action='store_true', help='Force input to be treated as lower triangular')
    parser.add_argument('--upper', action='store_true', help='Force input to be treated as upper triangular')
    parser.add_argument('-d', '--diagonal', type=float, help='Value to set for diagonal elements')
    parser.add_argument('--index-col', type=int, default=0, 
                      help='Column to use as row labels (default: 0)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.lower and args.upper:
        print("Error: Cannot specify both --lower and --upper", file=sys.stderr)
        sys.exit(1)
    
    # Determine triangle type
    lower = None
    if args.lower:
        lower = True
    elif args.upper:
        lower = False
    
    # Read triangular matrix
    print(f"Reading triangular matrix from {args.input}", file=sys.stderr)
    tri_matrix = read_triangle_matrix(
        args.input, 
        sep=args.separator, 
        header=args.header,
        index_col=args.index_col
    )
    
    # Convert to square matrix
    print("Converting to square matrix", file=sys.stderr)
    square_matrix = triangle_to_square(tri_matrix, lower=lower, diagonal=args.diagonal)
    
    # Write square matrix to output
    output = sys.stdout if args.output is None else open(args.output, 'w')
    try:
        square_matrix.to_csv(output, sep=args.separator, na_rep='NA')
    finally:
        if output is not sys.stdout:
            output.close()
    
    # Print summary
    print(f"\nConversion summary:", file=sys.stderr)
    print(f"Matrix dimensions: {square_matrix.shape[0]} x {square_matrix.shape[1]}", file=sys.stderr)
    print(f"Matrix type used: {'Lower' if lower else 'Upper'} triangular", file=sys.stderr)
    
    if args.output:
        print(f"Square matrix saved to {args.output}", file=sys.stderr)

if __name__ == "__main__":
    main()
