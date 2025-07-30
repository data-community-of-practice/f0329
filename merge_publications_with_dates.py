import json
import csv
import os
import pandas as pd
import re
from pathlib import Path
from datetime import datetime

def parse_date_range(date_range_str):
    """Parse date range string and extract start/end years."""
    try:
        # Clean the string and split by 'to'
        date_range_str = date_range_str.strip()
        parts = re.split(r'\s+to\s+', date_range_str, flags=re.IGNORECASE)
        
        if len(parts) != 2:
            print(f"Warning: Could not parse date range: {date_range_str}")
            return None, None
        
        start_date_str, end_date_str = parts
        
        # Extract years from date strings
        start_year = extract_year_from_date(start_date_str.strip())
        end_year = extract_year_from_date(end_date_str.strip())
        
        return start_year, end_year
    except Exception as e:
        print(f"Error parsing date range '{date_range_str}': {e}")
        return None, None

def extract_year_from_date(date_str):
    """Extract year from various date formats."""
    # Look for 4-digit year pattern
    year_match = re.search(r'(\d{4})', date_str)
    if year_match:
        return int(year_match.group(1))
    return None

def load_researcher_date_ranges(excel_file):
    """Load researcher date ranges from Excel file."""
    try:
        df = pd.read_excel(excel_file)
        researcher_ranges = {}
        
        for _, row in df.iterrows():
            full_name = str(row['Full Name']).strip()
            date_range = str(row['Date Range']).strip()
            
            start_year, end_year = parse_date_range(date_range)
            if start_year and end_year:
                researcher_ranges[full_name] = (start_year, end_year)
            else:
                print(f"Warning: Could not parse date range for {full_name}: {date_range}")
        
        print(f"Loaded date ranges for {len(researcher_ranges)} researchers")
        return researcher_ranges
    
    except Exception as e:
        print(f"Error loading researcher date ranges: {e}")
        return {}

def get_author_names_from_publication(pub):
    """Extract individual author names from authors_list."""
    authors_list = pub.get('authors_list', '')
    if not authors_list:
        return []
    
    # Split by comma and clean names
    authors = [name.strip() for name in authors_list.split(',')]
    return authors

def normalize_name(name):
    """Normalize name for matching (remove middle initials, extra spaces)."""
    import re
    # Remove middle initials (single letters followed by periods)
    name = re.sub(r'\b[A-Z]\.\s*', '', name)
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def is_publication_in_author_range(pub, researcher_ranges, json_filename):
    """Check if publication year falls within the JSON file author's date range."""
    pub_year_str = pub.get('publication_year', '')
    if not pub_year_str:
        return False
    
    try:
        pub_year = int(str(pub_year_str).strip())
    except (ValueError, TypeError):
        return False
    
    # Extract author name from JSON filename (remove .json and _nexus suffix)
    author_name = json_filename.replace('.json', '').replace('_nexus', '')
    
    # Try exact match first
    if author_name in researcher_ranges:
        start_year, end_year = researcher_ranges[author_name]
        return start_year <= pub_year <= end_year
    
    # Try normalized name match
    normalized_author = normalize_name(author_name)
    for researcher_name in researcher_ranges.keys():
        if normalize_name(researcher_name) == normalized_author:
            start_year, end_year = researcher_ranges[researcher_name]
            return start_year <= pub_year <= end_year
    
    # If author not found in researchers list, skip this publication
    return False

def read_publications_by_source(folder_path, researcher_ranges):
    """Read JSON files and separate by source (nexus vs national graph), filtering by date ranges."""
    nexus_publications = []
    national_graph_publications = []
    folder = Path(folder_path)
    
    total_processed = 0
    filtered_count = 0
    
    for json_file in folder.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Extract publications from the JSON structure
            if isinstance(data, list) and len(data) > 0:
                nodes = data[0].get('nodes', {})
                relationships = data[0].get('relationships', {})
                file_publications = nodes.get('publications', [])
                researchers = nodes.get('researchers', [])
                
                # Create a mapping of researcher keys to full names
                researcher_names = {r.get('key', ''): r.get('full_name', '') for r in researchers}
                
                # Determine source based on filename
                is_nexus = '_nexus' in json_file.name
                
                # Process each publication
                for pub in file_publications:
                    total_processed += 1
                    
                    # If authors_list is missing, try to construct it from relationships
                    if not pub.get('authors_list'):
                        pub_key = pub.get('key', '')
                        if pub_key:
                            # Find researchers linked to this publication
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
                    
                    # Filter by date ranges
                    if is_publication_in_author_range(pub, researcher_ranges, json_file.name):
                        # Add source information
                        pub['source_file'] = json_file.name
                        pub['source_type'] = 'nexus' if is_nexus else 'national_graph'
                        
                        # Add to appropriate list
                        if is_nexus:
                            nexus_publications.append(pub)
                        else:
                            national_graph_publications.append(pub)
                    else:
                        filtered_count += 1
                    
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
            continue
    
    print(f"Processed {total_processed} publications, filtered out {filtered_count} due to date ranges")
    return nexus_publications, national_graph_publications

def normalize_title_for_matching(title):
    """Normalize title for deduplication (handle HTML encoding differences)."""
    import re
    import html
    
    # Decode HTML entities
    title = html.unescape(title)
    # Remove HTML tags
    title = re.sub(r'<[^>]+>', '', title)
    # Normalize whitespace
    title = re.sub(r'\s+', ' ', title)
    # Convert to lowercase and strip
    return title.strip().lower()

def merge_publications_with_priority(nexus_pubs, national_graph_pubs):
    """Merge publications, giving priority to national graph when titles match."""
    # Create a dictionary with normalized title as key for national graph publications
    national_graph_dict = {}
    for pub in national_graph_pubs:
        title = normalize_title_for_matching(pub.get('title', ''))
        if title:  # Only add if title exists
            national_graph_dict[title] = pub
    
    # Create a dictionary for nexus publications
    nexus_dict = {}
    for pub in nexus_pubs:
        title = normalize_title_for_matching(pub.get('title', ''))
        if title:  # Only add if title exists
            nexus_dict[title] = pub
    
    # Merge with priority to national graph
    merged_publications = {}
    
    # First, add all national graph publications
    for title, pub in national_graph_dict.items():
        merged_publications[title] = pub
    
    # Then, add nexus publications only if title doesn't exist in national graph
    for title, pub in nexus_dict.items():
        if title not in merged_publications:
            merged_publications[title] = pub
    
    # Convert back to list
    return list(merged_publications.values())

def create_merged_csv(publications, output_file):
    """Create CSV file with merged publications."""
    if not publications:
        print("No publications found to merge.")
        return
    
    # Define CSV headers as specified
    headers = [
        'title',
        'publication_year', 
        'authors_list',
        'doi',
        'crossref_type',
        'key'
    ]
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for pub in publications:
            # Create row with specified headers
            row = {
                'title': pub.get('title', ''),
                'publication_year': pub.get('publication_year', ''),
                'authors_list': pub.get('authors_list', ''),
                'doi': pub.get('doi', ''),
                'crossref_type': pub.get('crossref_type', ''),
                'key': pub.get('key', '')
            }
            writer.writerow(row)
    
    print(f"Successfully merged {len(publications)} unique publications into {output_file}")

def main():
    # Define paths
    combined_folder = "Combined"
    researchers_excel = "Researchers.xlsx"
    output_csv = "Merged Publications Final.csv"
    
    # Check if files exist
    if not os.path.exists(combined_folder):
        print(f"Error: {combined_folder} folder not found!")
        return
    
    if not os.path.exists(researchers_excel):
        print(f"Error: {researchers_excel} file not found!")
        return
    
    # Load researcher date ranges
    print(f"Loading researcher date ranges from {researchers_excel}...")
    researcher_ranges = load_researcher_date_ranges(researchers_excel)
    
    if not researcher_ranges:
        print("No valid researcher date ranges found. Exiting.")
        return
    
    # Sample of loaded ranges
    print("Sample date ranges:")
    for i, (name, (start, end)) in enumerate(list(researcher_ranges.items())[:5]):
        print(f"  {name}: {start}-{end}")
    
    print(f"\nReading JSON files from {combined_folder} folder...")
    nexus_pubs, national_graph_pubs = read_publications_by_source(combined_folder, researcher_ranges)
    
    print(f"Found {len(nexus_pubs)} publications from nexus source (after date filtering)")
    print(f"Found {len(national_graph_pubs)} publications from national graph source (after date filtering)")
    
    # Merge with priority to national graph
    merged_pubs = merge_publications_with_priority(nexus_pubs, national_graph_pubs)
    
    print(f"After removing duplicates: {len(merged_pubs)} unique publications")
    
    # Count how many came from each source in final result
    nexus_count = sum(1 for pub in merged_pubs if pub.get('source_type') == 'nexus')
    national_graph_count = sum(1 for pub in merged_pubs if pub.get('source_type') == 'national_graph')
    
    print(f"Final composition: {national_graph_count} from national graph, {nexus_count} from nexus")
    
    if merged_pubs:
        create_merged_csv(merged_pubs, output_csv)
    else:
        print("No publications found to merge after date filtering.")

if __name__ == "__main__":
    main()