#!/usr/bin/env bash
# deploy/aws/backup-db.sh — dump the Postgres database to a compressed file,
# and optionally upload it to S3.
#
#   ./deploy/aws/backup-db.sh                    # writes backups/openrouter-<date>.sql.gz
#   S3_BACKUP_BUCKET=my-bucket ./deploy/aws/backup-db.sh   # also uploads to S3
#
# Automate it nightly at 03:15 with cron:
#   crontab -e
#   15 3 * * * /home/ubuntu/openrouter/deploy/aws/backup-db.sh >> /home/ubuntu/backup.log 2>&1

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE=(docker compose -f "$ROOT/deploy/aws/docker-compose.aws.yml" --env-file "$ROOT/.env.aws")

STAMP="$(date +%Y%m%d-%H%M%S)"
OUTDIR="$ROOT/backups"
OUTFILE="$OUTDIR/openrouter-$STAMP.sql.gz"
mkdir -p "$OUTDIR"

echo "==> Dumping database to $OUTFILE"
"${COMPOSE[@]}" exec -T postgres pg_dump -U openrouter openrouter | gzip > "$OUTFILE"
echo "    $(du -h "$OUTFILE" | cut -f1) written"

# keep the last 7 local backups
ls -1t "$OUTDIR"/openrouter-*.sql.gz | tail -n +8 | xargs -r rm --

if [ -n "${S3_BACKUP_BUCKET:-}" ]; then
  echo "==> Uploading to s3://$S3_BACKUP_BUCKET/"
  aws s3 cp "$OUTFILE" "s3://$S3_BACKUP_BUCKET/db-backups/" --only-show-errors
fi

echo "==> Done. Restore with:"
echo "    gunzip -c $OUTFILE | ${COMPOSE[*]} exec -T postgres psql -U openrouter openrouter"
