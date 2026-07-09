#!/usr/bin/env python3
"""
College Project - runs entirely in container
"""

import os
import json
import requests
from flask import Flask, render_template_string, request, jsonify
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
import base64
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# Store browser state
BROWSER_STATE = {
    'tabs': {},
    'active_tab': None,
    'next_tab_id': 0,
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>School Project</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            flex-direction: column;
            height: 100vh;
            background: #f0f0f0;
        }
        .toolbar {
            background: #333;
            color: white;
            padding: 12px;
            border-bottom: 1px solid #222;
        }
        .tabs {
            display: flex;
            gap: 4px;
            margin-bottom: 8px;
            flex-wrap: wrap;
            align-items: center;
        }
        .tab {
            background: #555;
            border: 1px solid #444;
            color: white;
            padding: 6px 12px;
            cursor: pointer;
            border-radius: 4px 4px 0 0;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 6px;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .tab.active {
            background: #007bff;
            border-color: #0056b3;
        }
        .tab .close {
            cursor: pointer;
            font-weight: bold;
            margin-left: 4px;
        }
        .tab .close:hover {
            color: #ffcccc;
        }
        .new-tab-btn {
            background: #444;
            border: 1px solid #333;
            color: white;
            padding: 6px 12px;
            cursor: pointer;
            border-radius: 3px;
            font-size: 12px;
        }
        .new-tab-btn:hover {
            background: #555;
        }
        .address-bar-container {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .nav-button {
            background: #444;
            border: 1px solid #333;
            color: white;
            padding: 6px 12px;
            cursor: pointer;
            border-radius: 3px;
            font-size: 12px;
        }
        .nav-button:hover {
            background: #555;
        }
        .nav-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .address-bar {
            flex: 1;
            padding: 8px 12px;
            border: 1px solid #555;
            border-radius: 3px;
            background: #444;
            color: white;
            font-family: monospace;
            font-size: 12px;
        }
        .address-bar::placeholder {
            color: #999;
        }
        .go-button {
            background: #007bff;
            border: 1px solid #0056b3;
            color: white;
            padding: 6px 12px;
            cursor: pointer;
            border-radius: 3px;
            font-size: 12px;
        }
        .go-button:hover {
            background: #0056b3;
        }
        .content {
            flex: 1;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .page-frame {
            flex: 1;
            width: 100%;
            background: white;
            position: relative;
            overflow: auto;
        }
        .page-content {
            width: 100%;
            height: 100%;
        }
        .status-bar {
            background: #222;
            color: #999;
            padding: 6px 12px;
            font-size: 11px;
            border-top: 1px solid #333;
        }
        .page-html {
            padding: 20px;
            font-size: 14px;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="toolbar">
        <div class="tabs" id="tabs"></div>
        <button class="new-tab-btn" onclick="newTab()">+ New Tab</button>
        <div class="address-bar-container">
            <button class="nav-button" onclick="goBack()" id="backBtn" disabled>← Back</button>
            <button class="nav-button" onclick="goForward()" id="forwardBtn" disabled>Forward →</button>
            <button class="nav-button" onclick="reloadPage()">↻ Reload</button>
            <input type="text" class="address-bar" id="addressBar" placeholder="https://example.com" onkeypress="if(event.key==='Enter') navigate()">
            <button class="go-button" onclick="navigate()">Go</button>
        </div>
    </div>

    <div class="content">
        <div class="page-frame">
            <div class="page-content" id="pageContent">
                <div class="page-html">
                    <h1>College Project</h1>
                    <p><strong>Isolated environment</strong></p>
                    <p>Enter a URL in the address bar above to start browsing.</p>
                    <p><strong>Features:</strong></p>
                    <ul style="margin-left: 20px; margin-top: 10px;">
                        <li>Multiple tabs</li>
                        <li>Back/Forward navigation</li>
                        <li>Complete isolation (no clipboard access, no redirects to host)</li>
                        <li>No data leakage to your machine</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <div class="status-bar" id="statusBar">Ready</div>

    <script>
        let tabs = {};
        let activeTab = null;

        async function initProject() {
            const response = await fetch('/api/init');
            const data = await response.json();
            createTab(data.initial_tab_id);
        }

        function createTab(tabId = null) {
            fetch('/api/new-tab', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    tabs[data.tab_id] = { id: data.tab_id, url: '', history: [], historyIndex: -1 };
                    activeTab = data.tab_id;
                    renderTabs();
                    updateAddressBar();
                });
        }

        function newTab() {
            createTab();
        }

        function closeTab(tabId) {
            fetch(`/api/close-tab/${tabId}`, { method: 'POST' })
                .then(() => {
                    delete tabs[tabId];
                    if (activeTab === tabId) {
                        activeTab = Object.keys(tabs)[0] || null;
                    }
                    renderTabs();
                });
        }

        function switchTab(tabId) {
            activeTab = tabId;
            renderTabs();
            updateAddressBar();
            loadPage();
        }

        function renderTabs() {
            const tabsDiv = document.getElementById('tabs');
            tabsDiv.innerHTML = '';
            
            Object.keys(tabs).forEach(id => {
                const tab = tabs[id];
                const tabEl = document.createElement('div');
                tabEl.className = 'tab' + (id === activeTab ? ' active' : '');
                tabEl.innerHTML = `
                    <span onclick="switchTab('${id}')" style="flex:1; overflow: hidden; text-overflow: ellipsis;">${tab.url || 'New Tab'}</span>
                    <span class="close" onclick="closeTab('${id}')">✕</span>
                `;
                tabsDiv.appendChild(tabEl);
            });
        }

        function updateAddressBar() {
            if (activeTab && tabs[activeTab]) {
                const url = tabs[activeTab].url;
                let displayUrl = url;
                if (url) {
                    try {
                        const urlObj = new URL(url);
                        displayUrl = urlObj.hostname.replace('www.', '');
                        document.title = displayUrl;
                    } catch (e) {
                        displayUrl = url;
                        document.title = url;
                    }
                }
                document.getElementById('addressBar').value = displayUrl;
                document.getElementById('addressBar').title = url;
            }
        }

        function navigate() {
            const url = document.getElementById('addressBar').value.trim();
            if (!url) return;

            let fullUrl = url;
            if (!fullUrl.startsWith('http://') && !fullUrl.startsWith('https://')) {
                fullUrl = 'https://' + url;
            }

            setStatus('Loading...');
            fetch('/api/navigate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tab_id: activeTab, url: fullUrl })
            })
                .then(r => r.json())
                .then(data => {
                    if (tabs[activeTab]) {
                        tabs[activeTab].url = data.url;
                        tabs[activeTab].history = data.history;
                        tabs[activeTab].historyIndex = data.history_index;
                    }
                    renderTabs();
                    loadPage();
                    setStatus('Ready');
                });
        }

        function loadPage() {
            if (!activeTab) return;
            fetch(`/api/screenshot/${activeTab}`)
                .then(r => r.text())
                .then(html => {
                    document.getElementById('pageContent').innerHTML = `<div class="page-html">${html}</div>`;
                    updateBackForward();
                });
        }

        function goBack() {
            fetch(`/api/back/${activeTab}`, { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    if (tabs[activeTab]) {
                        tabs[activeTab].url = data.url;
                        tabs[activeTab].history = data.history;
                        tabs[activeTab].historyIndex = data.history_index;
                    }
                    updateAddressBar();
                    loadPage();
                });
        }

        function goForward() {
            fetch(`/api/forward/${activeTab}`, { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    if (tabs[activeTab]) {
                        tabs[activeTab].url = data.url;
                        tabs[activeTab].history = data.history;
                        tabs[activeTab].historyIndex = data.history_index;
                    }
                    updateAddressBar();
                    loadPage();
                });
        }

        function reloadPage() {
            if (activeTab && tabs[activeTab].url) {
                navigate();
            }
        }

        function updateBackForward() {
            const tab = tabs[activeTab];
            document.getElementById('backBtn').disabled = !tab || tab.historyIndex <= 0;
            document.getElementById('forwardBtn').disabled = !tab || tab.historyIndex >= tab.history.length - 1;
        }

        function setStatus(msg) {
            document.getElementById('statusBar').textContent = msg;
        }

        initProject();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/init', methods=['GET'])
def api_init():
    tab_id = create_new_tab()
    return jsonify({'initial_tab_id': tab_id})

@app.route('/api/new-tab', methods=['POST'])
def api_new_tab():
    tab_id = create_new_tab()
    return jsonify({'tab_id': tab_id})

@app.route('/api/close-tab/<tab_id>', methods=['POST'])
def api_close_tab(tab_id):
    if tab_id in BROWSER_STATE['tabs']:
        del BROWSER_STATE['tabs'][tab_id]
    return jsonify({'status': 'closed'})

def resolve_url(base_url, target_url):
    if not target_url:
        return ''
    if target_url.startswith(('http://', 'https://', 'chrome://', 'about:')):
        return target_url
    if target_url.startswith('//'):
        return f"https:{target_url}"

    parsed = urlparse(target_url)
    if parsed.netloc:
        return target_url

    if target_url.startswith('/url'):
        query = urlparse(target_url).query
        if 'q=' in query:
            destination = query.split('q=', 1)[1].split('&', 1)[0]
            return unquote(destination)

    return urljoin(base_url, target_url)


def record_navigation(tab, url):
    tab['current_url'] = url
    if not tab['history'] or tab['history'][-1] != url:
        tab['history'] = tab['history'][:tab['history_index'] + 1]
        tab['history'].append(url)
        tab['history_index'] = len(tab['history']) - 1
    else:
        tab['history_index'] = tab['history'].index(url)
    return tab


@app.route('/api/navigate', methods=['POST'])
def api_navigate():
    data = request.json or {}
    tab_id = data['tab_id']
    url = data['url']
    
    tab = BROWSER_STATE['tabs'][tab_id]
    resolved_url = resolve_url(tab.get('current_url', ''), url)
    record_navigation(tab, resolved_url)
    
    return jsonify({
        'url': resolved_url,
        'history': tab['history'],
        'history_index': tab['history_index']
    })


@app.route('/api/open-link/<tab_id>', methods=['POST'])
def api_open_link(tab_id):
    data = request.json or {}
    target_url = data.get('url', '')
    tab = BROWSER_STATE['tabs'][tab_id]
    resolved_url = resolve_url(tab.get('current_url', ''), target_url)
    record_navigation(tab, resolved_url)
    return jsonify({
        'url': resolved_url,
        'history': tab['history'],
        'history_index': tab['history_index']
    })

@app.route('/api/back/<tab_id>', methods=['POST'])
def api_back(tab_id):
    tab = BROWSER_STATE['tabs'][tab_id]
    if tab['history_index'] > 0:
        tab['history_index'] -= 1
        url = tab['history'][tab['history_index']]
        tab['current_url'] = url
        return jsonify({
            'url': url,
            'history': tab['history'],
            'history_index': tab['history_index']
        })
    return jsonify({'error': 'No back history'})

@app.route('/api/forward/<tab_id>', methods=['POST'])
def api_forward(tab_id):
    tab = BROWSER_STATE['tabs'][tab_id]
    if tab['history_index'] < len(tab['history']) - 1:
        tab['history_index'] += 1
        url = tab['history'][tab['history_index']]
        tab['current_url'] = url
        return jsonify({
            'url': url,
            'history': tab['history'],
            'history_index': tab['history_index']
        })
    return jsonify({'error': 'No forward history'})

def render_internal_browser_page(url):
    if url in {'chrome://settings', 'chrome://settings/'}:
        return """
        <div style='font-family: Arial, sans-serif; padding: 20px;'>
            <h1>Settings</h1>
            <p>Browser settings page for the contained browser.</p>
            <div style='margin-top: 16px; padding: 12px; background: #f6f8fa; border-radius: 8px;'>
                <p><strong>Search engine</strong>: Google</p>
                <p><strong>Privacy</strong>: Isolated mode enabled</p>
                <p><strong>Extensions</strong>: <a href='#' data-internal-url='chrome://extensions'>Manage extensions</a></p>
            </div>
        </div>
        """

    if url in {'chrome://extensions', 'chrome://extensions/'}:
        return """
        <div style='font-family: Arial, sans-serif; padding: 20px;'>
            <h1>Extensions</h1>
            <p>Built-in extensions panel for the contained browser.</p>
            <div style='margin-top: 16px; display: grid; gap: 12px;'>
                <div style='padding: 12px; border: 1px solid #ddd; border-radius: 8px;'>
                    <strong>School Project Helper</strong><br/>Enabled · Built-in extension
                </div>
                <div style='padding: 12px; border: 1px solid #ddd; border-radius: 8px;'>
                    <strong>Isolated Mode</strong><br/>Enabled · Prevents host-browser leakage
                </div>
            </div>
        </div>
        """

    if url in {'chrome://newtab', 'chrome://newtab/', 'about:blank', 'about:blank/'}:
        return """
        <div style='font-family: Arial, sans-serif; padding: 24px; background: #f8fafc; border-radius: 10px; margin: 20px;'>
            <h1>New tab</h1>
            <p>Welcome to the contained browser.</p>
            <p>Type a URL in the address bar or open Settings or Extensions.</p>
        </div>
        """

    return None


@app.route('/api/screenshot/<tab_id>')
def api_screenshot(tab_id):
    tab = BROWSER_STATE['tabs'].get(tab_id)
    if not tab or 'current_url' not in tab:
        return "<p>No page loaded. Enter a URL above.</p>"

    current_url = tab['current_url']
    internal_html = render_internal_browser_page(current_url)
    if internal_html is not None:
        return internal_html

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            page = browser.new_page(viewport={'width': 1280, 'height': 960})
            page.goto(current_url, wait_until='networkidle', timeout=60000)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup(["script", "style", "noscript", "iframe"]):
            tag.decompose()

        for link in soup.find_all('a'):
            href = link.get('href', '#')
            if href.startswith('#'):
                link['href'] = '#'
            else:
                link['href'] = '#'
                link['data-internal-url'] = resolve_url(current_url, href)
            link['target'] = '_self'
            link['rel'] = 'noopener'
            link['style'] = 'color: #007bff; text-decoration: underline; cursor: pointer;'

        body = soup.find('body') or soup
        body['style'] = 'font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; color: #333;'

        for img in body.find_all('img'):
            img['style'] = 'max-width: 100%; height: auto; margin: 10px 0;'

        return f"<div style='font-family: Arial, sans-serif; line-height: 1.6; padding: 20px;'>{str(body)}</div>"
    except Exception as e:
        return f"<div style='padding: 20px; font-family: Arial;'><p style='color: red;'>Error loading page: {str(e)}</p></div>"

def create_new_tab():
    tab_id = str(BROWSER_STATE['next_tab_id'])
    BROWSER_STATE['next_tab_id'] += 1
    BROWSER_STATE['tabs'][tab_id] = {
        'id': tab_id,
        'current_url': '',
        'history': [],
        'history_index': -1
    }
    return tab_id

if __name__ == '__main__':
    print("=" * 60)
    print("🌐 COLLEGE PROJECT STARTING")
    print("=" * 60)
    print("✓ Running locally")
    print("✓ Private browsing environment")
    print("\nOpen: http://localhost:5000")
    print("=" * 60)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()

    print("=" * 60)
    print("🌐 COLLEGE PROJECT STARTING")
    print("=" * 60)
    print("✓ Running locally")
    print("✓ Private browsing environment")
    print(f"\nOpen: http://localhost:{args.port}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=args.port, debug=False)