"""Cloudflare DNS bulk deletion utility.

This script uses the Cloudflare API to find DNS records in a zone and delete
those that match a set of filters. It avoids external dependencies by using
the Python standard library for HTTP requests.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Iterable, List, Optional

API_BASE_URL = "https://api.cloudflare.com/client/v4"
PAGE_SIZE = 100
USER_AGENT = "cf-bulk-delete/1.0"


class CloudflareAPIError(RuntimeError):
    """Raised when the Cloudflare API returns an error response."""


class CloudflareClient:
    def __init__(self, token: str):
        self._token = token

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, object]] = None,
        data: Optional[Dict[str, object]] = None,
    ) -> Dict[str, object]:
        url = f"{API_BASE_URL}{path}"
        if params:
            query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            url = f"{url}?{query}" if query else url

        body: Optional[bytes] = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")

        request = urllib.request.Request(url, data=body, method=method.upper())
        request.add_header("Authorization", f"Bearer {self._token}")
        request.add_header("Content-Type", "application/json")
        request.add_header("User-Agent", USER_AGENT)

        try:
            with urllib.request.urlopen(request) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")
            raise CloudflareAPIError(
                f"HTTP {exc.code} error for {method} {path}: {error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise CloudflareAPIError(f"Network error while calling Cloudflare: {exc}") from exc

        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise CloudflareAPIError(
                f"Failed to decode Cloudflare response as JSON: {payload[:200]}"
            ) from exc

    def list_dns_records(
        self, zone_id: str, *, record_type: Optional[str] = None, page: int = 1
    ) -> Dict[str, object]:
        return self.request(
            "GET",
            f"/zones/{zone_id}/dns_records",
            params={"per_page": PAGE_SIZE, "page": page, "type": record_type},
        )

    def delete_dns_record(self, zone_id: str, record_id: str) -> Dict[str, object]:
        return self.request("DELETE", f"/zones/{zone_id}/dns_records/{record_id}")


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bulk delete Cloudflare DNS records based on filters.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--token",
        help="Cloudflare API token. Falls back to the CLOUDFLARE_API_TOKEN env var.",
    )
    parser.add_argument(
        "--zone-id",
        required=True,
        help="Cloudflare Zone identifier (can be found in the dashboard).",
    )
    parser.add_argument(
        "--name",
        action="append",
        default=[],
        help=(
            "Exact DNS record name to delete. Can be specified multiple times."
            " Mutually exclusive with --names-file."
        ),
    )
    parser.add_argument(
        "--names-file",
        help="Path to a file with one DNS record name per line to delete.",
    )
    parser.add_argument(
        "--contains",
        help="Delete records whose name contains this substring.",
    )
    parser.add_argument(
        "--type",
        help="Optional DNS record type to filter on (e.g., A, CNAME, TXT).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which records would be deleted without performing deletion.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation and proceed with deletion.",
    )
    return parser.parse_args(argv)


def load_names_from_file(path: str) -> List[str]:
    names: List[str] = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith("#"):
                    names.append(line)
    except OSError as exc:
        raise SystemExit(f"Failed to read names file '{path}': {exc}") from exc
    return names


def get_auth_token(args: argparse.Namespace) -> str:
    token = args.token or os.getenv("CLOUDFLARE_API_TOKEN")
    if not token:
        raise SystemExit(
            "Cloudflare API token not provided. Use --token or set "
            "CLOUDFLARE_API_TOKEN."
        )
    return token


def fetch_dns_records(
    client: CloudflareClient, zone_id: str, *, record_type: Optional[str] = None
) -> List[Dict[str, object]]:
    page = 1
    records: List[Dict[str, object]] = []
    while True:
        payload = client.list_dns_records(zone_id, record_type=record_type, page=page)
        if not payload.get("success"):
            raise CloudflareAPIError(f"Cloudflare API error: {payload.get('errors')}")
        records.extend(payload.get("result", []))
        result_info = payload.get("result_info", {})
        if page >= result_info.get("total_pages", 0):
            break
        page += 1
    return records


def filter_records(
    records: Iterable[Dict[str, object]],
    *,
    exact_names: Optional[Iterable[str]] = None,
    contains: Optional[str] = None,
) -> List[Dict[str, object]]:
    exact_set = {name.lower() for name in exact_names or []}
    contains_lower = contains.lower() if contains else None

    filtered: List[Dict[str, object]] = []
    for record in records:
        name = str(record.get("name", "")).lower()
        if exact_set and name not in exact_set:
            continue
        if contains_lower and contains_lower not in name:
            continue
        filtered.append(record)
    return filtered


def confirm(records: List[Dict[str, object]], *, assume_yes: bool) -> bool:
    if not records:
        print("No matching records found.")
        return False

    print("The following records will be deleted:")
    print("ID".ljust(36), "TYPE".ljust(6), "NAME".ljust(40), "CONTENT")
    print("-" * 110)
    for record in records:
        rid = str(record.get("id", ""))
        rtype = str(record.get("type", ""))
        name = str(record.get("name", ""))
        content = str(record.get("content", ""))
        print(rid.ljust(36), rtype.ljust(6), name.ljust(40), content)

    if assume_yes:
        return True

    answer = input("Proceed with deletion? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def delete_records(
    client: CloudflareClient, zone_id: str, records: Iterable[Dict[str, object]]
) -> None:
    for record in records:
        record_id = str(record.get("id", ""))
        name = record.get("name", "<unknown>")
        if not record_id:
            print(f"Skipping record without ID: {record}")
            continue
        try:
            payload = client.delete_dns_record(zone_id, record_id)
        except CloudflareAPIError as exc:
            print(f"Failed to delete {name} ({record_id}): {exc}", file=sys.stderr)
            continue
        if not payload.get("success"):
            print(
                f"Cloudflare API reported failure deleting {name} ({record_id}):"
                f" {payload.get('errors')}",
                file=sys.stderr,
            )
            continue
        print(f"Deleted {name} ({record_id}).")


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)

    if args.name and args.names_file:
        print("Specify either --name multiple times or --names-file, not both.")
        return 2

    names = list(args.name)
    if args.names_file:
        names.extend(load_names_from_file(args.names_file))

    token = get_auth_token(args)
    client = CloudflareClient(token)

    try:
        records = fetch_dns_records(client, args.zone_id, record_type=args.type)
    except CloudflareAPIError as exc:
        print(exc, file=sys.stderr)
        return 1

    filtered_records = filter_records(records, exact_names=names or None, contains=args.contains)

    if args.dry_run:
        confirm(filtered_records, assume_yes=True)
        return 0

    if not confirm(filtered_records, assume_yes=args.yes):
        print("Aborted.")
        return 0

    delete_records(client, args.zone_id, filtered_records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
