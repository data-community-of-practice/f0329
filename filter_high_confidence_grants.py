import pandas as pd

def filter_high_confidence_grants():
    """Filter out grants with Low or Very Low confidence levels."""
    
    print("Loading matched publications data...")
    
    # Load the matched publications CSV
    df = pd.read_csv("Merged Publications with Multiple Grants.csv")
    print(f"Total publications loaded: {len(df)}")
    
    # Show current confidence distribution
    matched_pubs = df[df['grant'].notna() & (df['grant'] != '')]
    print(f"Publications with grants: {len(matched_pubs)}")
    
    if len(matched_pubs) > 0:
        print("\nCurrent confidence level distribution:")
        confidence_counts = matched_pubs['confidence_level'].value_counts()
        for level, count in confidence_counts.items():
            print(f"  {level}: {count}")
    
    # Filter out Low and Very Low confidence grants
    # Keep publications with no grants (empty grant field) and Medium/High/Very High confidence
    filtered_df = df.copy()
    
    # Remove grant information for Low and Very Low confidence matches
    low_confidence_mask = filtered_df['confidence_level'].isin(['Low', 'Very Low'])
    filtered_df.loc[low_confidence_mask, 'grant'] = ''
    filtered_df.loc[low_confidence_mask, 'confidence_level'] = ''
    
    print(f"\nRemoving {low_confidence_mask.sum()} publications with Low or Very Low confidence grants")
    
    # Show new distribution
    remaining_matched = filtered_df[filtered_df['grant'].notna() & (filtered_df['grant'] != '')]
    print(f"Publications with grants after filtering: {len(remaining_matched)}")
    
    if len(remaining_matched) > 0:
        print("\nRemaining confidence level distribution:")
        remaining_confidence_counts = remaining_matched['confidence_level'].value_counts()
        for level, count in remaining_confidence_counts.items():
            print(f"  {level}: {count}")
        
        # Show unique grants remaining
        unique_grants = remaining_matched['grant'].nunique()
        print(f"\nUnique grants remaining: {unique_grants}")
        
        # Show some examples of remaining matches
        print(f"\nSample of remaining high-confidence matches:")
        for i, (_, row) in enumerate(remaining_matched.head(5).iterrows()):
            print(f"{i+1}. [{row['confidence_level']}] {row['title'][:60]}...")
            print(f"   Grant: {row['grant'][:60]}...")
            print()
    
    # Save filtered results
    output_file = "Merged Publications High Confidence Only.csv"
    filtered_df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Filtered results saved to: {output_file}")
    
    return filtered_df

if __name__ == "__main__":
    filtered_df = filter_high_confidence_grants()