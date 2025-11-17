# Fix: NFT Import Error in Webmail Container

## Problem

The webmail Docker container was failing to start with the following error:

```
ImportError: cannot import name 'nft_service' from 'nft_verification_service' (/app/nft_verification_service.py)
```

## Root Cause

The Docker container was built with stale code that contained an incorrect import statement in `app.py`:

```python
from nft_verification_service import nft_service
```

However:
1. The module `nft_verification_service` exports `nft_verification_service`, not `nft_service`
2. This import has been removed from the current source code
3. The webmail application no longer needs this dependency

## Solution

The Docker container needs to be rebuilt to pick up the latest source code without the problematic import.

### Quick Fix (Recommended)

Run the deployment script's fix command:

```bash
./deploy.sh fix
```

This automatically:
- Rebuilds the webmail container with latest code
- Checks for other common issues
- Verifies the container starts successfully
- Shows clear error messages if something fails

### Manual Fix

If you prefer to rebuild manually:

```bash
# Stop and remove the webmail container
docker compose stop webmail
docker compose rm -f webmail

# Rebuild the container with fresh code
docker compose build --no-cache webmail

# Start the container
docker compose up -d webmail

# Check logs to verify it's working
docker compose logs -f webmail
```

## Verification

After rebuilding, the webmail container should start successfully without import errors. You can verify by:

1. Checking container status: `docker compose ps webmail`
2. Viewing logs: `docker compose logs webmail`
3. Accessing the webmail interface in your browser

## Prevention

To avoid this issue in the future:
- Always rebuild Docker containers after pulling code changes
- Use `docker compose build` before `docker compose up` when updating services
- Consider using volume mounts for development to avoid rebuild cycles
