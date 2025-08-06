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

# LLM Configuration - uses environment variables for security
LLM_CONFIG = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "api_key": os.getenv("OPENAI_API_KEY"),  # Get from environment
    "delay_between_calls": 0.3,
    "pre_filter_threshold": 0.3,
    "max_grants_per_publication": 3
}

def setup_llm_client():
    """Setup OpenAI client with environment variable API key"""
    api_key = LLM_CONFIG["api_key"]
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    return openai.OpenAI(api_key=api_key)

def calculate_similarity(pub_title: str, grant_title: str, pub_authors: str, grant_investigators: str) -> float:
    """Calculate similarity for pre-filtering"""
    if not pub_title or not grant_title:
        return 0.0
    
    # Enhanced similarity calculation
    title_sim = fuzz.token_set_ratio(pub_title.lower(), grant_title.lower()) / 100.0
    author_sim = 0.0
    
    if pub_authors and grant_investigators:
        author_sim = fuzz.token_set_ratio(pub_authors.lower(), grant_investigators.lower()) / 100.0
    
    return title_sim * 0.8 + author_sim * 0.2

def create_matching_prompt(pub_title: str, pub_authors: str, pub_year: int,
                          grant_title: str, grant_investigators: str, grant_start_date: str) -> str:
    """Create optimized prompt for LLM matching"""
    return f"""Analyze if this publication could result from this grant:

PUBLICATION: "{pub_title}" ({pub_year}) - Authors: {pub_authors}
GRANT: "{grant_title}" (Started: {grant_start_date}) - Investigators: {grant_investigators}

Assess topic overlap, author overlap, timeline validity, and research continuity.

JSON response:
{{"match": true/false, "confidence": "Very High/High/Medium/Low", "topic_score": 0-100, "author_score": 0-100, "reasoning": "brief explanation"}}"""

def call_llm(client, prompt: str) -> Optional[str]:
    """Call LLM with error handling"""
    try:
        response = client.chat.completions.create(
            model=LLM_CONFIG["model"],
            messages=[
                {"role": "system", "content": "Research matching assistant. Provide precise JSON responses."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=400
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"API error: {e}")
        return None

def parse_llm_response(response: str) -> Dict:
    """Parse LLM JSON response"""
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                'match': result.get('match', False),
                'confidence': result.get('confidence', 'Low'),
                'topic_score': float(result.get('topic_score', 0)),
                'author_score': float(result.get('author_score', 0)),
                'reasoning': result.get('reasoning', '')
            }
    except Exception:
        pass
    
    return {
        'match': False, 'confidence': 'Low', 'topic_score': 0.0,
        'author_score': 0.0, 'reasoning': 'Parse failed'
    }

def is_temporally_valid(publication_year: int, grant_start_date: str) -> bool:
    """Check if publication is after grant start"""
    try:
        grant_year = pd.to_datetime(grant_start_date).year
        return publication_year >= grant_year
    except:
        return False

def combine_investigators(primary: str, others: str) -> str:
    """Combine investigator names"""
    investigators = []
    if primary and str(primary) != 'nan':
        investigators.append(str(primary))
    if others and str(others) != 'nan':
        investigators.append(str(others))
    return ', '.join(investigators)

def main():
    """Main LLM-based grant matching function"""
    print("LLM-Based Grant-to-Publication Matching")
    print("=" * 50)
    
    # Setup
    try:
        client = setup_llm_client()
        print("✓ LLM client initialized")
    except Exception as e:
        print(f"✗ LLM setup failed: {e}")
        print("Please set OPENAI_API_KEY environment variable")
        return
    
    # Load data
    print("\nLoading data...")
    try:
        grants_df = pd.read_excel("barbara dicker grants.xlsx")
        publications_df = pd.read_csv("Merged Publications Final.csv")
        print(f"✓ Loaded {len(grants_df)} grants and {len(publications_df)} publications")
    except Exception as e:
        print(f"✗ Data loading failed: {e}")
        return
    
    # Process grants
    grants_processed = []
    for _, row in grants_df.iterrows():
        if pd.notna(row['TITLE']) and pd.notna(row['Start Date']):
            all_investigators = combine_investigators(
                row['Preferred Full Name'] if pd.notna(row['Preferred Full Name']) else "",
                row['Other Investigators'] if pd.notna(row['Other Investigators']) else ""
            )
            
            if all_investigators:
                grants_processed.append({
                    'code': str(row['Project Code']),
                    'title': str(row['TITLE']),
                    'start_date': row['Start Date'].strftime('%Y-%m-%d'),
                    'investigators': all_investigators
                })
    
    print(f"✓ Processed {len(grants_processed)} valid grants")
    
    # Initialize result columns
    publications_df['grant_title'] = ''
    publications_df['grant_code'] = ''
    publications_df['grant_investigators'] = ''
    publications_df['grant_start_date'] = ''
    publications_df['match_confidence'] = ''
    publications_df['llm_reasoning'] = ''
    publications_df['topic_score'] = 0.0
    publications_df['author_score'] = 0.0
    publications_df['similarity_score'] = 0.0
    
    # Process publications
    print(f"\nProcessing publications with LLM analysis...")
    api_calls = 0
    matches_found = 0
    start_time = time.time()
    
    for pub_idx, pub_row in publications_df.iterrows():
        pub_title = str(pub_row['title']) if pd.notna(pub_row['title']) else ""
        pub_authors = str(pub_row['authors_list']) if pd.notna(pub_row['authors_list']) else ""
        pub_year = pub_row['publication_year'] if pd.notna(pub_row['publication_year']) else None
        
        if not pub_title:
            continue
        
        # Pre-filter grants by similarity and temporal validity
        candidates = []
        for grant in grants_processed:
            if is_temporally_valid(pub_year, grant['start_date']):
                sim = calculate_similarity(pub_title, grant['title'], pub_authors, grant['investigators'])
                if sim >= LLM_CONFIG["pre_filter_threshold"]:
                    candidates.append((sim, grant))
        
        # Sort by similarity and take top candidates
        candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = candidates[:LLM_CONFIG["max_grants_per_publication"]]
        
        if not top_candidates:
            continue
        
        # LLM analysis for top candidates
        best_match = None
        best_score = 0
        
        for sim, grant in top_candidates:
            prompt = create_matching_prompt(
                pub_title, pub_authors, pub_year,
                grant['title'], grant['investigators'], grant['start_date']
            )
            
            llm_response = call_llm(client, prompt)
            api_calls += 1
            
            if llm_response:
                result = parse_llm_response(llm_response)
                if result['match']:
                    combined_score = result['topic_score'] * 0.007 + result['author_score'] * 0.003 + sim * 0.3
                    
                    if combined_score > best_score:
                        best_score = combined_score
                        best_match = {
                            'grant': grant,
                            'result': result,
                            'similarity': sim
                        }
            
            time.sleep(LLM_CONFIG["delay_between_calls"])
        
        # Store best match
        if best_match:
            grant = best_match['grant']
            result = best_match['result']
            
            publications_df.at[pub_idx, 'grant_title'] = grant['title']
            publications_df.at[pub_idx, 'grant_code'] = grant['code']
            publications_df.at[pub_idx, 'grant_investigators'] = grant['investigators']
            publications_df.at[pub_idx, 'grant_start_date'] = grant['start_date']
            publications_df.at[pub_idx, 'match_confidence'] = result['confidence']
            publications_df.at[pub_idx, 'llm_reasoning'] = result['reasoning']
            publications_df.at[pub_idx, 'topic_score'] = result['topic_score']
            publications_df.at[pub_idx, 'author_score'] = result['author_score']
            publications_df.at[pub_idx, 'similarity_score'] = best_match['similarity']
            matches_found += 1
        
        # Progress reporting
        if (pub_idx + 1) % 50 == 0:
            elapsed = time.time() - start_time
            rate = (pub_idx + 1) / elapsed * 60 if elapsed > 0 else 0
            eta = (len(publications_df) - pub_idx - 1) / rate if rate > 0 else 0
            
            print(f"{pub_idx + 1}/{len(publications_df)} | API: {api_calls} | Matches: {matches_found} | "
                  f"{rate:.1f}/min | ETA: {eta:.1f}min")
    
    # Results summary
    elapsed = time.time() - start_time
    print(f"\n" + "=" * 50)
    print(f"LLM Matching Complete!")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"API calls: {api_calls}")
    print(f"Matches found: {matches_found} ({matches_found/len(publications_df)*100:.1f}%)")
    print(f"Estimated cost: ~${api_calls * 0.0002:.2f}")
    
    # Save results
    output_file = "LLM Grant Publication Matches.csv"
    publications_df.to_csv(output_file, index=False)
    print(f"\nResults saved to: {output_file}")
    
    # Confidence distribution
    if matches_found > 0:
        conf_counts = publications_df[publications_df['match_confidence'] != '']['match_confidence'].value_counts()
        print(f"\nConfidence Distribution:")
        for conf in ['Very High', 'High', 'Medium', 'Low']:
            count = conf_counts.get(conf, 0)
            print(f"  {conf}: {count}")

if __name__ == "__main__":
    main()