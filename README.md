### OpenConnect + Okta MFA

Use Palo Alto GlobalProtect VPN with Okta MFA without an official client. 

Please make sure you have the latest version of the openconnect installed. It should support the "--protocol=gp" option.


Usage:
```
pip install git+https://github.com/lvoloshyn/openconnect_with_okta.git
sudo openconnect-okta --gateway GATEWAY --username USERNAME
```
