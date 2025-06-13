#!/usr/bin/env python3
"""
MLST Analysis Script - Modernized Version

This script performs Multi-Locus Sequence Typing (MLST) analysis following the
protocol described in Larsen et al. (2012) J Clin Microbiol 50: 1355-1361.

Takes PubMLST profile tables and corresponding MLST sequences in FASTA format
to assign sequence types to input genome sequences.

License: MIT
"""

import argparse
import csv
import logging
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
from Bio import SeqIO


class MLSTAnalyzer:
    """Main class for MLST analysis operations."""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Configure logging with appropriate handlers and formatters."""
        logger = logging.getLogger('MLST_Analyzer')
        logger.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(formatter)
        
        if self.args.verbose:
            console_handler.setLevel(logging.INFO)
        else:
            console_handler.setLevel(logging.WARNING)
        
        logger.addHandler(console_handler)
        
        # File handler if specified
        if self.args.logfile:
            try:
                file_handler = logging.FileHandler(self.args.logfile, 'w')
                file_handler.setFormatter(formatter)
                file_handler.setLevel(logging.INFO)
                logger.addHandler(file_handler)
            except Exception as e:
                logger.error(f"Could not open {self.args.logfile} for logging: {e}")
                sys.exit(1)
        
        return logger
    
    def run_analysis(self) -> None:
        """Execute the complete MLST analysis workflow."""
        self.logger.info('# MLST Analysis Started')
        self.logger.info(f'# Run: {time.asctime()}')
        self.logger.info(f'Arguments: {self.args}')
        
        # Validate required arguments
        self._validate_arguments()
        
        # Load input data
        alleles = self._load_alleles()
        genomes = self._load_genomes()
        
        # Create output directory
        self._create_output_directory()
        
        # Run BLAST analysis
        blast_results = self._run_blast_analysis(alleles, genomes)
        
        # Process results
        results_df = self._process_blast_results(alleles, genomes, blast_results)
        results_df = self._assign_sequence_types(results_df)
        
        # Write output
        self._write_results(results_df)
        
        self.logger.info('Analysis completed successfully')
    
    def _validate_arguments(self) -> None:
        """Validate required command line arguments."""
        required_args = [
            (self.args.indirname, "input directory"),
            (self.args.outdirname, "output directory"),
            (self.args.profile, "MLST profile"),
            (self.args.genomedir, "genome directory")
        ]
        
        for arg_value, arg_name in required_args:
            if not arg_value:
                self.logger.error(f"No {arg_name} specified")
                sys.exit(1)
            self.logger.info(f"{arg_name.title()}: {arg_value}")
    
    def _load_alleles(self) -> Dict[str, Tuple[str, int]]:
        """Load allele sequences from FASTA files."""
        self.logger.info(f"Processing allele directory: {self.args.indirname}")
        
        try:
            fasta_files = self._get_fasta_files(self.args.indirname)
        except Exception as e:
            self.logger.error(f"Could not identify FASTA files in {self.args.indirname}: {e}")
            sys.exit(1)
        
        alleles = {}
        for filepath in fasta_files:
            try:
                sequences = list(SeqIO.parse(filepath, 'fasta'))
                if not sequences:
                    continue
                    
                gene_name = sequences[0].id.split('_')[0]
                alleles[gene_name] = (str(filepath), len(sequences))
                self.logger.info(f"Loaded {len(sequences)} alleles for {gene_name} from {filepath.name}")
                
            except Exception as e:
                self.logger.error(f"Could not process FASTA file {filepath}: {e}")
                sys.exit(1)
        
        self.logger.info(f"Found sequences for {len(alleles)} MLST genes")
        return alleles
    
    def _load_genomes(self) -> Dict[str, str]:
        """Load genome sequences from FASTA files."""
        self.logger.info(f"Processing genome directory: {self.args.genomedir}")
        
        try:
            fasta_files = self._get_fasta_files(self.args.genomedir)
        except Exception as e:
            self.logger.error(f"Could not identify FASTA files in {self.args.genomedir}: {e}")
            sys.exit(1)
        
        genomes = {}
        for filepath in fasta_files:
            try:
                sequences = list(SeqIO.parse(filepath, 'fasta'))
                if not sequences:
                    continue
                    
                # Use filename as identifier, removing problematic characters
                isolate_id = filepath.stem.replace("|", "_").replace(" ", "_")
                genomes[isolate_id] = str(filepath)
                self.logger.info(f"Loaded genome {isolate_id} from {filepath.name}")
                
            except Exception as e:
                self.logger.error(f"Could not process genome file {filepath}: {e}")
                sys.exit(1)
        
        self.logger.info(f"Found {len(genomes)} genome sequences")
        return genomes
    
    def _get_fasta_files(self, directory: str) -> List[Path]:
        """Get all FASTA files from a directory."""
        directory_path = Path(directory)
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory {directory} does not exist")
        
        extensions = {'.fasta', '.fas', '.fna', '.fa'}
        fasta_files = []
        
        for file_path in directory_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                fasta_files.append(file_path)
        
        return fasta_files
    
    def _create_output_directory(self) -> None:
        """Create output directory, handling existing directories."""
        output_path = Path(self.args.outdirname)
        
        if output_path.exists():
            if not self.args.force:
                self.logger.error(f"Output directory {output_path} exists. Use --force to overwrite")
                sys.exit(1)
            else:
                self.logger.info(f"Removing existing directory: {output_path}")
                shutil.rmtree(output_path)
        
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created output directory: {output_path}")
        except Exception as e:
            self.logger.error(f"Could not create output directory: {e}")
            sys.exit(1)
    
    def _run_blast_analysis(self, alleles: Dict, genomes: Dict) -> Dict[Tuple[str, str], str]:
        """Run BLAST analysis for all allele-genome combinations."""
        self.logger.info("Running BLAST analysis to identify alleles in genomes")
        
        commands = []
        output_files = {}
        
        for allele_name, (allele_file, _) in alleles.items():
            for genome_id, genome_file in genomes.items():
                output_file = Path(self.args.outdirname) / f"{allele_name}_vs_{genome_id}.tab"
                command = self._create_blast_command(
                    allele_file, genome_file, str(output_file)
                )
                commands.append(command)
                output_files[(genome_id, allele_name)] = str(output_file)
        
        self.logger.info(f"Generated {len(commands)} BLAST commands")
        self._run_parallel_commands(commands)
        
        return output_files
    
    def _create_blast_command(self, query_file: str, subject_file: str, output_file: str) -> str:
        """Create a BLAST command line."""
        cmd = (f"{self.args.blast_exe} -query {query_file} -subject {subject_file} "
               f"-out {output_file} "
               f"-outfmt '6 qseqid sseqid pident qlen length gaps mismatch'")
        return cmd
    
    def _run_parallel_commands(self, commands: List[str]) -> None:
        """Execute commands in parallel using multiprocessing."""
        self.logger.info(f"Running {len(commands)} jobs with multiprocessing")
        
        with mp.Pool() as pool:
            results = []
            for cmd in commands:
                result = pool.apply_async(
                    subprocess.run,
                    (cmd,),
                    {'shell': True, 'capture_output': True, 'text': True}
                )
                results.append(result)
            
            # Wait for all jobs to complete
            for i, result in enumerate(results):
                try:
                    completed_process = result.get()
                    if completed_process.returncode != 0:
                        self.logger.warning(f"Command {i+1} failed: {completed_process.stderr}")
                    elif self.args.verbose:
                        self.logger.info(f"Command {i+1} completed successfully")
                except Exception as e:
                    self.logger.error(f"Error in command {i+1}: {e}")
        
        self.logger.info("All BLAST jobs completed")
    
    def _process_blast_results(self, alleles: Dict, genomes: Dict, 
                             blast_files: Dict) -> pd.DataFrame:
        """Process BLAST results and assign alleles to genomes."""
        # Create results dataframe
        columns = list(alleles.keys()) + ['ST']
        df = pd.DataFrame(index=list(genomes.keys()), columns=columns)
        
        # Process each BLAST result file
        for (genome_id, allele_name), blast_file in blast_files.items():
            best_allele = self._find_best_allele(blast_file)
            if best_allele is not None:
                df.loc[genome_id, allele_name] = int(best_allele)
            else:
                df.loc[genome_id, allele_name] = None
        
        return df
    
    def _find_best_allele(self, blast_file: str) -> Optional[str]:
        """Find the best matching allele based on Larsen et al. (2012) criteria."""
        if not Path(blast_file).exists():
            return None
        
        try:
            with open(blast_file, 'r') as f:
                reader = csv.DictReader(
                    f, delimiter='\t',
                    fieldnames=['qseqid', 'sseqid', 'pident', 'qlen', 
                               'length', 'gaps', 'mismatch']
                )
                
                best_by_ls = None
                best_by_pident = None
                
                for row in reader:
                    allele_num = row['qseqid'].split('_')[-1]
                    
                    # Calculate Length Score (LS)
                    ls = int(row['qlen']) - int(row['length']) + int(row['gaps'])
                    pident = float(row['pident'])
                    
                    # Track best by percentage identity
                    if best_by_pident is None or pident > best_by_pident[1]:
                        best_by_pident = (ls, pident, allele_num)
                    
                    # Track best by LS (lower is better), with pident as tiebreaker
                    if (best_by_ls is None or 
                        ls < best_by_ls[0] or 
                        (ls == best_by_ls[0] and pident > best_by_ls[1])):
                        best_by_ls = (ls, pident, allele_num)
                
                if best_by_ls and best_by_pident:
                    if best_by_ls[2] != best_by_pident[2]:
                        self.logger.warning(
                            f"{blast_file}: Different alleles identified by LS and %ID"
                        )
                        self.logger.warning(f"Best LS: {best_by_ls}")
                        self.logger.warning(f"Best %ID: {best_by_pident}")
                    
                    return best_by_ls[2]
                
        except Exception as e:
            self.logger.error(f"Error processing {blast_file}: {e}")
        
        return None
    
    def _assign_sequence_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Assign sequence types based on allele profiles."""
        self.logger.info("Assigning sequence types to isolates")
        
        genes, profiles = self._load_mlst_profiles()
        
        for isolate_id, row in df.iterrows():
            # Create allele profile string
            allele_profile = ','.join([str(row[gene]) if pd.notna(row[gene]) else 'NA' 
                                     for gene in genes])
            
            self.logger.info(f"Isolate {isolate_id}: alleles {allele_profile}")
            
            # Look up sequence type
            if allele_profile in profiles:
                st = profiles[allele_profile]
                df.loc[isolate_id, 'ST'] = int(st)
                self.logger.info(f"Assigned ST: {st}")
            else:
                df.loc[isolate_id, 'ST'] = 'NEW'
                self.logger.warning(f"Profile {allele_profile} not found - assigning NEW")
        
        # Sort by gene columns for grouping
        return df.sort_values(list(genes))
    
    def _load_mlst_profiles(self) -> Tuple[List[str], Dict[str, str]]:
        """Load MLST profile data from file."""
        self.logger.info(f"Loading MLST profiles from {self.args.profile}")
        
        profiles = {}
        genes = None
        
        try:
            with open(self.args.profile, 'r') as f:
                reader = csv.DictReader(f, delimiter='\t')
                
                for row in reader:
                    if genes is None:
                        # Extract gene names (exclude ST and clonal_complex)
                        genes = sorted([k for k in row.keys() 
                                      if k not in ('ST', 'clonal_complex')])
                        self.logger.info(f"Gene order: {genes}")
                    
                    # Create allele profile key
                    allele_profile = ','.join([str(row[gene]) for gene in genes])
                    profiles[allele_profile] = row['ST']
            
            self.logger.info(f"Loaded {len(profiles)} MLST profiles")
            
        except Exception as e:
            self.logger.error(f"Error loading MLST profiles: {e}")
            sys.exit(1)
        
        return genes, profiles
    
    def _write_results(self, df: pd.DataFrame) -> None:
        """Write results in specified output formats."""
        output_formats = [fmt.lower().strip() for fmt in self.args.formats.split(',')]
        output_dir = Path(self.args.outdirname)
        
        for fmt in output_formats:
            output_file = output_dir / f"MLST_results.{fmt}"
            
            try:
                if fmt == 'csv':
                    df.to_csv(output_file)
                elif fmt in ('tab', 'tsv'):
                    df.to_csv(output_file, sep='\t')
                elif fmt in ('excel', 'xlsx', 'xls'):
                    df.to_excel(output_file.with_suffix('.xlsx'))
                else:
                    self.logger.warning(f"Unknown output format: {fmt}")
                    continue
                
                self.logger.info(f"Results written to {output_file}")
                
            except Exception as e:
                self.logger.error(f"Error writing {fmt} output: {e}")
        
        # Also write to stdout
        print("\nMLST Analysis Results:")
        print("=" * 50)
        print(df.to_string())


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MLST Analysis - Assign sequence types to bacterial genomes",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-i", "--indirname", required=True,
        help="Directory containing MLST allele sequence files"
    )
    
    parser.add_argument(
        "-g", "--genomedir", required=True,
        help="Directory containing genome sequence files"
    )
    
    parser.add_argument(
        "-p", "--profile", required=True,
        help="Tab-separated MLST profile table"
    )
    
    parser.add_argument(
        "-o", "--outdir", dest="outdirname", required=True,
        help="Output directory for results"
    )
    
    parser.add_argument(
        "-l", "--logfile",
        help="Log file location"
    )
    
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "-f", "--force", action="store_true",
        help="Force overwrite of existing output directory"
    )
    
    parser.add_argument(
        "--blast_exe", default="blastn",
        help="Path to BLASTN executable"
    )
    
    parser.add_argument(
        "--formats", default="csv,tab",
        help="Comma-separated list of output formats (csv,tab,excel)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    try:
        args = parse_arguments()
        analyzer = MLSTAnalyzer(args)
        analyzer.run_analysis()
        
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
