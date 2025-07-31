import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

def load_grants_data(excel_file):
    """Load grants data from Excel file."""
    df = pd.read_excel(excel_file)
    grants = []
    
    for _, row in df.iterrows():
        grant = {
            'title': str(row['TITLE']).strip(),
            'full_name': str(row['Preferred Full Name']).strip(),
            'start_date': row['Start Date'],
            'end_date': row['End Date']
        }
        grants.append(grant)
    
    return grants

def calculate_similarity(text1, text2):
    """Calculate similarity between two text strings."""
    if not text1 or not text2:
        return 0.0
    
    # Convert to lowercase and remove extra whitespace
    text1 = re.sub(r'\s+', ' ', str(text1).lower().strip())
    text2 = re.sub(r'\s+', ' ', str(text2).lower().strip())
    
    # Use SequenceMatcher for similarity
    similarity = SequenceMatcher(None, text1, text2).ratio()
    
    # Check for key word overlap
    words1 = set(re.findall(r'\b\w{4,}\b', text1))  # Words with 4+ characters
    words2 = set(re.findall(r'\b\w{4,}\b', text2))
    
    if words1 and words2:
        word_overlap = len(words1.intersection(words2)) / len(words1.union(words2))
        # Combine similarity scores
        combined_score = (similarity * 0.4) + (word_overlap * 0.6)
        return combined_score
    
    return similarity

def get_confidence_level(similarity_score):
    """Convert similarity score to confidence level."""
    if similarity_score >= 0.7:
        return "Very High"
    elif similarity_score >= 0.5:
        return "High"
    elif similarity_score >= 0.3:
        return "Medium"
    elif similarity_score >= 0.15:
        return "Low"
    else:
        return "Very Low"

def main():
    print("Loading grants and publications data...")
    
    # Load grants
    grants = load_grants_data("barbara dicker grants.xlsx")
    print(f"Loaded {len(grants)} grants")
    
    # Load publications CSV
    pub_df = pd.read_csv("Merged Publications Fixed.csv")
    print(f"Loaded {len(pub_df)} publications")
    
    # Create new columns
    pub_df['grant'] = ''
    pub_df['confidence_level'] = ''
    
    # Simple matching based on title similarity
    matches_found = 0
    
    print("\\nStarting matching process...")
    
    for i, grant in enumerate(grants):
        if i % 10 == 0:
            print(f"Processing grant {i+1}/{len(grants)}")
        
        grant_title = grant['title']
        researcher = grant['full_name']
        start_year = grant['start_date'].year
        end_year = grant['end_date'].year + 2  # Allow 2 years extension
        
        # Filter publications by researcher and date range
        researcher_pubs = pub_df[
            (pub_df['authors_list'].str.contains(researcher, na=False, case=False)) &
            (pub_df['publication_year'].astype(str).str.extract('(\d{4})')[0].astype(float) >= start_year) &
            (pub_df['publication_year'].astype(str).str.extract('(\d{4})')[0].astype(float) <= end_year)
        ]
        
        if len(researcher_pubs) == 0:
            continue
        
        # Find best matching publication
        best_match_idx = None
        best_similarity = 0.0
        
        for idx, row in researcher_pubs.iterrows():
            pub_title = row['title']
            similarity = calculate_similarity(grant_title, pub_title)
            
            if similarity > best_similarity and similarity >= 0.15:  # Minimum threshold
                best_similarity = similarity
                best_match_idx = idx
        
        # Update the best match
        if best_match_idx is not None:
            confidence = get_confidence_level(best_similarity)
            pub_df.at[best_match_idx, 'grant'] = grant_title
            pub_df.at[best_match_idx, 'confidence_level'] = confidence
            matches_found += 1
    
    print(f"\\nMatching completed!")
    print(f"Total matches found: {matches_found}")
    
    # Save results
    output_file = "Merged Publications with Grants.csv"
    pub_df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Results saved to: {output_file}")
    
    # Show sample results
    matches = pub_df[pub_df['grant'] != '']
    if len(matches) > 0:
        print(f"\\nSample matches:")
        for i, (_, row) in enumerate(matches.head(5).iterrows()):
            print(f"{i+1}. {row['confidence_level']} confidence")
            print(f"   Publication: {row['title'][:60]}...")
            print(f"   Grant: {row['grant'][:60]}...")
    
    # Show confidence distribution
    if len(matches) > 0:
        print(f"\\nConfidence level distribution:")
        confidence_counts = matches['confidence_level'].value_counts()
        for level, count in confidence_counts.items():
            print(f"  {level}: {count}")

if __name__ == "__main__":
    main()