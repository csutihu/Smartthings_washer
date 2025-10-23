# Samsung SmartThings Washer Domoticz Plugin

A Domoticz Python plugin to retrieve and display the status (Power On/Off, Washing Cycle, and Remaining Time) of a Samsung washing machine via the **SmartThings Cloud API**.

This plugin uses **SmartThings OAuth 2.0** for secure authentication.

---
## 💡 Key Features and Potential Use Cases

This plugin provides the core data points for comprehensive washer monitoring and automation:

* **Customizable:** The plugin architecture allows for easy expansion with additional washer parameters available through the SmartThings API.
* **Washing Cycle Monitoring:** Based on the `Washing Cycle` state, independent Domoticz scripts (e.g., using DzVents) can be used to trigger an acoustic signal (or notification) in the living area when the laundry cycle is complete.
* **Maintenance Alert:** By comparing the `Remaining Time` with the actual washing time, you can implement logic to signal the need for cleaning the filter/check-valve drain connector.

---
## 1. 🔑 SmartThings OAuth 2.0 Access

For the plugin to work, you require a **Client ID**, **Client Secret**, an initial **Access Token**, and a **Refresh Token** from the SmartThings API.

**GUIDE TO ACQUIRE ALL TOKENS:**

The best guide for generating the OAuth 2.0 credentials and acquiring the necessary tokens is provided in this article (Credit: Shashank Mayya):

➡️ **[SmartThings API: Taming the OAuth 2.0 Beast](https://levelup.gitconnected.com/smartthings-api-taming-the-oauth-2-0-beast-5d735ecc6b24)**

> 📌 **Note:** A PDF copy of this guide (e.g., named `SmartThings_OAuth_Guide.pdf`) is available in the GitHub repository alongside the source files, in case the original webpage becomes inaccessible. Windows CLI can be used successfully for the steps described.

---

## 2. 📋 Prerequisites Summary

After following the steps in the guide above, you must obtain the following 4 OAuth values, plus your washing machine's identifier:

| Requirement | Description | Used in Plugin As |
| :--- | :--- | :--- |
| **Client ID** | The identifier for your SmartThings Integration. | Domoticz `SmartThings Client ID` parameter. |
| **Client Secret** | The secret key for your SmartThings Integration. | Domoticz `SmartThings Client Secret` parameter. |
| **Access Token** (Initial) | The initial OAuth 2.0 authentication code. | `st_tokens.json` file. |
| **Refresh Token** | Used for automatically refreshing the Access Token. | `st_tokens.json` file. |
| **Washer Device ID** | The unique identifier for your washing machine in SmartThings. | Domoticz `Washer Device ID (SmartThings)` parameter. |

---

## 3. 💾 Installation

1.  **Copy Files:** Copy the following files into your Domoticz `plugins` folder (e.g., `/home/domoticz/plugins/SmartThingsWasher/`):
    * `plugin.py`
    * `token_manager.py`
2.  **Create `st_tokens.json`:** Create a new file in the plugin folder (`st_tokens.json`) and populate it with your initial tokens:
    ```json
    {
        "access_token": "YOUR-FIRST-ACCESS-TOKEN-HERE",
        "refresh_token": "YOUR-FIRST-REFRESH-TOKEN-HERE",
        "expiry": 0
    }
    ```
    *(Setting `expiry: 0` ensures an immediate token refresh upon startup).*
3.  **Restart Domoticz.**

---

## 4. ⚙️ Plugin Configuration

In the Domoticz interface (`Setup` -> `Hardware`), add a new device named **Samsung SmartThings Washer** and fill in the fields with your acquired credentials:

| Configuration Field | Code Parameter | Description |
| :--- | :--- | :--- |
| **SmartThings API URL** | Address | `https://api.smartthings.com` |
| **Debug (0 = off, 1 = on)** | Port | `0` (off) or `1` (on) |
| **ON State Polling Interval (sec)** | Mode1 | Polling frequency (in seconds) when the washer is ON. Recommended: `60`. |
| **OFF State Polling Interval (sec)** | Mode5 | Polling frequency (in seconds) when the washer is OFF. Recommended: `600`. |
| **SmartThings Client ID** | Mode2 | Your OAuth **Client ID**. |
| **SmartThings Client Secret** | Mode3 | Your OAuth **Client Secret**. |
| **Washer Device ID (SmartThings)** | Mode4 | The washer's unique **Device ID**. |

---

## 5. 📊 Operation and Created Devices

Upon starting the plugin, Domoticz automatically creates the following devices under the **Devices** tab:

| Device ID | Name | Type | Description |
| :--- | :--- | :--- | :--- |
| `WM_Power` | Washer Status (ON/OFF) | Switch | Shows the washer's power state (ON or OFF). |
| `WM_JobState` | Washing Cycle | Text | Shows the current washing cycle state (e.g., `running`, `pause`, `none`). |
| `WM_Remaining` | Remaining Time (min) | Text | The time remaining in the current cycle, in minutes. |

### Data Source

The plugin uses the following data points from the SmartThings API's `/v1/devices/{deviceId}/status` endpoint:

* **Power (ON/OFF):** `components.main.switch.switch.value`
* **Washing Cycle:** `components.main.samsungce.washerOperatingState.washerJobState.value`
* **Remaining Time (minutes):** `components.main.samsungce.washerOperatingState.remainingTime.value`

Developers wishing to extend the plugin's functionality can query the full status payload to discover additional parameters (like progress, water temperature, spin level, etc.). The full list of supported capabilities and their current values can be retrieved using a simple `curl` command:

```bash
curl -X GET "[https://api.smartthings.com/v1/devices/device-id/status](https://api.smartthings.com/v1/devices/device-id/status)" \
     -H "Authorization: Bearer access-token" \
     -H "Accept: application/json"
```
---

## 6. 🐛 Troubleshooting

* **Token Error (401 Unauthorized):** The plugin automatically manages Access Token expiration by using the Refresh Token. However, if the **Refresh Token itself expires or becomes invalid** (which happens after a long period of inactivity or a server-side change), Domoticz logs will show an **`401 Unauthorized`** or **`Token refresh failed`** error. **In this critical scenario, a new set of OAuth credentials is required.**
    1.  Follow the steps in the **SmartThings OAuth 2.0 Access** guide (Section 1) again to acquire a completely new set of tokens.
    2.  Manually update the `access_token` and `refresh_token` in the `st_tokens.json` file and set `expiry` to `0`.
* **Missing Data / Unknown State:** Check that the **Washer Device ID** is correct, and ensure your OAuth integration has the necessary `r:devices:*` scope permissions configured in the SmartThings Developer Workspace.
