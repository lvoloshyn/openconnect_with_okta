import argparse
import getpass
import base64
import json
import os
import urllib.parse
from typing import Optional, Tuple, Dict

import lxml.etree
import requests



class OktaGPConnect:
    def __init__(self, gateway: str, username: str, password: str):
        self._gateway = gateway
        self._username = username
        self._password = password

        self.session = requests.Session()
        self.json_headers = {"Accept": "application/json", "Content-Type": "application/json"}

        self.saml_url = self.get_saml_url()
        self.okta_domain = urllib.parse.urlparse(self.saml_url).netloc
        self.okta_url = f"https://{self.okta_domain}"

    def get_saml_url(self) -> str:
        """
        Return link to page with SAML form
        """
        url = f"https://{self._gateway}/ssl-vpn/prelogin.esp"
        response = self.session.post(url)

        doc = lxml.etree.fromstring(response.content)
        saml_url = base64.b64decode(doc.find("saml-request").text)

        return saml_url.decode("ascii")

    def okta_authorize(self) -> Optional[str]:
        """
        Authorize with username and password to get MFA options
        """

        data = {
            "username": self._username,
            "password": self._password,
        }

        response = self.session.post(
            url=f"https://{self.okta_domain}/api/v1/authn",
            data=json.dumps(data),
            headers=self.json_headers
        )

        response_data = response.json()

        factors = response_data.get("_embedded", {}).get("factors", [])
        state_token = response_data.get("stateToken")

        supported_factors = ("question", "sms")

        # SMS verification only
        for factor in factors:
            # @TODO add others
            if factor.get("factorType") not in supported_factors:
                continue

            data = {
                "factorId": factor.get("id"),
                "stateToken": state_token
            }
            factor_url = factor.get("_links", {}).get("verify", {}).get("href", "")

            if factor.get("factorType") == "sms":
                response = self.session.post(factor_url, json=data, headers=self.json_headers)

                sms_code = input("Enter SMS code: ")

                data["passCode"] = sms_code
                response = self.session.post(factor_url, json=data, headers=self.json_headers)

                session_token = response.json().get("sessionToken")
                return session_token

            elif factor.get("factorType") == "question":
                answer = getpass.getpass(factor.get("profile", {}).get("questionText", "") + " ")
                data["answer"] = answer

                response = self.session.post(factor_url, json=data, headers=self.json_headers)

                session_token = response.json().get("sessionToken")
                return session_token

        return None

    def auth(self) -> Tuple[str, str]:
        # Get DT cookie
        self.session.get(self.saml_url)

        # Get session token
        session_token = self.okta_authorize()

        url = f"{self.okta_url}/login/sessionCookieRedirect"
        data = {
            "token": session_token,
            "redirectUrl": self.saml_url
        }

        response = self.session.get(url=url, params=data)
        next_url, next_data = self._extract_form(response.text)

        response = self.session.post(url=next_url, data=next_data)
        full_username, cookie = response.headers["saml-username"], response.headers["prelogin-cookie"]

        return full_username, cookie

    def _extract_form(self, html: str) -> Tuple[str, Dict[str, str]]:
        form = lxml.etree.fromstring(html, lxml.etree.HTMLParser()).find(".//form")
        return form.attrib["action"], {inp.attrib["name"]: inp.attrib["value"] for inp in form.findall("input")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prefix_chars="--")
    parser.add_argument('--gateway', help='VPN gateway', required=True)
    parser.add_argument('--username', help='VPN username', required=True)

    args = parser.parse_args()
    password = getpass.getpass(prompt="VPN Password:")

    conn = OktaGPConnect(args.gateway, args.username, password)
    user, cookie = conn.auth()

    hip_report_path = os.path.join(os.path.dirname(__file__), "hipreport.sh")
    cmd = f"""echo "{cookie}" | openconnect --passwd-on-stdin --protocol=gp --no-dtls --user="{user}" --usergroup=gateway:prelogin-cookie --csd-wrapper="{hip_report_path}" {args.gateway}"""
    os.system(cmd)
