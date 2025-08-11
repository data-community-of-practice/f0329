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
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Roboto', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #ffffff;
            background-image: url('ResearchGraph dots.png');
            background-repeat: repeat;
            background-size: 50px auto;
            background-attachment: fixed;
            background-position: center;
            position: relative;
        }}

        body::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.95);
            z-index: -1;
            pointer-events: none;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px 60px;
        }}

        .header {{
            background: linear-gradient(135deg, #fff 0%, #f8f9fa 50%, #fff 100%);
            color: #333;
            padding: 50px 30px;
            margin-bottom: 30px;
            position: relative;
            display: flex;
            align-items: center;
            min-height: 120px;
            border-bottom: 1px solid #f0f0f0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            overflow: hidden;
        }}

        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 6px;
            background: linear-gradient(90deg, #ff6b35 0%, #f7931e 25%, #ffab00 50%, #f7931e 75%, #ff6b35 100%);
            background-size: 200% 100%;
            animation: gradientShift 8s ease-in-out infinite;
        }}

        .header::after {{
            content: '';
            position: absolute;
            top: -50px;
            right: -50px;
            width: 200px;
            height: 200px;
            background: radial-gradient(circle, rgba(255,107,53,0.08) 0%, rgba(255,107,53,0.02) 40%, transparent 70%);
            border-radius: 50%;
        }}

        .header .decorative-left {{
            position: absolute;
            top: 20px;
            left: 30px;
            width: 60px;
            height: 60px;
            background: linear-gradient(45deg, rgba(255,107,53,0.1) 0%, rgba(247,147,30,0.05) 100%);
            border-radius: 50%;
            opacity: 0.6;
        }}

        .header .decorative-right {{
            position: absolute;
            bottom: 15px;
            right: 80px;
            width: 45px;
            height: 45px;
            background: linear-gradient(45deg, rgba(255,171,0,0.08) 0%, rgba(255,107,53,0.04) 100%);
            border-radius: 50%;
            opacity: 0.7;
        }}

        .header .content {{
            flex: 1;
            text-align: center;
            position: relative;
            z-index: 2;
        }}

        .header h1 {{
            font-size: 3.0em;
            margin-bottom: 12px;
            font-weight: 300;
            color: #2c3e50;
            letter-spacing: -1.2px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
            position: relative;
        }}

        .header h1::after {{
            content: '';
            position: absolute;
            bottom: -8px;
            left: 50%;
            transform: translateX(-50%);
            width: 60px;
            height: 3px;
            background: linear-gradient(90deg, #ff6b35 0%, #f7931e 50%, #ffab00 100%);
            border-radius: 2px;
        }}

        .header h1 span {{
            color: #ff6b35;
            font-weight: 500;
            position: relative;
        }}

        .header p {{
            font-size: 1.2em;
            color: #666;
            font-weight: 400;
            margin: 0;
            opacity: 0.85;
            margin-top: 15px;
        }}

        @keyframes gradientShift {{
            0%, 100% {{
                background-position: 0% 50%;
            }}
            50% {{
                background-position: 100% 50%;
            }}
        }}

        .search-controls {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            border: 1px solid #f0f0f0;
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
            border-color: #ff6b35;
        }}

        .clear-btn {{
            background: #ff6b35;
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
            background: #e55a2b;
        }}

        .tabs {{
            display: flex;
            background: white;
            border-radius: 8px 8px 0 0;
            overflow: hidden;
            border: 1px solid #f0f0f0;
            border-bottom: none;
        }}

        .tab {{
            flex: 1;
            padding: 15px 20px;
            background: #fafafa;
            border: none;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            transition: all 0.3s;
            border-bottom: 2px solid transparent;
            color: #666;
        }}

        .tab:hover {{
            background: #f5f5f5;
            color: #333;
        }}

        .tab.active {{
            background: white;
            border-bottom-color: #ff6b35;
            color: #ff6b35;
            font-weight: 600;
        }}

        .tab-content {{
            display: none;
            background: white;
            border-radius: 0 0 8px 8px;
            border: 1px solid #f0f0f0;
        }}

        .tab-content.active {{
            display: block;
        }}

        .stats {{
            padding: 30px 20px;
            background: #fafafa;
            border-bottom: 1px solid #f0f0f0;
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
            padding: 20px;
            background: white;
            border-radius: 6px;
            border: 1px solid #f0f0f0;
            min-width: 140px;
            flex: 1;
        }}

        .stat-item.wide {{
            min-width: 180px;
            flex: 1.5;
        }}

        .stat-number {{
            font-size: 1.9em;
            font-weight: 300;
            color: #ff6b35;
            margin-bottom: 5px;
            text-align: center;
        }}

        .stat-label {{
            font-size: 0.8em;
            color: #666;
            text-align: center;
            font-weight: 500;
        }}

        .publications-list {{
            max-height: 600px;
            overflow-y: auto;
            padding: 20px;
        }}

        .publication-card {{
            background: white;
            border: 1px solid #f0f0f0;
            border-radius: 6px;
            padding: 24px;
            margin-bottom: 12px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .publication-card:hover {{
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
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
            background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
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
            border-left: 4px solid #ff6b35;
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
            color: #ff6b35;
        }}

        .footer {{
            text-align: right;
            padding: 30px 20px 20px 20px;
            background: white;
            border-top: 1px solid #f0f0f0;
            margin-top: 30px;
            position: relative;
        }}

        .footer .logo {{
            position: absolute;
            bottom: 20px;
            right: 30px;
            z-index: 10;
        }}

        .footer .logo img {{
            max-height: 30px;
            height: auto;
            width: auto;
        }}

        .footer .credits {{
            font-size: 0.85em;
            color: #999;
            margin-bottom: 40px;
        }}

        .footer .credits span {{
            color: #ff6b35;
            font-weight: 500;
        }}

        .trends-content {{
            padding: 20px;
        }}

        .trends-section {{
            margin-bottom: 40px;
            background: white;
            border-radius: 8px;
            border: 1px solid #f0f0f0;
            overflow: hidden;
        }}

        .trends-section h3 {{
            background: #fafafa;
            padding: 15px 20px;
            margin: 0;
            font-size: 1.1em;
            font-weight: 600;
            color: #333;
            border-bottom: 1px solid #f0f0f0;
        }}

        .trends-section > div {{
            padding: 20px;
        }}

        .topic-card {{
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 12px;
            transition: all 0.2s;
        }}

        .topic-card:hover {{
            border-color: #ff6b35;
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(255,107,53,0.1);
        }}

        .topic-name {{
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 8px;
            font-size: 0.95em;
            line-height: 1.3;
            word-wrap: break-word;
        }}

        .topic-stats {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .topic-count {{
            background: #ff6b35;
            color: white;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .topic-years {{
            color: #666;
            font-size: 0.9em;
        }}

        .topic-trend {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 0.85em;
        }}

        .trend-up {{
            color: #28a745;
        }}

        .trend-down {{
            color: #dc3545;
        }}

        .trend-stable {{
            color: #6c757d;
        }}

        .yearly-chart {{
            display: flex;
            align-items: end;
            gap: 3px;
            height: 80px;
            margin: 10px 0;
        }}

        .year-bar {{
            background: linear-gradient(to top, #ff6b35, #f7931e);
            border-radius: 2px 2px 0 0;
            min-width: 8px;
            flex: 1;
            position: relative;
            transition: all 0.2s;
        }}

        .year-bar:hover {{
            background: linear-gradient(to top, #e55a2b, #e8841a);
            transform: translateY(-2px);
        }}

        .year-label {{
            position: absolute;
            bottom: -25px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 0.7em;
            color: #666;
            writing-mode: horizontal-tb;
        }}

        .year-value {{
            position: absolute;
            top: -20px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 0.7em;
            color: #333;
            font-weight: 600;
            opacity: 0;
            transition: opacity 0.2s;
        }}

        .year-bar:hover .year-value {{
            opacity: 1;
        }}

        .chart-container {{
            position: relative;
            margin: 20px 0;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 10px 20px;
            }}
            
            .header {{
                flex-direction: column;
                text-align: center;
                min-height: auto;
                padding: 20px;
            }}

            .header .content {{
                margin-left: 0;
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
            <div class="decorative-left"></div>
            <div class="decorative-right"></div>
            <div class="content">
                <h1>Publications <span>Dashboard</span></h1>
                <p>Comprehensive view of research publications and grant mappings</p>
            </div>
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
            <button class="tab" onclick="showTab('trends')">Trends & Analytics</button>
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

        <div id="trendsTab" class="tab-content">
            <div class="stats" id="trendsStats">
                <div class="stats-row">
                    <div class="stat-item">
                        <div class="stat-number" id="totalTopics">-</div>
                        <div class="stat-label">Research Topics</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="avgPubsPerYear">-</div>
                        <div class="stat-label">Avg Pubs/Year</div>
                    </div>
                    <div class="stat-item wide">
                        <div class="stat-number" id="topTopic">-</div>
                        <div class="stat-label">Top Topic</div>
                    </div>
                </div>
            </div>
            <div class="trends-content">
                <div class="trends-section">
                    <h3>Research Topics Over Time</h3>
                    <div class="topic-trends" id="topicTrends">
                        <div class="loading">Analyzing topic trends...</div>
                    </div>
                </div>
                <div class="trends-section">
                    <h3>Yearly Growth Trends</h3>
                    <div class="yearly-trends" id="yearlyTrends">
                        <div class="loading">Computing yearly trends...</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="footer">
            <div class="credits">
                <p>Powered by <span>ResearchGraph</span> • Publications Dashboard • AI-Powered Grant Mapping</p>
            </div>
            <div class="logo">
                <img src="ResearchGraph.png" alt="ResearchGraph" onerror="this.style.display='none'">
            </div>
        </div>
    </div>

    <script>
        // Embedded publications data
        const publicationsData = {js_data};
        
        let allPublications = [];
        let bdbsfPublications = [];
        let topicAnalysis = {{}};
        let currentTab = 'all';

        // Initialize data
        function initializeData() {{
            allPublications = publicationsData;
            
            // Filter BDBSF publications (Medium, High, Very High confidence)
            bdbsfPublications = allPublications.filter(pub => 
                ['Medium', 'High', 'Very High'].includes(pub['Confidence level'])
            );

            populateYearFilter();
            analyzeTopics();
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

        // Analyze topics from publication titles
        function analyzeTopics() {{
            const topics = {{}};
            const stopWords = new Set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should']);
            
            // Extract key terms from BDBSF publications
            bdbsfPublications.forEach(pub => {{
                if (!pub.title) return;
                
                const year = pub.publication_year || 'Unknown';
                const words = pub.title.toLowerCase()
                    .replace(/[^a-z0-9\\s-]/g, '')
                    .split(/\\s+/)
                    .filter(word => word.length > 3 && !stopWords.has(word));
                
                // First check for compound terms (multi-word medical conditions)
                const titleLower = pub.title.toLowerCase();
                const compoundTerms = [];
                
                // Check for compound medical terms first
                if (titleLower.includes('anorexia nervosa')) compoundTerms.push('Eating Disorders');
                if (titleLower.includes('alzheimer') || titleLower.includes('dementia')) compoundTerms.push('Neurodegenerative Diseases');
                if (titleLower.includes('parkinson')) compoundTerms.push('Neurodegenerative Diseases');
                if (titleLower.includes('covid-19') || titleLower.includes('covid')) compoundTerms.push('COVID-19 Research');
                if (titleLower.includes('clinical trial')) compoundTerms.push('Clinical Trials');
                if (titleLower.includes('aged care')) compoundTerms.push('Aged Care Research');
                if (titleLower.includes('mental health')) compoundTerms.push('Mental Health');
                
                // Extract single-word meaningful terms
                const meaningfulTerms = [];
                const medicalTerms = ['cannabis', 'cbd', 'thc', 'pain', 'sleep', 'anxiety', 'depression', 'cognitive', 'neurocognitive', 'mental', 'health', 'brain', 'treatment', 'therapy', 'clinical', 'trial', 'study', 'effects', 'patients', 'aged', 'care', 'driving', 'alcohol', 'drug', 'medication', 'chronic', 'acute', 'medical', 'pharmacology'];
                
                words.forEach(word => {{
                    if (medicalTerms.includes(word) || word.length > 6) {{
                        meaningfulTerms.push(word);
                    }}
                }});
                
                // Combine compound terms and single terms
                const allTerms = [...compoundTerms, ...meaningfulTerms];
                
                // Group similar terms
                allTerms.forEach(term => {{
                    let topicKey = term;
                    
                    // Skip if already a compound term (these are already categorized)
                    if (compoundTerms.includes(term)) {{
                        topicKey = term;
                    }}
                    // Normalize single terms
                    else if (term.includes('cannab') || term.includes('cbd') || term.includes('thc')) topicKey = 'Cannabis Research';
                    else if (term.includes('sleep') || term.includes('insomnia')) topicKey = 'Sleep Studies';
                    else if (term.includes('pain') || term.includes('analges')) topicKey = 'Pain Management';
                    else if (term.includes('cognit') || term.includes('neurocog')) topicKey = 'Cognitive Research';
                    else if (term.includes('mental') || term.includes('anxiety') || term.includes('depression')) topicKey = 'Mental Health';
                    else if (term.includes('anorexia') || term.includes('nervosa')) topicKey = 'Eating Disorders';
                    else if (term.includes('driving') || term.includes('impair')) topicKey = 'Driving & Impairment';
                    else if (term.includes('clinical') || term.includes('trial')) topicKey = 'Clinical Trials';
                    
                    if (!topics[topicKey]) {{
                        topics[topicKey] = {{
                            count: 0,
                            years: {{}},
                            publications: []
                        }};
                    }}
                    
                    if (!topics[topicKey].years[year]) {{
                        topics[topicKey].years[year] = 0;
                    }}
                    
                    topics[topicKey].count++;
                    topics[topicKey].years[year]++;
                    topics[topicKey].publications.push(pub);
                }});
            }});
            
            // Calculate trends for each topic
            Object.keys(topics).forEach(topic => {{
                const years = Object.keys(topics[topic].years).map(Number).filter(y => !isNaN(y)).sort();
                if (years.length > 1) {{
                    const firstHalf = years.slice(0, Math.ceil(years.length / 2));
                    const secondHalf = years.slice(-Math.ceil(years.length / 2));
                    
                    const firstHalfAvg = firstHalf.reduce((sum, year) => sum + (topics[topic].years[year] || 0), 0) / firstHalf.length;
                    const secondHalfAvg = secondHalf.reduce((sum, year) => sum + (topics[topic].years[year] || 0), 0) / secondHalf.length;
                    
                    const change = ((secondHalfAvg - firstHalfAvg) / firstHalfAvg) * 100;
                    
                    topics[topic].trend = change > 15 ? 'increasing' : (change < -15 ? 'decreasing' : 'stable');
                    topics[topic].trendValue = change;
                }} else {{
                    topics[topic].trend = 'stable';
                    topics[topic].trendValue = 0;
                }}
                
                topics[topic].yearRange = years.length > 0 ? `${{Math.min(...years)}}-${{Math.max(...years)}}` : 'N/A';
            }});
            
            topicAnalysis = topics;
            displayTrends();
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
            }} else if (tabName === 'bdbsf') {{
                document.querySelectorAll('.tab')[1].classList.add('active');
                document.getElementById('bdbsfTab').classList.add('active');
            }} else if (tabName === 'trends') {{
                document.querySelectorAll('.tab')[2].classList.add('active');
                document.getElementById('trendsTab').classList.add('active');
                updateTrendsStats();
            }}
            
            if (tabName !== 'trends') {{
                displayPublications();
            }}
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

        // Update trends statistics
        function updateTrendsStats() {{
            const topics = Object.keys(topicAnalysis);
            const totalPubs = bdbsfPublications.length;
            const years = [...new Set(bdbsfPublications.map(pub => pub.publication_year).filter(y => y))].sort();
            const avgPubsPerYear = years.length > 0 ? Math.round(totalPubs / years.length) : 0;
            
            // Find top topic
            let topTopic = 'N/A';
            let maxCount = 0;
            Object.keys(topicAnalysis).forEach(topic => {{
                if (topicAnalysis[topic].count > maxCount) {{
                    maxCount = topicAnalysis[topic].count;
                    topTopic = topic.length > 20 ? topic.substring(0, 20) + '...' : topic;
                }}
            }});
            
            document.getElementById('totalTopics').textContent = topics.length;
            document.getElementById('avgPubsPerYear').textContent = avgPubsPerYear;
            document.getElementById('topTopic').textContent = topTopic;
        }}

        // Display trends analysis
        function displayTrends() {{
            // Display topic trends
            const topicTrendsHtml = Object.keys(topicAnalysis)
                .sort((a, b) => topicAnalysis[b].count - topicAnalysis[a].count)
                .slice(0, 10) // Show top 10 topics
                .map(topic => {{
                    const data = topicAnalysis[topic];
                    const trendIcon = data.trend === 'increasing' ? '↗' : (data.trend === 'decreasing' ? '↘' : '→');
                    const trendClass = data.trend === 'increasing' ? 'trend-up' : (data.trend === 'decreasing' ? 'trend-down' : 'trend-stable');
                    
                    return `
                        <div class="topic-card">
                            <div class="topic-name">${{topic}}</div>
                            <div class="topic-stats">
                                <div class="topic-count">${{data.count}} publications</div>
                                <div class="topic-years">${{data.yearRange}}</div>
                                <div class="topic-trend ${{trendClass}}">
                                    ${{trendIcon}} ${{data.trend}}
                                </div>
                            </div>
                        </div>
                    `;
                }}).join('');
            
            document.getElementById('topicTrends').innerHTML = topicTrendsHtml;

            // Display yearly trends
            const years = [...new Set(bdbsfPublications.map(pub => pub.publication_year).filter(y => y))].sort();
            const yearCounts = {{}};
            years.forEach(year => {{
                yearCounts[year] = bdbsfPublications.filter(pub => pub.publication_year === year).length;
            }});
            
            const maxCount = Math.max(...Object.values(yearCounts));
            const yearlyTrendsHtml = `
                <div class="chart-container">
                    <div class="yearly-chart">
                        ${{years.map(year => `
                            <div class="year-bar" style="height: ${{(yearCounts[year] / maxCount) * 60 + 10}}px;">
                                <div class="year-label">${{year}}</div>
                                <div class="year-value">${{yearCounts[year]}}</div>
                            </div>
                        `).join('')}}
                    </div>
                    <div style="text-align: center; margin-top: 30px; color: #666; font-size: 0.9em;">
                        Publications per year (hover for exact counts)
                    </div>
                </div>
            `;
            
            document.getElementById('yearlyTrends').innerHTML = yearlyTrendsHtml;
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