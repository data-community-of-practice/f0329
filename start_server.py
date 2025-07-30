#!/usr/bin/env python3
"""
Simple HTTP server to serve the publications viewer webpage.
This allows the webpage to fetch the CSV file without CORS issues.
"""

import http.server
import socketserver
import webbrowser
import os
import sys

def start_server():
    # Set the port
    PORT = 8000
    
    # Change to the directory containing the files
    web_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(web_dir)
    
    # Create the server
    Handler = http.server.SimpleHTTPRequestHandler
    
    # Add CORS headers to allow file access
    class CORSRequestHandler(Handler):
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()

    with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
        print(f"Starting server at http://localhost:{PORT}")
        print(f"Serving files from: {web_dir}")
        print(f"\nTo view the publications database:")
        print(f"  Open: http://localhost:{PORT}/publications_viewer_fixed.html")
        print(f"\nPress Ctrl+C to stop the server")
        
        # Try to open the browser automatically
        try:
            webbrowser.open(f'http://localhost:{PORT}/publications_viewer_fixed.html')
            print(f"\nOpening browser automatically...")
        except:
            print(f"\nCouldn't open browser automatically. Please open the URL manually.")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print(f"\nServer stopped.")
            sys.exit(0)

if __name__ == "__main__":
    start_server()