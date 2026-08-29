"""Backfill upload_date sidecar files for videos downloaded before
download_audios.py started capturing them.

Walks a corpus root and, for every video that already has audio but is
missing its {video_id}_upload_date.txt sidecar, does a metadata-only
yt-dlp query (--skip-download -- no re-download of the actual audio) to
fetch and save just the upload date. Safe to re-run: already-backfilled
videos are skipped.

Usage:
    python data/download/backfill_upload_dates.py /path/to/input/ParkCeleb
"""

import os
import random
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from download_audios import MIN_DELAY_SECONDS, MAX_DELAY_SECONDS  # noqa: E402


def find_missing_dates(root_directory):
    """Yield (video_dir, video_id) for every video that has audio but no
    upload_date sidecar yet. A "video folder" is identified by containing
    a {foldername}.wav matching its own name (see download_audios.py's -o
    pattern) -- this excludes SPEAKER_XX segment folders one level down,
    which contain differently-named .wav files (timestamps, or
    recording_concatenated.wav), not {foldername}.wav."""
    for dirpath, _dirnames, filenames in os.walk(root_directory):
        video_id = os.path.basename(dirpath)
        if f"{video_id}.wav" not in filenames:
            continue
        date_path = os.path.join(dirpath, f"{video_id}_upload_date.txt")
        if os.path.exists(date_path):
            continue
        yield dirpath, video_id


def backfill_one(video_dir, video_id):
    marker = "UPLOAD_DATE:"
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    command = [
        "yt-dlp", "--skip-download", "--no-check-certificate",
        "--sleep-requests", "1",
        "--print", f"{marker}%(upload_date)s",
        youtube_url,
    ]

    delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
    print(f"Sleeping {delay:.1f}s before querying {youtube_url}")
    time.sleep(delay)

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to fetch metadata for {video_id}: {e}")
        return False

    for line in result.stdout.splitlines():
        if line.startswith(marker):
            upload_date = line[len(marker):].strip()
            date_path = os.path.join(video_dir, f"{video_id}_upload_date.txt")
            with open(date_path, "w") as f:
                f.write(upload_date)
            print(f"Saved upload date {upload_date} for {video_id}")
            return True

    print(f"Warning: no upload date found in yt-dlp output for {video_id}")
    return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python backfill_upload_dates.py <root_directory>")
        sys.exit(1)

    root_directory = sys.argv[1]
    targets = list(find_missing_dates(root_directory))
    print(f"Found {len(targets)} video(s) missing an upload date.")

    succeeded, failed = 0, 0
    for video_dir, video_id in targets:
        if backfill_one(video_dir, video_id):
            succeeded += 1
        else:
            failed += 1

    print(f"\nDone: {succeeded} succeeded, {failed} failed out of {len(targets)}.")


if __name__ == "__main__":
    main()
