# Policy-as-code (OPA)
This folder contains sample OPA Rego policies for Jarvis.

To enable OPA evaluation:
- Run OPA server (Docker or sidecar)
- Load policies in OPA (bundle or volume mount)
- Set env var: OPA_URL=http://opa:8181
