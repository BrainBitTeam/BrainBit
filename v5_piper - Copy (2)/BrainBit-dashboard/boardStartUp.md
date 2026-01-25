To communicate via sftp, after each boot you --must-- give the following cmd in target terminal (procomm, mobaxterm, any ai agent you want to connect the target)

sudo ifconfig eth0 192.168.1.11 netmask 255.255.255.0 up

--in addition--

make sure 192.168.1.50 is added to the network interface as a gateway. (control panel -> network and sharing center -> change adapter settings -> <relevant ethernet connection> -> properties -> internet protocol version4 -> 
properties -> <insert to default gateway>



