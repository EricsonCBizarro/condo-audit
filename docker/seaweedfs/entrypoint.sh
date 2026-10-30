#!/bin/sh
# Single-node SeaweedFS with its S3 gateway. Credentials come from the
# environment and are written to the S3 identity file at start-up.
set -eu
: "${S3_ACCESS_KEY:?S3_ACCESS_KEY is required}"
: "${S3_SECRET_KEY:?S3_SECRET_KEY is required}"
cat > /tmp/s3.json <<JSON
{"identities":[{"name":"app","credentials":[{"accessKey":"${S3_ACCESS_KEY}","secretKey":"${S3_SECRET_KEY}"}],"actions":["Admin","Read","Write","List","Tagging"]}]}
JSON
exec weed server -dir=/data -s3 -s3.config=/tmp/s3.json -master.volumeSizeLimitMB=256 -volume.max=0
