# Tests qromp_enc_bps.py. Assumes that qromp.py works correctly.
# Warning: this script deletes files. Run at your own risk.
# Tests for error conditions are in IPS test script.
# TODO: add smb3u-mix.bps back when the speed has been improved.

clear
rm -f test-out/*.bps
rm -f test-out/*.nes

echo "=== Create BPS patches ==="
python3 qromp_enc_bps.py test-in-orig/megaman1u.nes \
    test-in-patched/megaman1u-fin.nes test-out/megaman1u-fin.bps
python3 qromp_enc_bps.py test-in-orig/megaman4u.nes \
    test-in-patched/megaman4u-fin.nes test-out/megaman4u-fin.bps
python3 qromp_enc_bps.py test-in-orig/megaman4u.nes \
    test-in-patched/megaman4u-fin.nes test-out/megaman4u-fin-copy8.bps \
    --min-copy 8
python3 qromp_enc_bps.py test-in-orig/smb1e.nes \
    test-in-patched/smb1e-fin.nes test-out/smb1e-fin.bps
python3 qromp_enc_bps.py test-in-orig/smb1e.nes \
    test-in-orig/smb1e.nes test-out/smb1e-nop.bps
python3 qromp_enc_bps.py test-in-orig/smb2e.nes \
    test-in-patched/smb2e-fin.nes test-out/smb2e-fin.bps
python3 qromp_enc_bps.py test-in-orig/smb3e.nes \
    test-in-patched/smb3e-fin-bps.nes test-out/smb3e-fin.bps
python3 qromp_enc_bps.py test-in-orig/smb3u.nes \
    test-in-patched/smb3u-marioadv.nes test-out/smb3u-marioadv.bps \
    --min-copy 16
echo "Original:"
ls -l test-in-patch/*.bps
echo "Created:"
ls -l test-out/*.bps
echo

echo "=== Apply BPS patches, verify patched files ==="
python3 qromp.py test-in-orig/megaman1u.nes \
    test-out/megaman1u-fin.bps test-out/megaman1u-fin.nes
python3 qromp.py test-in-orig/megaman4u.nes \
    test-out/megaman4u-fin.bps test-out/megaman4u-fin.nes
python3 qromp.py test-in-orig/megaman4u.nes \
    test-out/megaman4u-fin-copy8.bps test-out/megaman4u-fin-copy8.nes
python3 qromp.py test-in-orig/smb1e.nes \
    test-out/smb1e-fin.bps test-out/smb1e-fin.nes
python3 qromp.py test-in-orig/smb1e.nes \
    test-out/smb1e-nop.bps test-out/smb1e-nop.nes
python3 qromp.py test-in-orig/smb2e.nes \
    test-out/smb2e-fin.bps test-out/smb2e-fin.nes
python3 qromp.py test-in-orig/smb3e.nes \
    test-out/smb3e-fin.bps test-out/smb3e-fin.nes
python3 qromp.py test-in-orig/smb3u.nes \
    test-out/smb3u-marioadv.bps test-out/smb3u-marioadv.nes
md5sum -c --quiet test-enc-bps.md5
echo
