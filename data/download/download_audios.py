import os
import random
import sys
import subprocess
import time
import pandas as pd
from urllib.parse import urlparse, parse_qs

# YouTube doesn't publish an official rate-limit threshold -- this range is
# community practice, not a documented number. It only helps on an IP
# that YouTube already trusts (throttling avoidance); it does NOT fix the
# separate "Sign in to confirm you're not a bot" IP-reputation block seen
# from datacenter/cloud IPs, which can trigger on the very first request
# regardless of pacing.
MIN_DELAY_SECONDS = 3
MAX_DELAY_SECONDS = 8

def extract_video_id(youtube_url):
    parsed_url = urlparse(youtube_url)
    video_id = parse_qs(parsed_url.query).get('v')
    if video_id:
        return video_id[0]
    return None

# Function to download audio from YouTube
def download_youtube_content(base_output_path, video_id, youtube_url):
    # Define the output directory for this video ID
    output_dir = os.path.join(base_output_path, video_id)
    os.makedirs(output_dir, exist_ok=True)

    # Skip re-downloading if this video's audio is already here. The final
    # output is always {video_id}.wav (fixed by --audio-format wav below),
    # so this check is exact, not a guess -- without it, re-running this
    # script against a partially-downloaded corpus re-downloads and
    # re-converts every already-fetched file from scratch every time.
    expected_output = os.path.join(output_dir, f"{video_id}.wav")
    if os.path.exists(expected_output):
        print(f"Already downloaded, skipping: {expected_output}")
        return

    # Define the yt-dlp command. --sleep-requests adds a delay between
    # yt-dlp's own internal extraction requests (metadata/format lookups);
    # the delay *between separate videos* is the time.sleep() below, since
    # each invocation here only ever downloads one URL.
    yt_dlp_command = [
        'yt-dlp', '--retries', '5', '--no-check-certificate',
        '--extract-audio', '--audio-format', 'wav',
        '--output-na-placeholder', 'not_available',
        '--sleep-requests', '1',
        '-o', os.path.join(output_dir, '%(id)s.%(ext)s'),
        youtube_url]

    delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
    print(f"Sleeping {delay:.1f}s before downloading {youtube_url}")
    time.sleep(delay)

    # Run the command
    try:
        subprocess.run(yt_dlp_command, check=True)
        print(f"Downloaded and processed: {youtube_url}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to download {youtube_url}: {e}")

# Function to process metadata files in a given directory
def process_metadata_files(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('metadata.xlsx'):
                metadata_file_path = os.path.join(root, file)
                print(f"Processing metadata file: {metadata_file_path}")

                # Determine the speaker_id as the part of the path before 'metadata.xlsx'
                parts = metadata_file_path.split('/')
                metadata_index = parts.index('metadata.xlsx')
                speaker_id = parts[metadata_index - 1]
                print(f"Speaker ID: {speaker_id}")

                # Define base output path for this speaker
                base_output_path = os.path.join(directory, speaker_id)

                df = pd.read_excel(metadata_file_path)
                links = df['link'].tolist()

                for link in links:
                    video_id = extract_video_id(link)
                    if video_id:
                        # Define the output directory for this video ID
                        output_dir = os.path.join(base_output_path, video_id)
                        print(f"Output Directory: {output_dir}")
                        if not os.path.exists(output_dir):
                            os.makedirs(output_dir)
                        download_youtube_content(base_output_path, video_id, link)
                    else:
                        print(f"Video ID could not be extracted from {link}")

# Main script execution
if __name__ == "__main__":

    """
    This script processes metadata files containing YouTube links, extracts video IDs, and downloads the corresponding audio in WAV format using yt-dlp. 
    It organizes the audio files into directories based on speaker IDs and video IDs.

    Usage:
        python script.py <root_directory>

    The script expects subdirectories named 'PD' (Parkinson's Disease) and 'CN' (Control) within the root directory, each containing metadata.xlsx files with YouTube links.

    Functions:
    - extract_video_id(): Extracts YouTube video ID from a URL.
    - download_youtube_content(): Downloads audio from YouTube and saves it as a WAV file.
    - process_metadata_files(): Processes metadata files, downloads audio, and organizes files into speaker-specific folders.
    """

    if len(sys.argv) != 2:
        print("Usage: python script.py <root_directory>")
        sys.exit(1)
    #script is here: /export/b16/afavaro/parkceleb-publication/PARKCELEB/data/download
    root_directory = sys.argv[1] #/export/fs06/afavaro/parkceleb_zenodo/anonym_trial/

    # Directories to traverse
    subdirectories = ['PD', 'CN']
    for subdir in subdirectories:
        subdir_path = os.path.join(root_directory, subdir)
        if os.path.exists(subdir_path):
            process_metadata_files(subdir_path)
        else:
            print(f"Directory does not exist: {subdir_path}")
