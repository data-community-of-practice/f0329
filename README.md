# Grant-Publication Mapping Tool

This Python program maps research publications to grants based on investigator matching, date ranges, and AI-powered relationship analysis.

## Overview

The tool performs the following steps:
1. **Investigator Matching**: Filters publications that have authors matching grant investigators
2. **Date Range Filtering**: Ensures publications fall within grant period + 2 years
3. **AI Analysis**: Uses GPT-4o-mini to assess the relationship between grants and publications
4. **Output Generation**: Creates a CSV with all publications plus 4 additional columns

## Required Files

- `barbara dicker grants.xlsx` - Excel file containing grant information
- `Merged Publications Final.csv` - CSV file containing publication data

## Installation

1. Install required Python packages:
```bash
pip install -r requirements.txt
```

## Usage

### Method 1: Run the complete program
```bash
python grant_publication_mapper.py
```

You'll be prompted to enter your OpenAI API key when the program starts.

### Method 2: Test the functionality first
```bash
python test_mapper.py
```

This runs basic tests without making API calls to verify the data loading and filtering logic.

## Input File Requirements

### Grants File (`barbara dicker grants.xlsx`)
Expected columns:
- `TITLE`: Grant title
- `Preferred Full Name`: Primary investigator name
- `Other Investigators`: Comma-separated list of other investigators
- `Start Date`: Grant start date
- `End Date`: Grant end date
- `Project Code`: Used as grant DOI in output
- `Proejct Description`: Grant description (optional)

### Publications File (`Merged Publications Final.csv`)
Expected columns:
- `title`: Publication title
- `authors_list`: Comma-separated list of authors
- `publication_year`: Year of publication
- `doi`: Publication DOI
- `crossref_type`: Publication type
- `key`: Publication key

## Output

The program creates `mapped_publications_output.csv` containing all original publication data plus:

1. **Associated Grant**: Title of the matched grant (empty if no match)
2. **DOI of grant**: Grant project code/identifier
3. **Confidence level**: AI-assessed confidence (Very High/High/Medium/Low/Very Low)
4. **Reasoning**: AI explanation for the mapping decision

## Configuration

### OpenAI API Key
The program requires a valid OpenAI API key to access GPT-4o-mini. You can:
- Enter it when prompted
- Set it as an environment variable `OPENAI_API_KEY`
- Modify the code to read from a config file

### Customization Options

You can modify the following in the code:

- **Date Range**: Currently set to grant period + 2 years
- **Name Matching Logic**: Adjust fuzzy matching sensitivity
- **Confidence Thresholds**: Modify how LLM responses are interpreted
- **Rate Limiting**: Adjust delays between API calls

## Algorithm Details

### Name Matching
- Normalizes names (removes titles, extra spaces)
- Performs fuzzy matching on name components
- Matches if sufficient name parts overlap

### Date Filtering
- Publications must be published between grant start date and end date + 2 years
- Uses publication year for comparison

### AI Analysis
The LLM considers:
- Topic/subject matter alignment
- Author overlap with investigators
- Timing alignment
- Methodological approach alignment

## Troubleshooting

### Common Issues

1. **Unicode Errors**: Ensure your system supports UTF-8 encoding
2. **API Rate Limits**: The program includes delays, but you may need to adjust for your API tier
3. **Memory Issues**: For very large datasets, consider processing in batches
4. **Name Matching**: Review the matching logic if too few/many matches are found

### Error Handling

The program includes error handling for:
- File loading errors
- API call failures  
- Data format issues
- Network connectivity problems

## Performance Notes

- Processing time depends on the number of valid publication-grant pairs
- Each pair requires an LLM API call (~0.1-0.5 seconds each)
- For 1000+ pairs, expect 10-30 minutes processing time
- Consider running overnight for large datasets

## Cost Estimation

GPT-4o-mini API costs (as of 2024):
- ~$0.00015 per 1K input tokens
- ~$0.0006 per 1K output tokens
- Typical cost: ~$0.001-0.005 per publication-grant pair analysis

For 1000 pairs: ~$1-5 in API costs