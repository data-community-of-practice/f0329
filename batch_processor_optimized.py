#!/usr/bin/env python3
"""
Batch Processing Grant-Publication Mapper with Rate Limit Handling

This script processes publications in batches, handles 429 errors gracefully,
and can resume from where it left off.

Features:
- Optimized pre-filtering to minimize API calls
- Automatic batch processing with progress tracking
- Resume capability from partial results
- Detailed progress reporting
- Robust error handling for rate limits

Author: Claude Code Assistant
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import re
from typing import List, Tuple, Dict, Optional
import time
import json
from dataclasses import dataclass
import configparser
import os
from pathlib import Path

@dataclass
class MatchResult:
    """Data class to store matching results"""
    grant_title: str
    grant_doi: str
    confidence: str
    reasoning: str

@dataclass
class CandidateGrant:
    """Data class for candidate grants that passed initial filtering"""
    grant_idx: int
    grant_data: pd.Series
    investigator_matches: List[str]
    temporal_score: float

@dataclass
class ProcessingProgress:
    """Data class to track processing progress"""
    total_publications: int
    processed_count: int
    mapped_count: int
    batch_number: int
    last_processed_index: int
    api_calls_made: int
    api_calls_failed: int

class BatchProcessor:
    def __init__(self, config_file: str = "config.ini"):
        """Initialize the batch processor"""
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        self.api_url = self.config.get('API', 'base_url')
        self.auth_header = self.config.get('API', 'authorization')
        self.model = self.config.get('API', 'model')
        
        # Processing settings
        self.batch_size = 20  # Process 20 publications at a time
        self.max_candidates_per_pub = 2  # Max candidates to send to LLM
        self.api_delay = 2.0  # Delay between API calls in seconds
        self.retry_delay = 60.0  # Delay after 429 error in seconds
        
        # File paths
        self.progress_file = "processing_progress.json"
        self.results_file = "batch_results.csv"
        self.checkpoint_file = "checkpoint_results.csv"
        
    def load_data(self, grants_file: str, publications_file: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load grants and publications data"""
        print("Loading data files...")
        
        grants_df = pd.read_excel(grants_file)
        publications_df = pd.read_csv(publications_file)
        
        grants_df['Start Date'] = pd.to_datetime(grants_df['Start Date'])
        grants_df['End Date'] = pd.to_datetime(grants_df['End Date'])
        
        print(f"Loaded {len(grants_df)} grants and {len(publications_df)} publications")
        return grants_df, publications_df
    
    def extract_investigators(self, row) -> List[str]:
        """Extract all investigators from a grant row"""
        investigators = []
        
        if pd.notna(row['Preferred Full Name']):
            investigators.append(row['Preferred Full Name'].strip())
        
        if pd.notna(row['Other Investigators']):
            other_invs = str(row['Other Investigators']).split(',')
            investigators.extend([inv.strip() for inv in other_invs])
        
        return investigators
    
    def normalize_name(self, name: str) -> str:
        """Normalize investigator names for better matching"""
        if pd.isna(name):
            return ""
        
        name = str(name).strip().lower()
        name = re.sub(r'\b(dr|prof|professor|phd|md)\b\.?', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def check_name_match(self, author_name: str, investigator_names: List[str]) -> Tuple[bool, str]:
        """Check if an author matches any investigator"""
        author_normalized = self.normalize_name(author_name)
        
        for inv_name in investigator_names:
            inv_normalized = self.normalize_name(inv_name)
            
            author_parts = set(author_normalized.split())
            inv_parts = set(inv_normalized.split())
            
            if author_normalized == inv_normalized:
                return True, inv_name
            
            if len(author_parts) >= 2 and len(inv_parts) >= 2:
                common_parts = len(author_parts & inv_parts)
                if common_parts >= min(2, len(author_parts), len(inv_parts)):
                    return True, inv_name
        
        return False, ""
    
    def calculate_temporal_score(self, publication_year: int, grant_start: datetime, grant_end: datetime) -> float:
        """Calculate temporal alignment score"""
        grant_start_year = grant_start.year
        grant_end_year = (grant_end + timedelta(days=730)).year
        
        if publication_year < grant_start_year or publication_year > grant_end_year:
            return 0.0
        
        if grant_start_year <= publication_year <= grant_end.year:
            return 1.0
        elif grant_end.year < publication_year <= grant_end_year:
            years_after = publication_year - grant_end.year
            return max(0.5, 1.0 - (years_after * 0.25))
        
        return 0.5
    
    def find_candidate_grants(self, publication: pd.Series, grants_df: pd.DataFrame) -> List[CandidateGrant]:
        """Find pre-filtered candidate grants"""
        candidates = []
        authors = str(publication['authors_list']).split(', ')
        pub_year = int(publication['publication_year'])
        
        for grant_idx, grant_row in grants_df.iterrows():
            grant_investigators = self.extract_investigators(grant_row)
            
            # Check investigator matching
            investigator_matches = []
            for author in authors:
                is_match, matched_name = self.check_name_match(author, grant_investigators)
                if is_match:
                    investigator_matches.append(f"{author} -> {matched_name}")
            
            if not investigator_matches:
                continue
                
            # Check temporal alignment
            temporal_score = self.calculate_temporal_score(
                pub_year, grant_row['Start Date'], grant_row['End Date']
            )
            
            if temporal_score == 0:
                continue
            
            candidates.append(CandidateGrant(
                grant_idx=grant_idx,
                grant_data=grant_row,
                investigator_matches=investigator_matches,
                temporal_score=temporal_score
            ))
        
        # Sort by quality score
        candidates.sort(key=lambda x: x.temporal_score * len(x.investigator_matches), reverse=True)
        return candidates[:self.max_candidates_per_pub]  # Limit to top candidates
    
    def analyze_with_api(self, publication: pd.Series, candidate: CandidateGrant) -> Tuple[MatchResult, bool]:
        """
        Analyze using API with focused prompt
        Returns (MatchResult, success_flag)
        """
        
        prompt = f"""
        Assess topical relationship between this grant and publication:

        GRANT: {candidate.grant_data['TITLE']}
        PUBLICATION: {publication['title']}

        Rate topical alignment (investigators/timing already confirmed):
        - Very High: Perfect topic match
        - High: Strong topic overlap  
        - Medium: Moderate connection
        - Low: Minimal alignment
        - Very Low: No clear connection

        JSON response:
        {{
            "confidence": "Very High|High|Medium|Low|Very Low",
            "reasoning": "Brief explanation"
        }}
        """
        
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Assess topical relationships concisely."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 150,
                "stream": False
            }
            
            headers = {
                'accept': 'application/json',
                'authorization': self.auth_header,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                content = response_data['choices'][0]['message']['content'].strip()
                
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result_data = json.loads(json_match.group())
                    return MatchResult(
                        grant_title=candidate.grant_data['TITLE'],
                        grant_doi=str(candidate.grant_data.get('Project Code', 'N/A')),
                        confidence=result_data.get('confidence', 'Low'),
                        reasoning=result_data.get('reasoning', 'Parsed response')
                    ), True
            
            elif response.status_code == 429:
                # Rate limit hit
                return MatchResult(
                    grant_title=candidate.grant_data['TITLE'],
                    grant_doi=str(candidate.grant_data.get('Project Code', 'N/A')),
                    confidence="Low",
                    reasoning="Rate limit exceeded"
                ), False  # Indicates failure due to rate limit
            
            # Other HTTP errors
            return MatchResult(
                grant_title=candidate.grant_data['TITLE'],
                grant_doi=str(candidate.grant_data.get('Project Code', 'N/A')),
                confidence="Low",
                reasoning=f"HTTP {response.status_code} error"
            ), True  # Treat as successful but low confidence
                
        except Exception as e:
            return MatchResult(
                grant_title=candidate.grant_data['TITLE'],
                grant_doi=str(candidate.grant_data.get('Project Code', 'N/A')),
                confidence="Low",
                reasoning=f"Error: {str(e)[:100]}"
            ), True  # Treat as successful but low confidence
    
    def save_progress(self, progress: ProcessingProgress):
        """Save processing progress to file"""
        progress_data = {
            'total_publications': progress.total_publications,
            'processed_count': progress.processed_count,
            'mapped_count': progress.mapped_count,
            'batch_number': progress.batch_number,
            'last_processed_index': progress.last_processed_index,
            'api_calls_made': progress.api_calls_made,
            'api_calls_failed': progress.api_calls_failed,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
    
    def load_progress(self) -> Optional[ProcessingProgress]:
        """Load processing progress from file"""
        if not os.path.exists(self.progress_file):
            return None
        
        try:
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
            
            return ProcessingProgress(
                total_publications=data['total_publications'],
                processed_count=data['processed_count'],
                mapped_count=data['mapped_count'],
                batch_number=data['batch_number'],
                last_processed_index=data['last_processed_index'],
                api_calls_made=data['api_calls_made'],
                api_calls_failed=data['api_calls_failed']
            )
        except Exception as e:
            print(f"Error loading progress: {e}")
            return None
    
    def process_batch(self, publications_batch: pd.DataFrame, grants_df: pd.DataFrame, 
                     progress: ProcessingProgress) -> Tuple[pd.DataFrame, bool]:
        """
        Process a batch of publications
        Returns (results_df, continue_processing_flag)
        """
        
        print(f"\n{'='*60}")
        print(f"PROCESSING BATCH {progress.batch_number}")
        print(f"Publications {progress.processed_count + 1}-{progress.processed_count + len(publications_batch)}")
        print(f"{'='*60}")
        
        # Initialize results
        batch_results = publications_batch.copy()
        batch_results['Associated Grant'] = ''
        batch_results['DOI of grant'] = ''
        batch_results['Confidence level'] = ''
        batch_results['Reasoning'] = ''
        
        batch_mapped = 0
        batch_api_calls = 0
        
        for idx, (pub_idx, publication) in enumerate(publications_batch.iterrows()):
            print(f"\nPublication {idx+1}/{len(publications_batch)}: {publication['title'][:60]}...")
            
            # Find candidate grants (pre-filtering)
            candidates = self.find_candidate_grants(publication, grants_df)
            
            if not candidates:
                print("  No candidates found after pre-filtering")
                continue
            
            print(f"  Found {len(candidates)} candidates after pre-filtering")
            
            # Analyze with LLM
            best_match = None
            confidence_order = ['Very Low', 'Low', 'Medium', 'High', 'Very High']
            
            for i, candidate in enumerate(candidates):
                print(f"    API call {i+1}: {candidate.grant_data['TITLE'][:40]}...")
                
                # Make API call
                match_result, api_success = self.analyze_with_api(publication, candidate)
                batch_api_calls += 1
                progress.api_calls_made += 1
                
                if not api_success:
                    # Hit rate limit
                    progress.api_calls_failed += 1
                    print(f"    RATE LIMIT HIT! Processed {progress.processed_count + idx} publications")
                    print(f"    API calls made in this batch: {batch_api_calls}")
                    print(f"    Total API calls made: {progress.api_calls_made}")
                    
                    # Save current progress
                    progress.processed_count += idx
                    progress.last_processed_index = pub_idx
                    self.save_progress(progress)
                    
                    # Save partial results
                    if idx > 0:
                        partial_results = batch_results.iloc[:idx]
                        if os.path.exists(self.checkpoint_file):
                            existing_results = pd.read_csv(self.checkpoint_file)
                            combined_results = pd.concat([existing_results, partial_results], ignore_index=True)
                        else:
                            combined_results = partial_results
                        combined_results.to_csv(self.checkpoint_file, index=False)
                        print(f"    Saved partial results to {self.checkpoint_file}")
                    
                    return batch_results, False  # Stop processing
                
                # Update best match
                if best_match is None:
                    best_match = match_result
                else:
                    current_idx = confidence_order.index(best_match.confidence)
                    new_idx = confidence_order.index(match_result.confidence)
                    if new_idx > current_idx:
                        best_match = match_result
                
                # Add delay between API calls
                time.sleep(self.api_delay)
            
            # Apply best match to results
            if best_match:
                batch_results.at[pub_idx, 'Associated Grant'] = best_match.grant_title
                batch_results.at[pub_idx, 'DOI of grant'] = best_match.grant_doi
                batch_results.at[pub_idx, 'Confidence level'] = best_match.confidence
                batch_results.at[pub_idx, 'Reasoning'] = best_match.reasoning
                batch_mapped += 1
                print(f"    MAPPED with {best_match.confidence} confidence")
        
        # Update progress
        progress.processed_count += len(publications_batch)
        progress.mapped_count += batch_mapped
        progress.batch_number += 1
        
        print(f"\n  BATCH COMPLETE:")
        print(f"    Publications processed: {len(publications_batch)}")
        print(f"    Publications mapped: {batch_mapped}")
        print(f"    API calls made: {batch_api_calls}")
        
        return batch_results, True  # Continue processing
    
    def run_batch_processing(self, grants_file: str, publications_file: str):
        """Run the complete batch processing workflow"""
        print("Starting Batch Processing with Rate Limit Handling")
        print("="*60)
        
        # Load data
        grants_df, publications_df = self.load_data(grants_file, publications_file)
        
        # Check for existing progress
        progress = self.load_progress()
        if progress is None:
            # Start fresh
            progress = ProcessingProgress(
                total_publications=len(publications_df),
                processed_count=0,
                mapped_count=0,
                batch_number=1,
                last_processed_index=-1,
                api_calls_made=0,
                api_calls_failed=0
            )
            print("Starting fresh processing")
        else:
            print(f"Resuming from previous session:")
            print(f"  Total publications: {progress.total_publications}")
            print(f"  Already processed: {progress.processed_count}")
            print(f"  Already mapped: {progress.mapped_count}")
            print(f"  API calls made: {progress.api_calls_made}")
            
            # Filter out already processed publications
            publications_df = publications_df.iloc[progress.processed_count:]
        
        # Initialize final results file
        if not os.path.exists(self.results_file) and progress.processed_count == 0:
            # Create file with headers
            empty_result = publications_df.iloc[:0].copy()
            empty_result['Associated Grant'] = ''
            empty_result['DOI of grant'] = ''
            empty_result['Confidence level'] = ''
            empty_result['Reasoning'] = ''
            empty_result.to_csv(self.results_file, index=False)
        
        # Process in batches
        remaining_pubs = len(publications_df)
        
        while remaining_pubs > 0:
            print(f"\n{'='*80}")
            print(f"OVERALL PROGRESS: {progress.processed_count}/{progress.total_publications} publications")
            print(f"REMAINING: {remaining_pubs} publications")
            print(f"{'='*80}")
            
            # Get next batch
            batch_end = min(self.batch_size, remaining_pubs)
            current_batch = publications_df.iloc[:batch_end]
            
            # Process batch
            batch_results, continue_processing = self.process_batch(current_batch, grants_df, progress)
            
            # Save results if we processed any
            if len(batch_results) > 0 and continue_processing:
                # Append to results file
                if os.path.exists(self.results_file):
                    batch_results.to_csv(self.results_file, mode='a', header=False, index=False)
                else:
                    batch_results.to_csv(self.results_file, index=False)
            
            # Save progress
            self.save_progress(progress)
            
            if not continue_processing:
                # Hit rate limit
                print(f"\n{'='*80}")
                print("RATE LIMIT ENCOUNTERED - PROCESSING PAUSED")
                print(f"{'='*80}")
                print(f"Progress so far:")
                print(f"  Publications processed: {progress.processed_count}/{progress.total_publications}")
                print(f"  Publications mapped: {progress.mapped_count}")
                print(f"  API calls made: {progress.api_calls_made}")
                print(f"  API calls failed (rate limit): {progress.api_calls_failed}")
                print(f"  Success rate: {((progress.api_calls_made - progress.api_calls_failed) / max(1, progress.api_calls_made)) * 100:.1f}%")
                
                print(f"\nTo resume processing:")
                print(f"  1. Wait for rate limit reset ({self.retry_delay/60:.0f} minutes)")
                print(f"  2. Run this script again - it will resume automatically")
                print(f"  3. Results saved in: {self.results_file}")
                print(f"  4. Progress saved in: {self.progress_file}")
                
                # Wait and ask if user wants to continue
                print(f"\nWaiting {self.retry_delay} seconds before retrying...")
                time.sleep(self.retry_delay)
                print("Retrying...")
                continue
            
            # Update remaining publications
            publications_df = publications_df.iloc[batch_end:]
            remaining_pubs = len(publications_df)
        
        # Processing complete
        print(f"\n{'='*80}")
        print("PROCESSING COMPLETE!")
        print(f"{'='*80}")
        print(f"Total publications processed: {progress.total_publications}")
        print(f"Total publications mapped: {progress.mapped_count}")
        print(f"Mapping success rate: {(progress.mapped_count/progress.total_publications)*100:.1f}%")
        print(f"Total API calls made: {progress.api_calls_made}")
        print(f"API success rate: {((progress.api_calls_made - progress.api_calls_failed) / max(1, progress.api_calls_made)) * 100:.1f}%")
        print(f"Final results saved in: {self.results_file}")
        
        # Clean up progress files
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
        
        print("\nProcessing files cleaned up.")

def main():
    """Main function"""
    GRANTS_FILE = "barbara dicker grants.xlsx"
    PUBLICATIONS_FILE = "Merged Publications Final.csv"
    
    print("Grant-Publication Batch Processor with Rate Limit Handling")
    print("This script will process all publications in batches and handle rate limits automatically.")
    print("\nPress Enter to start processing...")
    input()
    
    processor = BatchProcessor()
    processor.run_batch_processing(GRANTS_FILE, PUBLICATIONS_FILE)

if __name__ == "__main__":
    main()