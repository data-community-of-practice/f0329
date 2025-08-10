#!/usr/bin/env python3
"""
Test batch processor with just 3 publications
"""

from batch_processor_optimized import BatchProcessor
import pandas as pd

def test_small_batch():
    print("Testing Batch Processor with 3 publications")
    print("=" * 50)
    
    processor = BatchProcessor()
    
    # Override batch size for testing
    processor.batch_size = 3
    processor.api_delay = 1.0  # Faster for testing
    
    # Load data
    grants_df, publications_df = processor.load_data("barbara dicker grants.xlsx", "Merged Publications Final.csv")
    
    # Use only first 3 publications
    test_pubs = publications_df.head(3).copy()
    
    print(f"\nTesting with {len(test_pubs)} publications:")
    for i, (idx, row) in enumerate(test_pubs.iterrows()):
        print(f"  {i+1}. {row['title'][:60]}...")
    
    # Create progress object
    from batch_processor_optimized import ProcessingProgress
    progress = ProcessingProgress(
        total_publications=len(test_pubs),
        processed_count=0,
        mapped_count=0,
        batch_number=1,
        last_processed_index=-1,
        api_calls_made=0,
        api_calls_failed=0
    )
    
    # Process the small batch
    results, continue_flag = processor.process_batch(test_pubs, grants_df, progress)
    
    print(f"\nResults:")
    print(f"Continue processing: {continue_flag}")
    print(f"API calls made: {progress.api_calls_made}")
    print(f"API calls failed: {progress.api_calls_failed}")
    
    # Show mapping results
    mapped_count = len(results[results['Associated Grant'] != ''])
    print(f"Publications mapped: {mapped_count}/{len(results)}")
    
    # Save test results
    results.to_csv("test_batch_results.csv", index=False)
    print(f"Results saved to test_batch_results.csv")
    
    return results

if __name__ == "__main__":
    test_small_batch()