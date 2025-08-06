import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import re
import csv
from difflib import SequenceMatcher
import json
import time
import os
from typing import List, Dict, Tuple, Optional
from datetime import datetime

def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two text strings using multiple methods"""
    if not text1 or not text2:
        return 0.0
    
    # Clean and normalize text
    text1_clean = re.sub(r'[^\w\s]', '', text1.lower().strip())
    text2_clean = re.sub(r'[^\w\s]', '', text2.lower().strip())
    
    # Multiple similarity measures
    fuzz_ratio = fuzz.ratio(text1_clean, text2_clean) / 100.0
    fuzz_partial = fuzz.partial_ratio(text1_clean, text2_clean) / 100.0
    fuzz_token_sort = fuzz.token_sort_ratio(text1_clean, text2_clean) / 100.0
    fuzz_token_set = fuzz.token_set_ratio(text1_clean, text2_clean) / 100.0
    
    # Sequence matcher
    seq_match = SequenceMatcher(None, text1_clean, text2_clean).ratio()
    
    # Word overlap (more sophisticated)
    words1 = set(text1_clean.split())
    words2 = set(text2_clean.split())
    if len(words1) == 0 or len(words2) == 0:
        word_overlap = 0.0
    else:
        # Common significant words (3+ chars)
        significant_words1 = {w for w in words1 if len(w) >= 3}
        significant_words2 = {w for w in words2 if len(w) >= 3}
        if significant_words1 and significant_words2:
            word_overlap = len(significant_words1.intersection(significant_words2)) / min(len(significant_words1), len(significant_words2))
        else:
            word_overlap = 0.0
    
    # Combined score (weighted average)
    combined_score = (
        fuzz_ratio * 0.15 +
        fuzz_partial * 0.15 +
        fuzz_token_sort * 0.25 +
        fuzz_token_set * 0.25 +
        seq_match * 0.1 +
        word_overlap * 0.1
    )
    
    return combined_score

def normalize_name(name: str) -> str:
    """Normalize a name for comparison"""
    if not name:
        return ""
    
    # Remove common titles and suffixes
    name = re.sub(r'\b(dr|prof|professor|mr|mrs|ms|phd|md)\b\.?', '', name.lower())
    # Remove extra whitespace
    name = ' '.join(name.split())
    return name.strip()

def calculate_author_similarity(grant_investigators: str, publication_authors: str) -> float:
    """Calculate similarity between grant investigators and publication authors"""
    if not grant_investigators or not publication_authors:
        return 0.0
    
    # Split and clean names
    investigators = [normalize_name(name.strip()) for name in grant_investigators.split(',')]
    authors = [normalize_name(name.strip()) for name in publication_authors.split(',')]
    
    # Remove empty names
    investigators = [name for name in investigators if name]
    authors = [name for name in authors if name]
    
    if not investigators or not authors:
        return 0.0
    
    # Check for exact matches and partial matches
    exact_matches = 0
    partial_matches = 0
    
    for investigator in investigators:
        investigator_parts = investigator.split()
        
        best_match_score = 0
        
        for author in authors:
            author_parts = author.split()
            
            # Exact match
            if investigator == author:
                exact_matches += 1
                best_match_score = 1.0
                break
            
            # Check if all parts of investigator name appear in author name or vice versa
            if len(investigator_parts) >= 2 and len(author_parts) >= 2:
                # Last name match + first initial/name match
                if (investigator_parts[-1] == author_parts[-1] and 
                    (investigator_parts[0][0] == author_parts[0][0] or investigator_parts[0] == author_parts[0])):
                    best_match_score = max(best_match_score, 0.8)
                
                # Fuzzy matching for similar names
                name_similarity = fuzz.ratio(investigator, author) / 100.0
                if name_similarity > 0.8:
                    best_match_score = max(best_match_score, name_similarity * 0.9)
        
        if best_match_score >= 0.8:
            if best_match_score == 1.0:
                exact_matches += 1
            else:
                partial_matches += 1
    
    total_investigators = len(investigators)
    if total_investigators == 0:
        return 0.0
    
    # Calculate similarity score
    exact_weight = 1.0
    partial_weight = 0.8
    
    similarity = (exact_matches * exact_weight + partial_matches * partial_weight) / total_investigators
    return min(similarity, 1.0)

def is_temporally_valid(publication_year: int, grant_start_date: pd.Timestamp) -> bool:
    """Check if publication date is after grant start date"""
    if pd.isna(grant_start_date) or pd.isna(publication_year):
        return False
    
    # Extract year from grant start date
    grant_start_year = grant_start_date.year
    
    # Publication must be in the same year as grant start or later
    return publication_year >= grant_start_year

def determine_confidence_level(title_similarity: float, author_similarity: float) -> str:
    """Determine confidence level based on title and author similarities"""
    # More sophisticated confidence scoring
    
    # Title similarity thresholds
    title_very_high = 0.8
    title_high = 0.6
    title_medium = 0.4
    title_low = 0.25
    
    # Author similarity thresholds
    author_very_high = 0.8
    author_high = 0.5
    author_medium = 0.3
    author_low = 0.1
    
    # Combined weighted score (title more important for topic matching)
    combined_score = title_similarity * 0.7 + author_similarity * 0.3
    
    # Determine confidence based on both individual and combined scores
    if (title_similarity >= title_very_high and author_similarity >= author_high) or \
       (title_similarity >= title_high and author_similarity >= author_very_high):
        return "Very High"
    elif (title_similarity >= title_high and author_similarity >= author_medium) or \
         (title_similarity >= title_medium and author_similarity >= author_high) or \
         combined_score >= 0.7:
        return "High"
    elif (title_similarity >= title_medium and author_similarity >= author_low) or \
         (title_similarity >= title_low and author_similarity >= author_medium) or \
         combined_score >= 0.5:
        return "Medium"
    elif title_similarity >= title_low or author_similarity >= author_low or combined_score >= 0.3:
        return "Low"
    else:
        return "Very Low"

def combine_investigators(primary_investigator: str, other_investigators: str) -> str:
    """Combine primary investigator with other investigators"""
    investigators = []
    
    if primary_investigator and str(primary_investigator) != 'nan':
        investigators.append(str(primary_investigator))
    
    if other_investigators and str(other_investigators) != 'nan':
        investigators.append(str(other_investigators))
    
    return ', '.join(investigators)

def main():
    # File paths
    grants_file = "barbara dicker grants.xlsx"
    publications_file = "Merged Publications Final.csv"
    output_file = "Mapped grants with publications - Temporal Validation.csv"
    
    print("Starting temporally-validated grant-to-publication matching...")
    
    # Parse grants file
    print(f"\n1. Parsing grants file: {grants_file}")
    try:
        grants_df = pd.read_excel(grants_file)
        print(f"Successfully loaded grants file with {len(grants_df)} rows")
    except Exception as e:
        print(f"Error reading grants file: {e}")
        return
    
    # Load publications file
    print(f"\n2. Loading publications file: {publications_file}")
    try:
        publications_df = pd.read_csv(publications_file)
        print(f"Successfully loaded publications file with {len(publications_df)} rows")
    except Exception as e:
        print(f"Error reading publications file: {e}")
        return
    
    # Initialize new columns for grant mapping
    publications_df['grant_title'] = ''
    publications_df['grant_investigators'] = ''
    publications_df['grant_code'] = ''
    publications_df['grant_start_date'] = ''
    publications_df['temporal_validity'] = ''
    publications_df['match_confidence'] = ''
    publications_df['title_similarity_score'] = 0.0
    publications_df['author_similarity_score'] = 0.0
    publications_df['combined_similarity_score'] = 0.0
    
    # Process grants data
    print(f"\n3. Processing grants data with temporal information...")
    grants_processed = []
    
    for idx, grant_row in grants_df.iterrows():
        grant_data = {
            'code': str(grant_row['Project Code']) if pd.notna(grant_row['Project Code']) else "",
            'title': str(grant_row['TITLE']) if pd.notna(grant_row['TITLE']) else "",
            'primary_investigator': str(grant_row['Preferred Full Name']) if pd.notna(grant_row['Preferred Full Name']) else "",
            'other_investigators': str(grant_row['Other Investigators']) if pd.notna(grant_row['Other Investigators']) else "",
            'start_date': grant_row['Start Date'] if pd.notna(grant_row['Start Date']) else None,
            'all_investigators': combine_investigators(
                grant_row['Preferred Full Name'] if pd.notna(grant_row['Preferred Full Name']) else "",
                grant_row['Other Investigators'] if pd.notna(grant_row['Other Investigators']) else ""
            )
        }
        
        if grant_data['title'] and grant_data['all_investigators'] and grant_data['start_date']:
            grants_processed.append(grant_data)
    
    print(f"Processed {len(grants_processed)} grants with complete data and start dates")
    
    # Sample of grants being processed
    print(f"\nSample grants with temporal data:")
    for i, grant in enumerate(grants_processed[:3]):
        print(f"Grant {i+1}:")
        print(f"  Title: {grant['title']}")
        print(f"  Start Date: {grant['start_date']}")
        print(f"  Investigators: {grant['all_investigators']}")
    
    # Perform matching with temporal validation
    print(f"\n4. Matching {len(publications_df)} publications with {len(grants_processed)} grants (with temporal validation)...")
    
    matches_found = 0
    high_confidence_matches = 0
    temporal_violations_filtered = 0
    
    for pub_idx, pub_row in publications_df.iterrows():
        pub_title = str(pub_row['title']) if pd.notna(pub_row['title']) else ""
        pub_authors = str(pub_row['authors_list']) if pd.notna(pub_row['authors_list']) else ""
        pub_year = pub_row['publication_year'] if pd.notna(pub_row['publication_year']) else None
        
        best_match = {
            'grant_code': '',
            'grant_title': '',
            'grant_investigators': '',
            'grant_start_date': '',
            'temporal_validity': 'Invalid',
            'confidence': 'No Match',
            'title_similarity': 0.0,
            'author_similarity': 0.0,
            'combined_similarity': 0.0
        }
        
        for grant in grants_processed:
            # First check temporal validity
            if not is_temporally_valid(pub_year, grant['start_date']):
                temporal_violations_filtered += 1
                continue  # Skip this grant if temporally invalid
            
            # Calculate similarities only for temporally valid matches
            title_sim = calculate_text_similarity(pub_title, grant['title'])
            author_sim = calculate_author_similarity(grant['all_investigators'], pub_authors)
            combined_sim = title_sim * 0.7 + author_sim * 0.3
            
            # Update best match if this is better
            if combined_sim > best_match['combined_similarity']:
                confidence = determine_confidence_level(title_sim, author_sim)
                best_match = {
                    'grant_code': grant['code'],
                    'grant_title': grant['title'],
                    'grant_investigators': grant['all_investigators'],
                    'grant_start_date': grant['start_date'].strftime('%Y-%m-%d'),
                    'temporal_validity': 'Valid',
                    'confidence': confidence,
                    'title_similarity': title_sim,
                    'author_similarity': author_sim,
                    'combined_similarity': combined_sim
                }
        
        # Only keep matches with reasonable confidence
        if best_match['combined_similarity'] >= 0.2:  # Minimum threshold
            publications_df.at[pub_idx, 'grant_code'] = best_match['grant_code']
            publications_df.at[pub_idx, 'grant_title'] = best_match['grant_title']
            publications_df.at[pub_idx, 'grant_investigators'] = best_match['grant_investigators']
            publications_df.at[pub_idx, 'grant_start_date'] = best_match['grant_start_date']
            publications_df.at[pub_idx, 'temporal_validity'] = best_match['temporal_validity']
            publications_df.at[pub_idx, 'match_confidence'] = best_match['confidence']
            publications_df.at[pub_idx, 'title_similarity_score'] = best_match['title_similarity']
            publications_df.at[pub_idx, 'author_similarity_score'] = best_match['author_similarity']
            publications_df.at[pub_idx, 'combined_similarity_score'] = best_match['combined_similarity']
            matches_found += 1
            
            if best_match['confidence'] in ['Very High', 'High', 'Medium']:
                high_confidence_matches += 1
        
        # Progress indicator
        if (pub_idx + 1) % 100 == 0:
            print(f"Processed {pub_idx + 1}/{len(publications_df)} publications...")
    
    print(f"\n5. Matching complete with temporal validation!")
    print(f"Found {matches_found} temporally valid matches")
    print(f"High confidence matches (Medium+): {high_confidence_matches}")
    print(f"Grant-publication pairs filtered due to temporal violations: {temporal_violations_filtered}")
    
    # Save results
    print(f"\n6. Saving results to: {output_file}")
    publications_df.to_csv(output_file, index=False)
    
    # Display summary statistics
    print(f"\nSummary with Temporal Validation:")
    print(f"Total publications: {len(publications_df)}")
    print(f"Publications with temporally valid matches: {matches_found}")
    print(f"Match rate: {matches_found/len(publications_df)*100:.1f}%")
    print(f"High confidence match rate: {high_confidence_matches/len(publications_df)*100:.1f}%")
    
    if matches_found > 0:
        confidence_counts = publications_df[publications_df['match_confidence'] != '']['match_confidence'].value_counts()
        print(f"\nConfidence level distribution:")
        for conf_level in ['Very High', 'High', 'Medium', 'Low', 'Very Low']:
            count = confidence_counts.get(conf_level, 0)
            percentage = count / matches_found * 100 if matches_found > 0 else 0
            print(f"  {conf_level}: {count} ({percentage:.1f}%)")
    
    # Show temporal validation impact
    print(f"\nTemporal Validation Impact:")
    print(f"  Total potential grant-publication combinations: {len(publications_df) * len(grants_processed):,}")
    print(f"  Combinations filtered due to temporal violations: {temporal_violations_filtered:,}")
    print(f"  Temporal filter effectiveness: {temporal_violations_filtered/(len(publications_df) * len(grants_processed))*100:.1f}% filtered")
    
    # Show some sample matches with temporal info
    valid_matches = publications_df[publications_df['temporal_validity'] == 'Valid'].head(5)
    if len(valid_matches) > 0:
        print(f"\nSample temporally valid matches:")
        for i, (idx, row) in enumerate(valid_matches.iterrows()):
            print(f"\n{i+1}. Confidence: {row['match_confidence']}")
            print(f"   Publication ({row['publication_year']}): {row['title'][:60]}...")
            print(f"   Grant (started {row['grant_start_date']}): {row['grant_title'][:60]}...")
            print(f"   Temporal validity: {row['temporal_validity']}")
    
    print(f"\nResults saved to '{output_file}'")

if __name__ == "__main__":
    main()