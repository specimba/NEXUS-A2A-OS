import os, filecmp

base = r'C:\Users\speci.000\Documents\NEXUS'
main_dir = os.path.join(base, 'nexus_os')
backups = [
    ('nexus_os_backup_untracked', os.path.join(base, 'nexus_os_backup_untracked')),
    ('nexus_os_shadow_backup', os.path.join(base, 'nexus_os_shadow_backup')),
    ('nexus_os_untracked_backup', os.path.join(base, 'nexus_os_untracked_backup')),
]

def get_files(root):
    result = set()
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        for fn in filenames:
            result.add(os.path.normpath(os.path.join(rel, fn)))
        for dn in dirnames:
            result.add(os.path.normpath(os.path.join(rel, dn)) + '/')
    return result

main_files = get_files(main_dir)
print(f"Main nexus_os: {len(main_files)} entries\n")

for bname, bpath in backups:
    if not os.path.exists(bpath):
        print(f"{bname}: DOES NOT EXIST\n")
        continue
    b_files = get_files(bpath)
    only_in_main = main_files - b_files
    only_in_backup = b_files - main_files
    common = main_files & b_files
    
    # Check if common files are identical
    identical = 0
    different = 0
    for f in common:
        if f.endswith('/'):
            identical += 1
            continue
        mp = os.path.join(main_dir, f)
        bp = os.path.join(bpath, f)
        if os.path.exists(mp) and os.path.exists(bp):
            try:
                if filecmp.cmp(mp, bp, shallow=False):
                    identical += 1
                else:
                    different += 1
            except:
                different += 1
    
    print(f"=== {bname} ({len(b_files)} entries) ===")
    print(f"  Identical to main: {identical}")
    print(f"  Different from main: {different}")
    print(f"  Only in backup (not in main): {len(only_in_backup)}")
    print(f"  Only in main (not in backup): {len(only_in_main)}")
    if only_in_backup:
        print(f"  Backup-only items (first 10):")
        for item in sorted(only_in_backup)[:10]:
            print(f"    {item}")
    print()
