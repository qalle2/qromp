# Tests qromp_bps.py.
# Warning: this script deletes files. Run at your own risk.
# .nes files: "e" = European, "u" = USA.
# Most patches are from Romhacking.net ("fin" = Finnish translation).
# "empty-nop.bps" does nothing to an empty file; in hex:
#     42 50 53 31 80 80 80 00 00 00 00 00 00 00 00 93 1f d8 5e

clear
rm -f test-out/*

echo "=== Applying BPS patches (1 verbosely) ==="
python3 qromp_bps.py test-in-orig/empty         test-in-bps/empty-nop.bps     test-out/empty-nop
python3 qromp_bps.py test-in-orig/megaman1u.nes test-in-bps/megaman1u-fin.bps test-out/megaman1u-fin.nes
python3 qromp_bps.py test-in-orig/megaman4u.nes test-in-bps/megaman4u-fin.bps test-out/megaman4u-fin.nes
python3 qromp_bps.py test-in-orig/smb1e.nes     test-in-bps/smb1e-fin.bps     test-out/smb1e-fin.nes -v
python3 qromp_bps.py test-in-orig/smb2e.nes     test-in-bps/smb2e-fin.bps     test-out/smb2e-fin.nes
python3 qromp_bps.py test-in-orig/smb3e.nes     test-in-bps/smb3e-fin.bps     test-out/smb3e-fin.nes
echo

echo "=== Verifying patched files ==="
md5sum -c --quiet test-dec-bps.md5
echo

echo "=== Five distinct errors and one warning ==="
# input1 not found, input2 not found, output already exists, not a BPS file,
# read from invalid position
python3 qromp_bps.py nonexistent            test-in-bps/smb1e-fin.bps test-out/temp1.nes
python3 qromp_bps.py test-in-orig/smb1e.nes nonexistent.bps           test-out/temp2.nes
python3 qromp_bps.py test-in-orig/smb1e.nes test-in-bps/smb1e-fin.bps test-in-ips/nop.ips
python3 qromp_bps.py test-in-orig/smb1e.nes test-in-ips/nop.ips       test-out/temp3.nes
python3 qromp_bps.py test-in-orig/smb1e.nes test-in-bps/smb3e-fin.bps test-out/temp4.nes
echo

echo "=== Four distinct size/CRC warnings ==="
python3 qromp_bps.py test-in-orig/ducktales-e.nes test-in-bps/smb1e-corrupt.bps test-out/temp5.nes
echo
