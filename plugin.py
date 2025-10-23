"""
<plugin key="SmartThingsWasher" name="Samsung SmartThings Washer" author="csuti" version="3.8" wikilink="https://github.com/csutihu/Smartthings_washer">
    <description>
        <p>Retrieves and displays the status (ON/Off, Cycle, Remaining Time) of a Samsung washing machine via the SmartThings API.</p>
        <p>This plugin uses **SmartThings OAuth 2.0** for authentication.</p>
        <p>This version exclusively uses the /status endpoint and extracts three values precisely from the SmartThings API response:</p>
        <ul>
            <li><b>Power (ON/OFF):</b> components.main.switch.switch.value</li>
            <li><b>Washing Cycle:</b> components.main.samsungce.washerOperatingState.washerJobState.value</li>
            <li><b>Remaining Time (minutes):</b> components.main.samsungce.washerOperatingState.remainingTime.value</li>
        </ul>
        <p><b>Getting your tokens:</b> This plugin requires a **Client ID**, **Client Secret**, **Access Token**, and **Refresh Token** from the SmartThings API. For detailed help on generating these OAuth 2.0 credentials, please refer to this guide (Credit: Shashank Mayya): <a href="https://levelup.gitconnected.com/smartthings-api-taming-the-oauth-2-0-beast-5d735ecc6b24">SmartThings API: Taming the OAuth 2.0 Beast</a></p>
        <p><b>Important: For operation, the 'st_tokens.json' file must be manually created in the plugin folder with the following content (example):</b></p>
        <pre>
{
    "access_token": "INSERT-YOUR-FIRST-ACCESS-TOKEN-HERE",
    "refresh_token": "INSERT-YOUR-FIRST-REFRESH-TOKEN-HERE",
    "expiry": 0
}
       </pre>
    </description>
    <params>
        <param field="Address" label="SmartThings API URL" width="300px" required="true" default="https://api.smartthings.com"/>
        <param field="Port" label="Debug (0 = off, 1 = on)" width="40px" required="true" default="0"/>
        <param field="Mode1" label="ON State Polling Interval (sec)" width="40px" required="true" default="60"/>
        <param field="Mode5" label="OFF State Polling Interval (sec)" width="40px" required="true" default="600"/>
        <param field="Mode2" label="SmartThings Client ID" width="300px" required="true"/>
        <param field="Mode3" label="SmartThings Client Secret" width="300px" required="true" password="true"/>
        <param field="Mode4" label="Washer Device ID (SmartThings)" width="300px" required="true"/>
    </params>
</plugin>
"""

import Domoticz
import json
import urllib.request
import urllib.error
import os

# TokenManager import
try:
    from token_manager import TokenManager
except Exception as e:
    Domoticz.Error("TokenManager import error: " + str(e))
    raise

WM_STATUS_ID = "WM_Power"
WM_JOBSTATE_ID = "WM_JobState"
WM_REMAINING_ID = "WM_Remaining"


class SmartThingsWMPlugin:
    def __init__(self):
        self.base_url = None
        self.device_id = None
        self.client_id = None
        self.client_secret = None
        self.token_manager = None
        self.poll_on_sec = 60
        self.poll_off_sec = 600
        self.heartbeat_seconds = 60
        self.counter_seconds = 0
        self.debug = False

    # ---------- LOG HELPERS ----------
    def _log_debug(self, msg):
        if self.debug:
            Domoticz.Debug(msg)

    def _log_info(self, msg):
        Domoticz.Log(msg)

    def _log_error(self, msg):
        Domoticz.Error(msg)

    def _get_device_idx(self, device_id):
        for idx in Devices:
            try:
                if Devices[idx].DeviceID == device_id:
                    return idx
            except Exception:
                pass
        return -1

    # ---------- Domoticz API ----------
    def onStart(self):
        self.base_url = Parameters["Address"].strip().rstrip("/")
        self.client_id = Parameters["Mode2"].strip()
        self.client_secret = Parameters["Mode3"].strip()
        self.device_id = Parameters["Mode4"].strip()

        try:
            self.poll_on_sec = max(60, int(Parameters["Mode1"]))
        except:
            self.poll_on_sec = 60

        try:
            self.poll_off_sec = max(60, int(Parameters["Mode5"]))
        except:
            self.poll_off_sec = 600

        self.debug = (Parameters["Port"] != "0")
        if self.debug:
            Domoticz.Debugging(1)
            Domoticz.Log("Debug mode enabled.")
        else:
            Domoticz.Debugging(0)

        Domoticz.Log("Starting SmartThings Washer Plugin...")
        Domoticz.Log(f"Base URL: {self.base_url}, Device ID: {self.device_id}")
        Domoticz.Log(f"Poll ON: {self.poll_on_sec}s, Poll OFF: {self.poll_off_sec}s, Heartbeat: {self.heartbeat_seconds}s")

        plugin_dir = os.path.dirname(os.path.realpath(__file__))
        self.token_manager = TokenManager(self.client_id, self.client_secret, plugin_dir, self.base_url, debug=self.debug)

        if not self.token_manager.load_tokens():
            Domoticz.Error("st_tokens.json is missing or invalid.")
            return
        else:
            Domoticz.Log("Tokens loaded (if present).")

        # Create Devices if missing
        if self._get_device_idx(WM_STATUS_ID) < 0:
            Domoticz.Device(Unit=1, Name="Washer Status (ON/OFF)", Type=244, Subtype=73, Switchtype=0, DeviceID=WM_STATUS_ID).Create()
        if self._get_device_idx(WM_JOBSTATE_ID) < 0:
            Domoticz.Device(Unit=2, Name="Washing Cycle", TypeName="Text", DeviceID=WM_JOBSTATE_ID).Create()
        if self._get_device_idx(WM_REMAINING_ID) < 0:
            Domoticz.Device(Unit=3, Name="Remaining Time (min)", TypeName="Text", DeviceID=WM_REMAINING_ID).Create()

        Domoticz.Heartbeat(self.heartbeat_seconds)
        Domoticz.Log(f"Heartbeat set to {self.heartbeat_seconds} seconds.")

    def onStop(self):
        Domoticz.Log("SmartThings Washer Plugin stopped.")

    def onHeartbeat(self):
        self.counter_seconds += self.heartbeat_seconds
        idx_status = self._get_device_idx(WM_STATUS_ID)
        is_on = False
        if idx_status >= 0:
            try:
                is_on = (Devices[idx_status].nValue == 1)
            except:
                is_on = False

        target = self.poll_on_sec if is_on else self.poll_off_sec
        if self.counter_seconds < target:
            return

        self.counter_seconds = 0
        Domoticz.Log(f"Starting SmartThings query (is_on={is_on})...")
        self._query_and_process()

   # ---------- API Request and Processing ----------
    def _query_and_process(self):
        token = self.token_manager.get_access_token()
        if not token:
            if not self.token_manager.refresh_access_token():
                Domoticz.Error("Token refresh failed.")
                return
            token = self.token_manager.get_access_token()

        url = f"{self.base_url}/v1/devices/{self.device_id}/status"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                code = resp.getcode()
                body = resp.read().decode("utf-8")

            truncated = body if len(body) < 4000 else (body[:4000] + "...(truncated)")
            Domoticz.Debug(f"[API RAW] GET {url} -> HTTP {code}. Payload (truncated): {truncated}")

            if code == 200:
                parsed = json.loads(body)
                self._update_devices_from_api_data(parsed)
            elif code == 401:
                Domoticz.Error("401 Unauthorized – token refresh required.")
                self.token_manager.refresh_access_token()
            else:
                Domoticz.Error(f"[Plugin] HTTP {code} error.")

        except Exception as e:
            Domoticz.Error(f"[Plugin] API call error: {e}")

    def _update_devices_from_api_data(self, data):
        """Direct extraction of three values: Power, Job, Remaining."""
        try:
            comp = data.get("components", {}).get("main", {})

            power_value = (
                comp.get("switch", {}).get("switch", {}).get("value")
            )

            job_value = (
                comp.get("samsungce.washerOperatingState", {})
                .get("washerJobState", {})
                .get("value")
            )

            remaining = (
                comp.get("samsungce.washerOperatingState", {})
                .get("remainingTime", {})
                .get("value")
            )

            Domoticz.Log(f"[STATE] Power={repr(power_value)}, Job={repr(job_value)}, Remaining={repr(remaining)}")

            # --- Power ---
            idx_power = self._get_device_idx(WM_STATUS_ID)
            is_on = str(power_value).lower() == "on"
            if idx_power >= 0:
                nValue = 1 if is_on else 0
                sValue = "On" if is_on else "Off"
                if Devices[idx_power].nValue != nValue:
                    Devices[idx_power].Update(nValue=nValue, sValue=sValue)
                    Domoticz.Log(f"[Update] Washer status: {sValue}")

            # --- Job state ---
            idx_job = self._get_device_idx(WM_JOBSTATE_ID)
            if job_value is None:
                job_text = "Unknown"
            elif job_value == "none":
                job_text = "No active wash"
            else:
                job_text = str(job_value)
            if idx_job >= 0 and Devices[idx_job].sValue != job_text:
                Devices[idx_job].Update(nValue=0, sValue=job_text)
                Domoticz.Log(f"[Update] Washing cycle: {job_text}")

            # --- Remaining time ---
            idx_rem = self._get_device_idx(WM_REMAINING_ID)
            if remaining is None:
                remaining_text = "Unknown"
                remaining_n = 0
            else:
                try:
                    remaining_n = int(float(remaining))
                    remaining_text = f"{remaining_n} min"
                except (ValueError, TypeError):
                    remaining_n = 0
                    remaining_text = str(remaining)
            if idx_rem >= 0 and Devices[idx_rem].sValue != remaining_text:
                Devices[idx_rem].Update(nValue=remaining_n, sValue=remaining_text)
                Domoticz.Log(f"[Update] Remaining time: {remaining_text}")

        except Exception as e:
            Domoticz.Error(f"[Plugin] Processing error: {e}")


_plugin = SmartThingsWMPlugin()

def onStart(): _plugin.onStart()
def onStop(): _plugin.onStop()
def onHeartbeat(): _plugin.onHeartbeat()
def onCommand(Unit, Command, Level, Hue): _plugin.onCommand(Unit, Command, Level, Hue) if hasattr(_plugin, "onCommand") else None
