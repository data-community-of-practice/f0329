#!/usr/bin/env python3
"""
Test the optimized grant-publication mapper with custom API
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

class OptimizedCustomMapper:
    def __init__(self, config_file: str = "config.ini"):
        """Initialize the mapper with custom API configuration"""
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        self.api_url = self.config.get('API', 'base_url')
        self.auth_header = self.config.get('API', 'authorization')
        self.model = self.config.get('API', 'model')
    
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
        return candidates
    
    def analyze_with_api(self, publication: pd.Series, candidate: CandidateGrant) -> MatchResult:
        """Analyze using custom API with focused prompt"""
        
        prompt = f"""
        Assess the TOPICAL RELATIONSHIP between this grant and publication:

        GRANT: {candidate.grant_data['TITLE']}
        PUBLICATION: {publication['title']}

        They already match on investigators and timing. Rate topical alignment:
        - Very High: Perfect topic match
        - High: Strong topic overlap
        - Medium: Moderate connection
        - Low: Minimal alignment
        - Very Low: No clear connection

        JSON response:
        {{
            "confidence": "Very High|High|Medium|Low|Very Low",
            "reasoning": "Brief topic alignment explanation"
        }}
        """
        
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Assess topical relationships between grants and publications concisely."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 200,
                "stream": False
            }
            
            headers = {
                'accept': 'application/json',
                'authorization': self.auth_header,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                content = response_data['choices'][0]['message']['content'].strip()
                
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result_data = json.loads(json_match.group())
                    return MatchResult(
                        grant_title=candidate.grant_data['TITLE'],
                        grant_doi=str(candidate.grant_data.get('Project Code', 'N/A')),
                        confidence=result_data['confidence'],
                        reasoning=result_data['reasoning']
                    )
            
            return MatchResult(
                grant_title=candidate.grant_data['TITLE'],
                grant_doi=str(candidate.grant_data.get('Project Code', 'N/A')),
                confidence="Low",
                reasoning=f"API error: status {response.status_code}"
            )
                
        except Exception as e:
            return MatchResult(
                grant_title=candidate.grant_data['TITLE'],
                grant_doi=str(candidate.grant_data.get('Project Code', 'N/A')),
                confidence="Low",
                reasoning=f"Analysis error: {str(e)}"
            )
    
    def process_sample(self, grants_df: pd.DataFrame, publications_df: pd.DataFrame, sample_size: int = 5) -> pd.DataFrame:
        """Process a sample with the optimized approach"""
        print(f"\nProcessing {sample_size} publications with optimized filtering...")
        
        sample_pubs = publications_df.head(sample_size).copy()
        
        # Initialize result columns
        sample_pubs['Associated Grant'] = ''
        sample_pubs['DOI of grant'] = ''
        sample_pubs['Confidence level'] = ''
        sample_pubs['Reasoning'] = ''
        
        total_candidates = 0
        total_llm_calls = 0
        
        for idx, (pub_idx, publication) in enumerate(sample_pubs.iterrows()):
            print(f"\nPublication {idx+1}: {publication['title'][:60]}...")
            
            # Find candidates (pre-filtered)
            candidates = self.find_candidate_grants(publication, grants_df)
            total_candidates += len(candidates)
            
            if not candidates:
                print("  No candidates found after filtering")
                continue
                
            print(f"  Found {len(candidates)} candidates after filtering")
            
            # Analyze top candidates with LLM
            best_match = None
            confidence_order = ['Very Low', 'Low', 'Medium', 'High', 'Very High']
            
            for i, candidate in enumerate(candidates[:2]):  # Top 2 candidates only
                print(f"    LLM analyzing: {candidate.grant_data['TITLE'][:40]}...")
                total_llm_calls += 1
                
                match_result = self.analyze_with_api(publication, candidate)
                
                if best_match is None:
                    best_match = match_result
                else:
                    current_idx = confidence_order.index(best_match.confidence)
                    new_idx = confidence_order.index(match_result.confidence)
                    if new_idx > current_idx:
                        best_match = match_result
                
                time.sleep(1)  # Rate limiting
            
            if best_match:
                sample_pubs.at[pub_idx, 'Associated Grant'] = best_match.grant_title
                sample_pubs.at[pub_idx, 'DOI of grant'] = best_match.grant_doi
                sample_pubs.at[pub_idx, 'Confidence level'] = best_match.confidence
                sample_pubs.at[pub_idx, 'Reasoning'] = best_match.reasoning
                print(f"  MAPPED with {best_match.confidence} confidence")
        
        # Summary
        mapped_count = len(sample_pubs[sample_pubs['Associated Grant'] != ''])
        original_llm_calls = len(sample_pubs) * len(grants_df)  # Without filtering
        
        print(f"\n" + "="*60)
        print("OPTIMIZATION RESULTS")
        print("="*60)
        print(f"Publications processed: {len(sample_pubs)}")
        print(f"Successfully mapped: {mapped_count}")
        print(f"Average candidates per publication: {total_candidates/len(sample_pubs):.1f}")
        print(f"LLM calls made: {total_llm_calls}")
        print(f"LLM calls without filtering: {original_llm_calls}")
        print(f"LLM calls saved: {original_llm_calls - total_llm_calls} ({((original_llm_calls - total_llm_calls)/original_llm_calls)*100:.1f}%)")
        
        return sample_pubs

def main():
    """Test the optimized approach"""
    print("Testing Optimized Grant-Publication Mapping")
    print("="*50)
    
    try:
        mapper = OptimizedCustomMapper()
        grants_df, publications_df = mapper.load_data("barbara dicker grants.xlsx", "Merged Publications Final.csv")
        
        # Test with 5 publications
        result_df = mapper.process_sample(grants_df, publications_df, sample_size=5)
        
        # Save results
        result_df.to_csv("optimized_test_results.csv", index=False)
        
        # Show detailed results
        print(f"\nDETAILED RESULTS:")
        print("-"*80)
        
        for idx, row in result_df.iterrows():
            print(f"\nPublication {idx+1}:")
            print(f"Title: {row['title']}")
            print(f"Authors: {row['authors_list']}")
            if row['Associated Grant']:
                print(f"MAPPED TO: {row['Associated Grant']}")
                print(f"Confidence: {row['Confidence level']}")
                print(f"Reasoning: {row['Reasoning']}")
            else:
                print("NO MAPPING FOUND")
            print("-"*40)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()