# token_manager.py - SmartThings OAuth Token Manager
import os
import json
import time
import Domoticz
import urllib.request
import urllib.parse
import base64
from datetime import datetime

TOKEN_FILE_NAME = "st_tokens.json"

class TokenManager:
    def __init__(self, client_id, client_secret, plugin_dir, base_url, debug=False):
        self.client_id = client_id
        self.client_secret = client_secret
        self.plugin_dir = plugin_dir
        self.base_url = base_url.rstrip("/")
        self.token_file_path = os.path.join(self.plugin_dir, TOKEN_FILE_NAME)
        self.debug = debug

        # default token structure
        self.tokens = {
            "access_token": None,
            "refresh_token": None,
            "expiry": 0
        }

        if self.debug:
            Domoticz.Log(f"[TokenManager] initialized. token_file: {self.token_file_path}, base_url: {self.base_url}")

    def load_tokens(self):
        if not os.path.exists(self.token_file_path):
            Domoticz.Error(f"[TokenManager] Token file not found: {self.token_file_path}")
            return False
        try:
            with open(self.token_file_path, "r") as f:
                data = json.load(f)
            
            self.tokens["access_token"] = data.get("access_token")
            self.tokens["refresh_token"] = data.get("refresh_token")
            self.tokens["expiry"] = int(data.get("expiry", 0))

            if self.tokens["expiry"] > 0:
                 expiry_str = datetime.fromtimestamp(self.tokens["expiry"]).strftime('%Y-%m-%d %H:%M:%S')
                 Domoticz.Log(f"[TokenManager] Tokens loaded. Expiry: {expiry_str}")
            else:
                 Domoticz.Log("[TokenManager] Tokens loaded. Expiry: Not set (forced refresh).")
            return True
        except Exception as e:
            Domoticz.Error(f"[TokenManager] Error reading token file: {e}")
            return False

    def save_tokens(self):
        try:
            with open(self.token_file_path, "w") as f:
                json.dump(self.tokens, f, indent=4)
            Domoticz.Debug(f"[TokenManager] Tokens saved: {self.token_file_path}")
            return True
        except Exception as e:
            Domoticz.Error(f"[TokenManager] Error saving token file: {e}")
            return False

    def is_expired(self):
        """CHECK: Plugin 3.6 calls this method!"""
        
        # If no access token or refresh token, consider it expired.
        if not self.tokens.get("access_token") or not self.tokens.get("refresh_token"):
            Domoticz.Log("[TokenManager] Token considered expired: access_token or refresh_token is missing.")
            return True

        # If expiry is 0, refresh immediately.
        if self.tokens.get("expiry", 0) == 0:
            Domoticz.Log("[TokenManager] Token considered expired: 'expiry' time is 0.")
            return True

        # If less than 30 seconds left (early refresh), consider it expired.
        if self.tokens["expiry"] < (int(time.time()) + 30):
            Domoticz.Log("[TokenManager] Token considered expired: Less than 30 seconds remaining.")
            return True

        return False

    def get_access_token(self):
        if self.is_expired():
            self.refresh_access_token()
        return self.tokens.get("access_token")

    def get_token_header(self):
        access_token = self.get_access_token()
        if access_token:
            return {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
        return None

    def refresh_access_token(self):
        refresh_token = self.tokens.get("refresh_token")
        if not refresh_token:
            Domoticz.Error("[TokenManager] No refresh token available for refresh.")
            return False

        url = f"{self.base_url}/oauth/token"
        
        # According to SmartThings documentation, client_id:client_secret must be base64 encoded.
        client_auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {client_auth}"
        }
        
        post_data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }).encode("utf-8")

        Domoticz.Debug(f"[TokenManager] Starting token refresh: {url}")
        
        try:
            request = urllib.request.Request(
                url,
                data=post_data,
                headers=headers,
                method='POST'
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                response_body = response.read().decode('utf-8')
                token_data = json.loads(response_body)
                
            new_access = token_data.get("access_token")
            # New refresh token may also be received
            new_refresh = token_data.get("refresh_token", refresh_token) 
            expires_in = token_data.get("expires_in", 3600)

            if not new_access:
                Domoticz.Error("[TokenManager] Token refresh response does not contain access_token.")
                return False

            expiry_ts = int(time.time()) + int(expires_in)
            self.tokens["access_token"] = new_access
            self.tokens["refresh_token"] = new_refresh
            self.tokens["expiry"] = expiry_ts

            saved = self.save_tokens()
            if saved:
                expiry_str = datetime.fromtimestamp(expiry_ts).strftime('%Y-%m-%d %H:%M:%S')
                Domoticz.Log(f"[TokenManager] Token refresh successful. New expiry: {expiry_str}")
            else:
                Domoticz.Error("[TokenManager] Token refresh successful, but saving failed.")
            return True
        except urllib.error.HTTPError as e:
            # Handle this exception separately to print the error message (e.g., invalid_grant)
            error_details = ""
            try:
                # Attempt to read the server response (which is the reason for the error)
                error_details = e.read().decode('utf-8')
                Domoticz.Error(f"[TokenManager] HTTP error during token refresh: {e.code}. Server response: {error_details}") 
            except:
                Domoticz.Error(f"[TokenManager] HTTP error during token refresh: {e.code}. Failed to read error details.")
            return False
        except urllib.error.URLError as e:
            Domoticz.Error(f"[TokenManager] Network error during token refresh: {e.reason}")
            return False
        except Exception as e:
            Domoticz.Error(f"[TokenManager] General error during token refresh: {e}")
            return False
