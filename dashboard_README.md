# Publications Dashboard

A comprehensive web-based dashboard for viewing and analyzing research publications with grant mappings.

## Overview

This dashboard provides an interactive interface to explore research publications and their associated grant mappings. It features two main views:

1. **All Publications** - Clean view of all publications with basic information
2. **Barbara Dicker Brain Sciences Foundation** - Detailed view with grant mappings and confidence levels

## Features

- **Dual Tab Interface**: Switch between all publications and BDBSF-specific publications
- **Real-time Search**: Search publications by author name
- **Dynamic Filtering**: Filter by publication year and confidence level
- **Live Statistics**: Publication counts update dynamically with filters
- **Responsive Design**: Mobile-friendly interface
- **Offline Capable**: All data embedded, no external dependencies

## Files Required

### Essential Files
- `publications_dashboard_embedded.html` - The main dashboard file (standalone)

### Supporting Files (for development/modification)
- `create_embedded_dashboard.py` - Python script to generate the HTML dashboard
- `all_mapped_publications.csv` - Source data file with publication and grant mappings

## How to Run

### Option 1: Direct Usage (Recommended)
1. Simply open `publications_dashboard_embedded.html` in any modern web browser
2. No additional setup or server required
3. Works completely offline

### Option 2: Development Setup
If you need to modify the dashboard or regenerate it with new data:

1. **Prerequisites**:
   - Python 3.6+
   - pandas library (`pip install pandas`)

2. **Data Requirements**:
   - `all_mapped_publications.csv` with the following columns:
     - `title` - Publication title
     - `publication_year` - Year of publication
     - `authors_list` - Comma-separated list of authors
     - `doi` - Digital Object Identifier
     - `Associated Grant` - Name of associated grant
     - `Confidence level` - Mapping confidence (Very High, High, Medium, Low, Very Low)
     - `Reasoning` - AI reasoning for the grant mapping

3. **Generate Dashboard**:
   ```bash
   python create_embedded_dashboard.py
   ```

## Dashboard Features

### All Publications Tab
- **Total Publications**: Static count of all publications in dataset
- **Publications Displayed**: Dynamic count based on current filters
- **Publication Years**: Number of unique years in dataset
- **Publication Cards**: Show title, authors, year, and DOI only

### BDBSF Tab
- **Total BDBSF Publications**: Static count of Medium/High/Very High confidence publications
- **Publications Displayed**: Dynamic count based on current filters
- **Confidence Breakdowns**: Dynamic counts for Very High, High, and Medium confidence levels
- **Publication Cards**: Full details including grant information and AI reasoning

### Search & Filter Options
- **Author Search**: Real-time text search across author names
- **Year Filter**: Dropdown with all available publication years
- **Confidence Filter**: Filter by confidence levels (BDBSF tab only)
- **Clear Filters**: Reset all filters to default state

## Data Source

The dashboard displays publications that have been processed through an AI-powered grant-publication mapping system that:

1. Pre-filters grants by investigator matching and temporal alignment
2. Uses GPT-4o-mini for topical relationship analysis
3. Assigns confidence levels based on content alignment
4. Provides detailed reasoning for each mapping decision

## Browser Compatibility

- Chrome/Edge: Fully supported
- Firefox: Fully supported  
- Safari: Fully supported
- Internet Explorer: Not supported (use Edge)

## Technical Details

- **Data Storage**: All publication data is embedded directly in the HTML file
- **Framework**: Vanilla JavaScript (no external dependencies)
- **Styling**: Modern CSS with responsive design
- **Performance**: Optimized for datasets up to ~2000 publications
- **File Size**: ~2-3MB for typical dataset (1300+ publications)

## Customization

To modify the dashboard appearance or functionality, edit the embedded CSS/JavaScript in the HTML file or modify the `create_embedded_dashboard.py` script and regenerate.