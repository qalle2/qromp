# Warning: this script deletes files. Run at your own risk.
# TODO: more test cases for the IPS encoder

clear

rm -f test-out/*

echo "=== Create BPS patches ==="
python3 qromp_enc.py test-in-orig/megaman4u.nes test-in-patched/megaman4u-fin.nes test-out/megaman4u-fin.bps -v
python3 qromp_enc.py test-in-orig/smb2e.nes     test-in-patched/smb2e-fin.nes     test-out/smb2e-fin.bps
python3 qromp_enc.py test-in-orig/smb3e.nes     test-in-patched/smb3e-fin-bps.nes test-out/smb3e-fin.bps
echo
ls -l test-in-patch/*.bps
echo
ls -l test-out/*.bps
echo

echo "=== Verify BPS patches by applying them ==="
python3 qromp.py test-in-orig/megaman4u.nes test-out/megaman4u-fin.bps test-out/megaman4u-fin.nes
python3 qromp.py test-in-orig/smb2e.nes     test-out/smb2e-fin.bps     test-out/smb2e-fin.nes
python3 qromp.py test-in-orig/smb3e.nes     test-out/smb3e-fin.bps     test-out/smb3e-fin-bps.nes
diff test-in-patched/megaman4u-fin.nes test-out/megaman4u-fin.nes
diff test-in-patched/smb2e-fin.nes     test-out/smb2e-fin.nes
diff test-in-patched/smb3e-fin-bps.nes test-out/smb3e-fin-bps.nes
echo

echo "=== Create IPS patches ==="
python3 qromp_enc.py test-in-orig/ducktales-e.nes test-in-patched/ducktales-e-fin.nes test-out/ducktales-e-fin.ips -v
python3 qromp_enc.py test-in-orig/megaman2u.nes   test-in-patched/megaman2u-fin.nes   test-out/megaman2u-fin.ips
python3 qromp_enc.py test-in-orig/smb3e.nes       test-in-patched/smb3e-fin-ips.nes   test-out/smb3e-fin.ips
echo
ls -l test-in-patch/*.ips
echo
ls -l test-out/*.ips
echo

echo "=== Verify IPS patches by applying them ==="
python3 qromp.py test-in-orig/ducktales-e.nes test-out/ducktales-e-fin.ips test-out/ducktales-e-fin.nes
python3 qromp.py test-in-orig/megaman2u.nes   test-out/megaman2u-fin.ips   test-out/megaman2u-fin.nes
python3 qromp.py test-in-orig/smb3e.nes       test-out/smb3e-fin.ips       test-out/smb3e-fin-ips.nes
diff test-in-patched/ducktales-e-fin.nes test-out/ducktales-e-fin.nes
diff test-in-patched/megaman2u-fin.nes   test-out/megaman2u-fin.nes
diff test-in-patched/smb3e-fin-ips.nes   test-out/smb3e-fin-ips.nes
echo

echo "=== Four distinct errors ==="
python3 qromp_enc.py nonexistent            test-in-orig/smb1e.nes test-out/temp1.bps
python3 qromp_enc.py test-in-orig/smb1e.nes nonexistent            test-out/temp2.bps
python3 qromp_enc.py test-in-orig/smb1e.nes test-in-orig/smb1e.nes test-out/x.unsupported
python3 qromp_enc.py test-in-orig/smb1e.nes test-in-orig/smb1e.nes test-in-patch/nop.ips   # target already exists
echo
