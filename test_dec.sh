# Warning: this script deletes files. Run at your own risk.
# .nes files: "e" = European, "u" = USA.
# Most patches are from Romhacking.net ("fin" = Finnish translation).
# "nop.ips" contains just "PATCHEOF".
# Note: Mega Man 3 Finnish patch doesn't work with any ROM I have.

clear
rm -f test-out/*

echo "=== Apply BPS patches (1 verbosely) ==="
python3 qromp.py test-in-orig/megaman1u.nes \
    test-in-patch/megaman1u-fin.bps test-out/megaman1u-fin.nes
python3 qromp.py test-in-orig/megaman4u.nes \
    test-in-patch/megaman4u-fin.bps test-out/megaman4u-fin.nes
python3 qromp.py test-in-orig/smb1e.nes \
    test-in-patch/smb1e-fin.bps test-out/smb1e-fin.nes -v
python3 qromp.py test-in-orig/smb2e.nes \
    test-in-patch/smb2e-fin.bps test-out/smb2e-fin.nes
python3 qromp.py test-in-orig/smb3e.nes \
    test-in-patch/smb3e-fin.bps test-out/smb3e-fin-bps.nes
echo

echo "=== Apply IPS patches (1 verbosely) ==="
python3 qromp.py test-in-orig/ducktales-e.nes \
    test-in-patch/ducktales-e-fin.ips test-out/ducktales-e-fin.nes -v
python3 qromp.py test-in-orig/megaman2u.nes \
    test-in-patch/megaman2u-fin.ips test-out/megaman2u-fin.nes
python3 qromp.py test-in-orig/smb3e.nes \
    test-in-patch/smb3e-fin.ips test-out/smb3e-fin-ips.nes
python3 qromp.py test-in-orig/smb3u.nes \
    test-in-patch/smb3u-marioadv.ips test-out/smb3u-marioadv.nes
python3 qromp.py test-in-orig/smb3u.nes \
    test-in-patch/smb3u-mix.ips test-out/smb3u-mix.nes
python3 qromp.py test-in-orig/smb1e.nes \
    test-in-patch/nop.ips test-out/smb1e-nop.nes
echo

echo "=== Verify patched files (1 missing file expected) ==="
md5sum -c --quiet patched.md5
echo

echo "=== Five distinct errors ==="
python3 qromp.py nonexistent \
    test-in-patch/smb1e-fin.bps test-out/temp1.nes
python3 qromp.py test-in-orig/smb1e.nes \
    nonexistent.bps test-out/temp2.nes
python3 qromp.py test-in-orig/smb1e.nes \
    x.unsupported test-out/temp3.nes
python3 qromp.py test-in-orig/smb1e.nes \
    test-in-patch/smb1e-fin.bps test-in-orig/smb1e.nes  # already exists
python3 qromp.py test-in-orig/smb1e.nes \
    test-in-patch/ducktales-e-fin.ips test-out/temp5.nes  # write past EOF
echo

echo "=== Five size/CRC warnings ==="
python3 qromp.py test-in-orig/ducktales-e.nes \
    test-in-patch/smb1e-fin.bps test-out/temp6.nes
python3 qromp.py test-in-orig/ducktales-e.nes \
    test-in-patch/megaman1u-fin.bps test-out/temp7.nes
echo
