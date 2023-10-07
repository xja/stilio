#!/bin/sh

set -o errexit
set -o nounset

export DATABASE_URL="mysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE}"

mysql_ready() {
python << END
import sys
from playhouse.db_url import connect
try:
    db = connect("${DATABASE_URL}")
    db.connect()
    if not db.is_closed():
        db.close()
except Exception:
    sys.exit(-1)
sys.exit(0)
END
}

until mysql_ready; do
  >&2 echo 'Waiting for MySQL to become available...'
  sleep 1
done
>&2 echo 'MySQL is available'

exec "$@"
