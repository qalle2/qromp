# Tests qromp_bps.py.
# Warning: this script deletes files. Run at your own risk.
# .nes files: "e" = European, "u" = USA.
# Most patches are from Romhacking.net ("fin" = Finnish translation).

clear
rm -f test-out/*.nes

echo "=== Applying BPS patches (1 verbosely) ==="
python3 qromp_bps.py test-in-orig/megaman1u.nes \
    test-in-patch/megaman1u-fin.bps test-out/megaman1u-fin.nes
python3 qromp_bps.py test-in-orig/megaman4u.nes \
    test-in-patch/megaman4u-fin.bps test-out/megaman4u-fin.nes
python3 qromp_bps.py test-in-orig/smb1e.nes \
    test-in-patch/smb1e-fin.bps test-out/smb1e-fin.nes -v
python3 qromp_bps.py test-in-orig/smb2e.nes \
    test-in-patch/smb2e-fin.bps test-out/smb2e-fin.nes
python3 qromp_bps.py test-in-orig/smb3e.nes \
    test-in-patch/smb3e-fin.bps test-out/smb3e-fin.nes
echo

echo "=== Verifying patched files ==="
md5sum -c --quiet test-dec-bps.md5
echo

echo "=== Four distinct errors and one warning ==="
python3 qromp_bps.py nonexistent test-in-patch/smb1e-fin.bps \
    test-out/temp1.nes
python3 qromp_bps.py test-in-orig/smb1e.nes nonexistent.bps \
    test-out/temp2.nes
python3 qromp_bps.py test-in-orig/smb1e.nes test-in-patch/smb1e-fin.bps \
    test-in-patch/nop.ips  # already exists
python3 qromp_bps.py test-in-orig/smb1e.nes test-in-patch/smb3e-fin.bps \
    test-out/temp3.nes  # read from invalid position
echo

echo "=== Five size/CRC warnings ==="
python3 qromp_bps.py test-in-orig/ducktales-e.nes \
    test-in-patch/smb1e-fin.bps test-out/temp6.nes
python3 qromp_bps.py test-in-orig/ducktales-e.nes \
    test-in-patch/megaman1u-fin.bps test-out/temp7.nes
echo
