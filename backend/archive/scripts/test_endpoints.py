import requests


def test_api():
    base_url = "http://localhost:8001"
    endpoints = [
        "/api/cms/announcements",
        "/api/admin/announcements",
        "/api/cms/testimonials",
        "/api/admin/testimonials",
        "/api/content/faro_home_hero",
        "/api/agents/analytics/summary",
    ]

    print(f"Testing API at {base_url}")
    for ep in endpoints:
        try:
            # We use GET for testing existence (some might 405 if only POST, but shouldn't 404 if it exists)
            resp = requests.get(base_url + ep)
            print(f"GET {ep:25} -> {resp.status_code}")
        except Exception as e:
            print(f"Error testing {ep}: {e}")


if __name__ == "__main__":
    test_api()
