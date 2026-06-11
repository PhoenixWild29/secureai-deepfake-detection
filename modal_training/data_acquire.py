"""Dataset acquisition + S3 organisation orchestration.

Several deepfake datasets are GATED behind access-request forms or competition
rules. This module does NOT attempt to bypass any access control. For gated
datasets it prints clear, correct instructions on how to request access and
where to place the downloaded data; it then provides helpers to VERIFY and
ORGANISE local data into the expected S3 layout:

    s3://secureai-deepfake-videos/datasets/<name>/{real,fake}/<identity>/<clip>...

For genuinely freely-scriptable data it can fetch automatically.

Expected layout (the contract every other module relies on):

    datasets/<name>/real/<identity>/<clip>.mp4        (videos)
    datasets/<name>/fake/<identity>/<clip>.mp4
    datasets/<name>/real/<identity>/<clip>/<frame>.png (pre-extracted frames)

boto3 is imported lazily so this module imports without AWS deps.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Access instructions for gated datasets
# ---------------------------------------------------------------------------
ACCESS_INSTRUCTIONS: Dict[str, str] = {
    "faceforensics": (
        "FaceForensics++ (gated):\n"
        "  1. Fill the access form linked from https://github.com/ondyari/FaceForensics\n"
        "     (Google form; academic/contact details required).\n"
        "  2. You will receive 'FaceForensics++ Dataset.py' (a download script) by email.\n"
        "  3. Run it to fetch the c23 (HQ) videos: \n"
        "       python download.py <out_dir> -d all -c c23 -t videos\n"
        "  4. Organise into: datasets/faceforensics/real/<identity>/<clip>.mp4\n"
        "     and             datasets/faceforensics/fake/<method>/<clip>.mp4\n"
        "     (original_sequences -> real ; manipulated_sequences -> fake).\n"
        "  5. Upload with sync_to_s3('faceforensics', <local_dir>)."
    ),
    "celeb_df_v2": (
        "Celeb-DF v2 (gated):\n"
        "  1. Request access via the Google form on the Celeb-DF GitHub\n"
        "     (https://github.com/yuezunli/celeb-deepfakeforensics).\n"
        "  2. Download Celeb-real, YouTube-real (-> real) and Celeb-synthesis (-> fake).\n"
        "  3. Organise into datasets/celeb_df_v2/{real,fake}/<id>/<clip>.mp4 \n"
        "     (the filename id NN in id<NN>_id<MM>_000n is the identity).\n"
        "  4. Upload with sync_to_s3('celeb_df_v2', <local_dir>)."
    ),
    "dfdc": (
        "DFDC (gated):\n"
        "  1. Accept the competition rules at\n"
        "     https://www.kaggle.com/c/deepfake-detection-challenge/rules\n"
        "     OR use the AWS open-data mirror if available to you.\n"
        "  2. Download the train/test mp4 chunks + metadata.json.\n"
        "  3. metadata.json gives label REAL/FAKE and 'original' for each clip;\n"
        "     map REAL->real, FAKE->fake, identity = the 'original' base name.\n"
        "  4. Organise into datasets/dfdc/{real,fake}/<identity>/<clip>.mp4 and\n"
        "     upload with sync_to_s3('dfdc', <local_dir>)."
    ),
    "diffusion": (
        "Diffusion faces (e.g. DiFF) — usually freely downloadable:\n"
        "  1. Obtain a diffusion-generated face set (DiFF, or generate with SD).\n"
        "  2. Real reference faces go in datasets/diffusion/real/<id>/...,\n"
        "     synthetic faces in datasets/diffusion/fake/<id>/...\n"
        "  3. These are typically already images, so kind='frames'.\n"
        "  4. Upload with sync_to_s3('diffusion', <local_dir>)."
    ),
}


def print_access_instructions(name: Optional[str] = None) -> None:
    """Print access instructions for one dataset, or all of them."""
    names = [name] if name else list(ACCESS_INSTRUCTIONS.keys())
    for n in names:
        print("=" * 72)
        print(ACCESS_INSTRUCTIONS.get(n, f"No instructions registered for '{n}'."))
    print("=" * 72)


# ---------------------------------------------------------------------------
# S3 helpers (boto3, lazy)
# ---------------------------------------------------------------------------
def _s3_client(region: str = "us-east-2"):
    import boto3
    # Credentials come from the Modal Secret 'aws-creds' (env vars) — never
    # hardcoded. boto3 picks up AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY /
    # AWS_REGION from the environment automatically.
    return boto3.client("s3", region_name=os.environ.get("AWS_REGION", region))


def list_s3_prefix(bucket: str, prefix: str, region: str = "us-east-2",
                   max_keys: int = 1000) -> List[str]:
    """List object keys under a bucket/prefix (first ``max_keys``)."""
    s3 = _s3_client(region)
    keys: List[str] = []
    token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": min(1000, max_keys)}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            keys.append(obj["Key"])
            if len(keys) >= max_keys:
                return keys
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return keys


def verify_dataset_present(bucket: str, name: str, region: str = "us-east-2") -> Dict:
    """Check that datasets/<name>/{real,fake} exist on S3 and count objects."""
    out = {"dataset": name, "bucket": bucket, "real": 0, "fake": 0, "ok": False}
    for label in ("real", "fake"):
        prefix = f"datasets/{name}/{label}/"
        try:
            keys = list_s3_prefix(bucket, prefix, region=region, max_keys=5000)
            out[label] = len(keys)
        except Exception as exc:
            out[f"{label}_error"] = str(exc)
    out["ok"] = out["real"] > 0 and out["fake"] > 0
    return out


def sync_to_s3(name: str, local_dir: str, bucket: str = "secureai-deepfake-videos",
               region: str = "us-east-2", dry_run: bool = False) -> int:
    """Upload a local dataset dir to datasets/<name>/... preserving structure.

    ``local_dir`` is expected to already contain real/ and fake/ subfolders
    (organise per the access instructions first). Returns the count uploaded.
    Idempotent-ish: re-uploads overwrite, but you can pass dry_run to preview.
    """
    s3 = _s3_client(region)
    uploaded = 0
    for root, _dirs, files in os.walk(local_dir):
        for fn in files:
            local_path = os.path.join(root, fn)
            rel = os.path.relpath(local_path, local_dir).replace(os.sep, "/")
            key = f"datasets/{name}/{rel}"
            if dry_run:
                print(f"[sync] would upload {local_path} -> s3://{bucket}/{key}")
            else:
                s3.upload_file(local_path, bucket, key)
            uploaded += 1
    print(f"[sync] {'(dry-run) ' if dry_run else ''}uploaded {uploaded} files for "
          f"'{name}' to s3://{bucket}/datasets/{name}/")
    return uploaded


def download_dataset_from_s3(name: str, dest_dir: str,
                             bucket: str = "secureai-deepfake-videos",
                             region: str = "us-east-2",
                             max_keys: int = 100000) -> int:
    """Download datasets/<name>/ from S3 into dest_dir, preserving layout.

    Used by the Modal worker if the data bucket is NOT mounted via
    CloudBucketMount (boto3 path). Returns the number of files downloaded.
    """
    s3 = _s3_client(region)
    prefix = f"datasets/{name}/"
    keys = list_s3_prefix(bucket, prefix, region=region, max_keys=max_keys)
    n = 0
    for key in keys:
        if key.endswith("/"):
            continue
        rel = key[len(prefix):]
        out_path = os.path.join(dest_dir, name, rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        s3.download_file(bucket, key, out_path)
        n += 1
    print(f"[acquire] downloaded {n} files for '{name}' from s3://{bucket}/{prefix}")
    return n


def acquire(config, names: Optional[List[str]] = None) -> Dict:
    """Top-level acquisition check across requested datasets.

    For each dataset: verify presence on S3; if missing and gated, print the
    access instructions. Returns a status dict. This is intentionally
    non-destructive — it never fabricates or bypasses gated data.
    """
    names = names or sorted(set(config.train_datasets) | set(config.test_datasets))
    status: Dict[str, Dict] = {}
    for n in names:
        spec = config.spec(n)
        present = verify_dataset_present(config.data_bucket, n, config.aws_region)
        status[n] = present
        if not present["ok"]:
            print(f"[acquire] '{n}' NOT fully present on S3 "
                  f"(real={present['real']}, fake={present['fake']}).")
            if spec.gated:
                print_access_instructions(n)
        else:
            print(f"[acquire] '{n}' present (real={present['real']}, "
                  f"fake={present['fake']}).")
    return status
