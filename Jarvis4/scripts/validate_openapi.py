import sys
from openapi_spec_validator import validate_spec
import yaml

def main():
    with open("openapi.yaml", "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    validate_spec(spec)
    print("OpenAPI spec is valid.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"OpenAPI validation failed: {e}", file=sys.stderr)
        sys.exit(1)
