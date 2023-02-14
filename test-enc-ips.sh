# Tests qromp_enc_ips.py. Assumes that qromp.py works correctly.
# Warning: this script deletes files. Run at your own risk.

clear
rm -f test-out/*.ips
rm -f test-out/*.nes

echo "=== Create IPS patches ==="
python3 qromp_enc_ips.py test-in-orig/ducktales-e.nes \
    test-in-patched/ducktales-e-fin.nes test-out/ducktales-e-fin.ips
python3 qromp_enc_ips.py test-in-orig/ducktales-e.nes \
    test-in-patched/ducktales-e-fin.nes test-out/ducktales-e-fin-u2.ips \
    --max-unchg 2
python3 qromp_enc_ips.py test-in-orig/megaman2u.nes \
    test-in-patched/megaman2u-fin.nes test-out/megaman2u-fin.ips
python3 qromp_enc_ips.py test-in-orig/smb1e.nes \
    test-in-patched/smb1e-fin.nes test-out/smb1e-fin.ips
python3 qromp_enc_ips.py test-in-orig/smb1e.nes \
    test-in-orig/smb1e.nes test-out/smb1e-nop.ips
python3 qromp_enc_ips.py test-in-orig/smb3e.nes \
    test-in-patched/smb3e-fin-ips.nes test-out/smb3e-fin.ips
python3 qromp_enc_ips.py test-in-orig/smb3u.nes \
    test-in-patched/smb3u-marioadv.nes test-out/smb3u-marioadv.ips
python3 qromp_enc_ips.py test-in-orig/smb3u.nes \
    test-in-patched/smb3u-mix.nes test-out/smb3u-mix.ips
echo "Original:"
ls -l test-in-patch/*.ips
echo "Created:"
ls -l test-out/*.ips
echo

echo "=== Apply IPS patches, verify patched files ==="
python3 qromp.py test-in-orig/ducktales-e.nes \
    test-out/ducktales-e-fin.ips test-out/ducktales-e-fin.nes
python3 qromp.py test-in-orig/ducktales-e.nes \
    test-out/ducktales-e-fin-u2.ips test-out/ducktales-e-fin-u2.nes
python3 qromp.py test-in-orig/megaman2u.nes \
    test-out/megaman2u-fin.ips test-out/megaman2u-fin.nes
python3 qromp.py test-in-orig/smb1e.nes \
    test-out/smb1e-fin.ips test-out/smb1e-fin.nes
python3 qromp.py test-in-orig/smb1e.nes \
    test-out/smb1e-nop.ips test-out/smb1e-nop.nes
python3 qromp.py test-in-orig/smb3e.nes \
    test-out/smb3e-fin.ips test-out/smb3e-fin.nes
python3 qromp.py test-in-orig/smb3u.nes \
    test-out/smb3u-marioadv.ips test-out/smb3u-marioadv.nes
python3 qromp.py test-in-orig/smb3u.nes \
    test-out/smb3u-mix.ips test-out/smb3u-mix.nes
md5sum -c --quiet test-enc-ips.md5
echo

echo "=== Four distinct errors ==="
python3 qromp_enc_ips.py nonexistent \
    test-in-orig/smb1e.nes test-out/temp1.bps
python3 qromp_enc_ips.py test-in-orig/smb1e.nes \
    nonexistent test-out/temp2.bps
python3 qromp_enc_ips.py test-in-orig/smb1e.nes \
    test-in-orig/smb1e.nes test-in-patch/nop.ips   # target already exists
python3 qromp_enc_ips.py test-in-orig/smb2e.nes \
    test-in-orig/smb1e.nes test-out/x.ips  # file2 smaller than file1
echo
