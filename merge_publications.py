import json
import csv
import os
from pathlib import Path

def read_json_files(folder_path):
    """Read all JSON files from the specified folder and extract publications."""
    publications = []
    folder = Path(folder_path)
    
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
                
                # Add each publication to the list
                for pub in file_publications:
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
                    
                    publications.append(pub)
                    
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
            continue
    
    return publications

def merge_to_csv(publications, output_file):
    """Merge publications data into a single CSV file with specified headers."""
    if not publications:
        print("No publications found to merge.")
        return
    
    # Define CSV headers as specified
    headers = [
        'title',
        'publication_year', 
        'authors_list',
        'doi',
        'source',
        'crossref_type',
        'key'
    ]
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for pub in publications:
            # Create row with specified headers and set source to "crossref.org"
            row = {
                'title': pub.get('title', ''),
                'publication_year': pub.get('publication_year', ''),
                'authors_list': pub.get('authors_list', ''),
                'doi': pub.get('doi', ''),
                'source': 'crossref.org',
                'crossref_type': pub.get('crossref_type', ''),
                'key': pub.get('key', '')
            }
            writer.writerow(row)
    
    print(f"Successfully merged {len(publications)} publications into {output_file}")

def main():
    # Define paths
    combined_folder = "Combined"
    output_csv = "Publications.csv"
    
    # Check if Combined folder exists
    if not os.path.exists(combined_folder):
        print(f"Error: {combined_folder} folder not found!")
        return
    
    print(f"Reading JSON files from {combined_folder} folder...")
    publications = read_json_files(combined_folder)
    
    print(f"Found {len(publications)} publications across all files")
    
    if publications:
        merge_to_csv(publications, output_csv)
    else:
        print("No publications found in the JSON files.")

if __name__ == "__main__":
    main()