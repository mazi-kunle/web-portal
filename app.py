import requests
from flask import Flask, render_template, redirect, url_for, request, make_response, jsonify
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def get_tokens():
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    if not access_token:
        return None, None

    return access_token, refresh_token


def get_auth_headers():
    """
    Builds auth headers from cookies.
    """
    access_token, _ = get_tokens()
    return {
        "Authorization": f"Bearer {access_token}",
        "X-API-Version": "1"
    }


def refresh_tokens(refresh_token):
    """
    Calls backend to refresh tokens.
    Returns new token pair or None if failed.
    """
    response = requests.post(
        f"{BACKEND_URL}/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    if response.status_code == 200:
        data = response.json()
        return data["access_token"], data["refresh_token"]

    return None, None


def make_api_request(method, endpoint, **kwargs):
    """
    Makes a request to the backend API.
    Handles token refresh automatically.
    """
    access_token, refresh_token = get_tokens()

    if not access_token:
        return None, "not_authenticated", None, None

    headers = get_auth_headers()
    response = requests.request(
        method,
        f"{BACKEND_URL}{endpoint}",
        headers=headers,
        **kwargs
    )

    # Access Token expired — try to refresh
    if response.status_code == 401:
        new_access, new_refresh = refresh_tokens(refresh_token)

        if not new_access:
            return None, "session_expired", None, None

        # Retry with new token
        headers["Authorization"] = f"Bearer {new_access}"
        response = requests.request(
            method,
            f"{BACKEND_URL}{endpoint}",
            headers=headers,
            **kwargs
        )

        # Return response with flag to update cookies
        return response, "tokens_refreshed", new_access, new_refresh

    return response, None, None, None

def build_proxy_response(result, content_type=None, extra_headers=None):
    """
    Builds a proxy response and handles:
    - Session expired → delete cookies, return 401
    - Tokens refreshed → update cookies with new tokens
    - Normal response → return as is
    """
    response, error, new_access, new_refresh = result

    # Session expired or not authenticated → delete cookies
    if error in ["not_authenticated", "session_expired"]:
        resp = make_response(
            jsonify({"status": "error", "message": "Session expired"}), 401
        )
        resp.delete_cookie("access_token")
        resp.delete_cookie("refresh_token")
        return resp

    # Build response body
    if content_type:
        resp = make_response(response.content)
        resp.headers["Content-Type"] = content_type
        if extra_headers:
            for key, value in extra_headers.items():
                resp.headers[key] = value
    else:
        resp = make_response(jsonify(response.json()), response.status_code)

    # Tokens refreshed → update cookies
    if error == "tokens_refreshed":
        resp.set_cookie(
            "access_token",
            new_access,
            max_age=5*60,
            httponly=True,
            samesite="Lax",
        )
        resp.set_cookie(
            "refresh_token",
            new_refresh,
            max_age=5*60,
            httponly=True,
            samesite="Lax",
        )

    return resp

# ─── AUTH ROUTES ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Redirect to dashboard if logged in, else login page."""
    access_token, _ = get_tokens()
    if access_token:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login")
def login():
    """Login page."""
    access_token, _ = get_tokens()

    if access_token:
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/auth/github")
def github_login():
    """Redirect to backend GitHub OAuth."""
    return redirect(f"{BACKEND_URL}/auth/github")


@app.route("/auth/callback")
def github_callback():
    access_token = request.args.get("access_token")
    refresh_token = request.args.get("refresh_token")

    if not access_token:
        return redirect(url_for("login"))

    resp = make_response(redirect(url_for("dashboard")))
    resp.set_cookie("access_token", access_token, max_age=5*60, httponly=True, samesite="Lax")
    resp.set_cookie("refresh_token", refresh_token, max_age=5*60, httponly=True, samesite="Lax")

    return resp


@app.route("/auth/logout")
def logout():
    """Logout and clear cookies."""
    _, refresh_token = get_tokens()

    if refresh_token:
        requests.post(
            f"{BACKEND_URL}/auth/logout",
            json={"refresh_token": refresh_token}
        )

    resp = make_response(redirect(url_for("login")))
    resp.delete_cookie("access_token")
    resp.delete_cookie("refresh_token")

    return resp


# ─── PAGE ROUTES ──────────────────────────────────────────────────────────────

@app.route("/dashboard")
def dashboard():
    access_token, _ = get_tokens()
    if not access_token:
        return redirect(url_for("login"))

    return render_template("dashboard.html")


@app.route("/profiles")
def profiles():
    access_token, _ = get_tokens()
    if not access_token:
        return redirect(url_for("login"))

    return render_template("profiles.html")


@app.route("/profiles/<id>")
def profile_detail(id):
    access_token, _ = get_tokens()
    if not access_token:
        return redirect(url_for("login"))

    return render_template("profile_detail.html", profile_id=id)


@app.route("/search")
def search():
    access_token, _ = get_tokens()
    if not access_token:
        return redirect(url_for("login"))

    return render_template("search.html")


@app.route("/account")
def account():
    access_token, _ = get_tokens()
    if not access_token:
        return redirect(url_for("login"))

    return render_template("account.html")


# ─── API PROXY ROUTES ─────────────────────────────────────────────────────────

@app.route("/api/profiles")
def api_profiles():
    result = make_api_request("GET", "/api/profiles", params=request.args)
    return build_proxy_response(result)


@app.route("/api/profiles/search")
def api_search():
    result = make_api_request("GET", "/api/profiles/search", params=request.args)
    return build_proxy_response(result)


@app.route("/api/profiles/<id>")
def api_profile_detail(id):
    result = make_api_request("GET", f"/api/profiles/{id}")
    return build_proxy_response(result)


@app.route("/api/profiles/export")
def api_export():
    result = make_api_request("GET", "/api/profiles/export", params=request.args)
    response = result[0]

    if response is None:
        return build_proxy_response(result)

    return build_proxy_response(
        result,
        content_type="text/csv",
        extra_headers={
            "Content-Disposition": response.headers.get(
                "Content-Disposition",
                "attachment; filename=profiles.csv"
            )
        }
    )

@app.route("/api/whoami")
def api_whoami():
    result = make_api_request("GET", "/api/whoami")
    return build_proxy_response(result)



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000)