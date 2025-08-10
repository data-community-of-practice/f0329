#!/usr/bin/env python3
"""
Test script for the grant-publication mapper
"""

import pandas as pd
from grant_publication_mapper import GrantPublicationMapper

def test_name_matching():
    """Test the name matching functionality"""
    print("Testing name matching functionality...")
    
    # Create a dummy mapper (no API key needed for name matching)
    mapper = GrantPublicationMapper("dummy_key")
    
    # Test cases
    test_cases = [
        ("Luke A. Downey", ["Luke Downey"], True),
        ("Susan Rossell", ["Susan Rossell", "Martin Williams"], True),
        ("John Smith", ["Jane Doe", "Bob Wilson"], False),
        ("Dr. Martin Williams", ["Martin Williams"], True),
        ("Maja Nedeljkovic", ["Maja Nedeljkovic"], True),
    ]
    
    for author, investigators, expected in test_cases:
        result = mapper.check_name_match(author, investigators)
        status = "PASS" if result == expected else "FAIL"
        print(f"{status} {author} vs {investigators} -> {result} (expected {expected})")

def test_data_loading():
    """Test data loading functionality"""
    print("\nTesting data loading...")
    
    try:
        mapper = GrantPublicationMapper("dummy_key")
        grants_df, pubs_df = mapper.load_data("barbara dicker grants.xlsx", "Merged Publications Final.csv")
        
        print(f"PASS Loaded {len(grants_df)} grants and {len(pubs_df)} publications")
        
        # Test investigator extraction
        sample_grant = grants_df.iloc[1]  # Second grant
        investigators = mapper.extract_investigators(sample_grant)
        print(f"PASS Extracted investigators from sample grant: {investigators}")
        
        return True
        
    except Exception as e:
        print(f"FAIL Error loading data: {e}")
        return False

def test_filtering():
    """Test the filtering logic without LLM calls"""
    print("\nTesting filtering logic...")
    
    try:
        mapper = GrantPublicationMapper("dummy_key")
        grants_df, pubs_df = mapper.load_data("barbara dicker grants.xlsx", "Merged Publications Final.csv")
        
        # Test investigator filtering
        filtered_pubs = mapper.filter_publications_by_investigators(pubs_df.head(20), grants_df)
        print(f"PASS Investigator filtering: {len(filtered_pubs)} matches from first 20 publications")
        
        if len(filtered_pubs) > 0:
            # Test date filtering
            valid_matches = mapper.filter_by_date_range(filtered_pubs, grants_df)
            print(f"PASS Date filtering: {len(valid_matches)} valid date matches")
        else:
            print("INFO No investigator matches found to test date filtering")
        
        return True
        
    except Exception as e:
        print(f"FAIL Error in filtering: {e}")
        return False

def main():
    """Run all tests"""
    print("Running tests for Grant-Publication Mapper...")
    print("=" * 50)
    
    # Test name matching
    test_name_matching()
    
    # Test data loading
    data_ok = test_data_loading()
    
    if data_ok:
        # Test filtering
        test_filtering()
    
    print("\n" + "=" * 50)
    print("Test completed. If all tests show PASS, the basic functionality is working.")
    print("To run the full program with LLM analysis, use: python grant_publication_mapper.py")

if __name__ == "__main__":
    main()