
tar -cvzf netset.tar.gz \
arubacli.py \
ciscoios.py \
dellpc.py \
mylog.py \
openwrtuci.py \
pexpect_serial.py \
setup-network.py \
switchdevice.py \
parseclock.py \
requirements.txt \
readme.txt \
pack.sh \
runcmd.sh \
$NULL

scp netset.tar.gz root@home-pogoplug-v3-1:
