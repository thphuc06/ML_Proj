"""Minimal Label Studio REST client: admin session login (cookie + CSRF), credentials from infra/.env.server."""
import re

import requests

from common import ROOT

ENV = dict(l.strip().split("=", 1) for l in (ROOT / "infra" / ".env.server").read_text().splitlines() if "=" in l)
BASE = f"https://{ENV['DOMAIN']}"
FILES_ROOT = "/label-studio/files"  # container path of /srv/sidewalk/data/crops is FILES_ROOT/crops


def session():
    s = requests.Session()
    tok = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)', s.get(BASE + "/user/login/").text).group(1)
    r = s.post(BASE + "/user/login/", headers={"Referer": BASE + "/user/login/"},
               data={"csrfmiddlewaretoken": tok, "email": ENV["ADMIN_EMAIL"], "password": ENV["ADMIN_PASSWORD"]})
    if r.url.rstrip("/") != BASE:
        raise SystemExit("admin login failed - update ADMIN_PASSWORD in infra/.env.server")
    s.headers.update({"X-CSRFToken": s.cookies["csrftoken"], "Referer": BASE + "/"})
    return s


def projects(s):
    out, url = [], BASE + "/api/projects?page_size=100"
    while url:
        j = s.get(url).json()
        out += j["results"]
        url = j.get("next")
    return {p["title"]: p for p in out}
