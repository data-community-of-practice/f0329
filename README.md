# Grant-Publication Matcher

This script uses an LLM to intelligently match research grants to their resulting publications based on four key criteria:

## Matching Criteria

1. **Topic Relevance**: Assesses research questions, methodologies, and domain overlap
2. **Author Overlap**: Checks for name variations and research team continuity  
3. **Temporal Validity**: Ensures publication is after grant start date
4. **Research Continuity**: Evaluates if this could be a plausible research outcome

## Setup

1. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration File Setup** (Recommended):
   
   Copy the example configuration file:
   ```bash
   cp config.ini.example config.ini
   ```
   
   Edit `config.ini` with your API credentials and settings:
   ```ini
   [openai]
   api_key = your-openai-api-key-here

   [researchgraph_api]
   authorization = Basic your-base64-encoded-credentials-here
   url = https://researchgraph.cloud/api/gpt

   [files]
   grants_file = barbara dicker grants.xlsx
   publications_file = Merged Publications Final.csv
   output_file = Grant_Publication_Matches.xlsx

   [matching]
   confidence_threshold = 30.0
   test_mode = false
   test_sample_size = 10
   ```

3. **Alternative: Environment Variable**:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```
   
   Or on Windows:
   ```cmd
   set OPENAI_API_KEY=your-api-key-here
   ```

## Usage

1. Place your data files in the same directory:
   - `barbara dicker grants.xlsx` - Grant information
   - `Merged Publications Final.csv` - Publications data

2. Run the script:
   ```bash
   # Full processing (all publications)
   python grant_publication_matcher.py
   
   # Demo mode (process specific number of publications)
   python grant_publication_matcher.py --demo 10
   
   # Test mode (uses config file sample size)
   python grant_publication_matcher.py --test
   
   # Custom confidence threshold
   python grant_publication_matcher.py --confidence 50
   ```

3. The script will generate `Grant_Publication_Matches.xlsx` with:
   - All original publication data
   - Matched grant title
   - Confidence level (Very High/High/Medium/Low/Very Low)
   - Individual scores for each matching criterion
   - Reasoning for the match

## Output Format

The output Excel file contains all original publication columns plus:
- `matched_grant_title`: The best matching grant (or "No match found")
- `confidence_score`: Overall confidence score (0-100) 
- `confidence_level`: Categorical confidence level (Very High/High/Medium/Low/Very Low)
- `topic_relevance`: Topic similarity score (0-100)
- `author_overlap`: Author overlap score (0-100)
- `temporal_validity`: Temporal validity score (0-100)
- `research_continuity`: Research continuity score (0-100)
- `matching_reasoning`: Brief explanation of the match assessment

## Notes

- The script only matches publications to grants that meet a minimum confidence threshold (30% by default)
- Publications with no author overlap AND invalid timing are skipped for efficiency
- The LLM provides detailed reasoning for each match decision