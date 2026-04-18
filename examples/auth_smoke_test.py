import argparse
import logging
import sys
import os

# Configure logger to capture azure.identity sequence
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
az_logger = logging.getLogger("azure.identity")
az_logger.setLevel(logging.DEBUG)

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from orchestrator.auth import get_secret

def main():
    parser = argparse.ArgumentParser(description="D04 Credential Smoke Test")
    parser.add_argument("--vault-url", required=True, help="Azure Key Vault Endpoint URL")
    parser.add_argument("--secret-name", required=True, help="Target Secret Name")
    args = parser.parse_args()

    print(f"\n[D04 Smoke Test] Vault Target: {args.vault_url}")
    print(f"[D04 Smoke Test] Secret Name: {args.secret_name}")
    print("=" * 60)
    print("Initiating DefaultAzureCredential auth chain resolution...\n")
    
    try:
        secret_val, cred_type = get_secret(args.vault_url, args.secret_name)
        print("\n" + "=" * 60)
        print("✅ SUCCESS: Credential resolution resolved effectively.")
        print(f"Retrieved Secret: '{args.secret_name}' (Length: {len(secret_val) if secret_val else 0} chars)")
        print(f"Envelope Provider: {cred_type}")
        print("\nNOTE: Check the above azure.identity debug logs to pinpoint the exact local or remote ")
        print("provider that successfully returned the token (e.g. AzureCliCredential vs ManagedIdentityCredential).")
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ FAILED: Could not retrieve credential. Exception details:")
        print(str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
