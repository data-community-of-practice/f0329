# BDBSF Publications Viewer - Setup Guide

## Overview
This project contains a web-based publications viewer for the Barbara Dicker Brain Science Foundation, with advanced topic trends analysis and grant-to-publication matching capabilities.

## Required Files
The following files are essential for the webpage to function:

### Data Files
- `Merged Publications Fixed.csv` - Main publications database
- `Merged Publications High Confidence Only.csv` - Filtered high-confidence grant matches (51 publications)

### Web Files
- `index.html` (or `publications_viewer_with_grants.html`) - Main webpage with all tabs
- `publications_viewer_paginated.html` - Alternative paginated view

### Processing Scripts
- `filter_high_confidence_grants.py` - Script to filter grants by confidence level

## Setup Instructions

### 1. Data Preparation
First, ensure you have the required CSV data files:
```bash
# Run the filtering script to generate high-confidence data (if needed)
python filter_high_confidence_grants.py
```

### 2. Web Server Setup
The webpage requires a local web server to function properly due to CORS restrictions when loading CSV files.

#### Option A: Python HTTP Server (Recommended)
```bash
# Navigate to the project directory
cd E:\Ponnu\BDBSF

# Start a simple HTTP server (Python 3.x)
python -m http.server 8000

# Or for Python 2.x
python -m SimpleHTTPServer 8000
```

#### Option B: Node.js HTTP Server
```bash
# Install http-server globally
npm install -g http-server

# Navigate to project directory and start server
cd E:\Ponnu\BDBSF
http-server -p 8000
```

#### Option C: PHP Server
```bash
# Navigate to project directory
cd E:\Ponnu\BDBSF

# Start PHP built-in server
php -S localhost:8000
```

### 3. Access the Webpage
Once the server is running, open your web browser and navigate to:
```
http://localhost:8000/index.html
```

## Features Available

### Publications Tab
- Search and browse all publications
- Paginated view with customizable page sizes
- Filter by author names
- View publication details including DOI links

### Barbara Dicker Brain Science Foundation Tab
- Shows 51 high-confidence grant-to-publication matches
- Filtered to only include Medium, High, and Very High confidence levels
- Displays grant information alongside publication data

### Topic Trends Analysis Tab
- **Research Topic Categories**: Visual breakdown of research domains
- **Research Focus Distribution**: Pie chart of topic distribution
- **Trending Topics by Year**: Timeline showing popular research themes
- **Topic Evolution**: Comparison of emerging vs established trends
- Interactive controls for analysis type and number of topics displayed

## File Structure
```
BDBSF/
├── index.html                                    # Main webpage
├── publications_viewer_with_grants.html          # Same as index.html
├── publications_viewer_paginated.html            # Alternative view
├── Merged Publications Fixed.csv                 # Main data file
├── Merged Publications High Confidence Only.csv  # Filtered data
├── filter_high_confidence_grants.py             # Processing script
├── CLAUDE.md                                     # This setup guide
└── .gitignore                                    # Git ignore rules
```

## Troubleshooting

### Common Issues

1. **"Error loading publications data"**
   - Ensure you're accessing via HTTP server, not file:// protocol
   - Check that CSV files exist in the same directory as HTML files
   - Verify CSV file names match exactly

2. **Blank/Empty Page**
   - Check browser console for JavaScript errors
   - Ensure all required CSV files are present
   - Try refreshing the page after server starts

3. **Topic Trends Not Working**
   - Verify the main CSV file contains publication titles
   - Check that publication years are properly formatted
   - Ensure browser supports modern JavaScript features

### Browser Requirements
- Modern web browser with JavaScript enabled
- Chrome, Firefox, Safari, or Edge (recent versions)
- JavaScript ES6+ support required for topic analysis

## Development Notes

### Data Processing
- The `filter_high_confidence_grants.py` script removes Low and Very Low confidence grants
- Original dataset: 530 matched publications
- Filtered dataset: 51 high-confidence matches across 17 unique grants

### Topic Analysis
- Uses natural language processing on publication titles
- Categorizes research into domains: Health, Psychology, COVID, Technology, etc.
- Extracts trending topics and analyzes evolution over time
- Responsive 2x2 grid layout for optimal data presentation

## Support
For issues or questions, refer to the git commit history which contains detailed change logs and implementation notes.