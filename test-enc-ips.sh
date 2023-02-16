# Tests qromp_enc_ips.py. Assumes that qromp_ips.py works correctly.
# Warning: this script deletes files. Run at your own risk.

clear
rm -f test-out/*

echo "=== Creating IPS patches ==="
python3 qromp_enc_ips.py test-in-orig/ducktales-e.nes test-in-patched/ducktales-e-fin.nes test-out/ducktales-e-fin.ips
python3 qromp_enc_ips.py test-in-orig/ducktales-e.nes test-in-patched/ducktales-e-fin.nes test-out/ducktales-e-fin-u2.ips --max-unchg 2
python3 qromp_enc_ips.py test-in-orig/empty           test-in-orig/1k-zeroes              test-out/empty-to-1k-zeroes.ips
python3 qromp_enc_ips.py test-in-orig/empty           test-in-orig/empty                  test-out/empty-nop.ips
python3 qromp_enc_ips.py test-in-orig/megaman2u.nes   test-in-patched/megaman2u-fin.nes   test-out/megaman2u-fin.ips
python3 qromp_enc_ips.py test-in-orig/smb1e.nes       test-in-patched/smb1e-fin.nes       test-out/smb1e-fin.ips
python3 qromp_enc_ips.py test-in-orig/smb3e.nes       test-in-patched/smb3e-fin-ips.nes   test-out/smb3e-fin.ips
python3 qromp_enc_ips.py test-in-orig/smb3u.nes       test-in-patched/smb3u-marioadv.nes  test-out/smb3u-marioadv.ips
python3 qromp_enc_ips.py test-in-orig/smb3u.nes       test-in-patched/smb3u-mix.nes       test-out/smb3u-mix.ips
echo "Original:"
ls -l test-in-ips/
echo "Created:"
ls -l test-out/*.ips
echo

echo "=== Applying IPS patches, verifying patched files ==="
python3 qromp_ips.py test-in-orig/ducktales-e.nes test-out/ducktales-e-fin.ips    test-out/ducktales-e-fin.nes
python3 qromp_ips.py test-in-orig/ducktales-e.nes test-out/ducktales-e-fin-u2.ips test-out/ducktales-e-fin-u2.nes
python3 qromp_ips.py test-in-orig/empty           test-out/empty-to-1k-zeroes.ips test-out/1k-zeroes
python3 qromp_ips.py test-in-orig/empty           test-out/empty-nop.ips          test-out/empty-nop
python3 qromp_ips.py test-in-orig/megaman2u.nes   test-out/megaman2u-fin.ips      test-out/megaman2u-fin.nes
python3 qromp_ips.py test-in-orig/smb1e.nes       test-out/smb1e-fin.ips          test-out/smb1e-fin.nes
python3 qromp_ips.py test-in-orig/smb3e.nes       test-out/smb3e-fin.ips          test-out/smb3e-fin.nes
python3 qromp_ips.py test-in-orig/smb3u.nes       test-out/smb3u-marioadv.ips     test-out/smb3u-marioadv.nes
python3 qromp_ips.py test-in-orig/smb3u.nes       test-out/smb3u-mix.ips          test-out/smb3u-mix.nes
md5sum -c --quiet test-enc-ips.md5
echo

echo "=== Four distinct errors ==="
# input1 not found, input2 not found, output already exists, input2 smaller
# than input1
python3 qromp_enc_ips.py nonexistent            test-in-orig/smb1e.nes test-out/temp1.ips
python3 qromp_enc_ips.py test-in-orig/smb1e.nes nonexistent            test-out/temp2.ips
python3 qromp_enc_ips.py test-in-orig/smb1e.nes test-in-orig/smb1e.nes test-in-ips/nop.ips
python3 qromp_enc_ips.py test-in-orig/smb2e.nes test-in-orig/smb1e.nes test-out/temp3.ips
echo
