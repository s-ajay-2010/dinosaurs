import subprocess, re, datetime, sys

def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

changed = sh("git diff --name-only origin/main...HEAD").splitlines()

results = []
ok = True

def check(name, passed, detail=""):
    global ok
    ok = ok and passed
    results.append(f"- {'✅' if passed else '❌'} {name}" + (f": {detail}" if detail else ""))

# 1. only README + one new image file changed
img_ext = (".png", ".jpg", ".jpeg", ".gif")
non_readme_img = [f for f in changed if f != "README.md" and not f.lower().endswith(img_ext)]
check("No other git changes", len(non_readme_img) == 0, ", ".join(non_readme_img))

imgs = [f for f in changed if f.lower().endswith(img_ext)]
check("Exactly one new image added", len(imgs) == 1, str(imgs))

# 2. README diff: exactly 3 lines added (caption, blank, image embed), none removed
readme_diff = sh("git diff origin/main...HEAD -- README.md")
added = [l[1:] for l in readme_diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
removed = [l for l in readme_diff.splitlines() if l.startswith("-") and not l.startswith("---")]
check("Exactly 3 lines added to README (caption, blank, image), none removed",
      len(added) == 3 and len(removed) == 0,
      f"{len(added)} added, {len(removed)} removed")

# 3. those 3 lines follow the "caption" / blank / "![](path)" pattern, and the
# image line matches the new file added in this PR
if len(added) == 3 and imgs:
    caption, blank, img_line = added
    check("Caption line is quoted text", bool(re.match(r'^".+"$', caption.strip())), caption)
    check("Second line is blank", blank.strip() == "", repr(blank))
    check("Third line is a valid image embed matching the new file",
          img_line.strip() == f"![]({imgs[0]})", img_line)
elif not imgs:
    check("README entry matches new image", False, "no image file found in PR")

# 4. new entry was inserted right after the divider (top of the list), not elsewhere
diff_lines = readme_diff.splitlines()
hunk_headers = [l for l in diff_lines if l.startswith("@@")]
check("New entry inserted at top of list (right after divider)",
      len(hunk_headers) == 1, f"{len(hunk_headers)} separate diff hunks found — entry should be one contiguous insertion at the top")

# 4. image lives in <Year>/<Month Name>/ folder, current month (1-day forgiveness)
MONTHS = ["January","February","March","April","May","June","July",
          "August","September","October","November","December"]

if imgs:
    p = imgs[0]
    parts = p.split("/")
    today = datetime.date.today()
    valid = {(str(today.year), MONTHS[today.month - 1])}
    if today.day == 1:
        prev = today.replace(day=1) - datetime.timedelta(days=1)
        valid.add((str(prev.year), MONTHS[prev.month - 1]))
    if len(parts) >= 3:
        year, month = parts[0], parts[1]
        check("Image is in correct Year/Month folder (or forgiven)",
              (year, month) in valid, f"found {year}/{month}, expected one of {valid}")
    else:
        check("Image is inside a Year/Month folder", False, p)

with open("comment.md", "w") as f:
    f.write("## Dino PR Check Results\n\n")
    f.write("\n".join(results))
    f.write(f"\n\n**Overall: {'✅ All checks passed' if ok else '❌ Some checks failed'}**")

sys.exit(0 if ok else 1)
