import pandas as pd
import re
from difflib import SequenceMatcher

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

def match_grants_to_multiple_publications():
    """Enhanced matching that allows multiple publications per grant."""
    
    print("Loading data...")
    # Load grants
    grants_df = pd.read_excel("barbara dicker grants.xlsx")
    print(f"Loaded {len(grants_df)} grants")
    
    # Load publications CSV
    pub_df = pd.read_csv("Merged Publications Fixed.csv")
    print(f"Loaded {len(pub_df)} publications")
    
    # Create new columns
    pub_df['grant'] = ''
    pub_df['confidence_level'] = ''
    
    # Track all matches (not just best matches)
    all_matches = []
    
    print("\\nStarting enhanced matching process...")
    
    for i, grant_row in grants_df.iterrows():
        if i % 20 == 0:
            print(f"Processing grant {i+1}/{len(grants_df)}")
        
        grant_title = str(grant_row['TITLE']).strip()
        researcher = str(grant_row['Preferred Full Name']).strip()
        start_year = grant_row['Start Date'].year
        end_year = grant_row['End Date'].year + 2  # Allow 2 years extension
        
        # Filter publications by researcher and date range
        researcher_pubs = pub_df[
            (pub_df['authors_list'].str.contains(researcher, na=False, case=False)) &
            (pub_df['publication_year'].astype(str).str.extract(r'(\d{4})')[0].astype(float) >= start_year) &
            (pub_df['publication_year'].astype(str).str.extract(r'(\d{4})')[0].astype(float) <= end_year)
        ]
        
        if len(researcher_pubs) == 0:
            continue
        
        # Find ALL publications that meet the threshold (not just the best)
        grant_matches = []
        
        for idx, pub_row in researcher_pubs.iterrows():
            pub_title = pub_row['title']
            similarity = calculate_similarity(grant_title, pub_title)
            
            # Lower threshold to catch more potential matches
            if similarity >= 0.12:  # Even lower threshold
                confidence = get_confidence_level(similarity)
                grant_matches.append({
                    'pub_idx': idx,
                    'pub_title': pub_title,
                    'similarity': similarity,
                    'confidence': confidence,
                    'grant_title': grant_title,
                    'researcher': researcher
                })
        
        # Add all matches above threshold
        all_matches.extend(grant_matches)
    
    print(f"\\nFound {len(all_matches)} total grant-publication matches")
    
    # Apply matches to dataframe
    matches_applied = 0
    for match in all_matches:
        pub_idx = match['pub_idx']
        
        # Only update if no grant assigned yet, or if this is a better match
        current_grant = pub_df.at[pub_idx, 'grant']
        if current_grant == '' or pd.isna(current_grant):
            pub_df.at[pub_idx, 'grant'] = match['grant_title']
            pub_df.at[pub_idx, 'confidence_level'] = match['confidence']
            matches_applied += 1
        else:
            # If there's already a grant, check if this one has higher confidence
            current_conf = pub_df.at[pub_idx, 'confidence_level']
            conf_hierarchy = {'Very Low': 1, 'Low': 2, 'Medium': 3, 'High': 4, 'Very High': 5}
            
            current_score = conf_hierarchy.get(current_conf, 0)
            new_score = conf_hierarchy.get(match['confidence'], 0)
            
            if new_score > current_score:
                pub_df.at[pub_idx, 'grant'] = match['grant_title']
                pub_df.at[pub_idx, 'confidence_level'] = match['confidence']
    
    print(f"Applied {matches_applied} matches to publications")
    
    # Save results
    output_file = "Merged Publications with Multiple Grants.csv"
    pub_df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Results saved to: {output_file}")
    
    # Analyze results
    analyze_multiple_matches(pub_df, all_matches)
    
    return pub_df, all_matches

def analyze_multiple_matches(pub_df, all_matches):
    """Analyze the results of multiple grant matching."""
    
    # Get publications with grants
    matched_pubs = pub_df[pub_df['grant'].notna() & (pub_df['grant'] != '')]
    
    print(f"\\n" + "="*60)
    print("MULTIPLE GRANT MATCHING RESULTS")
    print("="*60)
    
    print(f"Total publications: {len(pub_df)}")
    print(f"Publications with grants: {len(matched_pubs)}")
    
    # Count publications per grant
    grant_counts = matched_pubs['grant'].value_counts()
    print(f"Unique grants matched: {len(grant_counts)}")
    
    # Show distribution
    from collections import Counter
    pub_per_grant_dist = Counter(grant_counts.values)
    print(f"\\nDistribution of publications per grant:")
    for num_pubs, num_grants in sorted(pub_per_grant_dist.items()):
        print(f"  {num_pubs} publication(s): {num_grants} grants")
    
    # Show confidence distribution
    print(f"\\nConfidence level distribution:")
    confidence_counts = matched_pubs['confidence_level'].value_counts()
    for level, count in confidence_counts.items():
        print(f"  {level}: {count}")
    
    # Show grants with multiple publications
    multi_pub_grants = grant_counts[grant_counts > 1]
    if len(multi_pub_grants) > 0:
        print(f"\\nGrants with multiple publications ({len(multi_pub_grants)} grants):")
        for grant_title, pub_count in multi_pub_grants.head(5).items():
            print(f"\\n{pub_count} publications - Grant: {grant_title[:70]}...")
            
            # Show the publications for this grant
            grant_pubs = matched_pubs[matched_pubs['grant'] == grant_title]
            for i, (_, pub) in enumerate(grant_pubs.iterrows()):
                print(f"  {i+1}. [{pub['confidence_level']}] {pub['title'][:60]}...")
    
    # Show some high confidence matches
    high_conf = matched_pubs[matched_pubs['confidence_level'].isin(['High', 'Very High'])]
    if len(high_conf) > 0:
        print(f"\\nHigh confidence matches ({len(high_conf)}):")
        for i, (_, row) in enumerate(high_conf.head(3).iterrows()):
            print(f"\\n{i+1}. {row['confidence_level']} confidence")
            print(f"   Publication: {row['title'][:70]}...")
            print(f"   Grant: {row['grant'][:70]}...")

if __name__ == "__main__":
    pub_df, all_matches = match_grants_to_multiple_publications()