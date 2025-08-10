#!/usr/bin/env python3
"""
Grant-Publication Mapping Tool

This script maps publications to grants based on:
1. Investigator matching
2. Date range filtering (grant start to end + 2 years)
3. LLM-based relationship analysis using GPT-4o-mini

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

@dataclass
class MatchResult:
    """Data class to store matching results"""
    grant_title: str
    grant_doi: str
    confidence: str
    reasoning: str

class GrantPublicationMapper:
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
            
            # Check if last names match and at least one first name/initial matches
            if len(author_parts) >= 2 and len(inv_parts) >= 2:
                # Assume last part is surname
                if (author_parts & inv_parts):  # Any common parts
                    # More sophisticated matching could be added here
                    common_parts = len(author_parts & inv_parts)
                    if common_parts >= min(2, len(author_parts), len(inv_parts)):
                        return True
        
        return False
    
    def filter_publications_by_investigators(self, publications_df: pd.DataFrame, grants_df: pd.DataFrame) -> pd.DataFrame:
        """Filter publications that have matching investigators with grants"""
        print("Filtering publications by investigators...")
        
        filtered_pubs = []
        
        for pub_idx, pub_row in publications_df.iterrows():
            if pub_idx % 100 == 0:
                print(f"Processing publication {pub_idx}/{len(publications_df)}")
            
            # Extract publication authors
            authors = str(pub_row['authors_list']).split(', ')
            
            # Check against all grants
            matching_grants = []
            for grant_idx, grant_row in grants_df.iterrows():
                grant_investigators = self.extract_investigators(grant_row)
                
                # Check if any author matches any investigator
                for author in authors:
                    if self.check_name_match(author, grant_investigators):
                        matching_grants.append(grant_idx)
                        break
            
            if matching_grants:
                pub_row_copy = pub_row.copy()
                pub_row_copy['matching_grants'] = matching_grants
                filtered_pubs.append(pub_row_copy)
        
        filtered_df = pd.DataFrame(filtered_pubs)
        print(f"Found {len(filtered_df)} publications with matching investigators")
        return filtered_df
    
    def filter_by_date_range(self, filtered_pubs: pd.DataFrame, grants_df: pd.DataFrame) -> List[Tuple[int, int]]:
        """Filter by date range: grant start to end + 2 years"""
        print("Filtering by date ranges...")
        
        valid_matches = []
        
        for pub_idx, pub_row in filtered_pubs.iterrows():
            pub_year = int(pub_row['publication_year'])
            
            for grant_idx in pub_row['matching_grants']:
                grant_row = grants_df.iloc[grant_idx]
                
                # Calculate date range
                start_date = grant_row['Start Date']
                end_date = grant_row['End Date'] + timedelta(days=730)  # +2 years
                
                # Check if publication year falls within range
                if start_date.year <= pub_year <= end_date.year:
                    valid_matches.append((pub_idx, grant_idx))
        
        print(f"Found {len(valid_matches)} publication-grant pairs within date range")
        return valid_matches
    
    def analyze_relationship_with_llm(self, publication: pd.Series, grant: pd.Series) -> MatchResult:
        """Use GPT-4o-mini to analyze the relationship between publication and grant"""
        
        prompt = f"""
        Analyze the relationship between the following research grant and publication to determine if they could be related.

        GRANT INFORMATION:
        Title: {grant['TITLE']}
        Description: {grant.get('Proejct Description', 'N/A')}
        Investigators: {grant['Preferred Full Name']}, {grant.get('Other Investigators', 'N/A')}
        Start Date: {grant['Start Date']}
        End Date: {grant['End Date']}

        PUBLICATION INFORMATION:
        Title: {publication['title']}
        Authors: {publication['authors_list']}
        Publication Year: {publication['publication_year']}
        DOI: {publication['doi']}

        Based on the above information, please:
        1. Determine the likelihood that this publication resulted from or is related to this grant
        2. Assign a confidence level: Very High / High / Medium / Low / Very Low
        3. Provide clear reasoning for your assessment

        Consider factors such as:
        - Topic/subject matter alignment between grant and publication
        - Author overlap with grant investigators
        - Timing alignment (publication should be during or shortly after grant period)
        - Methodological or research approach alignment

        Respond in the following JSON format:
        {{
            "confidence": "Very High|High|Medium|Low|Very Low",
            "reasoning": "Clear explanation of why you assigned this confidence level, focusing on specific alignments or mismatches between the grant and publication"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a research analyst expert at identifying relationships between research grants and publications. Provide accurate, concise assessments."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            # Parse the JSON response
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                return MatchResult(
                    grant_title=grant['TITLE'],
                    grant_doi=str(grant.get('Project Code', 'N/A')),  # Using Project Code as DOI
                    confidence=result_data['confidence'],
                    reasoning=result_data['reasoning']
                )
            else:
                return MatchResult(
                    grant_title=grant['TITLE'],
                    grant_doi=str(grant.get('Project Code', 'N/A')),
                    confidence="Low",
                    reasoning="Failed to parse LLM response"
                )
                
        except Exception as e:
            print(f"Error in LLM analysis: {e}")
            return MatchResult(
                grant_title=grant['TITLE'],
                grant_doi=str(grant.get('Project Code', 'N/A')),
                confidence="Low",
                reasoning=f"Error in analysis: {str(e)}"
            )
    
    def process_all_publications(self, publications_df: pd.DataFrame, grants_df: pd.DataFrame, 
                               valid_matches: List[Tuple[int, int]]) -> pd.DataFrame:
        """Process all publications and add the required columns"""
        print("Processing all publications with LLM analysis...")
        
        # Create a copy of the original publications dataframe
        result_df = publications_df.copy()
        
        # Initialize new columns
        result_df['Associated Grant'] = ''
        result_df['DOI of grant'] = ''
        result_df['Confidence level'] = ''
        result_df['Reasoning'] = ''
        
        # Create a mapping of publication indices to their best match
        pub_to_best_match = {}
        
        # Process valid matches with LLM
        total_matches = len(valid_matches)
        for idx, (pub_idx, grant_idx) in enumerate(valid_matches):
            if idx % 10 == 0:
                print(f"Processing match {idx}/{total_matches}")
            
            publication = publications_df.iloc[pub_idx]
            grant = grants_df.iloc[grant_idx]
            
            # Analyze with LLM
            match_result = self.analyze_relationship_with_llm(publication, grant)
            
            # Store the best match for this publication (you might want to implement logic to choose the best if multiple)
            if pub_idx not in pub_to_best_match:
                pub_to_best_match[pub_idx] = match_result
            else:
                # Simple logic: keep the match with higher confidence
                current_confidence = pub_to_best_match[pub_idx].confidence
                new_confidence = match_result.confidence
                
                confidence_order = ['Very Low', 'Low', 'Medium', 'High', 'Very High']
                if confidence_order.index(new_confidence) > confidence_order.index(current_confidence):
                    pub_to_best_match[pub_idx] = match_result
            
            # Add small delay to avoid rate limiting
            time.sleep(0.1)
        
        # Apply the results to the dataframe
        for pub_idx, match_result in pub_to_best_match.items():
            result_df.at[pub_idx, 'Associated Grant'] = match_result.grant_title
            result_df.at[pub_idx, 'DOI of grant'] = match_result.grant_doi
            result_df.at[pub_idx, 'Confidence level'] = match_result.confidence
            result_df.at[pub_idx, 'Reasoning'] = match_result.reasoning
        
        return result_df
    
    def run_mapping(self, grants_file: str, publications_file: str, output_file: str):
        """Run the complete mapping process"""
        print("Starting grant-publication mapping process...")
        
        # Load data
        grants_df, publications_df = self.load_data(grants_file, publications_file)
        
        # Step 1: Filter by investigators
        filtered_pubs = self.filter_publications_by_investigators(publications_df, grants_df)
        
        if len(filtered_pubs) == 0:
            print("No publications found with matching investigators. Check name matching logic.")
            return
        
        # Step 2: Filter by date range
        valid_matches = self.filter_by_date_range(filtered_pubs, grants_df)
        
        if len(valid_matches) == 0:
            print("No publications found within valid date ranges.")
            return
        
        # Step 3: Process all publications with LLM analysis
        result_df = self.process_all_publications(publications_df, grants_df, valid_matches)
        
        # Save results
        result_df.to_csv(output_file, index=False)
        print(f"Results saved to {output_file}")
        
        # Print summary
        mapped_pubs = len(result_df[result_df['Associated Grant'] != ''])
        print(f"\nSummary:")
        print(f"Total publications: {len(publications_df)}")
        print(f"Publications mapped to grants: {mapped_pubs}")
        print(f"Mapping rate: {mapped_pubs/len(publications_df)*100:.1f}%")

def main():
    """Main function"""
    # Configuration
    GRANTS_FILE = "barbara dicker grants.xlsx"
    PUBLICATIONS_FILE = "Merged Publications Final.csv"
    OUTPUT_FILE = "mapped_publications_output.csv"
    
    # Get OpenAI API key
    api_key = input("Please enter your OpenAI API key: ").strip()
    
    if not api_key:
        print("Error: OpenAI API key is required")
        return
    
    # Create mapper and run
    mapper = GrantPublicationMapper(api_key)
    mapper.run_mapping(GRANTS_FILE, PUBLICATIONS_FILE, OUTPUT_FILE)

if __name__ == "__main__":
    main()