def test_web_app_is_served(client):
    r = client.get("/app/")
    assert r.status_code == 200
    assert "LabTrack" in r.text
    assert 'src="app.js"' in r.text


def test_web_assets_are_served(client):
    assert client.get("/app/app.js").status_code == 200
    assert client.get("/app/style.css").status_code == 200


def test_browser_root_redirects_to_web_app(client):
    r = client.get("/", headers={"accept": "text/html,application/xhtml+xml"}, follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "/app/"


def test_api_root_still_returns_json(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["app"] == "/app/"
    assert body["docs"] == "/docs"
