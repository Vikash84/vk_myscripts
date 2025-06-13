#!/usr/bin/env python3

import argparse
import sys
import pandas as pd
import os

def read_table(file_path, id_col=0, header=True, sep='\t'):
    """
    Read a table file into a pandas DataFrame.
    
    Args:
        file_path (str): Path to the table file
        id_col (int or str): Index or name of the column to use as row IDs
        header (bool): Whether the file has a header row
        sep (str): Column separator in the file
    
    Returns:
        pandas.DataFrame: The loaded DataFrame
    """
    try:
        # Determine header setting for pandas
        header_setting = 0 if header else None
        
        # Read the table
        df = pd.read_csv(file_path, sep=sep, header=header_setting)
        
        # Set the ID column as index
        if header:
            if isinstance(id_col, int):
                # If id_col is an integer and header=True, get the column name
                id_col_name = df.columns[id_col]
                df = df.set_index(id_col_name)
            else:
                # If id_col is a string (column name)
                df = df.set_index(id_col)
        else:
            # If no header, use the column position directly
            df = df.set_index(df.columns[id_col])
        
        return df
        
    except FileNotFoundError:
        print(f"Error: Table file not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading table file {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

def merge_tables(table_files, id_file=None, id_col=0, header=True, sep='\t', join_type='outer', 
                output_file=None, keep_id_order=True):
    """
    Merge multiple tables based on row IDs.
    
    Args:
        table_files (list): List of paths to table files
        id_file (str): Optional file with IDs in desired order
        id_col (int or str): Index or name of the column to use as row IDs
        header (bool): Whether the files have header rows
        sep (str): Column separator in the files
        join_type (str): Type of join to perform ('inner', 'outer', 'left')
        output_file (str): Path to the output file (None for stdout)
        keep_id_order (bool): Whether to maintain order of IDs from id_file
    
    Returns:
        pandas.DataFrame: The merged DataFrame
    """
    if not table_files:
        print("Error: No table files provided", file=sys.stderr)
        sys.exit(1)
    
    # Read the first table
    print(f"Reading table file: {table_files[0]}", file=sys.stderr)
    merged_df = read_table(table_files[0], id_col, header, sep)
    
    # Add file name as suffix to column names if they don't already have file-specific names
    file_name = os.path.basename(table_files[0])
    if header:
        merged_df.columns = [f"{col}_{file_name}" for col in merged_df.columns]
    
    # Merge with the rest of the tables
    for file_path in table_files[1:]:
        print(f"Reading table file: {file_path}", file=sys.stderr)
        df = read_table(file_path, id_col, header, sep)
        
        # Add file name as suffix to column names
        file_name = os.path.basename(file_path)
        if header:
            df.columns = [f"{col}_{file_name}" for col in df.columns]
        
        # Merge with the accumulated result
        merged_df = merged_df.join(df, how=join_type)
    
    # If an ID file is provided, filter and order rows accordingly
    if id_file:
        print(f"Reading ID file: {id_file}", file=sys.stderr)
        try:
            with open(id_file, 'r') as f:
                ids = [line.strip() for line in f if line.strip()]
            
            # Filter rows to keep only those in the ID list
            merged_df = merged_df.loc[merged_df.index.isin(ids)]
            
            # Reorder rows to match the order in the ID file
            if keep_id_order:
                # Create a new dataframe with the IDs in the right order
                ordered_df = pd.DataFrame(index=ids)
                # Join with the merged data
                merged_df = ordered_df.join(merged_df, how='left')
                
        except FileNotFoundError:
            print(f"Error: ID file not found: {id_file}", file=sys.stderr)
            sys.exit(1)
    
    # Write the merged table to output
    output = sys.stdout if output_file is None else open(output_file, 'w')
    try:
        merged_df.to_csv(output, sep=sep, na_rep='NA')
    finally:
        if output is not sys.stdout:
            output.close()
    
    # Print summary
    print(f"\nMerge summary:", file=sys.stderr)
    print(f"Tables merged: {len(table_files)}", file=sys.stderr)
    print(f"Total rows: {merged_df.shape[0]}", file=sys.stderr)
    print(f"Total columns: {merged_df.shape[1]}", file=sys.stderr)
    
    # Check for missing values
    missing_values = merged_df.isna().sum().sum()
    if missing_values > 0:
        print(f"Missing values: {missing_values} (filled with 'NA' in output)", file=sys.stderr)
    
    if output_file:
        print(f"Merged table saved to {output_file}", file=sys.stderr)
    
    return merged_df

def main():
    parser = argparse.ArgumentParser(description='Merge multiple tables based on row IDs')
    parser.add_argument('-t', '--tables', required=True, nargs='+', 
                        help='List of table files to merge')
    parser.add_argument('-i', '--ids', help='Optional file with IDs in desired order')
    parser.add_argument('-c', '--id-column', default=0, 
                        help='Index or name of the column with row IDs (default: 0)')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    parser.add_argument('--no-header', action='store_false', dest='header',
                        help='Specify if input files have no header row')
    parser.add_argument('-s', '--separator', default='\t',
                        help='Column separator in files (default: tab)')
    parser.add_argument('-j', '--join', choices=['inner', 'outer', 'left'], default='outer',
                        help='Type of join to perform (default: outer)')
    parser.add_argument('--no-order', action='store_false', dest='keep_order',
                        help='Do not maintain order of IDs from id file')
    
    args = parser.parse_args()
    
    # Try to convert id_column to int if it's numeric
    try:
        id_col = int(args.id_column)
    except ValueError:
        id_col = args.id_column
    
    # Merge tables
    merge_tables(
        args.tables,
        id_file=args.ids,
        id_col=id_col,
        header=args.header,
        sep=args.separator,
        join_type=args.join,
        output_file=args.output,
        keep_id_order=args.keep_order
    )

if __name__ == "__main__":
    main()
