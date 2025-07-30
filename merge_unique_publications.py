import json
import csv
import os
from pathlib import Path

def read_publications_by_source(folder_path):
    """Read JSON files and separate by source (nexus vs national graph)."""
    nexus_publications = []
    national_graph_publications = []
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
                
                # Determine source based on filename
                is_nexus = '_nexus' in json_file.name
                
                # Process each publication
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
                    
                    # Add source information
                    pub['source_file'] = json_file.name
                    pub['source_type'] = 'nexus' if is_nexus else 'national_graph'
                    
                    # Add to appropriate list
                    if is_nexus:
                        nexus_publications.append(pub)
                    else:
                        national_graph_publications.append(pub)
                    
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
            continue
    
    return nexus_publications, national_graph_publications

def merge_publications_with_priority(nexus_pubs, national_graph_pubs):
    """Merge publications, giving priority to national graph when titles match."""
    # Create a dictionary with title as key for national graph publications
    national_graph_dict = {}
    for pub in national_graph_pubs:
        title = pub.get('title', '').strip().lower()
        if title:  # Only add if title exists
            national_graph_dict[title] = pub
    
    # Create a dictionary for nexus publications
    nexus_dict = {}
    for pub in nexus_pubs:
        title = pub.get('title', '').strip().lower()
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
    output_csv = "Merged Publications.csv"
    
    # Check if Combined folder exists
    if not os.path.exists(combined_folder):
        print(f"Error: {combined_folder} folder not found!")
        return
    
    print(f"Reading JSON files from {combined_folder} folder...")
    nexus_pubs, national_graph_pubs = read_publications_by_source(combined_folder)
    
    print(f"Found {len(nexus_pubs)} publications from nexus source")
    print(f"Found {len(national_graph_pubs)} publications from national graph source")
    
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
        print("No publications found to merge.")

if __name__ == "__main__":
    main()