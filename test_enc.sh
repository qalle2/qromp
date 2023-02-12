# Warning: this script deletes files. Run at your own risk.
# TODO: more test cases for the IPS encoder
# Note: can't test smb3u-marioadv and smb3u-mix because files of different size
# are not supported.

clear
rm -f test-out/*

echo "=== Create BPS patches (1 verbosely) ==="
python3 qromp_enc.py test-in-orig/megaman1u.nes \
    test-in-patched/megaman1u-fin.nes test-out/megaman1u-fin.bps
python3 qromp_enc.py test-in-orig/megaman4u.nes \
    test-in-patched/megaman4u-fin.nes test-out/megaman4u-fin.bps
python3 qromp_enc.py test-in-orig/smb1e.nes \
    test-in-patched/smb1e-fin.nes test-out/smb1e-fin.bps
python3 qromp_enc.py test-in-orig/smb2e.nes \
    test-in-patched/smb2e-fin.nes test-out/smb2e-fin.bps -v
python3 qromp_enc.py test-in-orig/smb3e.nes \
    test-in-patched/smb3e-fin-bps.nes test-out/smb3e-fin.bps
echo "Original:"
ls -l test-in-patch/*.bps
echo "Created:"
ls -l test-out/*.bps
echo

echo "=== Create IPS patches (1 verbosely) ==="
python3 qromp_enc.py test-in-orig/ducktales-e.nes \
    test-in-patched/ducktales-e-fin.nes test-out/ducktales-e-fin.ips
python3 qromp_enc.py test-in-orig/ducktales-e.nes \
    test-in-patched/ducktales-e-fin.nes test-out/ducktales-e-fin-u2-r4.ips \
    -u2 -r4
python3 qromp_enc.py test-in-orig/megaman2u.nes \
    test-in-patched/megaman2u-fin.nes test-out/megaman2u-fin.ips -v
python3 qromp_enc.py test-in-orig/smb3e.nes \
    test-in-patched/smb3e-fin-ips.nes test-out/smb3e-fin.ips
echo "Original:"
ls -l test-in-patch/*.ips
echo "Created:"
ls -l test-out/*.ips
echo

echo "=== Apply patches, verify patched files (2 missing files expected) ==="
# apply BPS
python3 qromp.py test-in-orig/megaman1u.nes \
    test-out/megaman1u-fin.bps test-out/megaman1u-fin.nes
python3 qromp.py test-in-orig/megaman4u.nes \
    test-out/megaman4u-fin.bps test-out/megaman4u-fin.nes
python3 qromp.py test-in-orig/smb1e.nes \
    test-out/smb1e-fin.bps test-out/smb1e-fin.nes
python3 qromp.py test-in-orig/smb2e.nes \
    test-out/smb2e-fin.bps test-out/smb2e-fin.nes
python3 qromp.py test-in-orig/smb3e.nes \
    test-out/smb3e-fin.bps test-out/smb3e-fin-bps.nes
# apply IPS
python3 qromp.py test-in-orig/ducktales-e.nes \
    test-out/ducktales-e-fin.ips test-out/ducktales-e-fin.nes
python3 qromp.py test-in-orig/ducktales-e.nes \
    test-out/ducktales-e-fin-u2-r4.ips test-out/ducktales-e-fin-u2-r4.nes
python3 qromp.py test-in-orig/megaman2u.nes \
    test-out/megaman2u-fin.ips test-out/megaman2u-fin.nes
python3 qromp.py test-in-orig/smb3e.nes \
    test-out/smb3e-fin.ips test-out/smb3e-fin-ips.nes
# verify
md5sum -c --quiet patched.md5
echo

echo "=== Five distinct errors ==="
python3 qromp_enc.py nonexistent \
    test-in-orig/smb1e.nes test-out/temp1.bps
python3 qromp_enc.py test-in-orig/smb1e.nes \
    nonexistent test-out/temp2.bps
python3 qromp_enc.py test-in-orig/smb1e.nes \
    test-in-orig/smb1e.nes test-out/x.unsupported
python3 qromp_enc.py test-in-orig/smb1e.nes \
    test-in-orig/smb1e.nes test-in-patch/nop.ips   # target already exists
python3 qromp_enc.py test-in-orig/smb1e.nes \
    test-in-orig/smb2e.nes test-out/temp2.bps  # different size
echo
