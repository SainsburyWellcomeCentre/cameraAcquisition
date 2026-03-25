"""
launch_cameras.py
-----------------
Launcher for BehaviourCamerasAcquisition.bonsai

- Prompts for Subject and Protocol at the terminal
- Builds all 6 output paths and passes them to Bonsai via --property flags
- After Bonsai exits, finds the files Bonsai wrote (which already have the
  start timestamp inserted by Bonsai's Suffix=Timestamp) and renames them
  to also include the end timestamp, e.g.:
    test_test_CameraAcqLeft2026-03-19T13_32_48_end20260319T133307.avi
"""

import subprocess
import sys
import os
import glob
from datetime import datetime, timezone

# ── Configuration ─────────────────────────────────────────────────────────────

BONSAI_EXE = r"C:\Users\harrislab\AppData\Local\Bonsai\Bonsai.exe"
WORKFLOW    = r"C:\Users\harrislab\Bonsai\BehaviourCamerasAcquisition.bonsai"
BASE_DIR    = r"C:\Users\harrislab\luminoseData"

CAMERAS = ["Left", "Right", "Body"]

# ── Helpers ───────────────────────────────────────────────────────────────────

def prompt(label):
    while True:
        value = input("  {}: ".format(label)).strip()
        if value:
            return value
        print("  [!] {} cannot be empty.".format(label))


def build_paths(subject, protocol):
    """Return dict of the 6 base paths (without Bonsai's timestamp suffix)."""
    session_dir = os.path.join(BASE_DIR, subject, "luminose_hf_videos", "Session Videos")
    prefix = "{}_{}".format(subject, protocol)
    paths = {}
    for cam in CAMERAS:
        paths["{}Video".format(cam)]     = os.path.join(session_dir, "{}_CameraAcq{}.avi".format(prefix, cam))
        paths["{}FrameData".format(cam)] = os.path.join(session_dir, "{}_CameraAcq{}.FrameData.bin".format(prefix, cam))
    return paths


def ensure_dirs(paths):
    dirs = set(os.path.dirname(p) for p in paths.values())
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def build_bonsai_args(paths):
    """Build the --property CLI arguments for Bonsai."""
    args = [BONSAI_EXE, WORKFLOW, "--start"]
    for prop, path in paths.items():
        args += ["--property", "{}={}".format(prop, path)]
    return args


def find_bonsai_file(base_path):
    """
    Find the file Bonsai actually wrote given the base path we passed in.
    Bonsai inserts the timestamp directly before the final extension, e.g.:
      base:   Subject_Protocol_CameraAcqLeft.avi
      actual: Subject_Protocol_CameraAcqLeft2026-03-19T13_32_48.avi
      base:   Subject_Protocol_CameraAcqLeft.FrameData.bin
      actual: Subject_Protocol_CameraAcqLeft.FrameData2026-03-19T13_32_48.bin
    """
    directory = os.path.dirname(base_path)
    basename  = os.path.basename(base_path)

    if basename.endswith(".FrameData.bin"):
        stem    = basename[:-len(".FrameData.bin")]
        pattern = os.path.join(directory, stem + ".FrameData*.bin")
    else:
        stem, ext = os.path.splitext(basename)
        pattern   = os.path.join(directory, stem + "*" + ext)

    matches = glob.glob(pattern)
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)


def append_end_timestamp(filepath, end_ts):
    """
    Rename file to append end timestamp before the final extension.
      Input:  Name.FrameData2026-03-19T13_32_48.bin
      Output: Name.FrameData2026-03-19T13_32_48_end20260319T133307.bin
      Input:  Name2026-03-19T13_32_48.avi
      Output: Name2026-03-19T13_32_48_end20260319T133307.avi
    """
    directory = os.path.dirname(filepath)
    basename  = os.path.basename(filepath)

    # Split off only the final extension (.bin or .avi)
    core, ext = os.path.splitext(basename)
    new_name  = core + "_end" + end_ts + ext
    new_path  = os.path.join(directory, new_name)
    os.rename(filepath, new_path)
    return new_path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n=== Behaviour Camera Acquisition Launcher ===\n")
    subject  = prompt("Subject")
    protocol = prompt("Protocol")

    paths = build_paths(subject, protocol)
    ensure_dirs(paths)

    print("\n  Output directory: {}".format(os.path.dirname(list(paths.values())[0])))
    print("  Files will be written as:")
    for name, path in paths.items():
        print("    [{}] {}".format(name, os.path.basename(path)))

    print("\n  Launching Bonsai... (stop the workflow and REMEMBER TO CLOSE BONSAI to finish)\n")

    bonsai_args = build_bonsai_args(paths)

    try:
        subprocess.run(bonsai_args, check=True)
    except FileNotFoundError:
        print("\n[ERROR] Bonsai executable not found at:\n  {}".format(BONSAI_EXE))
        print("  Edit BONSAI_EXE in this script to point to your Bonsai installation.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("\n[WARNING] Bonsai exited with code {}. Proceeding with rename.".format(e.returncode))

    # Record end timestamp immediately after Bonsai exits
    end_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    print("\n  Bonsai stopped. End timestamp: {}".format(end_ts))
    print("  Renaming output files to append end timestamp...\n")

    any_found = False
    for prop, base_path in paths.items():
        actual = find_bonsai_file(base_path)
        if actual is None:
            print("  [!] Could not find output file for {} -- skipping rename.".format(prop))
            print("      Searched: {}".format(os.path.dirname(base_path)))
            continue
        new_path = append_end_timestamp(actual, end_ts)
        print("  [{}] {}".format(prop, os.path.basename(actual)))
        print("       -> {}".format(os.path.basename(new_path)))
        any_found = True

    if not any_found:
        print("\n  [WARNING] No output files were found to rename.")
        print("  This can happen if Bonsai was stopped before any frames were written,")
        print("  or if the output directory differs from expected.")

    print("\n  Done.\n")


if __name__ == "__main__":
    main()
