# Tests qromp_enc_bps.py. Assumes that qromp_bps.py works correctly.
# Warning: this script deletes files. Run at your own risk.
# TODO: add smb3u-mix.bps back when the speed has been improved.

clear
rm -f test-out/*

echo "=== Creating BPS patches ==="
python3 qromp_enc_bps.py test-in-orig/empty         test-in-orig/1k-zeroes             test-out/empty-to-1k-zeroes.bps
python3 qromp_enc_bps.py test-in-orig/empty         test-in-orig/empty                 test-out/empty-nop.bps
python3 qromp_enc_bps.py test-in-orig/megaman1u.nes test-in-patched/megaman1u-fin.nes  test-out/megaman1u-fin.bps
python3 qromp_enc_bps.py test-in-orig/megaman4u.nes test-in-patched/megaman4u-fin.nes  test-out/megaman4u-fin.bps
python3 qromp_enc_bps.py test-in-orig/megaman4u.nes test-in-patched/megaman4u-fin.nes  test-out/megaman4u-fin-copy8.bps --min-copy 8
python3 qromp_enc_bps.py test-in-orig/smb1e.nes     test-in-patched/smb1e-fin.nes      test-out/smb1e-fin.bps
python3 qromp_enc_bps.py test-in-orig/smb2e.nes     test-in-patched/smb2e-fin.nes      test-out/smb2e-fin.bps
python3 qromp_enc_bps.py test-in-orig/smb3e.nes     test-in-patched/smb3e-fin-bps.nes  test-out/smb3e-fin.bps
python3 qromp_enc_bps.py test-in-orig/smb3u.nes     test-in-patched/smb3u-marioadv.nes test-out/smb3u-marioadv.bps --min-copy 16
echo "Original:"
ls -l test-in-bps/
echo "Created:"
ls -l test-out/*.bps
echo

echo "=== Applying BPS patches, verifying patched files ==="
python3 qromp_bps.py test-in-orig/empty         test-out/empty-to-1k-zeroes.bps  test-out/1k-zeroes
python3 qromp_bps.py test-in-orig/empty         test-out/empty-nop.bps           test-out/empty-nop
python3 qromp_bps.py test-in-orig/megaman1u.nes test-out/megaman1u-fin.bps       test-out/megaman1u-fin.nes
python3 qromp_bps.py test-in-orig/megaman4u.nes test-out/megaman4u-fin.bps       test-out/megaman4u-fin.nes
python3 qromp_bps.py test-in-orig/megaman4u.nes test-out/megaman4u-fin-copy8.bps test-out/megaman4u-fin-copy8.nes
python3 qromp_bps.py test-in-orig/smb1e.nes     test-out/smb1e-fin.bps           test-out/smb1e-fin.nes
python3 qromp_bps.py test-in-orig/smb2e.nes     test-out/smb2e-fin.bps           test-out/smb2e-fin.nes
python3 qromp_bps.py test-in-orig/smb3e.nes     test-out/smb3e-fin.bps           test-out/smb3e-fin.nes
python3 qromp_bps.py test-in-orig/smb3u.nes     test-out/smb3u-marioadv.bps      test-out/smb3u-marioadv.nes
md5sum -c --quiet test-enc-bps.md5
echo

echo "=== Three distinct errors ==="
# input1 not found, input2 not found, output already exists
python3 qromp_enc_bps.py nonexistent            test-in-orig/smb1e.nes test-out/temp1.bps
python3 qromp_enc_bps.py test-in-orig/smb1e.nes nonexistent            test-out/temp2.bps
python3 qromp_enc_bps.py test-in-orig/smb1e.nes test-in-orig/smb1e.nes test-in-ips/nop.ips
echo
