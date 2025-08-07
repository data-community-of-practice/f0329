"""
Grant-Publication Matching Script
Matches grants to publications using LLM analysis based on:
1. Topic Relevance
2. Author Overlap  
3. Temporal Validity
4. Research Continuity
"""

import pandas as pd
import openai
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple
import os
from pathlib import Path

class GrantPublicationMatcher:
    def __init__(self, openai_api_key: str = None):
        """Initialize the matcher with OpenAI API key"""
        if openai_api_key:
            openai.api_key = openai_api_key
        elif 'OPENAI_API_KEY' in os.environ:
            openai.api_key = os.environ['OPENAI_API_KEY']
        else:
            print("Warning: No OpenAI API key provided. Set OPENAI_API_KEY environment variable or pass key to constructor.")
    
    def load_data(self, grants_file: str, publications_file: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load grants and publications data"""
        print("Loading data files...")
        
        # Load grants data (Excel)
        grants_df = pd.read_excel(grants_file)
        print(f"Loaded {len(grants_df)} grants")
        print("Grants columns:", grants_df.columns.tolist())
        
        # Load publications data (CSV)
        publications_df = pd.read_csv(publications_file)
        print(f"Loaded {len(publications_df)} publications")
        print("Publications columns:", publications_df.columns.tolist())
        
        return grants_df, publications_df
    
    def preprocess_authors(self, authors_str: str) -> List[str]:
        """Extract and clean author names from string"""
        if pd.isna(authors_str):
            return []
        
        # Split by comma and clean each author name
        authors = [author.strip().strip('"') for author in str(authors_str).split(',')]
        
        # Extract last names for matching
        cleaned_authors = []
        for author in authors:
            # Split by space and take last part as surname
            parts = author.split()
            if parts:
                cleaned_authors.append(parts[-1].lower())
        
        return cleaned_authors
    
    def calculate_author_overlap(self, grant_investigators: str, pub_authors: str) -> float:
        """Calculate overlap between grant investigators and publication authors"""
        grant_authors = self.preprocess_authors(grant_investigators)
        pub_authors_list = self.preprocess_authors(pub_authors)
        
        if not grant_authors or not pub_authors_list:
            return 0.0
        
        # Calculate overlap percentage
        overlap = len(set(grant_authors) & set(pub_authors_list))
        total_grant_authors = len(grant_authors)
        
        return overlap / total_grant_authors if total_grant_authors > 0 else 0.0
    
    def check_temporal_validity(self, grant_start_date, pub_year) -> bool:
        """Check if publication year is after grant start date"""
        try:
            if pd.isna(grant_start_date) or pd.isna(pub_year):
                return False
            
            # Convert grant start date to year
            if isinstance(grant_start_date, str):
                grant_year = int(grant_start_date.split('-')[0]) if '-' in grant_start_date else int(grant_start_date)
            else:
                grant_year = grant_start_date.year if hasattr(grant_start_date, 'year') else int(grant_start_date)
            
            return int(pub_year) >= grant_year
        except:
            return False
    
    def create_matching_prompt(self, grant_info: Dict, publication_info: Dict) -> str:
        """Create prompt for LLM to assess grant-publication match"""
        
        prompt = f"""
Analyze the match between this grant and publication based on four criteria:

GRANT INFORMATION:
Title: {grant_info.get('title', 'N/A')}
Lead Investigator: {grant_info.get('lead_investigator', 'N/A')}
Co-investigators: {grant_info.get('co_investigators', 'N/A')}
Start Date: {grant_info.get('start_date', 'N/A')}
End Date: {grant_info.get('end_date', 'N/A')}

PUBLICATION INFORMATION:
Title: {publication_info.get('title', 'N/A')}
Authors: {publication_info.get('authors', 'N/A')}
Year: {publication_info.get('year', 'N/A')}
DOI: {publication_info.get('doi', 'N/A')}

ASSESSMENT CRITERIA:
1. Topic Relevance (0-100): How well do the research topics, methodologies, and domains align?
2. Author Overlap (0-100): Degree of overlap between grant investigators and publication authors (already calculated: {grant_info.get('author_overlap_score', 0):.1f}%)
3. Temporal Validity (0-100): Is the publication date after the grant start date? (already calculated: {grant_info.get('temporal_valid', False)})
4. Research Continuity (0-100): How plausible is this publication as an outcome of this grant?

Respond with a JSON object containing:
{{
    "topic_relevance": <score 0-100>,
    "author_overlap": <score 0-100>,
    "temporal_validity": <score 0-100>,
    "research_continuity": <score 0-100>,
    "overall_confidence": <score 0-100>,
    "reasoning": "<brief explanation of the match assessment>"
}}
"""
        return prompt
    
    def get_llm_assessment(self, grant_info: Dict, publication_info: Dict) -> Dict:
        """Get LLM assessment of grant-publication match"""
        try:
            prompt = self.create_matching_prompt(grant_info, publication_info)
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert research analyst specializing in matching research grants to their resulting publications. Provide accurate, objective assessments."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            # Parse JSON response
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response if it contains other text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_text = response_text[json_start:json_end]
                return json.loads(json_text)
            else:
                return json.loads(response_text)
                
        except Exception as e:
            print(f"Error in LLM assessment: {e}")
            return {
                "topic_relevance": 0,
                "author_overlap": 0,
                "temporal_validity": 0,
                "research_continuity": 0,
                "overall_confidence": 0,
                "reasoning": f"Error: {str(e)}"
            }
    
    def match_grants_to_publications(self, grants_df: pd.DataFrame, publications_df: pd.DataFrame, 
                                   confidence_threshold: float = 30.0) -> pd.DataFrame:
        """Match each publication to the best fitting grant"""
        
        results = []
        total_pubs = len(publications_df)
        
        print(f"Processing {total_pubs} publications...")
        
        for pub_idx, pub_row in publications_df.iterrows():
            print(f"Processing publication {pub_idx + 1}/{total_pubs}")
            
            best_match = None
            best_confidence = 0
            
            publication_info = {
                'title': pub_row.get('title', ''),
                'authors': pub_row.get('authors_list', ''),
                'year': pub_row.get('publication_year', ''),
                'doi': pub_row.get('doi', '')
            }
            
            # Check against each grant
            for grant_idx, grant_row in grants_df.iterrows():
                # Pre-calculate author overlap and temporal validity
                author_overlap = self.calculate_author_overlap(
                    str(grant_row.get('Lead Investigator', '')) + ', ' + str(grant_row.get('Co-investigators', '')),
                    publication_info['authors']
                )
                
                temporal_valid = self.check_temporal_validity(
                    grant_row.get('Start Date', ''),
                    publication_info['year']
                )
                
                grant_info = {
                    'title': grant_row.get('Grant Title', ''),
                    'lead_investigator': grant_row.get('Lead Investigator', ''),
                    'co_investigators': grant_row.get('Co-investigators', ''),
                    'start_date': grant_row.get('Start Date', ''),
                    'end_date': grant_row.get('End Date', ''),
                    'author_overlap_score': author_overlap * 100,
                    'temporal_valid': temporal_valid
                }
                
                # Skip if no author overlap and not temporally valid
                if author_overlap == 0 and not temporal_valid:
                    continue
                
                # Get LLM assessment
                assessment = self.get_llm_assessment(grant_info, publication_info)
                confidence = assessment.get('overall_confidence', 0)
                
                if confidence > best_confidence and confidence >= confidence_threshold:
                    best_confidence = confidence
                    best_match = {
                        'grant_title': grant_info['title'],
                        'grant_index': grant_idx,
                        'confidence': confidence,
                        'assessment': assessment
                    }
            
            # Create result row
            result_row = pub_row.copy()
            
            if best_match:
                result_row['matched_grant_title'] = best_match['grant_title']
                result_row['confidence_score'] = best_match['confidence']
                result_row['topic_relevance'] = best_match['assessment'].get('topic_relevance', 0)
                result_row['author_overlap'] = best_match['assessment'].get('author_overlap', 0)
                result_row['temporal_validity'] = best_match['assessment'].get('temporal_validity', 0)
                result_row['research_continuity'] = best_match['assessment'].get('research_continuity', 0)
                result_row['matching_reasoning'] = best_match['assessment'].get('reasoning', '')
            else:
                result_row['matched_grant_title'] = 'No match found'
                result_row['confidence_score'] = 0
                result_row['topic_relevance'] = 0
                result_row['author_overlap'] = 0
                result_row['temporal_validity'] = 0
                result_row['research_continuity'] = 0
                result_row['matching_reasoning'] = 'No grants met minimum confidence threshold'
            
            results.append(result_row)
        
        return pd.DataFrame(results)
    
    def save_results(self, results_df: pd.DataFrame, output_file: str):
        """Save results to Excel file"""
        print(f"Saving results to {output_file}")
        
        # Reorder columns to put matching info at the end
        original_cols = ['title', 'publication_year', 'authors_list', 'doi', 'crossref_type', 'key']
        new_cols = ['matched_grant_title', 'confidence_score', 'topic_relevance', 'author_overlap', 
                   'temporal_validity', 'research_continuity', 'matching_reasoning']
        
        column_order = original_cols + new_cols
        results_df = results_df.reindex(columns=column_order)
        
        results_df.to_excel(output_file, index=False)
        print(f"Results saved successfully!")
        
        # Print summary statistics
        matched_pubs = len(results_df[results_df['confidence_score'] > 0])
        total_pubs = len(results_df)
        avg_confidence = results_df[results_df['confidence_score'] > 0]['confidence_score'].mean()
        
        print(f"\nSUMMARY:")
        print(f"Total publications: {total_pubs}")
        print(f"Matched publications: {matched_pubs}")
        print(f"Match rate: {matched_pubs/total_pubs*100:.1f}%")
        print(f"Average confidence score (matched): {avg_confidence:.1f}")

def main():
    """Main execution function"""
    # Initialize matcher
    matcher = GrantPublicationMatcher()
    
    # File paths
    grants_file = "barbara dicker grants.xlsx"
    publications_file = "Merged Publications Final.csv"
    output_file = "Grant_Publication_Matches.xlsx"
    
    try:
        # Load data
        grants_df, publications_df = matcher.load_data(grants_file, publications_file)
        
        # Perform matching
        results_df = matcher.match_grants_to_publications(grants_df, publications_df)
        
        # Save results
        matcher.save_results(results_df, output_file)
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("1. Both input files exist in the current directory")
        print("2. OpenAI API key is set in OPENAI_API_KEY environment variable")
        print("3. Required packages are installed: pip install pandas openai openpyxl")

if __name__ == "__main__":
    main()