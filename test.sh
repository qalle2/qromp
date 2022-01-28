# Warning: this script deletes files. Run at your own risk.
# .nes files: "e" = European, "u" = USA
# most patches are from Romhacking.net ("fin" = Finnish translation)
# "nop.ips" contains just "PATCHEOF"
# TODO: more test cases for the IPS encoder

clear

rm -f test-out/*

echo "=== Apply BPS patches ==="
# note: Mega Man 3 Finnish patch doesn't work with any ROM I have
python3 qromp.py test-in/megaman1u.nes test-in/megaman1u-fin.bps test-out/megaman1u-fin.nes
python3 qromp.py test-in/megaman4u.nes test-in/megaman4u-fin.bps test-out/megaman4u-fin.nes
python3 qromp.py test-in/smb1e.nes     test-in/smb1e-fin.bps     test-out/smb1e-fin.nes     -v
python3 qromp.py test-in/smb2e.nes     test-in/smb2e-fin.bps     test-out/smb2e-fin.nes
python3 qromp.py test-in/smb3e.nes     test-in/smb3e-fin.bps     test-out/smb3e-fin-bps.nes
echo

echo "=== Apply IPS patches ==="
# note: expected CRCs of output files are from files patched with Romhacking.net online patcher
python3 qromp.py test-in/ducktales-e.nes test-in/ducktales-e-fin.ips test-out/ducktales-e-fin.nes -i e3202b75 -o d776dd64 -v
python3 qromp.py test-in/megaman2u.nes   test-in/megaman2u-fin.ips   test-out/megaman2u-fin.nes   -i 5e268761 -o b094f9a6
python3 qromp.py test-in/smb3e.nes       test-in/smb3e-fin.ips       test-out/smb3e-fin-ips.nes   -i 3bc2e2df -o 89bcc1f9
python3 qromp.py test-in/smb3u.nes       test-in/smb3u-marioadv.ips  test-out/smb3u-marioadv.nes  -i 0B742B33 -o 2E6D3FDC  # uppercase CRCs
python3 qromp.py test-in/smb3u.nes       test-in/smb3u-mix.ips       test-out/smb3u-mix.nes       -i 0b742b33 -o 16b3fe50
python3 qromp.py test-in/smb1e.nes       test-in/nop.ips             test-out/smb1e-nop.nes       -i 7d5faa58 -o 7d5faa58  # no change
echo

echo "=== Create BPS patches ==="
python3 qromp.py -mc test-in/megaman4u.nes test-out/megaman4u-fin.nes test-out/megaman4u-fin.bps -v
python3 qromp.py -mc test-in/smb2e.nes     test-out/smb2e-fin.nes     test-out/smb2e-fin.bps
python3 qromp.py -mc test-in/smb3e.nes     test-out/smb3e-fin-bps.nes test-out/smb3e-fin.bps
ls -l test-in/*.bps test-out/*.bps
echo

echo "=== Verify created BPS patches ==="
python3 qromp.py test-in/megaman4u.nes test-out/megaman4u-fin.bps test-out/megaman4u-fin2.nes
python3 qromp.py test-in/smb2e.nes     test-out/smb2e-fin.bps     test-out/smb2e-fin2.nes
python3 qromp.py test-in/smb3e.nes     test-out/smb3e-fin.bps     test-out/smb3e-fin-bps2.nes
diff test-out/megaman4u-fin.nes test-out/megaman4u-fin2.nes
diff test-out/smb2e-fin.nes     test-out/smb2e-fin2.nes
diff test-out/smb3e-fin-bps.nes test-out/smb3e-fin-bps2.nes
echo

echo "=== Create IPS patches ==="
python3 qromp.py -mc test-in/ducktales-e.nes test-out/ducktales-e-fin.nes test-out/ducktales-e-fin.ips -v
python3 qromp.py -mc test-in/megaman2u.nes   test-out/megaman2u-fin.nes   test-out/megaman2u-fin.ips
python3 qromp.py -mc test-in/smb3e.nes       test-out/smb3e-fin-ips.nes   test-out/smb3e-fin.ips
ls -l test-in/*.ips test-out/*.ips
echo

echo "=== Verify created IPS patches ==="
python3 qromp.py test-in/ducktales-e.nes test-out/ducktales-e-fin.ips test-out/ducktales-e-fin2.nes
python3 qromp.py test-in/megaman2u.nes   test-out/megaman2u-fin.ips   test-out/megaman2u-fin2.nes
python3 qromp.py test-in/smb3e.nes       test-out/smb3e-fin.ips       test-out/smb3e-fin-ips2.nes
diff test-out/ducktales-e-fin.nes test-out/ducktales-e-fin2.nes
diff test-out/megaman2u-fin.nes   test-out/megaman2u-fin2.nes
diff test-out/smb3e-fin-ips.nes   test-out/smb3e-fin-ips2.nes
echo

echo "=== Five errors ==="
python3 qromp.py x                 x.bps                 test-out/a        -i xxxxxxxx
python3 qromp.py x                 x                     test-out/b
python3 qromp.py x                 x.ips                 test-out/c
python3 qromp.py test-in/smb1e.nes x.bps                 test-out/d
python3 qromp.py test-in/smb1e.nes test-in/smb1e-fin.bps test-in/smb1e.nes
echo

echo "=== One error ==="
python3 qromp.py test-in/smb1e.nes test-in/ducktales-e-fin.ips test-out/e
echo

echo "=== Three warnings ==="
python3 qromp.py test-in/ducktales-e.nes test-in/smb1e-fin.bps test-out/f
echo

echo "=== Four CRC warnings ==="
python3 qromp.py test-in/ducktales-e.nes test-in/megaman1u-fin.bps   test-out/i
python3 qromp.py test-in/ducktales-e.nes test-in/ducktales-e-fin.ips test-out/j -i deadbeef -o deadbeef
echo
