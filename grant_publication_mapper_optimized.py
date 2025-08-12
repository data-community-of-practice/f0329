#!/usr/bin/env python3
"""
Optimized Grant-Publication Mapping Tool

This script maps publications to grants using an efficient approach:
1. Pre-filter grants by investigator matching
2. Pre-filter by date range (grant start to end + 2 years)
3. Send only relevant grants to LLM for final relationship assessment

Author: Claude Code Assistant
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import openai
import re
from typing import List, Tuple, Dict, Optional
import time
import json
from dataclasses import dataclass
from pathlib import Path
import sys
import configparser

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
    temporal_score: float  # How well the timing aligns

class OptimizedGrantPublicationMapper:
    def __init__(self, openai_api_key: str):
        """Initialize the mapper with OpenAI API key"""
        self.client = openai.OpenAI(api_key=openai_api_key)
        
    def load_data(self, grants_file: str, publications_file: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load grants and publications data"""
        print("Loading data files...")
        
        # Load grants data
        grants_df = pd.read_excel(grants_file)
        print(f"Loaded {len(grants_df)} grants")
        
        # Load publications data
        publications_df = pd.read_csv(publications_file)
        print(f"Loaded {len(publications_df)} publications")
        
        # Convert date columns to datetime
        grants_df['Start Date'] = pd.to_datetime(grants_df['Start Date'])
        grants_df['End Date'] = pd.to_datetime(grants_df['End Date'])
        
        return grants_df, publications_df
    
    def extract_investigators(self, row) -> List[str]:
        """Extract all investigators from a grant row"""
        investigators = []
        
        # Add primary investigator
        if pd.notna(row['Preferred Full Name']):
            investigators.append(row['Preferred Full Name'].strip())
        
        # Add other investigators
        if pd.notna(row['Other Investigators']):
            other_invs = str(row['Other Investigators']).split(',')
            investigators.extend([inv.strip() for inv in other_invs])
        
        return investigators
    
    def normalize_name(self, name: str) -> str:
        """Normalize investigator names for better matching"""
        if pd.isna(name):
            return ""
        
        # Remove extra whitespace and convert to lowercase
        name = str(name).strip().lower()
        
        # Remove common titles and suffixes
        name = re.sub(r'\b(dr|prof|professor|phd|md)\b\.?', '', name)
        
        # Remove extra spaces
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def check_name_match(self, author_name: str, investigator_names: List[str]) -> Tuple[bool, str]:
        """Check if an author matches any investigator, return match and matched name"""
        author_normalized = self.normalize_name(author_name)
        
        for inv_name in investigator_names:
            inv_normalized = self.normalize_name(inv_name)
            
            # Split names into parts
            author_parts = set(author_normalized.split())
            inv_parts = set(inv_normalized.split())
            
            # Check for exact match
            if author_normalized == inv_normalized:
                return True, inv_name
            
            # Check if names have common parts (indicates similarity)
            if len(author_parts) >= 2 and len(inv_parts) >= 2:
                common_parts = len(author_parts & inv_parts)
                if common_parts >= min(2, len(author_parts), len(inv_parts)):
                    return True, inv_name
        
        return False, ""
    
    def calculate_temporal_score(self, publication_year: int, grant_start: datetime, grant_end: datetime) -> float:
        """Calculate how well the publication timing aligns with the grant period"""
        grant_start_year = grant_start.year
        grant_end_year = (grant_end + timedelta(days=730)).year  # +2 years
        
        # Publication outside valid range gets 0
        if publication_year < grant_start_year or publication_year > grant_end_year:
            return 0.0
        
        # Perfect timing scores
        if grant_start_year <= publication_year <= grant_end.year:
            return 1.0  # During grant period
        elif grant_end.year < publication_year <= grant_end_year:
            # After grant end but within 2 years - slightly lower score
            years_after = publication_year - grant_end.year
            return max(0.5, 1.0 - (years_after * 0.25))
        
        return 0.5  # Default for edge cases
    
    def find_candidate_grants(self, publication: pd.Series, grants_df: pd.DataFrame) -> List[CandidateGrant]:
        """Find grants that could potentially be related to this publication"""
        candidates = []
        
        # Extract publication authors
        authors = str(publication['authors_list']).split(', ')
        pub_year = int(publication['publication_year'])
        
        # Check each grant
        for grant_idx, grant_row in grants_df.iterrows():
            grant_investigators = self.extract_investigators(grant_row)
            
            # Step 1: Check investigator matching
            investigator_matches = []
            for author in authors:
                is_match, matched_name = self.check_name_match(author, grant_investigators)
                if is_match:
                    investigator_matches.append(f"{author} -> {matched_name}")
            
            # Skip if no investigator matches
            if not investigator_matches:
                continue
                
            # Step 2: Check temporal alignment
            temporal_score = self.calculate_temporal_score(
                pub_year, grant_row['Start Date'], grant_row['End Date']
            )
            
            # Skip if outside valid time range
            if temporal_score == 0:
                continue
            
            # This grant passed both filters - add as candidate
            candidates.append(CandidateGrant(
                grant_idx=grant_idx,
                grant_data=grant_row,
                investigator_matches=investigator_matches,
                temporal_score=temporal_score
            ))
        
        # Sort candidates by quality (temporal score * number of investigator matches)
        candidates.sort(key=lambda x: x.temporal_score * len(x.investigator_matches), reverse=True)
        
        return candidates
    
    def analyze_publication_grant_relationship(self, publication: pd.Series, candidate: CandidateGrant) -> MatchResult:
        """Use LLM to analyze the relationship between a publication and a specific candidate grant"""
        
        # Much more focused prompt since we already know they match on investigators and timing
        prompt = f"""
        You are analyzing a pre-filtered publication-grant pair that has already been confirmed to have:
        - Matching investigators: {', '.join(candidate.investigator_matches)}
        - Valid timing alignment (publication within grant period + 2 years)
        
        Now assess the TOPICAL RELATIONSHIP between this grant and publication:

        GRANT:
        Title: {candidate.grant_data['TITLE']}
        Description: {candidate.grant_data.get('Proejct Description', 'Not provided')}

        PUBLICATION:
        Title: {publication['title']}
        Publication Year: {publication['publication_year']}

        Based on the research topics and content, rate the likelihood this publication resulted from this grant:

        - Very High: Perfect topical alignment, publication clearly addresses grant objectives
        - High: Strong topical overlap, publication likely resulted from grant work  
        - Medium: Moderate topical connection, possible relationship
        - Low: Minimal topical alignment, unlikely direct relationship
        - Very Low: No clear topical connection despite investigator/timing match

        Respond in JSON format:
        {{
            "confidence": "Very High|High|Medium|Low|Very Low",
            "reasoning": "Brief explanation focusing on topical alignment between grant objectives and publication content"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a research analyst assessing topical relationships between grants and publications. Be concise and focus only on content alignment."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            # Parse the JSON response
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                return MatchResult(
                    grant_title=candidate.grant_data['TITLE'],
                    grant_doi=str(candidate.grant_data.get('Project Code', 'N/A')),
                    confidence=result_data['confidence'],
                    reasoning=result_data['reasoning']
                )
            else:
                return MatchResult(
                    grant_title=candidate.grant_data['TITLE'],
                    grant_doi=str(candidate.grant_data.get('Project Code', 'N/A')),
                    confidence="Low",
                    reasoning="Failed to parse LLM response"
                )
                
        except Exception as e:
            print(f"Error in LLM analysis: {e}")
            return MatchResult(
                grant_title=candidate.grant_data['TITLE'],
                grant_doi=str(candidate.grant_data.get('Project Code', 'N/A')),
                confidence="Low",
                reasoning=f"Error in analysis: {str(e)}"
            )
    
    def process_publication(self, publication: pd.Series, grants_df: pd.DataFrame) -> Optional[MatchResult]:
        """Process a single publication and find its best grant match"""
        
        # Step 1: Find candidate grants (pre-filtered)
        candidates = self.find_candidate_grants(publication, grants_df)
        
        if not candidates:
            return None  # No candidates found
        
        print(f"  Found {len(candidates)} candidate grants for analysis")
        
        # Step 2: Analyze only the top candidates with LLM
        best_match = None
        confidence_order = ['Very Low', 'Low', 'Medium', 'High', 'Very High']
        
        # Analyze up to top 3 candidates to find the best match
        for i, candidate in enumerate(candidates[:3]):
            # Handle Unicode characters in grant title for Windows console
            grant_title_safe = str(candidate.grant_data['TITLE'])[:50].encode('ascii', 'ignore').decode('ascii')
            print(f"    Analyzing candidate {i+1}: {grant_title_safe}...")
            
            match_result = self.analyze_publication_grant_relationship(publication, candidate)
            
            # Keep the best match
            if best_match is None:
                best_match = match_result
            else:
                current_idx = confidence_order.index(best_match.confidence)
                new_idx = confidence_order.index(match_result.confidence)
                if new_idx > current_idx:
                    best_match = match_result
            
            # Add delay to avoid rate limiting
            time.sleep(0.2)
        
        return best_match
    
    def run_mapping(self, grants_file: str, publications_file: str, output_file: str, sample_size: Optional[int] = None):
        """Run the complete optimized mapping process"""
        print("Starting optimized grant-publication mapping process...")
        
        # Load data
        grants_df, publications_df = self.load_data(grants_file, publications_file)
        
        # Use sample if specified
        if sample_size:
            publications_df = publications_df.head(sample_size)
            print(f"Processing sample of {len(publications_df)} publications")
        
        # Create result dataframe
        result_df = publications_df.copy()
        result_df['Associated Grant'] = ''
        result_df['DOI of grant'] = ''
        result_df['Confidence level'] = ''
        result_df['Reasoning'] = ''
        
        # Process each publication
        mapped_count = 0
        total_llm_calls = 0
        
        for idx, (pub_idx, publication) in enumerate(publications_df.iterrows()):
            # Handle Unicode characters in title for Windows console
            title_safe = publication['title'][:60].encode('ascii', 'ignore').decode('ascii')
            print(f"\nProcessing publication {idx+1}/{len(publications_df)}: {title_safe}...")
            
            # Find best match for this publication
            best_match = self.process_publication(publication, grants_df)
            
            if best_match:
                result_df.at[pub_idx, 'Associated Grant'] = best_match.grant_title
                result_df.at[pub_idx, 'DOI of grant'] = best_match.grant_doi
                result_df.at[pub_idx, 'Confidence level'] = best_match.confidence
                result_df.at[pub_idx, 'Reasoning'] = best_match.reasoning
                mapped_count += 1
                print(f"  [+] Mapped with {best_match.confidence} confidence")
            else:
                print(f"  [-] No valid grant matches found")
        
        # Save results
        result_df.to_csv(output_file, index=False)
        print(f"\nResults saved to {output_file}")
        
        # Print summary
        print(f"\nOptimized Mapping Summary:")
        print(f"Total publications processed: {len(publications_df)}")
        print(f"Publications mapped to grants: {mapped_count}")
        print(f"Mapping rate: {mapped_count/len(publications_df)*100:.1f}%")
        print(f"Estimated LLM calls saved: {len(publications_df) * len(grants_df) - total_llm_calls}")

def main():
    """Main function"""
    # Configuration
    GRANTS_FILE = "barbara dicker grants.xlsx"
    PUBLICATIONS_FILE = "Merged Publications Final.csv"
    OUTPUT_FILE = "all_mapped_publications.csv"
    
    # Read API key from config file
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    try:
        api_key = config.get('API', 'api_key').strip()
        if not api_key:
            print("Error: OpenAI API key not found in config.ini")
            return
    except (configparser.NoSectionError, configparser.NoOptionError):
        print("Error: Could not find API key in config.ini file")
        return
    
    # Process ALL publications (no sample limit)
    sample_size = None
    print(f"Processing ALL publications using API key from config.ini")
    
    # Create mapper and run
    mapper = OptimizedGrantPublicationMapper(api_key)
    mapper.run_mapping(GRANTS_FILE, PUBLICATIONS_FILE, OUTPUT_FILE, sample_size)

if __name__ == "__main__":
    main()