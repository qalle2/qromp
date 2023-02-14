# Tests qromp_ips.py.
# Warning: this script deletes files. Run at your own risk.
# .nes files: "e" = European, "u" = USA.
# Most patches are from Romhacking.net ("fin" = Finnish translation).
# "nop.ips" contains just "PATCHEOF".

clear
rm -f test-out/*.nes

echo "=== Applying IPS patches (1 verbosely) ==="
python3 qromp_ips.py test-in-orig/ducktales-e.nes \
    test-in-patch/ducktales-e-fin.ips test-out/ducktales-e-fin.nes -v
python3 qromp_ips.py test-in-orig/megaman2u.nes \
    test-in-patch/megaman2u-fin.ips test-out/megaman2u-fin.nes
python3 qromp_ips.py test-in-orig/smb1e.nes \
    test-in-patch/nop.ips test-out/smb1e-nop.nes
python3 qromp_ips.py test-in-orig/smb3e.nes \
    test-in-patch/smb3e-fin.ips test-out/smb3e-fin.nes
python3 qromp_ips.py test-in-orig/smb3u.nes \
    test-in-patch/smb3u-marioadv.ips test-out/smb3u-marioadv.nes
python3 qromp_ips.py test-in-orig/smb3u.nes \
    test-in-patch/smb3u-mix.ips test-out/smb3u-mix.nes
echo

echo "=== Verifying patched files ==="
md5sum -c --quiet test-dec-ips.md5
echo

echo "=== Four distinct errors ==="
python3 qromp_ips.py nonexistent test-in-patch/nop.ips test-out/temp1.nes
python3 qromp_ips.py test-in-orig/smb1e.nes nonexistent test-out/temp2.nes
python3 qromp_ips.py test-in-orig/smb1e.nes test-in-patch/nop.ips \
    test-in-patch/nop.ips  # already exists
python3 qromp_ips.py test-in-orig/smb1e.nes test-in-patch/ducktales-e-fin.ips \
    test-out/temp3.nes  # write past EOF
echo
