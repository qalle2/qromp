# Tests qromp_ips.py.
# Warning: this script deletes files. Run at your own risk.
# .nes files: "e" = European, "u" = USA.
# Most patches are from Romhacking.net ("fin" = Finnish translation).
# "nop.ips" does nothing; it contains just "PATCHEOF".

clear
rm -f test-out/*

echo "=== Applying IPS patches (1 verbosely) ==="
python3 qromp_ips.py test-in-orig/ducktales-e.nes test-in-ips/ducktales-e-fin.ips test-out/ducktales-e-fin.nes -v
python3 qromp_ips.py test-in-orig/empty           test-in-ips/nop.ips             test-out/empty-nop
python3 qromp_ips.py test-in-orig/megaman2u.nes   test-in-ips/megaman2u-fin.ips   test-out/megaman2u-fin.nes
python3 qromp_ips.py test-in-orig/smb3e.nes       test-in-ips/smb3e-fin.ips       test-out/smb3e-fin.nes
python3 qromp_ips.py test-in-orig/smb3u.nes       test-in-ips/smb3u-marioadv.ips  test-out/smb3u-marioadv.nes
python3 qromp_ips.py test-in-orig/smb3u.nes       test-in-ips/smb3u-mix.ips       test-out/smb3u-mix.nes
echo

echo "=== Verifying patched files ==="
md5sum -c --quiet test-dec-ips.md5
echo

echo "=== Five distinct errors ==="
# input1 not found, input2 not found, output already exists, not an IPS file,
# write past EOF
python3 qromp_ips.py nonexistent            test-in-ips/nop.ips             test-out/temp1.nes
python3 qromp_ips.py test-in-orig/smb1e.nes nonexistent                     test-out/temp2.nes
python3 qromp_ips.py test-in-orig/smb1e.nes test-in-ips/nop.ips             test-in-ips/nop.ips
python3 qromp_ips.py test-in-orig/smb1e.nes test-in-bps/smb1e-fin.bps       test-out/temp3.nes
python3 qromp_ips.py test-in-orig/smb1e.nes test-in-ips/ducktales-e-fin.ips test-out/temp4.nes
echo
