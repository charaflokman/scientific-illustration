#!/usr/bin/env python3
"""Generate or correct an image with a Google Gemini image model. Claude writes the prompt and checks the result.

  python gemini_image.py "prompt or path/to/prompt.txt" -o out.png
  python gemini_image.py "Change only: correct the spelling of ..." --edit draft.png -o draft_v2.png

The key comes from GEMINI_API_KEY only, never from an argument or a file in the project. The API needs a project with
billing (the free tier has a limit of 0 for image models). Without it, use the Gemini website: see SKILL.md.
Writes <out>.provenance.json (model, prompt, source image) so the AI origin of the image stays on record.
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", help="prompt text, or a path to a text file")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--edit", help="existing image to correct")
    ap.add_argument("--model", default="gemini-3-pro-image")
    a = ap.parse_args()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY is not set. Set it, or use the Gemini website (see SKILL.md).")
    is_file = len(a.prompt) < 260 and Path(a.prompt).is_file()
    prompt = Path(a.prompt).read_text(encoding="utf-8") if is_file else a.prompt
    parts = [{"text": prompt}]
    if a.edit:
        mime = "image/jpeg" if a.edit.lower().endswith((".jpg", ".jpeg")) else "image/png"
        parts.append({"inlineData": {"mimeType": mime, "data": base64.b64encode(Path(a.edit).read_bytes()).decode()}})
    body = {"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["IMAGE"]}}
    rq = urllib.request.Request(API.format(a.model), json.dumps(body).encode(),
                                {"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        d = json.load(urllib.request.urlopen(rq, timeout=300))
    except urllib.error.HTTPError as e:
        msg = json.loads(e.read() or b"{}").get("error", {}).get("message", "")[:300]
        hint = " Image models need billing on this project; otherwise use the Gemini website." if e.code == 429 else ""
        sys.exit(f"Gemini API error {e.code}: {msg}{hint}")
    for part in d.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            out = Path(a.out)
            out.write_bytes(base64.b64decode(part["inlineData"]["data"]))
            Path(str(out) + ".provenance.json").write_text(json.dumps(
                {"generator": a.model, "ai_generated": True, "prompt": prompt, "edited_from": a.edit}, ensure_ascii=False, indent=1),
                encoding="utf-8")
            print("Image:", out.resolve())
            return
    sys.exit("No image returned: " + json.dumps(d)[:300])


if __name__ == "__main__":
    main()
