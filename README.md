# CursorCS Playground

## Cloudflare DNS Bulk Deletion Utility

The repository now includes `cf_bulk_delete_dns.py`, a helper script for removing
multiple DNS records from a Cloudflare zone in one go. It supports filtering by
record name, substring, or type, and asks for confirmation before performing
changes.

### Requirements

- Python 3.8+
- A Cloudflare API token with permissions to read and edit DNS for the target zone

### Example usage

```bash
# Delete DNS records listed in names.txt (one name per line)
python cf_bulk_delete_dns.py --zone-id <ZONE_ID> --names-file names.txt --token $CLOUDFLARE_API_TOKEN

# Delete TXT records that contain the substring "legacy" in their name
python cf_bulk_delete_dns.py --zone-id <ZONE_ID> --type TXT --contains legacy

# Preview which A records would be deleted without making changes
python cf_bulk_delete_dns.py --zone-id <ZONE_ID> --type A --dry-run
```

## To-Do Application

This repository now includes a small command-line to-do list utility.

### Usage

```bash
python todo.py add "Buy milk"
python todo.py list
python todo.py done 1
```

Tasks are stored in `tasks.json`, which is ignored by git.
