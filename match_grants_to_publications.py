import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from difflib import SequenceMatcher

def clean_filename(name):
    """Clean name to match JSON filename format."""
    return name.strip()

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

def load_publications_for_researcher(researcher_name, combined_folder):
    """Load publications for a specific researcher from JSON files."""
    publications = []
    folder = Path(combined_folder)
    
    # Try both regular and _nexus files
    possible_files = [
        f"{researcher_name}.json",
        f"{researcher_name}_nexus.json"
    ]
    
    for filename in possible_files:
        json_file = folder / filename
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list) and len(data) > 0:
                    nodes = data[0].get('nodes', {})
                    relationships = data[0].get('relationships', {})
                    file_publications = nodes.get('publications', [])
                    researchers = nodes.get('researchers', [])
                    
                    # Create researcher name mapping
                    researcher_names = {r.get('key', ''): r.get('full_name', '') for r in researchers}
                    
                    for pub in file_publications:
                        # Handle missing authors_list by reconstructing from relationships
                        if not pub.get('authors_list'):
                            pub_key = pub.get('key', '')
                            if pub_key:
                                linked_researchers = []
                                for rel in relationships.get('researcher-publication', []):
                                    if rel.get('to') == pub_key:
                                        researcher_key = rel.get('from')
                                        if researcher_key in researcher_names:
                                            linked_researchers.append(researcher_names[researcher_key])
                                
                                if linked_researchers:
                                    pub['authors_list'] = ', '.join(linked_researchers)
                        
                        # Handle crossref_type vs orcid_type
                        if not pub.get('crossref_type') and pub.get('orcid_type'):
                            pub['crossref_type'] = pub['orcid_type']
                        
                        publications.append(pub)
            
            except Exception as e:
                print(f"Error reading {json_file}: {e}")
                continue
    
    return publications

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
        # Combine similarity scores with word overlap weighted more
        combined_score = (similarity * 0.4) + (word_overlap * 0.6)
        return combined_score
    
    return similarity

def is_publication_in_date_range(pub_year, start_date, end_date):
    """Check if publication year falls within grant date range (with 2-year extension)."""
    if not pub_year:
        return False
    
    try:
        pub_year = int(pub_year)
        start_year = start_date.year
        # Allow publications up to 2 years after end date
        end_year = end_date.year + 2
        
        return start_year <= pub_year <= end_year
    except (ValueError, AttributeError):
        return False

def get_confidence_level(similarity_score):
    """Convert similarity score to confidence level."""
    if similarity_score >= 0.8:
        return "Very High"
    elif similarity_score >= 0.6:
        return "High"
    elif similarity_score >= 0.4:
        return "Medium"
    elif similarity_score >= 0.2:
        return "Low"
    else:
        return "Very Low"

def match_grants_to_publications(grants_file, combined_folder, publications_csv, output_csv):
    """Main function to match grants to publications and create enhanced CSV."""
    
    # Load grants data
    print("Loading grants data...")
    grants = load_grants_data(grants_file)
    print(f"Loaded {len(grants)} grants")
    
    # Load publications CSV
    print("Loading publications CSV...")
    pub_df = pd.read_csv(publications_csv)
    print(f"Loaded {len(pub_df)} publications")
    
    # Create new columns for grant information
    pub_df['grant'] = ''
    pub_df['confidence_level'] = ''
    
    # Track matching statistics
    matches_found = 0
    total_checked = 0
    
    print("\\nStarting grant-publication matching...")
    
    # Group grants by researcher to reduce JSON file reads
    grants_by_researcher = {}
    for grant in grants:
        researcher = grant['full_name']
        if researcher not in grants_by_researcher:
            grants_by_researcher[researcher] = []
        grants_by_researcher[researcher].append(grant)
    
    print(f"Processing {len(grants_by_researcher)} unique researchers...")
    
    # Process each researcher
    for researcher_name, researcher_grants in grants_by_researcher.items():
        print(f"\\nProcessing {researcher_name} ({len(researcher_grants)} grants)...")
        
        # Load publications for this researcher
        publications = load_publications_for_researcher(researcher_name, combined_folder)
        
        if not publications:
            print(f"  No publications found for {researcher_name}")
            continue
        
        print(f"  Found {len(publications)} publications")
        
        # Check each grant against each publication
        for grant in researcher_grants:
            grant_title = grant['title']
            start_date = grant['start_date']
            end_date = grant['end_date']
            
            best_match = None
            best_similarity = 0.0
            
            # Filter publications by date range
            relevant_publications = []
            for pub in publications:
                pub_year = pub.get('publication_year', '')
                if is_publication_in_date_range(pub_year, start_date, end_date):
                    relevant_publications.append(pub)
            
            print(f"    Grant: {grant_title[:50]}...")
            print(f"    Date range: {start_date.year} - {end_date.year + 2}")
            print(f"    Publications in range: {len(relevant_publications)}")
            
            # Find best matching publication
            for pub in relevant_publications:
                pub_title = pub.get('title', '')
                similarity = calculate_similarity(grant_title, pub_title)
                total_checked += 1
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = pub
            
            # If we found a decent match, add it to the CSV
            if best_match and best_similarity >= 0.2:  # Minimum threshold
                pub_title_to_match = best_match.get('title', '')
                confidence = get_confidence_level(best_similarity)
                
                # Find matching rows in the publications CSV
                matching_rows = pub_df[pub_df['title'] == pub_title_to_match]
                
                if len(matching_rows) > 0:
                    # Update the matching rows
                    pub_df.loc[pub_df['title'] == pub_title_to_match, 'grant'] = grant_title
                    pub_df.loc[pub_df['title'] == pub_title_to_match, 'confidence_level'] = confidence
                    matches_found += 1
                    
                    print(f"    MATCH FOUND!")
                    print(f"      Publication: {pub_title_to_match[:50]}...")
                    print(f"      Similarity: {best_similarity:.3f} ({confidence})")
                else:
                    print(f"    Publication not found in merged CSV: {pub_title_to_match[:50]}...")
    
    # Save enhanced CSV
    print(f"\\n" + "="*60)
    print(f"MATCHING SUMMARY:")
    print(f"Total grant-publication pairs checked: {total_checked}")
    print(f"Matches found and added to CSV: {matches_found}")
    print(f"Publications with grants: {len(pub_df[pub_df['grant'] != ''])}")
    
    # Save the enhanced CSV
    pub_df.to_csv(output_csv, index=False)
    print(f"\\nEnhanced CSV saved to: {output_csv}")
    
    # Show some sample matches
    matches = pub_df[pub_df['grant'] != '']
    if len(matches) > 0:
        print(f"\\nSample matches:")
        for i, (_, row) in enumerate(matches.head(3).iterrows()):
            print(f"\\n{i+1}. Publication: {row['title'][:60]}...")
            print(f"   Grant: {row['grant'][:60]}...")
            print(f"   Confidence: {row['confidence_level']}")

def main():
    grants_file = "barbara dicker grants.xlsx"
    combined_folder = "Combined"
    publications_csv = "Merged Publications Fixed.csv"
    output_csv = "Merged Publications with Grants.csv"
    
    # Check if all files exist
    required_files = [grants_file, publications_csv]
    for file in required_files:
        if not Path(file).exists():
            print(f"Error: Required file not found: {file}")
            return
    
    if not Path(combined_folder).exists():
        print(f"Error: Required folder not found: {combined_folder}")
        return
    
    # Run the matching process
    match_grants_to_publications(grants_file, combined_folder, publications_csv, output_csv)

if __name__ == "__main__":
    main()