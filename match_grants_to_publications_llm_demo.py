import pandas as pd
import numpy as np
import json
import time
import os
import re
from typing import List, Dict, Optional
from datetime import datetime
from fuzzywuzzy import fuzz
import openai
import configparser

# Demo Configuration
DEMO_MODE = True
TEST_LIMIT = 20  # Limit to first 20 publications for demo

# LLM Configuration
LLM_CONFIG = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "api_key": os.getenv("OPENAI_API_KEY"),
    "delay_between_calls": 0.5,
    "pre_filter_threshold": 0.2,
    "max_grants_per_publication": 5
}

def setup_llm_client():
    """Setup OpenAI client"""
    api_key = LLM_CONFIG["api_key"]
    if not api_key:
        # Try to load from config.ini
        try:
            config = configparser.ConfigParser()
            config.read('config.ini')
            api_key = config.get('openai', 'api_key')
            print("API key loaded from config.ini")
        except Exception as e:
            print(f"Warning: Could not load API key from config.ini: {e}")
            print("Please set OPENAI_API_KEY environment variable or add API key to config.ini")
            return None
    return openai.OpenAI(api_key=api_key)

def calculate_similarity_score(pub_title: str, grant_title: str, pub_authors: str, grant_investigators: str) -> float:
    """Calculate basic similarity score for pre-filtering"""
    if not pub_title or not grant_title:
        return 0.0
    
    # Title similarity (main component)
    title_similarity = fuzz.token_set_ratio(pub_title.lower(), grant_title.lower()) / 100.0
    
    # Author similarity (if available)
    author_similarity = 0.0
    if pub_authors and grant_investigators:
        author_similarity = fuzz.token_set_ratio(pub_authors.lower(), grant_investigators.lower()) / 100.0
    
    # Weighted combination
    combined_score = title_similarity * 0.8 + author_similarity * 0.2
    return combined_score

def create_llm_matching_prompt(pub_title: str, pub_authors: str, pub_year: int,
                               grant_title: str, grant_investigators: str, grant_start_date: str) -> str:
    """Create detailed prompt for LLM grant-publication matching"""
    prompt = f"""You are a research matching expert. Analyze whether this publication could plausibly result from this grant.

PUBLICATION:
Title: "{pub_title}"
Year: {pub_year}
Authors: {pub_authors}

GRANT:
Title: "{grant_title}"
Start Date: {grant_start_date}
Investigators: {grant_investigators}

ANALYSIS REQUIREMENTS:
1. Topic Relevance: Assess research questions, methodologies, and domain overlap
2. Author Overlap: Check for name variations and research team continuity
3. Temporal Validity: Ensure publication is after grant start date
4. Research Continuity: Evaluate if this could be a plausible research outcome

RESPONSE FORMAT (JSON only):
{{
    "match": true/false,
    "confidence": "Very High/High/Medium/Low/Very Low",
    "topic_relevance_score": 0-100,
    "author_overlap_score": 0-100,
    "temporal_valid": true/false,
    "reasoning": "Brief explanation of matching decision",
    "matched_authors": ["list", "of", "overlapping", "authors"]
}}"""
    return prompt

def call_llm_api(client, prompt: str) -> Optional[str]:
    """Call LLM API with error handling and retries"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=LLM_CONFIG["model"],
                messages=[
                    {"role": "system", "content": "You are a precise research matching assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"API call failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    return None

def parse_llm_json_response(response: str) -> Dict:
    """Parse and validate LLM JSON response"""
    try:
        # Extract JSON from response (in case there's extra text)
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            result = json.loads(json_str)
            
            # Validate and normalize response
            return {
                'match': result.get('match', False),
                'confidence': result.get('confidence', 'Low'),
                'topic_relevance_score': float(result.get('topic_relevance_score', 0)),
                'author_overlap_score': float(result.get('author_overlap_score', 0)),
                'temporal_valid': result.get('temporal_valid', False),
                'reasoning': result.get('reasoning', 'No reasoning provided'),
                'matched_authors': result.get('matched_authors', [])
            }
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"Failed to parse LLM response: {e}")
    
    # Return default response on parse failure
    return {
        'match': False, 
        'confidence': 'Low', 
        'topic_relevance_score': 0.0,
        'author_overlap_score': 0.0, 
        'temporal_valid': False,
        'reasoning': 'Failed to parse LLM response',
        'matched_authors': []
    }

def check_temporal_validity(publication_year: int, grant_start_date: str) -> bool:
    """Check if publication date is after grant start date"""
    try:
        grant_start = pd.to_datetime(grant_start_date)
        return publication_year >= grant_start.year
    except:
        return False

def format_investigators_list(primary_investigator: str, other_investigators: str) -> str:
    """Combine and format investigator names"""
    investigators = []
    
    if primary_investigator and str(primary_investigator) != 'nan':
        investigators.append(str(primary_investigator))
    
    if other_investigators and str(other_investigators) != 'nan':
        investigators.append(str(other_investigators))
    
    return ', '.join(investigators)

def main():
    """Main demo function for LLM-based grant matching"""
    print("LLM-Based Grant-to-Publication Matching Demo")
    print("=" * 60)
    
    if DEMO_MODE:
        print(f"DEMO MODE: Processing first {TEST_LIMIT} publications only")
    
    # Initialize LLM client
    print("\n Setting up LLM client...")
    try:
        client = setup_llm_client()
        print(" LLM client initialized successfully")
    except Exception as e:
        print(f" Failed to initialize LLM client: {e}")
        return
    
    # Load data files
    print("\n Loading data files...")
    try:
        # Load grants data
        grants_df = pd.read_excel("barbara dicker grants.xlsx")
        print(f" Loaded {len(grants_df)} grants from Excel file")
        
        # Load publications data
        publications_df = pd.read_csv("Merged Publications Final.csv")
        if DEMO_MODE and TEST_LIMIT:
            publications_df = publications_df.head(TEST_LIMIT)
        print(f" Loaded {len(publications_df)} publications from CSV file")
        
    except Exception as e:
        print(f" Error loading data files: {e}")
        return
    
    # Process grants data
    print("\n Processing grants data...")
    processed_grants = []
    
    for idx, grant_row in grants_df.iterrows():
        if pd.notna(grant_row['TITLE']) and pd.notna(grant_row['Start Date']):
            # Combine all investigators
            all_investigators = format_investigators_list(
                grant_row.get('Preferred Full Name', ''),
                grant_row.get('Other Investigators', '')
            )
            
            if all_investigators:  # Only include grants with investigators
                grant_info = {
                    'code': str(grant_row['Project Code']),
                    'title': str(grant_row['TITLE']),
                    'start_date': grant_row['Start Date'].strftime('%Y-%m-%d'),
                    'investigators': all_investigators
                }
                processed_grants.append(grant_info)
    
    print(f" Processed {len(processed_grants)} valid grants with investigators")
    
    # Initialize result columns in publications dataframe
    publications_df['grant_title'] = ''
    publications_df['grant_investigators'] = ''
    publications_df['grant_code'] = ''
    publications_df['grant_start_date'] = ''
    publications_df['temporal_validity'] = False
    publications_df['match_confidence'] = ''
    publications_df['llm_reasoning'] = ''
    publications_df['topic_relevance_score'] = 0.0
    publications_df['author_overlap_score'] = 0.0
    publications_df['matched_authors'] = ''
    publications_df['llm_mode'] = f"{LLM_CONFIG['provider']}-{LLM_CONFIG['model']}"
    
    # Start matching process
    print(f"\n Starting LLM-based matching process...")
    total_api_calls = 0
    successful_matches = 0
    start_time = time.time()
    
    for pub_index, pub_row in publications_df.iterrows():
        pub_title = str(pub_row['title']) if pd.notna(pub_row['title']) else ""
        pub_authors = str(pub_row['authors_list']) if pd.notna(pub_row['authors_list']) else ""
        pub_year = pub_row['publication_year'] if pd.notna(pub_row['publication_year']) else None
        
        if not pub_title:
            continue
        
        # Pre-filter grants using similarity and temporal constraints
        candidate_grants = []
        for grant in processed_grants:
            # Check temporal validity first
            if check_temporal_validity(pub_year, grant['start_date']):
                # Calculate similarity score
                similarity = calculate_similarity_score(
                    pub_title, grant['title'], pub_authors, grant['investigators']
                )
                
                if similarity >= LLM_CONFIG["pre_filter_threshold"]:
                    candidate_grants.append((similarity, grant))
        
        # Sort candidates by similarity and limit to top matches
        candidate_grants.sort(key=lambda x: x[0], reverse=True)
        top_candidates = candidate_grants[:LLM_CONFIG["max_grants_per_publication"]]
        
        if not top_candidates:
            continue
        
        # Analyze top candidates with LLM
        best_match = None
        highest_score = 0
        
        for similarity_score, grant in top_candidates:
            # Create LLM prompt
            prompt = create_llm_matching_prompt(
                pub_title, pub_authors, pub_year,
                grant['title'], grant['investigators'], grant['start_date']
            )
            
            # Call LLM API
            llm_response = call_llm_api(client, prompt)
            total_api_calls += 1
            
            if llm_response:
                # Parse LLM response
                analysis = parse_llm_json_response(llm_response)
                
                if analysis['match']:
                    # Calculate combined matching score
                    topic_weight = 0.6
                    author_weight = 0.3
                    similarity_weight = 0.1
                    
                    combined_score = (
                        analysis['topic_relevance_score'] * topic_weight +
                        analysis['author_overlap_score'] * author_weight +
                        similarity_score * 100 * similarity_weight
                    )
                    
                    if combined_score > highest_score:
                        highest_score = combined_score
                        best_match = {
                            'grant': grant,
                            'analysis': analysis,
                            'similarity': similarity_score
                        }
            
            # Rate limiting between API calls
            time.sleep(LLM_CONFIG["delay_between_calls"])
        
        # Store the best match if found
        if best_match:
            grant = best_match['grant']
            analysis = best_match['analysis']
            
            publications_df.at[pub_index, 'grant_title'] = grant['title']
            publications_df.at[pub_index, 'grant_investigators'] = grant['investigators']
            publications_df.at[pub_index, 'grant_code'] = grant['code']
            publications_df.at[pub_index, 'grant_start_date'] = grant['start_date']
            publications_df.at[pub_index, 'temporal_validity'] = analysis['temporal_valid']
            publications_df.at[pub_index, 'match_confidence'] = analysis['confidence']
            publications_df.at[pub_index, 'llm_reasoning'] = analysis['reasoning']
            publications_df.at[pub_index, 'topic_relevance_score'] = analysis['topic_relevance_score']
            publications_df.at[pub_index, 'author_overlap_score'] = analysis['author_overlap_score']
            publications_df.at[pub_index, 'matched_authors'] = ', '.join(analysis['matched_authors'])
            
            successful_matches += 1
        
        # Progress reporting every 25 publications
        if (pub_index + 1) % 25 == 0:
            elapsed_time = time.time() - start_time
            processing_rate = (pub_index + 1) / elapsed_time * 60  # per minute
            estimated_remaining = (len(publications_df) - pub_index - 1) / processing_rate if processing_rate > 0 else 0
            
            print(f" Progress: {pub_index + 1}/{len(publications_df)} | "
                  f"API calls: {total_api_calls} | Matches: {successful_matches} | "
                  f"Rate: {processing_rate:.1f}/min | ETA: {estimated_remaining:.1f}min")
    
    # Final results summary
    total_elapsed = time.time() - start_time
    print(f"\n" + "=" * 60)
    print(f" LLM Matching Demo Complete!")
    print(f"⏱️  Total time: {total_elapsed/60:.2f} minutes")
    print(f" Total API calls: {total_api_calls}")
    print(f" Successful matches: {successful_matches} out of {len(publications_df)} publications")
    print(f" Match rate: {successful_matches/len(publications_df)*100:.1f}%")
    print(f" Estimated cost: ~${total_api_calls * 0.0002:.3f} USD")
    
    # Save results to CSV
    output_filename = "Mapped grants with publications - LLM Based.csv"
    publications_df.to_csv(output_filename, index=False)
    print(f" Results saved to: {output_filename}")
    
    # Show confidence distribution
    if successful_matches > 0:
        confidence_counts = publications_df[publications_df['match_confidence'] != '']['match_confidence'].value_counts()
        print(f"\n Confidence Distribution:")
        for confidence_level in ['Very High', 'High', 'Medium', 'Low', 'Very Low']:
            count = confidence_counts.get(confidence_level, 0)
            percentage = count / successful_matches * 100 if successful_matches > 0 else 0
            print(f"   {confidence_level}: {count} ({percentage:.1f}%)")
    
    # Show sample matches
    high_confidence_matches = publications_df[
        publications_df['match_confidence'].isin(['Very High', 'High'])
    ].head(3)
    
    if len(high_confidence_matches) > 0:
        print(f"\n Sample High-Confidence Matches:")
        for idx, match in high_confidence_matches.iterrows():
            print(f"    \"{match['title'][:60]}...\"")
            print(f"    Grant: \"{match['grant_title'][:60]}...\"")
            print(f"    Confidence: {match['match_confidence']} | "
                  f"Topic: {match['topic_relevance_score']:.0f}% | "
                  f"Author: {match['author_overlap_score']:.0f}%")
            print(f"    Reasoning: {match['llm_reasoning']}")
            print()

if __name__ == "__main__":
    main()