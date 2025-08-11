#!/usr/bin/env python3
"""
Convert CSV data to embedded HTML dashboard
"""

import pandas as pd
import json
import html

def create_embedded_dashboard():
    # Read the CSV file
    try:
        df = pd.read_csv('all_mapped_publications.csv')
        print(f"Loaded {len(df)} publications")
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
    
    # Convert to JSON, handling NaN values
    df = df.fillna('')  # Replace NaN with empty strings
    publications_data = df.to_dict('records')
    
    # Convert to JavaScript-compatible JSON
    js_data = json.dumps(publications_data, ensure_ascii=False, indent=2)
    
    # Create the HTML with embedded data
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Publications Dashboard - BDBSF</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}

        .search-controls {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}

        .search-row {{
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }}

        .search-group {{
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}

        .search-group label {{
            font-weight: 600;
            color: #555;
            font-size: 0.9em;
        }}

        .search-group input, .search-group select {{
            padding: 10px;
            border: 2px solid #e1e5e9;
            border-radius: 5px;
            font-size: 14px;
            transition: border-color 0.3s;
            min-width: 200px;
        }}

        .search-group input:focus, .search-group select:focus {{
            outline: none;
            border-color: #667eea;
        }}

        .clear-btn {{
            background: #dc3545;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
            align-self: end;
        }}

        .clear-btn:hover {{
            background: #c82333;
        }}

        .tabs {{
            display: flex;
            background: white;
            border-radius: 10px 10px 0 0;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .tab {{
            flex: 1;
            padding: 15px 20px;
            background: #f8f9fa;
            border: none;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }}

        .tab:hover {{
            background: #e9ecef;
        }}

        .tab.active {{
            background: white;
            border-bottom-color: #667eea;
            color: #667eea;
        }}

        .tab-content {{
            display: none;
            background: white;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .tab-content.active {{
            display: block;
        }}

        .stats {{
            padding: 20px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-bottom: 1px solid #dee2e6;
        }}

        .stats-row {{
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
            justify-content: center;
        }}

        .stat-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            min-width: 120px;
        }}

        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}

        .stat-label {{
            font-size: 0.9em;
            color: #666;
            text-align: center;
        }}

        .publications-list {{
            max-height: 600px;
            overflow-y: auto;
            padding: 20px;
        }}

        .publication-card {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .publication-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}

        .pub-title {{
            font-size: 1.2em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 10px;
            line-height: 1.4;
        }}

        .pub-authors {{
            color: #666;
            margin-bottom: 8px;
            font-style: italic;
        }}

        .pub-details {{
            display: flex;
            gap: 20px;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }}

        .pub-detail {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 0.9em;
        }}

        .pub-year {{
            background: #667eea;
            color: white;
            padding: 3px 8px;
            border-radius: 12px;
            font-weight: 600;
        }}

        .confidence-badge {{
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .confidence-very-high {{
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}

        .confidence-high {{
            background: #cce7ff;
            color: #004085;
            border: 1px solid #b3d7ff;
        }}

        .confidence-medium {{
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }}

        .confidence-low {{
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f1b0b7;
        }}

        .confidence-very-low {{
            background: #f5f5f5;
            color: #6c757d;
            border: 1px solid #dadada;
        }}

        .grant-info {{
            background: white;
            border-left: 4px solid #667eea;
            padding: 12px;
            margin-top: 12px;
            border-radius: 0 5px 5px 0;
        }}

        .grant-title {{
            font-weight: 600;
            color: #495057;
            margin-bottom: 5px;
        }}

        .grant-reasoning {{
            font-size: 0.9em;
            color: #666;
            line-height: 1.4;
        }}

        .no-results {{
            text-align: center;
            padding: 50px;
            color: #666;
            font-size: 1.1em;
        }}

        .loading {{
            text-align: center;
            padding: 50px;
            font-size: 1.1em;
            color: #667eea;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
            
            .search-row {{
                flex-direction: column;
                align-items: stretch;
            }}
            
            .search-group input, .search-group select {{
                min-width: 100%;
            }}
            
            .tabs {{
                flex-direction: column;
            }}
            
            .pub-details {{
                flex-direction: column;
                gap: 10px;
            }}
            
            .stats-row {{
                justify-content: center;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Publications Dashboard</h1>
            <p>Comprehensive view of research publications and grant mappings</p>
        </div>

        <div class="search-controls">
            <div class="search-row">
                <div class="search-group">
                    <label for="authorSearch">Search by Author</label>
                    <input type="text" id="authorSearch" placeholder="Enter author name...">
                </div>
                <div class="search-group">
                    <label for="yearFilter">Publication Year</label>
                    <select id="yearFilter">
                        <option value="">All Years</option>
                    </select>
                </div>
                <div class="search-group">
                    <label for="confidenceFilter">Confidence Level</label>
                    <select id="confidenceFilter">
                        <option value="">All Levels</option>
                        <option value="Very High">Very High</option>
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                        <option value="Very Low">Very Low</option>
                    </select>
                </div>
                <button class="clear-btn" onclick="clearFilters()">Clear Filters</button>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('all')">All Publications</button>
            <button class="tab" onclick="showTab('bdbsf')">Barbara Dicker Brain Sciences Foundation</button>
        </div>

        <div id="allTab" class="tab-content active">
            <div class="stats" id="allStats">
                <div class="stats-row">
                    <div class="stat-item">
                        <div class="stat-number" id="totalPubs">-</div>
                        <div class="stat-label">Total Publications</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="displayedPubs">-</div>
                        <div class="stat-label">Publications Displayed</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="uniqueYears">-</div>
                        <div class="stat-label">Publication Years</div>
                    </div>
                </div>
            </div>
            <div class="publications-list" id="allPublications">
                <div class="loading">Loading publications...</div>
            </div>
        </div>

        <div id="bdbsfTab" class="tab-content">
            <div class="stats" id="bdbsfStats">
                <div class="stats-row">
                    <div class="stat-item">
                        <div class="stat-number" id="bdbsfTotalPubs">-</div>
                        <div class="stat-label">Total BDBSF Publications</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="bdbsfDisplayedPubs">-</div>
                        <div class="stat-label">Publications Displayed</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="veryHighPubs">-</div>
                        <div class="stat-label">Very High Confidence</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="highPubs">-</div>
                        <div class="stat-label">High Confidence</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="mediumPubs">-</div>
                        <div class="stat-label">Medium Confidence</div>
                    </div>
                </div>
            </div>
            <div class="publications-list" id="bdbsfPublications">
                <div class="loading">Loading BDBSF publications...</div>
            </div>
        </div>
    </div>

    <script>
        // Embedded publications data
        const publicationsData = {js_data};
        
        let allPublications = [];
        let bdbsfPublications = [];
        let currentTab = 'all';

        // Initialize data
        function initializeData() {{
            allPublications = publicationsData;
            
            // Filter BDBSF publications (Medium, High, Very High confidence)
            bdbsfPublications = allPublications.filter(pub => 
                ['Medium', 'High', 'Very High'].includes(pub['Confidence level'])
            );

            populateYearFilter();
            updateStats();
            displayPublications();
        }}

        // Populate year filter dropdown
        function populateYearFilter() {{
            const years = [...new Set(allPublications.map(pub => pub.publication_year))];
            years.sort((a, b) => b - a);
            
            const yearFilter = document.getElementById('yearFilter');
            years.forEach(year => {{
                if (year) {{
                    const option = document.createElement('option');
                    option.value = year;
                    option.textContent = year;
                    yearFilter.appendChild(option);
                }}
            }});
        }}

        // Update statistics
        function updateStats() {{
            // All publications stats
            document.getElementById('totalPubs').textContent = allPublications.length;
            document.getElementById('uniqueYears').textContent = 
                [...new Set(allPublications.map(pub => pub.publication_year))].filter(y => y).length;

            // BDBSF stats
            document.getElementById('bdbsfTotalPubs').textContent = bdbsfPublications.length;
            document.getElementById('veryHighPubs').textContent = 
                bdbsfPublications.filter(pub => pub['Confidence level'] === 'Very High').length;
            document.getElementById('highPubs').textContent = 
                bdbsfPublications.filter(pub => pub['Confidence level'] === 'High').length;
            document.getElementById('mediumPubs').textContent = 
                bdbsfPublications.filter(pub => pub['Confidence level'] === 'Medium').length;
        }}

        // Update displayed count and confidence stats based on current filters
        function updateDisplayedCount(filteredPublications) {{
            if (currentTab === 'all') {{
                document.getElementById('displayedPubs').textContent = filteredPublications.length;
            }} else {{
                document.getElementById('bdbsfDisplayedPubs').textContent = filteredPublications.length;
                
                // Update confidence level counts based on filtered publications
                document.getElementById('veryHighPubs').textContent = 
                    filteredPublications.filter(pub => pub['Confidence level'] === 'Very High').length;
                document.getElementById('highPubs').textContent = 
                    filteredPublications.filter(pub => pub['Confidence level'] === 'High').length;
                document.getElementById('mediumPubs').textContent = 
                    filteredPublications.filter(pub => pub['Confidence level'] === 'Medium').length;
            }}
        }}

        // Show specific tab
        function showTab(tabName) {{
            currentTab = tabName;
            
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            if (tabName === 'all') {{
                document.querySelectorAll('.tab')[0].classList.add('active');
                document.getElementById('allTab').classList.add('active');
            }} else {{
                document.querySelectorAll('.tab')[1].classList.add('active');
                document.getElementById('bdbsfTab').classList.add('active');
            }}
            
            displayPublications();
        }}

        // Display publications based on current tab and filters
        function displayPublications() {{
            const authorSearch = document.getElementById('authorSearch').value.toLowerCase();
            const yearFilter = document.getElementById('yearFilter').value;
            const confidenceFilter = document.getElementById('confidenceFilter').value;

            let publications = currentTab === 'all' ? allPublications : bdbsfPublications;
            
            // Apply filters
            publications = publications.filter(pub => {{
                const authorMatch = !authorSearch || 
                    (pub.authors_list && pub.authors_list.toLowerCase().includes(authorSearch));
                const yearMatch = !yearFilter || pub.publication_year == yearFilter;
                const confidenceMatch = !confidenceFilter || 
                    pub['Confidence level'] === confidenceFilter;
                
                return authorMatch && yearMatch && confidenceMatch;
            }});

            const containerId = currentTab === 'all' ? 'allPublications' : 'bdbsfPublications';
            const container = document.getElementById(containerId);
            
            // Update the displayed count
            updateDisplayedCount(publications);
            
            if (publications.length === 0) {{
                container.innerHTML = '<div class="no-results">No publications found matching your criteria</div>';
                return;
            }}

            container.innerHTML = publications.map(pub => createPublicationCard(pub)).join('');
        }}

        // Create HTML for publication card
        function createPublicationCard(pub) {{
            const confidenceClass = pub['Confidence level'] ? 
                `confidence-${{pub['Confidence level'].toLowerCase().replace(' ', '-')}}` : '';
            
            // Different card layout for different tabs
            if (currentTab === 'all') {{
                // Simple card for "All Publications" tab - only basic info
                return `
                    <div class="publication-card">
                        <div class="pub-title">${{pub.title || 'Untitled'}}</div>
                        <div class="pub-authors">${{pub.authors_list || 'No authors listed'}}</div>
                        <div class="pub-details">
                            <div class="pub-detail">
                                <span class="pub-year">${{pub.publication_year || 'N/A'}}</span>
                            </div>
                            ${{pub.doi ? `
                                <div class="pub-detail">
                                    <strong>DOI:</strong> 
                                    <a href="https://doi.org/${{pub.doi}}" target="_blank">${{pub.doi}}</a>
                                </div>
                            ` : ''}}
                        </div>
                    </div>
                `;
            }} else {{
                // Full card for "BDBSF" tab - includes grant information
                const grantInfo = pub['Associated Grant'] ? `
                    <div class="grant-info">
                        <div class="grant-title">Associated Grant: ${{pub['Associated Grant'] || 'N/A'}}</div>
                        <div class="grant-reasoning">${{pub.Reasoning || 'No reasoning provided'}}</div>
                    </div>
                ` : '';

                return `
                    <div class="publication-card">
                        <div class="pub-title">${{pub.title || 'Untitled'}}</div>
                        <div class="pub-authors">${{pub.authors_list || 'No authors listed'}}</div>
                        <div class="pub-details">
                            <div class="pub-detail">
                                <span class="pub-year">${{pub.publication_year || 'N/A'}}</span>
                            </div>
                            ${{pub['Confidence level'] ? `
                                <div class="pub-detail">
                                    <span class="confidence-badge ${{confidenceClass}}">
                                        ${{pub['Confidence level']}} Confidence
                                    </span>
                                </div>
                            ` : ''}}
                            ${{pub.doi ? `
                                <div class="pub-detail">
                                    <strong>DOI:</strong> 
                                    <a href="https://doi.org/${{pub.doi}}" target="_blank">${{pub.doi}}</a>
                                </div>
                            ` : ''}}
                        </div>
                        ${{grantInfo}}
                    </div>
                `;
            }}
        }}

        // Clear all filters
        function clearFilters() {{
            document.getElementById('authorSearch').value = '';
            document.getElementById('yearFilter').value = '';
            document.getElementById('confidenceFilter').value = '';
            displayPublications();
        }}

        // Add event listeners for real-time filtering
        document.getElementById('authorSearch').addEventListener('input', displayPublications);
        document.getElementById('yearFilter').addEventListener('change', displayPublications);
        document.getElementById('confidenceFilter').addEventListener('change', displayPublications);

        // Initialize when page loads
        window.addEventListener('load', initializeData);
    </script>
</body>
</html>'''

    # Write the HTML file
    with open('publications_dashboard_embedded.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("Created publications_dashboard_embedded.html with embedded data")
    print(f"Dashboard contains {len(publications_data)} publications")
    print(f"BDBSF-relevant publications (Medium/High/Very High): {len([p for p in publications_data if p.get('Confidence level') in ['Medium', 'High', 'Very High']])}")

if __name__ == "__main__":
    create_embedded_dashboard()