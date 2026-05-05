# Insighta Labs — Web Portal

A browser-based interface for the Insighta Labs+ platform. Built for non-technical users, it provides a clean and simple way to browse, search, and export profile intelligence data without needing to use the CLI or API directly.

---

## Prerequisites

Python 3.8 or higher and the Insighta Labs backend running and accessible.

---

## Installation

```bash
git clone https://github.com/mazi-kunle/web-portal
cd web-portal
pip install -r requirements.txt
```

---


The following variables are required:

```bash
SECRET_KEY=your_secret_key_here
BACKEND_URL=http://localhost:5000
```

---

## Running

```bash
python3 app.py
```

The web portal runs on `http://localhost:3000`.

---

## Architecture

The web portal is a thin Flask server that sits between the browser and the backend. It serves HTML pages, manages HTTP-only cookies for authentication, and proxies API requests to the backend on behalf of the browser. The browser never talks to the backend directly — all requests go through the web portal server which adds the authentication headers before forwarding them.

This architecture keeps tokens secure in HTTP-only cookies that JavaScript cannot read, protecting against XSS attacks.

---

## Authentication Flow

The web portal uses GitHub OAuth handled entirely by the backend. When the user clicks "Login with GitHub" the browser is redirected through the following steps.

The web portal redirects to the backend `/auth/github` endpoint. The backend generates a state value, stores it in its session, and redirects the browser to GitHub's OAuth page. After the user approves access, GitHub redirects back to the backend `/auth/github/callback`. The backend validates the state, exchanges the code with GitHub, creates or updates the user in the database, generates access and refresh tokens, and redirects the browser to the web portal `/auth/callback` with the tokens in the URL. The web portal reads the tokens from the URL, sets them as HTTP-only cookies, and redirects the user to the dashboard.

All subsequent requests include these cookies automatically. The web portal reads the cookies, adds the access token as a Bearer token in the Authorization header, and forwards the request to the backend.

---

## Token Handling

The web portal stores tokens in HTTP-only cookies which cannot be read by JavaScript. This protects against XSS attacks where malicious scripts try to steal tokens.

Cookies are set with a `max_age` of 5 minutes matching the refresh token expiry. When the cookies expire the browser deletes them automatically and the user is redirected to the login page on their next request.

When the access token expires after 3 minutes the web portal proxy routes automatically detect the 401 response, call the backend refresh endpoint with the stored refresh token, update the cookies with the new tokens, and retry the original request. The user never sees an interruption.

If the refresh token has also expired the proxy routes delete the cookies and return a 401 response. The browser redirects the user to the login page.

---

## Pages

### Login

The entry point for all users. Shows a "Continue with GitHub" button that starts the OAuth flow. Users who are already logged in are automatically redirected to the dashboard.

### Dashboard

Shows an overview of the platform data including total profiles, male profiles, female profiles, and total countries. Also shows a table of the most recently created profiles. Clicking any row navigates to the profile detail page.

### Profiles

Shows a paginated table of all profiles with filters for gender, country, age group, minimum age, maximum age, and sorting. Filters can be applied and reset. Profiles can be exported as a CSV file with the current filters applied. Clicking any row navigates to the profile detail page.

### Profile Detail

Shows all available information about a single profile including name, gender, gender probability, age, age group, country, country probability, and creation date.

### Search

Accepts natural language queries and returns matching profiles in a paginated table. Supports queries like "young males from nigeria" or "adults over 30 from the US". Results support pagination.

### Account

Shows the currently logged in user's information including username, email, role, member since date, last login time, and active status. Also shows the user's permissions based on their role. Provides a logout button.

---

## Role Based Access

The web portal reflects the same role restrictions enforced by the backend. Admin users can create and delete profiles in addition to reading and searching. Analyst users can only read and search. The account page shows the user's current permissions based on their role.

---


## Deployment

The web portal is deployed on Railway. Set all environment variables in the Railway dashboard under the Variables tab. Update `BACKEND_URL` to point to your deployed backend URL.

Live URL: `https://web-portal-production-4f4e.up.railway.app`
