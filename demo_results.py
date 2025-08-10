#!/usr/bin/env python3
"""
Demo script showing the matching results for 10 publications with simulated LLM analysis
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

@dataclass
class MatchResult:
    """Data class to store matching results"""
    grant_title: str
    grant_doi: str
    confidence: str
    reasoning: str

class DemoGrantPublicationMapper:
    def __init__(self):
        """Initialize the mapper"""
        pass
        
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
    
    def check_name_match(self, author_name: str, investigator_names: List[str]) -> bool:
        """Check if an author matches any investigator using fuzzy matching"""
        author_normalized = self.normalize_name(author_name)
        
        for inv_name in investigator_names:
            inv_normalized = self.normalize_name(inv_name)
            
            # Split names into parts
            author_parts = set(author_normalized.split())
            inv_parts = set(inv_normalized.split())
            
            # Check for exact match
            if author_normalized == inv_normalized:
                return True
            
            # Check if names have common parts (indicates similarity)
            if len(author_parts) >= 2 and len(inv_parts) >= 2:
                common_parts = len(author_parts & inv_parts)
                if common_parts >= min(2, len(author_parts), len(inv_parts)):
                    return True
        
        return False
    
    def simulate_llm_analysis(self, publication: pd.Series, grant: pd.Series) -> MatchResult:
        """Simulate LLM analysis based on heuristics"""
        
        # Extract key terms for basic topic matching
        pub_title_lower = publication['title'].lower()
        grant_title_lower = grant['TITLE'].lower()
        
        # Check for topic overlap using keywords
        common_keywords = []
        
        # Define topic clusters
        psychology_terms = ['psychological', 'mental', 'cognitive', 'depression', 'anxiety', 'stress', 'psychotherapy', 'therapy']
        neuroscience_terms = ['brain', 'neural', 'neurocognitive', 'neurobiological', 'eeg', 'imaging']
        substance_terms = ['alcohol', 'drug', 'cannabis', 'psilocybin', 'amphetamine', 'cbd', 'ketamine', 'benzodiazepine']
        sleep_terms = ['sleep', 'insomnia', 'circadian', 'fatigue']
        aging_terms = ['aged', 'aging', 'elderly', 'dementia', 'alzheimer']
        
        # Check for keyword matches
        topic_match_score = 0
        
        for term_group in [psychology_terms, neuroscience_terms, substance_terms, sleep_terms, aging_terms]:
            pub_matches = sum(1 for term in term_group if term in pub_title_lower)
            grant_matches = sum(1 for term in term_group if term in grant_title_lower)
            if pub_matches > 0 and grant_matches > 0:
                topic_match_score += 1
                common_keywords.extend([term for term in term_group if term in pub_title_lower and term in grant_title_lower])
        
        # Check investigator overlap
        pub_authors = publication['authors_list'].split(', ')
        grant_investigators = self.extract_investigators(grant)
        
        investigator_matches = []
        for author in pub_authors:
            for inv in grant_investigators:
                if self.check_name_match(author, [inv]):
                    investigator_matches.append(author)
                    break
        
        # Determine confidence based on matches
        if topic_match_score >= 2 and len(investigator_matches) >= 2:
            confidence = "High"
            reasoning = f"Strong topic alignment (common themes: {', '.join(common_keywords[:3])}) and multiple investigator matches: {', '.join(investigator_matches[:2])}"
        elif topic_match_score >= 1 and len(investigator_matches) >= 1:
            confidence = "Medium" 
            reasoning = f"Moderate alignment with shared topics ({', '.join(common_keywords[:2])}) and investigator match: {investigator_matches[0]}"
        elif len(investigator_matches) >= 1:
            confidence = "Low"
            reasoning = f"Primary match based on investigator overlap: {investigator_matches[0]}, but limited topic alignment"
        else:
            confidence = "Very Low"
            reasoning = "Minimal evidence for relationship - matched only through secondary criteria"
        
        return MatchResult(
            grant_title=grant['TITLE'],
            grant_doi=str(grant.get('Project Code', 'N/A')),
            confidence=confidence,
            reasoning=reasoning
        )
    
    def process_sample_with_demo(self, publications_df: pd.DataFrame, grants_df: pd.DataFrame, 
                               sample_size: int = 10) -> pd.DataFrame:
        """Process a sample showing the complete pipeline"""
        print(f"Processing sample of {sample_size} publications...")
        
        # Take sample
        sample_pubs = publications_df.head(sample_size).copy()
        
        # Initialize new columns
        sample_pubs['Associated Grant'] = ''
        sample_pubs['DOI of grant'] = ''
        sample_pubs['Confidence level'] = ''
        sample_pubs['Reasoning'] = ''
        
        print("\nStep 1: Investigator Matching")
        print("-" * 40)
        
        # Filter by investigators
        filtered_pubs = []
        for pub_idx, pub_row in sample_pubs.iterrows():
            authors = str(pub_row['authors_list']).split(', ')
            matching_grants = []
            
            for grant_idx, grant_row in grants_df.iterrows():
                grant_investigators = self.extract_investigators(grant_row)
                
                for author in authors:
                    if self.check_name_match(author, grant_investigators):
                        matching_grants.append(grant_idx)
                        print(f"MATCH: '{author}' in publication {pub_idx+1} matches grant {grant_idx+1} investigators")
                        break
            
            if matching_grants:
                pub_row_copy = pub_row.copy()
                pub_row_copy['matching_grants'] = matching_grants
                filtered_pubs.append(pub_row_copy)
        
        filtered_df = pd.DataFrame(filtered_pubs)
        print(f"\nFound {len(filtered_df)} publications with investigator matches")
        
        print("\nStep 2: Date Range Filtering")
        print("-" * 40)
        
        # Filter by date range
        valid_matches = []
        for pub_idx, pub_row in filtered_df.iterrows():
            pub_year = int(pub_row['publication_year'])
            
            for grant_idx in pub_row['matching_grants']:
                grant_row = grants_df.iloc[grant_idx]
                start_year = grant_row['Start Date'].year
                end_year = (grant_row['End Date'] + timedelta(days=730)).year  # +2 years
                
                if start_year <= pub_year <= end_year:
                    valid_matches.append((pub_idx, grant_idx))
                    print(f"DATE_MATCH: Publication {pub_idx+1} ({pub_year}) fits grant {grant_idx+1} timeline ({start_year}-{end_year})")
        
        print(f"\nFound {len(valid_matches)} publication-grant pairs within valid date ranges")
        
        print("\nStep 3: Content Analysis (Simulated)")
        print("-" * 40)
        
        # Apply simulated LLM analysis
        pub_to_best_match = {}
        
        for pub_idx, grant_idx in valid_matches:
            publication = publications_df.iloc[pub_idx]
            grant = grants_df.iloc[grant_idx]
            
            match_result = self.simulate_llm_analysis(publication, grant)
            
            print(f"Analysis: Pub {pub_idx+1} -> Grant {grant_idx+1}: {match_result.confidence}")
            print(f"  Reasoning: {match_result.reasoning[:80]}...")
            
            # Keep best match per publication
            if pub_idx not in pub_to_best_match:
                pub_to_best_match[pub_idx] = match_result
            else:
                confidence_order = ['Very Low', 'Low', 'Medium', 'High', 'Very High']
                current_idx = confidence_order.index(pub_to_best_match[pub_idx].confidence)
                new_idx = confidence_order.index(match_result.confidence)
                if new_idx > current_idx:
                    pub_to_best_match[pub_idx] = match_result
        
        # Apply results
        for pub_idx, match_result in pub_to_best_match.items():
            sample_idx = sample_pubs[sample_pubs.index == pub_idx].index
            if len(sample_idx) > 0:
                idx = sample_idx[0]
                sample_pubs.at[idx, 'Associated Grant'] = match_result.grant_title
                sample_pubs.at[idx, 'DOI of grant'] = match_result.grant_doi
                sample_pubs.at[idx, 'Confidence level'] = match_result.confidence
                sample_pubs.at[idx, 'Reasoning'] = match_result.reasoning
        
        return sample_pubs

def main():
    """Main demo function"""
    print("Grant-Publication Mapping Demo")
    print("=" * 50)
    
    # Configuration
    GRANTS_FILE = "barbara dicker grants.xlsx"
    PUBLICATIONS_FILE = "Merged Publications Final.csv"
    OUTPUT_FILE = "demo_mapped_publications.csv"
    
    try:
        mapper = DemoGrantPublicationMapper()
        
        # Load data
        grants_df, publications_df = mapper.load_data(GRANTS_FILE, PUBLICATIONS_FILE)
        
        # Process sample
        result_df = mapper.process_sample_with_demo(publications_df, grants_df, sample_size=10)
        
        # Save and display results
        result_df.to_csv(OUTPUT_FILE, index=False)
        
        print(f"\n" + "=" * 80)
        print("FINAL RESULTS")
        print("=" * 80)
        
        mapped_pubs = len(result_df[result_df['Associated Grant'] != ''])
        print(f"Sample size: {len(result_df)} publications")
        print(f"Successfully mapped: {mapped_pubs} publications")
        print(f"Mapping rate: {mapped_pubs/len(result_df)*100:.1f}%")
        
        print(f"\nDetailed Results:")
        print("-" * 80)
        
        for idx, row in result_df.iterrows():
            print(f"\nPublication {idx+1}:")
            print(f"Title: {row['title']}")
            print(f"Authors: {row['authors_list']}")
            print(f"Year: {row['publication_year']}")
            print(f"DOI: {row['doi']}")
            
            if row['Associated Grant']:
                print(f"MAPPED TO GRANT:")
                print(f"  Grant: {row['Associated Grant']}")
                print(f"  Grant ID: {row['DOI of grant']}")
                print(f"  Confidence: {row['Confidence level']}")
                print(f"  Reasoning: {row['Reasoning']}")
            else:
                print("NO GRANT MAPPING FOUND")
            
            print("-" * 40)
        
        print(f"\nResults saved to {OUTPUT_FILE}")
        return result_df
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = main()