import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("browser_app", Path(__file__).with_name("test.py"))
browser_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser_app)


class BrowserAppTests(unittest.TestCase):
    def setUp(self):
        self.client = browser_app.app.test_client()

    def test_homepage_uses_school_project_title(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('School Project', body)

    def test_screenshot_rewrites_links_for_internal_navigation(self):
        tab_id = browser_app.create_new_tab()
        browser_app.BROWSER_STATE['tabs'][tab_id]['current_url'] = 'https://example.com'

        response = self.client.get(f'/api/screenshot/{tab_id}')
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('data-internal-url', body)
        self.assertNotIn('<script', body.lower())

    def test_google_redirect_links_resolve_to_destination(self):
        resolved = browser_app.resolve_url('https://www.google.com', '/url?q=https://example.com')
        self.assertEqual(resolved, 'https://example.com')

    def test_internal_browser_pages_render(self):
        tab_id = browser_app.create_new_tab()
        browser_app.BROWSER_STATE['tabs'][tab_id]['current_url'] = 'chrome://settings'
        response = self.client.get(f'/api/screenshot/{tab_id}')
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('Settings', body)
        self.assertIn('Extensions', body)

    def test_screenshot_renders_browser_content_for_data_urls(self):
        tab_id = browser_app.create_new_tab()
        browser_app.BROWSER_STATE['tabs'][tab_id]['current_url'] = 'data:text/html,<html><body><h1>Hello from browser</h1></body></html>'
        response = self.client.get(f'/api/screenshot/{tab_id}')
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('Hello from browser', body)

    def test_launcher_uses_video_stable_chromium_flags(self):
        script = Path(__file__).with_name('scripts').joinpath('launch_remote_browser.sh').read_text(encoding='utf-8')
        self.assertIn('--disable-dev-shm-usage', script)
        self.assertIn('--enable-unsafe-swiftshader', script)
        self.assertIn('--autoplay-policy=no-user-gesture-required', script)


if __name__ == '__main__':
    unittest.main()
