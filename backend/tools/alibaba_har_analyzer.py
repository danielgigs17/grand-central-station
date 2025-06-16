#!/usr/bin/env python3
"""
Alibaba HAR File Analyzer
Analyzes HAR files to extract authentication flows and API patterns for Alibaba.com
"""
import json
import sys
from typing import Dict, List, Any
from urllib.parse import urlparse, parse_qs
import re


class AlibabaHARAnalyzer:
    def __init__(self, har_file_path: str):
        self.har_file_path = har_file_path
        self.har_data = None
        self.login_flow = []
        self.api_endpoints = {}
        self.cookies = {}
        self.headers = {}
        
    def load_har(self):
        """Load and parse HAR file."""
        with open(self.har_file_path, 'r') as f:
            self.har_data = json.load(f)
            
    def analyze_login_flow(self):
        """Extract login-related requests."""
        print("\n=== LOGIN FLOW ANALYSIS ===")
        
        for entry in self.har_data['log']['entries']:
            request = entry['request']
            response = entry['response']
            url = request['url']
            
            # Check for login-related URLs
            if 'login' in url.lower() or 'auth' in url.lower():
                self.login_flow.append({
                    'url': url,
                    'method': request['method'],
                    'status': response['status'],
                    'headers': {h['name']: h['value'] for h in request['headers']},
                    'postData': request.get('postData', {}),
                    'cookies': response.get('cookies', [])
                })
                
                print(f"\nLogin Request Found:")
                print(f"  URL: {url}")
                print(f"  Method: {request['method']}")
                print(f"  Status: {response['status']}")
                
                if request['method'] == 'POST' and 'postData' in request:
                    print(f"  Post Data Available: Yes")
                    if 'params' in request['postData']:
                        print("  Parameters:")
                        for param in request['postData']['params']:
                            if param['name'] not in ['password', 'bx-ua', 'bx-umidtoken']:
                                print(f"    - {param['name']}: {param['value'][:50]}...")
                                
    def analyze_api_patterns(self):
        """Extract API endpoints and patterns."""
        print("\n=== API PATTERNS ANALYSIS ===")
        
        api_patterns = {
            'mtop': [],  # Alibaba's MTOP API
            'message': [],  # Message-related APIs
            'conversation': [],  # Conversation APIs
            'websocket': []  # WebSocket connections
        }
        
        for entry in self.har_data['log']['entries']:
            request = entry['request']
            response = entry['response']
            url = request['url']
            
            # Skip static resources
            if any(ext in url for ext in ['.css', '.js', '.png', '.jpg', '.gif', '.woff']):
                continue
                
            # Categorize APIs
            if 'mtop' in url:
                api_patterns['mtop'].append({
                    'url': url,
                    'api': self._extract_mtop_api(url),
                    'method': request['method'],
                    'status': response['status']
                })
            elif 'message' in url and 'api' in url:
                api_patterns['message'].append({
                    'url': url,
                    'method': request['method'],
                    'status': response['status']
                })
            elif 'conversation' in url:
                api_patterns['conversation'].append({
                    'url': url,
                    'method': request['method'],
                    'status': response['status']
                })
            elif 'ws://' in url or 'wss://' in url:
                api_patterns['websocket'].append({
                    'url': url,
                    'method': request['method'],
                    'status': response['status']
                })
                
        # Print findings
        for category, endpoints in api_patterns.items():
            if endpoints:
                print(f"\n{category.upper()} Endpoints:")
                for ep in endpoints[:5]:  # Show first 5
                    print(f"  - {ep.get('api', ep['url'])}")
                    print(f"    Method: {ep['method']}, Status: {ep['status']}")
                    
    def _extract_mtop_api(self, url: str) -> str:
        """Extract MTOP API name from URL."""
        match = re.search(r'/h5/([^/]+)/[\d.]+/', url)
        if match:
            return match.group(1)
        return url
        
    def extract_cookies_and_headers(self):
        """Extract important cookies and headers after login."""
        print("\n=== COOKIES AND HEADERS ===")
        
        # Find cookies set after login
        for entry in self.har_data['log']['entries']:
            if 'login' in entry['request']['url'] and entry['response']['status'] == 200:
                for cookie in entry['response'].get('cookies', []):
                    self.cookies[cookie['name']] = cookie['value']
                    
        # Find common headers used in API requests
        header_frequency = {}
        for entry in self.har_data['log']['entries']:
            for header in entry['request']['headers']:
                name = header['name']
                if name.startswith(':') or name in ['accept-encoding', 'accept-language']:
                    continue
                if name not in header_frequency:
                    header_frequency[name] = 0
                header_frequency[name] += 1
                
        # Print important headers
        print("\nCommon Headers:")
        for header, count in sorted(header_frequency.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {header}: {count} occurrences")
            
    def find_conversation_data(self):
        """Try to find conversation/message data in responses."""
        print("\n=== SEARCHING FOR CONVERSATION DATA ===")
        
        for entry in self.har_data['log']['entries']:
            response = entry['response']
            if 'content' in response and 'text' in response['content']:
                content = response['content']['text']
                if content and ('Linda Wu' in content or 'conversation' in content.lower()):
                    print(f"\nPotential conversation data found in:")
                    print(f"  URL: {entry['request']['url']}")
                    print(f"  Method: {entry['request']['method']}")
                    print(f"  Status: {response['status']}")
                    
    def generate_adapter_code(self):
        """Generate adapter code based on findings."""
        print("\n=== ADAPTER CODE SUGGESTIONS ===")
        
        # Find the actual login endpoint
        login_endpoint = None
        for flow in self.login_flow:
            if flow['method'] == 'POST' and 'login.do' in flow['url']:
                login_endpoint = flow
                break
                
        if login_endpoint:
            print("\nLogin Endpoint Configuration:")
            print(f"LOGIN_URL = '{login_endpoint['url']}'")
            print("\nRequired Headers:")
            important_headers = ['content-type', 'origin', 'referer', 'user-agent']
            for header in important_headers:
                if header in login_endpoint['headers']:
                    print(f"  '{header}': '{login_endpoint['headers'][header]}'")
                    
            print("\nLogin Parameters Found:")
            if 'params' in login_endpoint['postData']:
                for param in login_endpoint['postData']['params']:
                    if param['name'] not in ['password', 'bx-ua', 'bx-umidtoken', 'bx-sys']:
                        print(f"  - {param['name']}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python alibaba_har_analyzer.py <har_file_path>")
        sys.exit(1)
        
    har_file = sys.argv[1]
    analyzer = AlibabaHARAnalyzer(har_file)
    
    print(f"Analyzing HAR file: {har_file}")
    analyzer.load_har()
    analyzer.analyze_login_flow()
    analyzer.analyze_api_patterns()
    analyzer.extract_cookies_and_headers()
    analyzer.find_conversation_data()
    analyzer.generate_adapter_code()


if __name__ == "__main__":
    main()